import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from collections import defaultdict

# ---------- CONFIG ----------
faculty_tree = [
    "https://search.asu.edu/profile/3170872",  # Asmaa Elbadrawy 
    "https://search.asu.edu/profile/2786364",  # Damien Doheny
    "https://search.asu.edu/profile/2100155",  # Jim Helm
    "https://search.asu.edu/profile/254985",   # Robert Rucker
    "https://search.asu.edu/profile/3293953",  # Tatiana Walsh
    "https://search.asu.edu/profile/3381260",  # Brian L Atkinson
    "https://search.asu.edu/profile/646098",   # Eric Bishop
    "https://search.asu.edu/profile/3978451",  # Derex Griffin
    "https://search.asu.edu/profile/3350560",  # Dinesh Sthapit
    "https://search.asu.edu/profile/3536507",  # Ashish Gulati
    "https://search.asu.edu/profile/1817541",  # Carl Iverson
    "https://search.asu.edu/profile/3038002",  # Durgesh Sharma
]

ALLOWED_TERM_KEYWORDS = ["&term=2261", "&term=2257", "&term=2254"]
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
OUTPUT_FILE = "faculty_profile_subchild_tree.txt"
# --------------------------------------------------


def get_relevant_links(url):
    """Extract only relevant profile/catalog links from a page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            print(f"❌ Failed {url}: {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        links = set()

        for a in soup.find_all("a", href=True):
            link = urljoin(url, a["href"]).split("#")[0]
            if link.startswith("https://search.asu.edu/profile") or link.startswith("https://isearch.asu.edu/profile"):
                links.add(link)
            elif link.startswith("https://catalog.apps.asu.edu/catalog") and any(
                term in link for term in ALLOWED_TERM_KEYWORDS
            ):
                links.add(link)

        return sorted(links)

    except Exception as e:
        print(f"⚠️ Error scraping {url}: {e}")
        return []


def crawl_children(faculty_list):
    """Step: For each profile, get subchildren."""
    deep_tree = defaultdict(list)

    for child in faculty_list:
        print(f"🌿 Crawling profile: {child}")
        sublinks = get_relevant_links(child)
        if sublinks:
            deep_tree[child] = sublinks
        else:
            print(f"⚠️ No sub-links found for {child}")
    return deep_tree


def save_full_tree(faculty_list, deep_tree):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for child in faculty_list:
            f.write(f"{child}\n")
            if child in deep_tree:
                for sub in deep_tree[child]:
                    f.write(f"    {sub}\n")
            f.write("\n")
    print(f"\n✅ Saved complete tree to {OUTPUT_FILE}")


if __name__ == "__main__":
    deep_tree = crawl_children(faculty_tree)
    save_full_tree(faculty_tree, deep_tree)
