import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque, defaultdict

# ---------- CONFIG ----------
BASE_DOMAIN = "poly.engineering.asu.edu"
START_URL = "https://poly.engineering.asu.edu/it/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
SAVE_DIR = "data_more"
os.makedirs(SAVE_DIR, exist_ok=True)

STOP = [
    "https://poly.engineering.asu.edu/accelerated-masters-degree-programs/",
    "https://poly.engineering.asu.edu/",
    "https://poly.engineering.asu.edu/2020/01/asmaa-elbadrawy/",
    "https://poly.engineering.asu.edu/2020/01/damien-doheny/",
    "https://poly.engineering.asu.edu/2020/01/jim-helm/",
    "https://poly.engineering.asu.edu/2020/01/robert-rucker/",
    "https://poly.engineering.asu.edu/2020/01/tatiana-walsh/",
    "https://poly.engineering.asu.edu/2021/08/brian-l-atkinson/",
    "https://poly.engineering.asu.edu/2021/08/eric-bishop/",
    "https://poly.engineering.asu.edu/2022/08/derex-griffin/",
    "https://poly.engineering.asu.edu/2022/08/dinesh-sthapit/",
    "https://poly.engineering.asu.edu/2023/09/ashish-gulati-2/",
    "https://poly.engineering.asu.edu/2023/09/carl-iverson/",
    "https://poly.engineering.asu.edu/2023/09/durgesh-sharma/",
    "https://poly.engineering.asu.edu/degrees/"
]
# -------------------------------------------------------------


# ---------- EMAIL UNMASKER ----------
def decode_cf_email(cfstring: str) -> str:
    r = int(cfstring[:2], 16)
    return ''.join(chr(int(cfstring[i:i + 2], 16) ^ r) for i in range(2, len(cfstring), 2))

def unmask_emails(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")

    # Handle Cloudflare email obfuscation
    for tag in soup.find_all(["a", "span"], attrs={"data-user": True, "data-domain": True}):
        user = tag.get("data-user")
        domain = tag.get("data-domain")
        if user and domain:
            tag.string = f"{user}@{domain}"

    for tag in soup.find_all("a", {"class": "__cf_email__"}):
        data_cf = tag.get("data-cfemail")
        if data_cf:
            tag.string = decode_cf_email(data_cf)

    html_text = str(soup)
    html_text = re.sub(r"\bemail\s*protected\b", "[email protected]", html_text, flags=re.IGNORECASE)
    return html_text
# -----------------------------------


# ---------- GOOGLE DOC SCRAPER ----------
def fetch_google_doc(url, parent_url=None):
    """Export Google Doc text content and save it."""
    try:
        match = re.search(r"/d/([a-zA-Z0-9_-]+)/", url)
        if not match:
            return None
        doc_id = match.group(1)
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        resp = requests.get(export_url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            content = resp.text
            filename = os.path.join(SAVE_DIR, f"google_doc_{doc_id}.txt")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"URL: {url}\nParent: {parent_url}\n\n{content}")
            print(f"✅ Saved Google Doc: {url}")
            return {"url": url, "content": content, "parent": parent_url}
        else:
            print(f"❌ Failed Google Doc ({resp.status_code}): {url}")
            return None
    except Exception as e:
        print(f"⚠️ Error fetching Google Doc {url}: {e}")
        return None
# ----------------------------------------


# ---------- REGULAR PAGE SCRAPER ----------
def is_valid_url(url):
    parsed = urlparse(url)
    return (BASE_DOMAIN in parsed.netloc) or ("docs.google.com/document/d/" in url)


def scrape_page(url, parent_url=None):
    """Extract visible text and save to file."""
    try:
        # Handle Google Docs
        if "docs.google.com/document/d/" in url:
            return fetch_google_doc(url, parent_url)

        # Skip Cloudflare email protection
        if "cdn-cgi/l/email-protection" in url:
            return None

        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            print(f"❌ Failed ({resp.status_code}): {url}")
            return None

        clean_html = unmask_emails(resp.text)
        soup = BeautifulSoup(clean_html, "html.parser")

        # Skip "Email Protection" fallback pages
        if soup.title and "Email Protection" in soup.title.get_text():
            return None

        title = soup.title.string.strip() if soup.title else "Untitled Page"

        # Collect readable content
        texts = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
            txt = tag.get_text(separator=" ", strip=True)
            if txt:
                texts.append(txt)

        content = "\n".join(texts)
        if not content.strip():
            return None

        # Save content
        filename = os.path.join(SAVE_DIR, f"{title[:80].replace('/', '_')}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"URL: {url}\nParent: {parent_url}\n\n{content}")

        print(f"✅ Saved: {title[:80]}")
        return {"url": url, "title": title, "content": content, "parent": parent_url}

    except Exception as e:
        print(f"⚠️ Error scraping {url}: {e}")
        return None
# ----------------------------------------


# ---------- CRAWLER ----------
def get_links(url):
    """Extract valid links from a page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")

        links = set()
        for a in soup.find_all("a", href=True):
            link = urljoin(url, a["href"]).split("#")[0].strip()
            if not link:
                continue
            if any(x in link.lower() for x in ["mailto:", "tel:", "cdn-cgi/l/email-protection", "email-protection"]):
                continue
            if is_valid_url(link):
                links.add(link)
        return sorted(list(links))
    except Exception:
        return []


def crawl(start_url, max_depth=3, max_pages=200):
    """BFS crawl + scrape pages (stop at STOP URLs)."""
    visited = set()
    queue = deque([(start_url, 0, None)])
    scraped_pages = []

    while queue and len(scraped_pages) < max_pages:
        url, depth, parent_url = queue.popleft()
        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        print(f"🔍 Scraping (depth={depth}): {url}")
        page_data = scrape_page(url, parent_url)
        if page_data:
            scraped_pages.append(page_data)

        # Stop deeper traversal for STOP pages
        if any(url.rstrip("/") == s.rstrip("/") for s in STOP):
            print(f"⛔ Stop expansion for: {url}")
            continue

        if depth < max_depth:
            for link in get_links(url):
                if link not in visited:
                    queue.append((link, depth + 1, url))

    print(f"\n✅ Scraped {len(scraped_pages)} total pages.")
    return scraped_pages


if __name__ == "__main__":
    crawl(START_URL, max_depth=3, max_pages=200)
