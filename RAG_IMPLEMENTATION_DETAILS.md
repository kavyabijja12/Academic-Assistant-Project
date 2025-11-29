# RAG Chatbot Implementation Details

## Overview
This document explains how the RAG (Retrieval-Augmented Generation) chatbot is implemented, including all processing steps and LLM API calls made for each user query.

---

## Complete Flow for Each Query

### Step 1: User Input Processing (`main.py`)
**Location:** `process_user_input()` function (line 1114)

1. User submits a query through the Streamlit UI
2. The query is saved to the database (with intent classification)
3. The system checks if it's a booking request or a question

**LLM Calls:** 0 (at this stage)

---

### Step 2: Intent Classification (`agents/IntentClassifier.py`)
**Location:** `detect_intent()` method (line 31)

The system classifies the user's intent to determine if it's:
- **"booking"** - User wants to book an appointment
- **"question"** - User is asking a question (goes to RAG)

#### Classification Process:

**2a. Keyword Matching (Fast Path)**
- Checks for booking keywords: "book", "schedule", "appointment", etc.
- Checks for question keywords: "what", "how", "when", "requirements", etc.
- If strong keyword match found → **0 LLM calls**

**2b. Question Subcategory Classification** (if question detected)
- Classifies into subcategories:
  - `course_information`
  - `application_process`
  - `program_requirements`
  - `professor_information`
- Uses keyword matching first → **0 LLM calls** (usually)
- If ambiguous → calls `_classify_question_with_llm()` → **+1 LLM call**

**2c. Ambiguous Intent Classification**
- If intent is unclear (neither booking nor question keywords match strongly)
- Calls `_classify_with_llm()` → **+1 LLM call**

**LLM Calls for Intent Classification:**
- **Best case:** 0 LLM calls (clear keywords)
- **Typical case:** 0-1 LLM calls (usually keywords are sufficient)
- **Worst case:** 2 LLM calls (ambiguous intent + ambiguous question type)

---

### Step 3: RAG System Processing (`SimpleUnbiasedRAG.py`)
**Location:** `ask()` method (line 49)

If the intent is "question", the query is routed to the RAG system.

#### 3a. Cache Check (`GeminiSystem.ask()` - line 116)
- Checks if the query (lowercased) exists in response cache
- If cached → **0 LLM calls**, returns cached response immediately

**LLM Calls:** 0 (if cached)

---

#### 3b. Document Retrieval (Hybrid Retrieval)
**Location:** `GeminiSystem.ask()` - line 122

The system uses **Ensemble Retrieval** combining two methods:

1. **FAISS Vector Search** (Semantic Search)
   - Uses SentenceTransformers embeddings (`all-MiniLM-L6-v2`)
   - **NO LLM calls** - embeddings are generated locally
   - Retrieves top 10 most semantically similar chunks

2. **BM25 Retrieval** (Keyword-based Search)
   - Traditional keyword-based retrieval
   - **NO LLM calls** - pure text matching algorithm
   - Retrieves top 10 keyword-matching chunks

3. **Ensemble Combination**
   - Combines results with weights: 60% FAISS, 40% BM25
   - **NO LLM calls** - just mathematical combination

**LLM Calls:** 0 (all retrieval is local)

---

#### 3c. Document Scoring and Re-ranking (line 125-161)
- Enhanced scoring function that considers:
  - Word matches between query and document
  - Document type relevance (specialization, course, requirement)
  - Program level matching (BS vs MS)
- **NO LLM calls** - pure algorithmic scoring

**LLM Calls:** 0

---

#### 3d. Diversity Filtering (line 164-191)
- Selects diverse chunks from different sources
- Prefers chunks from different documents to avoid redundancy
- Limits to top 10 most relevant and diverse chunks
- **NO LLM calls** - algorithmic selection

**LLM Calls:** 0

---

#### 3e. Context Building (line 193-204)
- Formats retrieved chunks with source labels
- Creates a structured context string for the LLM
- **NO LLM calls** - just string formatting

**LLM Calls:** 0

---

#### 3f. LLM Generation (line 207-234)
**Location:** `GeminiSystem.ask()` - line 233

This is where the **actual LLM call** happens:

1. **Prompt Construction:**
   - System instructions for academic assistant
   - Context from retrieved documents (top 10 chunks)
   - Source information
   - User's question

2. **LLM API Call:**
   - Model: `gemini-2.5-flash`
   - Method: `self.model.generate_content(prompt)`
   - **1 LLM call** to generate the final answer

3. **Response Processing:**
   - Extracts text from LLM response
   - Caches the response for future queries
   - Returns answer with source documents

**LLM Calls:** **1** (the main generation call)

---

## Total LLM Calls Per Query

### For RAG Questions (Non-Booking):

| Scenario | Intent Classification | RAG Generation | Total LLM Calls |
|----------|----------------------|----------------|-----------------|
| **Best Case** | 0 (clear keywords) | 1 (not cached) | **1** |
| **Cached Query** | 0 (clear keywords) | 0 (cached) | **0** |
| **Typical Case** | 0-1 (usually keywords work) | 1 (not cached) | **1-2** |
| **Worst Case** | 2 (ambiguous intent + question type) | 1 (not cached) | **3** |

### Summary:
- **Minimum:** 0 LLM calls (cached query with clear keywords)
- **Typical:** 1-2 LLM calls (1 for generation, sometimes 1 for classification)
- **Maximum:** 3 LLM calls (2 for classification + 1 for generation)

---

## Key Implementation Details

### 1. Embeddings (No API Calls)
- **Model:** SentenceTransformers `all-MiniLM-L6-v2`
- **Location:** `VectorStore.py` - `SentenceTransformerEmbeddings` class
- **Type:** Local embeddings (runs on your machine)
- **No API calls** - completely offline

### 2. Vector Store
- **Type:** FAISS (Facebook AI Similarity Search)
- **Location:** `vector_store/faiss_index_sentence_transformer/`
- **Pre-built:** Index is created offline and loaded at runtime
- **No API calls** during retrieval

### 3. BM25 Retriever
- **Type:** Traditional keyword-based retrieval
- **Cached:** `vector_store/bm25_cache.pkl`
- **No API calls** - pure algorithmic text matching

### 4. Response Caching
- **Location:** `GeminiSystem.response_cache` (in-memory dictionary)
- **Key:** Lowercased query string
- **Benefit:** Avoids duplicate LLM calls for same queries

### 5. LLM Model
- **Provider:** Google Gemini
- **Model:** `gemini-2.5-flash`
- **API:** `google.generativeai.GenerativeModel`
- **Usage:** Only for final answer generation (and optional intent classification)

---

## Code Flow Diagram

```
User Query
    ↓
[main.py] process_user_input()
    ↓
[AgentController] route_request()
    ↓
[IntentClassifier] detect_intent()
    ├─ Keyword matching? → 0 LLM calls
    ├─ Ambiguous? → 1 LLM call (_classify_with_llm)
    └─ Question type ambiguous? → +1 LLM call (_classify_question_with_llm)
    ↓
[SimpleUnbiasedRAG] ask()
    ↓
[GeminiSystem] ask()
    ├─ Cache check → 0 LLM calls (if cached)
    ├─ Ensemble Retrieval → 0 LLM calls (local embeddings + BM25)
    ├─ Scoring & Re-ranking → 0 LLM calls (algorithmic)
    ├─ Diversity Filtering → 0 LLM calls (algorithmic)
    ├─ Context Building → 0 LLM calls (string formatting)
    └─ LLM Generation → 1 LLM call (gemini-2.5-flash)
    ↓
Final Answer
```

---

## Performance Optimizations

1. **Local Embeddings:** No API calls for embeddings (uses SentenceTransformers)
2. **Response Caching:** Avoids duplicate LLM calls for same queries
3. **Keyword-based Intent Classification:** Most queries don't need LLM for intent
4. **Hybrid Retrieval:** Combines semantic (FAISS) and keyword (BM25) for better results
5. **Diversity Filtering:** Ensures retrieved chunks are from different sources

---

## Files Involved

1. **`main.py`** - Main UI and query routing
2. **`SimpleUnbiasedRAG.py`** - RAG system implementation
3. **`VectorStore.py`** - Embedding classes (SentenceTransformers, Gemini)
4. **`agents/IntentClassifier.py`** - Intent classification
5. **`agents/AgentController.py`** - Request routing
6. **`vector_store/faiss_index_sentence_transformer/`** - Pre-built vector index
7. **`vector_store/bm25_cache.pkl`** - Cached BM25 retriever

---

## Example Query Flow

**Query:** "What are the graduation requirements for MS in IT?"

1. **Intent Classification:**
   - Keywords detected: "what", "requirements", "MS", "IT"
   - Classification: `question:program_requirements`
   - **LLM Calls: 0** (keywords sufficient)

2. **RAG Processing:**
   - Cache check: Not cached
   - FAISS retrieval: Top 10 semantic matches
   - BM25 retrieval: Top 10 keyword matches
   - Ensemble: Combined results
   - Scoring: Re-ranked by relevance
   - Diversity: Selected 10 diverse chunks
   - Context: Built from chunks
   - LLM generation: 1 call to Gemini
   - **LLM Calls: 1**

**Total LLM Calls: 1**

---

## Notes

- The system is designed to minimize LLM calls through caching and keyword-based classification
- Most queries only require 1 LLM call (the final answer generation)
- Embeddings are completely local (no API costs for retrieval)
- Response caching significantly reduces costs for repeated queries

