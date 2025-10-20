import os, re

RAW_DIR = "data"
CLEAN_DIR = "data_processed"
os.makedirs(CLEAN_DIR, exist_ok=True)

for filename in os.listdir(RAW_DIR):
    if not filename.endswith(".txt"):
        continue
    with open(os.path.join(RAW_DIR, filename), "r", encoding="utf-8") as f:
        text = f.read()

    # Remove excessive whitespace but preserve structure
    clean_text = re.sub(r'[ \t]+', ' ', text)  # Replace multiple spaces/tabs with single space
    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)  # Preserve paragraph breaks
    # Remove only repetitive navigation elements, not all ASU references
    clean_text = re.sub(r'(?i)URL:\s*https://poly\.engineering\.asu\.edu[^\n]*\n', '', clean_text)
    clean_text = re.sub(r'(?i)Parent:\s*https://poly\.engineering\.asu\.edu[^\n]*\n', '', clean_text)

    with open(os.path.join(CLEAN_DIR, filename), "w", encoding="utf-8") as f:
        f.write(clean_text)

print("✅ Cleaned and stored processed text files.")
