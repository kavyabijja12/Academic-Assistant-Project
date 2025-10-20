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
TREE_FILE = "link_tree_only.txt"
os.makedirs("data", exist_ok=True)

# Pages to scrape but NOT expand further (stop recursion)
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


def is_valid_url(url):
    """Check whether URL belongs to ASU Polytechnic or a Google Doc."""
    parsed = urlparse(url)
    return (BASE_DOMAIN in parsed.netloc) or ("docs.google.com/document/d/" in url)


def get_links(url):
    """Extract all valid child links from a page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            print(f"❌ Failed ({resp.status_code}): {url}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        links = set()

        for a in soup.find_all("a", href=True):
            link = urljoin(url, a["href"]).split("#")[0].strip()
            if not link:
                continue
            # Skip useless or email-protected links
            if any(x in link.lower() for x in ["mailto:", "tel:", "cdn-cgi/l/email-protection", "email-protection"]):
                continue
            if is_valid_url(link):
                links.add(link)

        return sorted(list(links))
    except Exception as e:
        print(f"⚠️ Error fetching {url}: {e}")
        return []


def crawl_tree(start_url, max_depth=3, max_pages=200):
    """Breadth-first crawl to build parent→child mapping, without scraping text."""
    visited = set()
    queue = deque([(start_url, 0, None)])
    tree = defaultdict(list)

    while queue and len(visited) < max_pages:
        url, depth, parent_url = queue.popleft()
        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        print(f"🔍 Visiting (depth={depth}): {url}")
        if parent_url:
            tree[parent_url].append(url)

        # Stop deeper traversal for STOP URLs (still included in tree)
        if any(url.rstrip("/") == s.rstrip("/") for s in STOP):
            print(f"⛔ Stop expansion for: {url}")
            continue

        if depth < max_depth:
            child_links = get_links(url)
            for link in child_links:
                if link not in visited:
                    queue.append((link, depth + 1, url))

    print(f"\n✅ Total unique pages found: {len(visited)}")
    save_tree(tree, start_url)


def save_tree(tree, root):
    """Write the link hierarchy as a tree structure."""
    with open(TREE_FILE, "w", encoding="utf-8") as f:
        def dfs(url, indent=""):
            f.write(f"{indent}{url}\n")
            for child in tree.get(url, []):
                dfs(child, indent + "    ")
        dfs(root)
    print(f"🌳 Link tree saved to: {os.path.abspath(TREE_FILE)}")


if __name__ == "__main__":
    crawl_tree(START_URL, max_depth=3, max_pages=200)
