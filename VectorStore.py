# VectorStore.py
import os
# Fix tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import json
import time
from dotenv import load_dotenv

# Load .env
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ---- SentenceTransformers Embedding (Local, No API needed) ----
class SentenceTransformerEmbeddings(Embeddings):
    """Local embeddings using SentenceTransformers - no API calls, no rate limits"""
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading SentenceTransformer model: {model_name}...")
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            print(f"Model loaded. Embedding dimension: {self.embedding_dim}")
        except ImportError:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
    
    def embed_documents(self, texts):
        """Embed multiple documents efficiently"""
        if not texts:
            return []
        print(f"Embedding {len(texts)} documents locally...")
        embeddings = self.model.encode(texts, show_progress_bar=True, batch_size=32)
        return embeddings.tolist()
    
    def embed_query(self, text):
        """Embed a single query"""
        embedding = self.model.encode([text])
        return embedding[0].tolist()

# ---- Embedding wrapper ----
class GeminiEmbeddings(Embeddings):
    def __init__(self, chunk_limit_chars=3500):
        self.chunk_limit_chars = chunk_limit_chars
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_limit_chars,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " "],
        )

    def _safe_embed(self, text, max_retries=3, base_delay=1.0):
        """Embed one safe-sized chunk with retry logic"""
        if not text or not text.strip():
            return [0.0] * 768
        
        for attempt in range(max_retries):
            try:
                result = genai.embed_content(
                    model="models/text-embedding-004", 
                    content=text
                )
                if result and "embedding" in result:
                    return result["embedding"]
                else:
                    raise ValueError("Invalid response from embedding API")
            except Exception as e:
                error_str = str(e)
                # Check if it's a retryable error (500, 503, rate limit, etc.)
                is_retryable = (
                    "500" in error_str or 
                    "503" in error_str or 
                    "429" in error_str or
                    "rate limit" in error_str.lower() or
                    "internal error" in error_str.lower()
                )
                
                if attempt < max_retries - 1 and is_retryable:
                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** attempt) + (time.time() % 1)
                    print(f"Embedding attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                else:
                    print(f"Embedding failed after {attempt + 1} attempts: {e}")
                    if attempt == max_retries - 1:
                        # Only return fallback on final failure
                        return [0.0] * 768
                    break
        
        return [0.0] * 768  # fallback vector size

    def embed_documents(self, texts):
        """Handles long docs safely by slicing > chunk_limit_chars"""
        embeddings = []
        total = len(texts)
        for idx, text in enumerate(texts):
            if len(text) > self.chunk_limit_chars:
                subchunks = self.splitter.split_text(text)
                sub_vecs = []
                for subchunk in subchunks:
                    sub_vecs.append(self._safe_embed(subchunk))
                    # Small delay between subchunks to avoid rate limiting
                    time.sleep(0.1)
                avg_vec = [sum(col) / len(col) for col in zip(*sub_vecs)]
                embeddings.append(avg_vec)
            else:
                embeddings.append(self._safe_embed(text))
            
            # Rate limiting: small delay between documents (except for the last one)
            if idx < total - 1:
                time.sleep(0.1)
            
            # Progress indicator for large batches
            if total > 10 and (idx + 1) % 10 == 0:
                print(f"Processed {idx + 1}/{total} documents...")
        
        return embeddings

    def embed_query(self, text):
        return self._safe_embed(text)

# ---- Script execution (only runs when file is executed directly) ----
if __name__ == "__main__":
    # Load your processed chunks
    with open("chunks.json", "r", encoding="utf-8") as f:
        chunks = json.load(f)

    texts = [c["text"] for c in chunks]  # Preserve original case for better embeddings
    
    # Extract program level from source or text content
    def extract_program_level(chunk):
        """Extract program level (bs/ms) from chunk source or content"""
        source = chunk.get("source", "").lower()
        text = chunk.get("text", "").lower()
        
        # Check source filename
        if "b.s" in source or "bachelor" in source or "bs in" in source or "undergraduate" in source:
            return "bs"
        elif "m.s" in source or "master" in source or "ms in" in source or "graduate" in source:
            return "ms"
        
        # Check text content for program mentions
        if "bachelor" in text[:500] or "undergraduate" in text[:500] or "b.s" in text[:500]:
            return "bs"
        elif "master" in text[:500] or "graduate" in text[:500] or "m.s" in text[:500]:
            return "ms"
        
        return None
    
    metadatas = [
        {
            "source": c.get("source"),
            "type": c.get("type"),
            "program_level": extract_program_level(c)
        }
        for c in chunks
    ]

    # ---- Choose embedding method ----
    # Set USE_SENTENCE_TRANSFORMERS to True to use local embeddings (recommended if Gemini API is failing)
    USE_SENTENCE_TRANSFORMERS = True  # Change to False to use Gemini API

    if USE_SENTENCE_TRANSFORMERS:
        print("Using SentenceTransformers (local, no API needed)...")
        embeddings = SentenceTransformerEmbeddings()
        index_path = "vector_store/faiss_index_sentence_transformer"
    else:
        print("Using Gemini Embeddings (requires API)...")
        embeddings = GeminiEmbeddings()
        index_path = "vector_store/faiss_index_gemini"

    # ---- Build and save FAISS index ----
    print(f"Building FAISS index with {len(texts)} documents...")
    db = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
    db.save_local(index_path)
    print(f"FAISS vector store created and saved to: {index_path}")
