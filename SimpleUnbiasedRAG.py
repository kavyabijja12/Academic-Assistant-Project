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
        
        def score(doc):
            text = doc.page_content.lower()
            query_words = query_lower.split()
            matches = sum(1 for word in query_words if word in text)
            if query_lower in text:
                matches += len(query_words)
            return matches
        
        docs = sorted(docs, key=score, reverse=True)[:4]
        
        context = "\n\n".join(d.page_content for d in docs)
        sources = [f"Source {i+1}: {doc.metadata.get('source', 'Unknown')}" for i, doc in enumerate(docs)]
        
        prompt = f"""
You are an expert academic advisor for Arizona State University's Polytechnic School, specifically for the Information Technology program.

**Instructions:**
1. Answer the question using ONLY the provided context from ASU IT materials
2. Be specific and detailed when information is available
3. If asking about courses, include course codes, credits, and descriptions when available
4. If asking about requirements, provide specific details about prerequisites, GPA requirements, etc.
5. If asking about locations, specify campus locations and delivery methods (on-campus, online, hybrid)
6. Format your response clearly with bullet points or numbered lists when appropriate
7. If the information is not available in the context, clearly state "I couldn't find specific information about [topic] in the current ASU IT materials"
8. Always be helpful and encourage students to contact advisors for additional information

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
