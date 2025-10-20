

# RAGChat.py (fixed import)
import os
from difflib import SequenceMatcher
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_cohere import CohereRerank
from langchain.retrievers import ContextualCompressionRetriever
from VectorStore import GeminiEmbeddings
from dotenv import load_dotenv


load_dotenv()

class RAGChat:
    """Advanced RAG pipeline with Hybrid Search, optional Cohere reranking, and Contextual Compression."""

    def __init__(self, index_path="vector_store/faiss_index_gemini", use_cohere=False):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.embeddings = GeminiEmbeddings()
        self.index_path = index_path
        self.use_cohere = use_cohere
        self.db = None
        self.retriever = None
        self.model_name = "models/gemini-2.5-flash"
        self.model = genai.GenerativeModel(self.model_name)

    def load_index(self):
        """Load FAISS index and create Hybrid Retriever."""
        try:
            # Load FAISS
            self.db = FAISS.load_local(
                self.index_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )

            # Get all text data
            texts = [d.page_content for d in self.db.docstore._dict.values()]

            # BM25 retriever (keyword-based)
            bm25 = BM25Retriever.from_texts(texts)
            bm25.k = 10  # Increased from 5

            # FAISS retriever (semantic)
            faiss_retriever = self.db.as_retriever(search_kwargs={"k": 10})  # Increased from 5

            # Hybrid Retriever
            hybrid_retriever = EnsembleRetriever(
                retrievers=[faiss_retriever, bm25],
                weights=[0.6, 0.4]
            )

            # Optional reranking with Cohere
            if self.use_cohere and os.getenv("COHERE_API_KEY"):
                compressor = CohereRerank()
                self.retriever = ContextualCompressionRetriever(
                    base_compressor=compressor, base_retriever=hybrid_retriever
                )
                print("🔁 Using Cohere reranker")
            else:
                self.retriever = hybrid_retriever
                print("⚙️ Using Hybrid Search (FAISS + BM25)")

            return True
        except Exception as e:
            print(f"⚠️ Failed to load index: {e}")
            return False

    def fallback_rerank(self, query, docs):
        """Improved fallback reranker using semantic similarity and keyword matching."""
        def score(doc):
            # Combine multiple scoring methods
            text = doc.page_content.lower()
            query_lower = query.lower()
            
            # 1. Exact phrase matches (highest weight)
            phrase_score = 0
            for word in query_lower.split():
                if word in text:
                    phrase_score += 1
            
            # 2. Sequence similarity (medium weight)
            seq_score = SequenceMatcher(None, query_lower, text).ratio()
            
            # 3. Keyword density (lower weight)
            keyword_score = sum(1 for word in query_lower.split() if word in text) / len(query_lower.split())
            
            # Weighted combination
            return (phrase_score * 0.5) + (seq_score * 0.3) + (keyword_score * 0.2)
        
        return sorted(docs, key=score, reverse=True)

    def ask(self, query, k=6):
        """Run hybrid retrieval + rerank + Gemini generation."""
        if not self.retriever:
            raise RuntimeError("Retriever not loaded. Call load_index() first.")

        query = query.strip()
        docs = self.retriever.invoke(query)

        # Fallback rerank if Cohere not used
        if not self.use_cohere:
            docs = self.fallback_rerank(query, docs)[:k]

        context = "\n\n".join(d.page_content for d in docs)
        sources = [f"Source {i+1}: {doc.metadata.get('source', 'Unknown')}" for i, doc in enumerate(docs)]
        
        prompt = f"""
You are an expert academic advisor for Arizona State University's Polytechnic School, specifically for the Information Technology program. Your role is to provide accurate, comprehensive, and helpful information to students about IT programs, courses, requirements, and resources.

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
        return response.text, docs

    def get_info(self):
        """Return status for sidebar."""
        chunks = len(self.db.index_to_docstore_id) if self.db else 0
        return {
            "model": self.model_name,
            "vector_store": self.index_path,
            "chunks": chunks,
            "retriever": "Hybrid + Cohere" if self.use_cohere else "Hybrid (FAISS + BM25)"
        }
