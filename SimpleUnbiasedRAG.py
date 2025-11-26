#!/usr/bin/env python3
"""
RAG System using Gemini
- Uses Gemini for question answering
- Hybrid retrieval (FAISS + BM25)
- Sentence Transformers for embeddings
"""

import os
import time
import json
from dotenv import load_dotenv

# Fix tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
from langchain_community.vectorstores import FAISS as LangChainFAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from VectorStore import SentenceTransformerEmbeddings

load_dotenv()

class SimpleUnbiasedRAG:
    """RAG system using Gemini"""
    
    def __init__(self):
        # Initialize Gemini system
        self.gemini_system = GeminiSystem()
        
        # Simple stats
        self.stats = {"total_queries": 0}
        
    def load_systems(self):
        """Load Gemini system"""
        print("Loading RAG system...")
        
        gemini_loaded = self.gemini_system.load_system()
        
        if gemini_loaded:
            print("Gemini system loaded")
            
        return gemini_loaded
    
    def ask(self, query):
        """Get response from Gemini"""
        start_time = time.time()
        
        print(f"Processing: {query}")
        
        # Get Gemini response
        try:
            print("Getting Gemini response...")
            gemini_answer, gemini_docs, gemini_cached = self.gemini_system.ask(query)
            result = {
                "answer": gemini_answer,
                "docs": gemini_docs,
                "cached": gemini_cached,
                "model": "gemini",
                "total_time": time.time() - start_time
            }
            
            self.stats["total_queries"] += 1
            return result
        except Exception as e:
            print(f"Gemini failed: {e}")
            raise RuntimeError(f"Failed to get response: {e}")

# Same system classes as before (simplified)
class GeminiSystem:
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.embeddings = SentenceTransformerEmbeddings()
        self.model = genai.GenerativeModel("models/gemini-2.5-flash")
        self.db = None
        self.retriever = None
        self.response_cache = {}
    
    def load_system(self):
        try:
            self.db = LangChainFAISS.load_local(
                "vector_store/faiss_index_sentence_transformer",
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            texts = [d.page_content for d in self.db.docstore._dict.values()]
            
            bm25_cache_path = "vector_store/bm25_cache.pkl"
            import pickle
            
            if os.path.exists(bm25_cache_path):
                with open(bm25_cache_path, 'rb') as f:
                    bm25 = pickle.load(f)
            else:
                bm25 = BM25Retriever.from_texts(texts)
                with open(bm25_cache_path, 'wb') as f:
                    pickle.dump(bm25, f)
            
            bm25.k = 10
            faiss_retriever = self.db.as_retriever(search_kwargs={"k": 10})
            
            self.retriever = EnsembleRetriever(
                retrievers=[faiss_retriever, bm25],
                weights=[0.6, 0.4]
            )
            return True
        except Exception as e:
            print(f"Gemini system load failed: {e}")
            return False
    
    def ask(self, query):
        query_lower = query.lower()
        
        if query_lower in self.response_cache:
            return self.response_cache[query_lower], [], True
        
        docs = self.retriever.invoke(query)
        
        # Enhanced scoring function with metadata awareness
        def score(doc):
            text = doc.page_content.lower()
            metadata = doc.metadata or {}
            query_words = query_lower.split()
            
            # Base score: word matches
            matches = sum(1 for word in query_words if word in text)
            if query_lower in text:
                matches += len(query_words)
            
            # Boost for type relevance
            doc_type = metadata.get('type', '').lower()
            if 'specialization' in query_lower or 'focus area' in query_lower or 'concentration' in query_lower:
                if 'specialization' in doc_type or 'focus area' in doc_type:
                    matches += 5  # Significant boost for specialization-related chunks
            
            if 'course' in query_lower or 'class' in query_lower:
                if 'course' in doc_type:
                    matches += 3
            
            if 'requirement' in query_lower:
                if 'requirement' in doc_type:
                    matches += 3
            
            # Boost for program level match (if query mentions MS/BS)
            program_level = metadata.get('program_level', '')
            if 'ms' in query_lower or 'master' in query_lower or 'graduate' in query_lower:
                if program_level == 'ms':
                    matches += 2
            elif 'bs' in query_lower or 'bachelor' in query_lower or 'undergraduate' in query_lower:
                if program_level == 'bs':
                    matches += 2
            
            return matches
        
        # Sort by score
        docs = sorted(docs, key=score, reverse=True)
        
        # Add diversity: prefer chunks from different sources
        def add_diversity(docs_list, max_docs=10):
            """Select diverse chunks, preferring different sources"""
            selected = []
            seen_sources = set()
            
            # First pass: add high-scoring chunks from different sources
            for doc in docs_list:
                if len(selected) >= max_docs:
                    break
                source = doc.metadata.get('source', 'unknown')
                source_key = source.split('/')[-1] if '/' in source else source  # Use filename as key
                
                # Prefer chunks from sources we haven't seen yet
                if source_key not in seen_sources or len(selected) < max_docs // 2:
                    selected.append(doc)
                    seen_sources.add(source_key)
            
            # Second pass: fill remaining slots with highest scoring docs
            for doc in docs_list:
                if len(selected) >= max_docs:
                    break
                if doc not in selected:
                    selected.append(doc)
            
            return selected[:max_docs]
        
        # Use 8-10 chunks with diversity
        docs = add_diversity(docs, max_docs=10)
        
        # Build context with source labels for better LLM understanding
        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source', 'Unknown')
            doc_type = doc.metadata.get('type', 'general_text')
            # Clean source name for display
            source_name = source.split('/')[-1] if '/' in source else source
            source_name = source_name.replace('.txt', '').replace('_', ' ')
            
            context_parts.append(f"[Source {i} - {source_name} ({doc_type})]\n{doc.page_content}")
        
        context = "\n\n".join(context_parts)
        sources = [f"Source {i+1}: {doc.metadata.get('source', 'Unknown')}" for i, doc in enumerate(docs)]
        
        prompt = f"""
You are an expert academic assistant for Arizona State University's Polytechnic School, specifically for the Information Technology program.

**Instructions:**
1. Answer the question using ONLY the provided context from ASU IT materials
2. **IMPORTANT: Read through ALL context pieces and synthesize information across them. Do not rely on only a single snippet if others contain additional relevant information.**
3. **If the context mentions multiple relevant items (courses, requirements, specializations, focus areas, options, steps), list ALL of them. Do not omit any items that appear in the context.**
4. Be specific and detailed when information is available
5. If asking about courses, include course codes, credits, and descriptions when available
6. If asking about requirements, provide specific details about prerequisites, GPA requirements, etc.
7. If asking about locations, specify campus locations and delivery methods (on-campus, online, hybrid)
8. Format your response clearly with bullet points or numbered lists when appropriate
9. If the information is not available in the context, clearly state "I couldn't find specific information about [topic] in the current ASU IT materials"
10. **Before finalizing your answer, quickly verify: Did I use information from all relevant context pieces? Did I miss any items that should be included?**
11. Always be helpful and encourage students to contact advisors for additional information

**Context from ASU IT Materials:**
{context}

**Available Sources:**
{chr(10).join(sources)}

**Student Question:** {query}

**Academic Advisor Response:**"""
        
        response = self.model.generate_content(prompt)
        result = response.text
        
        self.response_cache[query_lower] = result
        return result, docs, False

# Test
if __name__ == "__main__":
    rag = SimpleUnbiasedRAG()
    success = rag.load_systems()
    
    if success:
        print("\nTesting RAG System")
        print("=" * 40)
        
        result = rag.ask("What are the core IT courses?")
        
        print(f"\nModel: {result['model'].upper()}")
        print(f"Answer: {result['answer'][:200]}...")
        print(f"Total Queries: {rag.stats['total_queries']}")
    else:
        print("Failed to load system")
