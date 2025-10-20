import os, re

RAW_DIR = "data"
CLEAN_DIR = "data_processed"
os.makedirs(CLEAN_DIR, exist_ok=True)

for filename in os.listdir(RAW_DIR):
    if not filename.endswith(".txt"):
        continue
    with open(os.path.join(RAW_DIR, filename), "r", encoding="utf-8") as f:
        text = f.read()

    # Remove duplicate whitespace and navigation noise
    clean_text = re.sub(r'\s+', ' ', text)
    clean_text = re.sub(r'(?i)(ASU|Arizona State University).*?Polytechnic.*?(School|Campus)', '', clean_text)

    with open(os.path.join(CLEAN_DIR, filename), "w", encoding="utf-8") as f:
        f.write(clean_text)

print("✅ Cleaned and stored processed text files.")
