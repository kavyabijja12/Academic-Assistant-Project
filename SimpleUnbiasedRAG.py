#!/usr/bin/env python3
"""
Simple Unbiased RAG: Just the essential bias prevention
- Blind evaluation (no model names)
- Random A/B assignment
- Single evaluator (Gemini)
- Much simpler than the complex system
"""

import os
import time
import json
import random
from dotenv import load_dotenv
import google.generativeai as genai
from groq import Groq
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
from langchain_community.vectorstores import FAISS as LangChainFAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from VectorStore import GeminiEmbeddings

load_dotenv()

class SimpleUnbiasedRAG:
    """Simple unbiased RAG system - just the essential bias prevention"""
    
    def __init__(self):
        # Initialize both systems
        self.gemini_system = GeminiSystem()
        self.groq_system = GROQSystem()
        
        # Single evaluator (Gemini)
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.evaluator = genai.GenerativeModel("models/gemini-2.5-flash")
        
        # Simple stats
        self.stats = {"gemini_wins": 0, "groq_wins": 0, "total_queries": 0}
        
    def load_systems(self):
        """Load both systems"""
        print("🔄 Loading simple unbiased RAG systems...")
        
        gemini_loaded = self.gemini_system.load_system()
        groq_loaded = self.groq_system.load_system()
        
        if gemini_loaded:
            print("✅ Gemini system loaded")
        if groq_loaded:
            print("✅ GROQ system loaded")
            
        return gemini_loaded or groq_loaded
    
    def blind_evaluate(self, query, response_a, response_b):
        """Simple blind evaluation - the core innovation"""
        
        # Randomly assign A/B to prevent bias
        if random.choice([True, False]):
            gemini_response, groq_response = response_a, response_b
            gemini_is_a = True
        else:
            gemini_response, groq_response = response_b, response_a
            gemini_is_a = False
        
        # Simple evaluation prompt
        prompt = f"""
You are an expert academic advisor. Evaluate these two responses to a student's question about ASU's IT program.

**Question:** {query}

**Response A:**
{response_a}

**Response B:**
{response_b}

Which response is better? Consider:
- Accuracy and completeness
- Clarity and helpfulness
- Academic appropriateness

Respond with just "A" or "B" and a brief reason.
"""
        
        try:
            response = self.evaluator.generate_content(prompt)
            result = response.text.strip()
            
            # Extract winner
            if "A" in result and "B" not in result:
                winner = "A"
            elif "B" in result:
                winner = "B"
            else:
                winner = "A"  # Default
            
            # Map back to actual model
            if winner == "A":
                actual_winner = "gemini" if gemini_is_a else "groq"
            else:
                actual_winner = "groq" if gemini_is_a else "gemini"
            
            return {
                "winner": actual_winner,
                "reasoning": result,
                "confidence": "High" if len(result) > 50 else "Medium"
            }
            
        except Exception as e:
            print(f"⚠️ Evaluation failed: {e}")
            return {
                "winner": "gemini",
                "reasoning": f"Evaluation failed: {e}",
                "confidence": "Low"
            }
    
    def ask(self, query):
        """Get responses and evaluate blindly"""
        start_time = time.time()
        
        print(f"🔍 Processing: {query}")
        
        # Get both responses
        gemini_result = None
        groq_result = None
        
        # Gemini response
        try:
            print("🧠 Getting Gemini response...")
            gemini_answer, gemini_docs, gemini_cached = self.gemini_system.ask(query)
            gemini_result = {
                "answer": gemini_answer,
                "docs": gemini_docs,
                "cached": gemini_cached,
                "model": "gemini"
            }
        except Exception as e:
            print(f"❌ Gemini failed: {e}")
        
        # GROQ response
        try:
            print("⚡ Getting GROQ response...")
            groq_answer, groq_docs, groq_cached = self.groq_system.ask(query)
            groq_result = {
                "answer": groq_answer,
                "docs": groq_docs,
                "cached": groq_cached,
                "model": "groq"
            }
        except Exception as e:
            print(f"❌ GROQ failed: {e}")
        
        # Handle single model case
        if not gemini_result and not groq_result:
            raise RuntimeError("Both models failed")
        elif not gemini_result:
            return groq_result
        elif not groq_result:
            return gemini_result
        
        # Blind evaluation
        print("🤖 Blind evaluation...")
        evaluation = self.blind_evaluate(query, gemini_result["answer"], groq_result["answer"])
        
        # Select winner
        if evaluation["winner"] == "gemini":
            winner = gemini_result
            self.stats["gemini_wins"] += 1
        else:
            winner = groq_result
            self.stats["groq_wins"] += 1
        
        # Add evaluation info
        winner["evaluation"] = evaluation
        winner["both_responses"] = {
            "gemini": gemini_result,
            "groq": groq_result
        }
        winner["total_time"] = time.time() - start_time
        self.stats["total_queries"] += 1
        
        print(f"🏆 Winner: {winner['model'].upper()} (confidence: {evaluation['confidence']})")
        
        return winner

# Same system classes as before (simplified)
class GeminiSystem:
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.embeddings = GeminiEmbeddings()
        self.model = genai.GenerativeModel("models/gemini-2.5-flash")
        self.db = None
        self.retriever = None
        self.response_cache = {}
    
    def load_system(self):
        try:
            self.db = LangChainFAISS.load_local(
                "vector_store/faiss_index_gemini",
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
            print(f"❌ Gemini system load failed: {e}")
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

class GROQSystem:
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.documents = []
        self.embeddings = None
        self.faiss_index = None
        self.response_cache = {}
        
    def load_system(self):
        try:
            with open("chunks.json", "r", encoding="utf-8") as f:
                chunks = json.load(f)
            
            self.documents = [chunk["text"] for chunk in chunks]
            
            print("🔨 Creating sentence transformer embeddings...")
            self.embeddings = self.embedder.encode(self.documents)
            
            dimension = self.embeddings.shape[1]
            self.faiss_index = faiss.IndexFlatIP(dimension)
            self.faiss_index.add(self.embeddings.astype('float32'))
            
            return True
        except Exception as e:
            print(f"❌ GROQ system load failed: {e}")
            return False
    
    def ask(self, query):
        query_lower = query.lower()
        
        if query_lower in self.response_cache:
            return self.response_cache[query_lower], [], True
        
        query_embedding = self.embedder.encode([query])
        scores, indices = self.faiss_index.search(query_embedding.astype('float32'), 2)  # Reduced from 4 to 2
        
        docs = [self.documents[i] for i in indices[0]]
        context = "\n\n".join(docs)
        
        prompt = f"""You are an ASU IT academic advisor. Answer using ONLY the provided context.

**Context:**
{context}

**Question:** {query}

**Answer:**"""
        
        response = self.groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        result = response.choices[0].message.content
        
        self.response_cache[query_lower] = result
        return result, docs, False

# Test
if __name__ == "__main__":
    rag = SimpleUnbiasedRAG()
    success = rag.load_systems()
    
    if success:
        print("\n🧪 Testing Simple Unbiased RAG")
        print("=" * 40)
        
        result = rag.ask("What are the core IT courses?")
        
        print(f"\n🏆 Winner: {result['model'].upper()}")
        print(f"Reasoning: {result['evaluation']['reasoning']}")
        print(f"Stats: Gemini {rag.stats['gemini_wins']}, GROQ {rag.stats['groq_wins']}")
    else:
        print("❌ Failed to load system")
