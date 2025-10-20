

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
            bm25.k = 5

            # FAISS retriever (semantic)
            faiss_retriever = self.db.as_retriever(search_kwargs={"k": 5})

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

    @staticmethod
    def fallback_rerank(query, docs):
        """Fallback reranker using textual overlap."""
        def score(doc):
            return SequenceMatcher(None, query.lower(), doc.page_content.lower()).ratio()
        return sorted(docs, key=score, reverse=True)

    def ask(self, query, k=4):
        """Run hybrid retrieval + rerank + Gemini generation."""
        if not self.retriever:
            raise RuntimeError("Retriever not loaded. Call load_index() first.")

        query = query.strip()
        docs = self.retriever.get_relevant_documents(query)

        # Fallback rerank if Cohere not used
        if not self.use_cohere:
            docs = self.fallback_rerank(query, docs)[:k]

        context = "\n\n".join(d.page_content for d in docs)
        prompt = f"""
You are an academic advising assistant for Arizona State University’s Polytechnic School (Information Technology program).
Use the provided context to answer precisely. If uncertain, reply "I couldn’t find that in the current ASU IT materials."

Context:
{context}

Question:
{query}

Answer:
"""
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
