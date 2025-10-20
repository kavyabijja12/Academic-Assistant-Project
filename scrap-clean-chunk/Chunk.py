"""
Chunk.py — Robust hybrid chunker for ASU Academic Assistant

✅ Handles both structured (faculty/course) and unstructured data
✅ Preserves newlines for reliable parsing
✅ Extracts metadata (faculty_name, term, course_code, title)
✅ Always runs a fallback semantic chunker so no file is skipped
✅ Saves chunks to data_processed/chunks.json
"""

import os
import re
import json
from collections import Counter
from langchain.text_splitter import RecursiveCharacterTextSplitter

# ---------------- CONFIG ----------------
CLEAN_DIR = "data_processed"
ROOT_DIR =os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
OUTPUT_FILE = os.path.join(ROOT_DIR, "chunks.json")
os.makedirs(CLEAN_DIR, exist_ok=True)

# ----------- Helpers --------------------
def normalize_spaces_preserve_newlines(txt: str) -> str:
    """Collapse spaces/tabs but preserve newlines."""
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = "\n".join(line.strip() for line in txt.split("\n"))
    return txt.strip()

# Splitter for general text
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=150,
    separators=["\n\n", "\n", ".", " "],
)

# ----------- Regex patterns ------------
FACULTY_BLOCK_RE = re.compile(
    r"(FACULTY PROFILE:.*?)(?=FACULTY PROFILE:|$)", re.DOTALL | re.IGNORECASE
)
COURSE_BLOCK_RE = re.compile(
    r"(?:(?:📚\s*)?TERM\s*:\s*.*?)(?=(?:📚\s*)?TERM\s*:|===\s*COURSES\s*===|FACULTY PROFILE:|$)",
    re.DOTALL | re.IGNORECASE,
)
FACULTY_NAME_RE = re.compile(
    r"FACULTY PROFILE:\s*(?:https?://\S+\s+)?([A-Z][^\n,]+)", re.IGNORECASE
)
TERM_RE = re.compile(r"(?i)\bTERM\s*:\s*([A-Za-z]+\s*\d{4})")
COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,4}\s*\d{3})\b")
TITLE_RE = re.compile(
    r"(?i)\bTITLE\s*:\s*(.+?)(?=\bNUMBER\b:|\bINSTRUCTOR\b:|\bUNITS\b:|\bSEATS\b:|$)"
)

# ------------- Process ------------------
docs = []
type_counts = Counter()

for fname in os.listdir(CLEAN_DIR):
    if not fname.endswith(".txt"):
        continue

    path = os.path.join(CLEAN_DIR, fname)
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    text = normalize_spaces_preserve_newlines(raw)

    # --- Smarter detection of structured content ---
    faculty_hits = len(re.findall(r"FACULTY PROFILE:", text, re.IGNORECASE))
    term_hits = len(re.findall(r"(?:(?:📚\s*)?TERM\s*:)", text, re.IGNORECASE))
    course_hits = len(re.findall(r"\bCOURSE\s*TITLE\b", text, re.IGNORECASE))
    looks_structured = (faculty_hits >= 1 and (term_hits > 2 or course_hits > 2))

    structured_chunks = []
    general_chunks = []

    # ---------- Structured Mode ----------
    if looks_structured:
        faculty_blocks = FACULTY_BLOCK_RE.findall(text)
        if not faculty_blocks:
            faculty_blocks = [text]

        for fidx, ftxt in enumerate(faculty_blocks, start=1):
            ftxt = ftxt.strip()
            if len(ftxt) < 120:
                continue

            faculty_name = None
            m_name = FACULTY_NAME_RE.search(ftxt)
            if m_name:
                faculty_name = m_name.group(1).strip()

            fid = f"{fname}_F{fidx}"
            structured_chunks.append({
                "type": "faculty_profile",
                "source": fname,
                "faculty_id": fid,
                "faculty_name": faculty_name,
                "text": ftxt,
            })
            type_counts["faculty_profile"] += 1

            # --- Extract course chunks ---
            course_blocks = COURSE_BLOCK_RE.findall(ftxt)
            for cidx, ctxt in enumerate(course_blocks, start=1):
                ctxt = ctxt.strip()
                if len(ctxt) < 60:
                    continue
                term_match = TERM_RE.search(ctxt)
                code_match = COURSE_CODE_RE.search(ctxt)
                title_match = TITLE_RE.search(ctxt)

                structured_chunks.append({
                    "type": "course_detail",
                    "source": fname,
                    "faculty_id": fid,
                    "course_id": f"{fid}_C{cidx}",
                    "faculty_name": faculty_name,
                    "term": term_match.group(1).strip() if term_match else None,
                    "course_code": code_match.group(1).strip() if code_match else None,
                    "title": title_match.group(1).strip() if title_match else None,
                    "text": ctxt,
                })
                type_counts["course_detail"] += 1

    # ---------- General Mode (always run) ----------
    chunks = splitter.split_text(text)
    for i, ch in enumerate(chunks, start=1):
        ch = ch.strip()
        if not ch:
            continue
        general_chunks.append({
            "type": "general_text",
            "source": fname,
            "chunk_id": f"{fname}_G{i}",
            "text": ch,
        })
        type_counts["general_text"] += 1

    docs.extend(structured_chunks + general_chunks)

# ---------- Dedup identical chunks ----------
seen = set()
unique_docs = []
for d in docs:
    key = (d["type"], d["source"], d.get("text", ""))
    if key in seen:
        continue
    seen.add(key)
    unique_docs.append(d)

# ---------- Save & summary ----------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(unique_docs, f, indent=2, ensure_ascii=False)

print("✅ Chunking complete")
print(f"  • Files scanned: {sum(1 for x in os.listdir(CLEAN_DIR) if x.endswith('.txt'))}")
print(f"  • Chunks written: {len(unique_docs)} → {OUTPUT_FILE}")
print("  • By type:", dict(type_counts))


