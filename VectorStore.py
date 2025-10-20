# VectorStore.py
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os, json
from dotenv import load_dotenv

# Load .env
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ---- Embedding wrapper ----
class GeminiEmbeddings(Embeddings):
    def __init__(self, chunk_limit_chars=3500):
        self.chunk_limit_chars = chunk_limit_chars
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_limit_chars,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " "],
        )

    def _safe_embed(self, text):
        """Embed one safe-sized chunk"""
        try:
            result = genai.embed_content(model="models/text-embedding-004", content=text)
            return result["embedding"]
        except Exception as e:
            print(f"⚠️ Embedding failed: {e}")
            return [0.0] * 768  # fallback vector size

    def embed_documents(self, texts):
        """Handles long docs safely by slicing > chunk_limit_chars"""
        embeddings = []
        for text in texts:
            if len(text) > self.chunk_limit_chars:
                subchunks = self.splitter.split_text(text)
                sub_vecs = [self._safe_embed(t) for t in subchunks]
                avg_vec = [sum(col) / len(col) for col in zip(*sub_vecs)]
                embeddings.append(avg_vec)
            else:
                embeddings.append(self._safe_embed(text))
        return embeddings

    def embed_query(self, text):
        return self._safe_embed(text)

# ---- Load your processed chunks ----
with open("chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

texts = [c["text"].lower() for c in chunks]
metadatas = [{"source": c.get("source"), "type": c.get("type")} for c in chunks]

# ---- Build and save FAISS index ----
embeddings = GeminiEmbeddings()
db = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
db.save_local("vector_store/faiss_index_gemini")
print("✅ Gemini-based FAISS vector store created safely.")
