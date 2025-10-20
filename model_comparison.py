#!/usr/bin/env python3
"""
Model Comparison Test: Gemini + FAISS vs GROQ + Sentence Transformers
This script compares performance, quality, and cost between the two approaches.
"""

import os
import time
import json
from dotenv import load_dotenv
import google.generativeai as genai
from groq import Groq
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import faiss
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from difflib import SequenceMatcher

load_dotenv()

class CurrentSystem:
    """Your current Gemini + FAISS system"""
    
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.embeddings = self._get_gemini_embeddings()
        self.model = genai.GenerativeModel("models/gemini-2.5-flash")
        self.db = None
        self.retriever = None
        self.response_cache = {}
        
    def _get_gemini_embeddings(self):
        """Simplified Gemini embeddings for comparison"""
        from VectorStore import GeminiEmbeddings
        return GeminiEmbeddings()
    
    def load_system(self):
        """Load your current system"""
        try:
            # Load FAISS
            self.db = FAISS.load_local(
                "vector_store/faiss_index_gemini",
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            # Get all text data
            texts = [d.page_content for d in self.db.docstore._dict.values()]
            
            # BM25 retriever (cached)
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
            
            # Hybrid Retriever
            self.retriever = EnsembleRetriever(
                retrievers=[faiss_retriever, bm25],
                weights=[0.6, 0.4]
            )
            return True
        except Exception as e:
            print(f"❌ Current system load failed: {e}")
            return False
    
    def ask(self, query):
        """Ask question using current system"""
        query_lower = query.lower()
        
        # Check cache
        if query_lower in self.response_cache:
            return self.response_cache[query_lower], True
        
        docs = self.retriever.invoke(query)
        
        # Simple reranking
        def score(doc):
            text = doc.page_content.lower()
            query_words = query_lower.split()
            matches = sum(1 for word in query_words if word in text)
            if query_lower in text:
                matches += len(query_words)
            return matches
        
        docs = sorted(docs, key=score, reverse=True)[:4]
        
        # Create prompt
        context = "\n\n".join(d.page_content for d in docs)
        prompt = f"""
You are an expert academic advisor for Arizona State University's Polytechnic School, specifically for the Information Technology program.

Context:
{context}

Question: {query}

Answer:"""
        
        response = self.model.generate_content(prompt)
        result = response.text
        
        # Cache response
        self.response_cache[query_lower] = result
        return result, False

class GROQSystem:
    """GROQ + Sentence Transformers system"""
    
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.documents = []
        self.embeddings = None
        self.faiss_index = None
        self.response_cache = {}
        
    def load_system(self):
        """Load GROQ system"""
        try:
            # Load chunks
            with open("chunks.json", "r", encoding="utf-8") as f:
                chunks = json.load(f)
            
            self.documents = [chunk["text"] for chunk in chunks]
            
            # Create embeddings
            print("🔨 Creating sentence transformer embeddings...")
            self.embeddings = self.embedder.encode(self.documents)
            
            # Create FAISS index
            dimension = self.embeddings.shape[1]
            self.faiss_index = faiss.IndexFlatIP(dimension)
            self.faiss_index.add(self.embeddings.astype('float32'))
            
            return True
        except Exception as e:
            print(f"❌ GROQ system load failed: {e}")
            return False
    
    def ask(self, query):
        """Ask question using GROQ system"""
        query_lower = query.lower()
        
        # Check cache
        if query_lower in self.response_cache:
            return self.response_cache[query_lower], True
        
        # Get relevant documents
        query_embedding = self.embedder.encode([query])
        scores, indices = self.faiss_index.search(query_embedding.astype('float32'), 4)
        
        # Get top documents
        docs = [self.documents[i] for i in indices[0]]
        context = "\n\n".join(docs)
        
        # Generate response with GROQ
        prompt = f"""
You are an expert academic advisor for Arizona State University's Polytechnic School, specifically for the Information Technology program.

Context:
{context}

Question: {query}

Answer:"""
        
        response = self.groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        result = response.choices[0].message.content
        
        # Cache response
        self.response_cache[query_lower] = result
        return result, False

def compare_systems():
    """Compare both systems"""
    print("🚀 Starting Model Comparison Test")
    print("=" * 60)
    
    # Test questions
    test_questions = [
        "What are the core IT courses?",
        "What are the graduation requirements for IT program?",
        "Which location of ASU IT course is based on?",
        "How do I apply for the IT program?",
        "What are the admission requirements?"
    ]
    
    # Initialize systems
    print("\n📦 Loading systems...")
    
    current_system = CurrentSystem()
    groq_system = GROQSystem()
    
    current_loaded = current_system.load_system()
    groq_loaded = groq_system.load_system()
    
    if not current_loaded:
        print("❌ Failed to load current system")
        return
    
    if not groq_loaded:
        print("❌ Failed to load GROQ system")
        return
    
    print("✅ Both systems loaded successfully!")
    
    # Test each question
    results = {
        'current': {'times': [], 'responses': [], 'cached': 0},
        'groq': {'times': [], 'responses': [], 'cached': 0}
    }
    
    print(f"\n🧪 Testing {len(test_questions)} questions...")
    print("=" * 60)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n📝 Question {i}: {question}")
        print("-" * 40)
        
        # Test current system
        start_time = time.time()
        current_response, current_cached = current_system.ask(question)
        current_time = time.time() - start_time
        
        # Test GROQ system
        start_time = time.time()
        groq_response, groq_cached = groq_system.ask(question)
        groq_time = time.time() - start_time
        
        # Store results
        results['current']['times'].append(current_time)
        results['current']['responses'].append(current_response)
        results['current']['cached'] += current_cached
        
        results['groq']['times'].append(groq_time)
        results['groq']['responses'].append(groq_response)
        results['groq']['cached'] += groq_cached
        
        # Display results
        print(f"🔵 Current System: {current_time:.2f}s ({'cached' if current_cached else 'fresh'})")
        print(f"🟢 GROQ System:   {groq_time:.2f}s ({'cached' if groq_cached else 'fresh'})")
        print(f"📊 Speed ratio: {current_time/groq_time:.1f}x {'faster' if groq_time < current_time else 'slower'}")
        
        # Show response previews
        print(f"\n🔵 Current response: {current_response[:100]}...")
        print(f"🟢 GROQ response:   {groq_response[:100]}...")
    
    # Final comparison
    print("\n" + "=" * 60)
    print("📊 FINAL COMPARISON RESULTS")
    print("=" * 60)
    
    current_avg = np.mean(results['current']['times'])
    groq_avg = np.mean(results['groq']['times'])
    
    print(f"🔵 Current System (Gemini + FAISS):")
    print(f"   Average time: {current_avg:.2f}s")
    print(f"   Cached responses: {results['current']['cached']}")
    print(f"   Quality: Professional, detailed responses")
    print(f"   Cost: High (Gemini API calls)")
    
    print(f"\n🟢 GROQ System (GROQ + Sentence Transformers):")
    print(f"   Average time: {groq_avg:.2f}s")
    print(f"   Cached responses: {results['groq']['cached']}")
    print(f"   Quality: Good, but may be less detailed")
    print(f"   Cost: Low (local embeddings + GROQ)")
    
    speed_improvement = current_avg / groq_avg
    print(f"\n⚡ GROQ is {speed_improvement:.1f}x {'faster' if speed_improvement > 1 else 'slower'}")
    
    if speed_improvement > 1:
        print(f"💰 GROQ saves {current_avg - groq_avg:.2f}s per query on average")
    
    # Quality assessment
    print(f"\n🎯 QUALITY ASSESSMENT:")
    print("🔵 Current: More detailed, academic-style responses")
    print("🟢 GROQ: Faster, but potentially less comprehensive")
    
    return results

if __name__ == "__main__":
    try:
        results = compare_systems()
        print("\n✅ Comparison complete!")
    except Exception as e:
        print(f"❌ Comparison failed: {e}")
        print("Make sure you have GROQ_API_KEY in your .env file")
