import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time


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


# term=2261 means Spring 2026
# term=2257 means Fall 2025
# term=2254 means Summer 2025

ALLOWED_TERM_KEYWORDS = ["&term=2261", "&term=2257", "&term=2254"]
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
SAVE_DIR = "data_new"
os.makedirs(SAVE_DIR, exist_ok=True)
# --------------------------------------------------


def get_relevant_links(url):
    """Extract catalog classlist links (children) from faculty profile pages."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            print(f"❌ Failed {url}: {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        links = set()

        for a in soup.find_all("a", href=True):
            link = urljoin(url, a["href"]).split("#")[0]
            if (
                link.startswith("https://catalog.apps.asu.edu/catalog/classes/classlist")
                and any(term in link for term in ALLOWED_TERM_KEYWORDS)
            ):
                links.add(link)

        return sorted(links)

    except Exception as e:
        print(f"⚠️ Error scraping {url}: {e}")
        return []


def extract_faculty_text(url):
    """Extract readable text from a faculty profile."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"❌ Failed ({resp.status_code}): {url}")
            return ""

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove unwanted tags
        for tag in soup(["script", "style", "noscript", "footer", "header", "nav"]):
            tag.decompose()

        texts = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "span", "div"]):
            txt = tag.get_text(separator=" ", strip=True)
            if txt and len(txt) > 30:
                texts.append(txt)

        content = "\n".join(texts)
        if not content.strip():
            print(f"⚠️ No readable text at {url}")
        return content

    except Exception as e:
        print(f"⚠️ Error scraping faculty profile {url}: {e}")
        return ""



from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time, re
from urllib.parse import urlparse, parse_qs

TERM_MAP = {
    "2261": "Spring 2026",
    "2257": "Fall 2025",
    "2254": "Summer 2025"
}




def extract_course_details(page_url):
    """Extract full ASU course info (summary table + detail fields)."""
    try:
        # --- Determine semester name from URL ---
        query = parse_qs(urlparse(page_url).query)
        term_code = query.get("term", [""])[0]
        semester = TERM_MAP.get(term_code, f"Unknown ({term_code})")

        # --- Set up Selenium Chrome ---
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=options)
        driver.get(page_url)

        # Wait for either results or details to load
        try:
            WebDriverWait(driver, 25).until(
                EC.any_of(
                    EC.presence_of_element_located((By.ID, "class-results")),
                    EC.presence_of_element_located((By.ID, "class-details"))
                )
            )
        except Exception:
            print(f"⚠️ Timeout waiting for page to load: {page_url}")

        time.sleep(3)
        html = driver.page_source
        driver.quit()

        soup = BeautifulSoup(html, "html.parser")

        # ------------------ SUMMARY SECTION ------------------
        results_text = ""
        results_section = soup.find("div", id="class-results")
        if results_section:
            rows = results_section.select("div.class-accordion")
            if rows:
                blocks = []
                for div in rows:
                    def safe(sel):
                        el = div.select_one(sel)
                        return el.get_text(strip=True) if el else ""

                    course = safe(".class-results-cell.course span")
                    title = safe(".class-results-cell.title span")
                    number = safe(".class-results-cell.number div")
                    instructor = safe(".class-results-cell.instructor a")
                    location = safe(".class-results-cell.location div")
                    dates = safe(".class-results-cell.dates p")
                    units = safe(".class-results-cell.units")
                    seats = safe(".class-results-cell.seats div")

                    block = f"""Course: {course}
Title: {title}
Number: {number}
Instructor: {instructor}
Location: {location}
Dates: {dates}
Units: {units}
Seats: {seats}"""
                    blocks.append(block.strip())
                results_text = "\n\n---\n\n".join(blocks)

        # ------------------ DETAILS SECTION ------------------
        details_text = ""
        details = soup.find("div", id="class-details")
        if details:
            info = {}

            # Each <h5> heading followed by <p>, <ul>, or table content
            for h5 in details.find_all("h5"):
                label = h5.get_text(strip=True)
                values = []
                for sib in h5.find_next_siblings():
                    if sib.name == "h5":
                        break
                    txt = sib.get_text(" ", strip=True)
                    if txt:
                        values.append(txt)
                if values:
                    info[label] = " ".join(values)

            # Also include instructor link if present
            link = details.select_one("a.link-color[href]")
            if link:
                info["Instructor Link"] = link["href"]

            # Reserved Seats table
            table = details.find("table", class_="reserved-seats")
            if table:
                rows = []
                for tr in table.select("tbody tr"):
                    cols = [td.get_text(strip=True) for td in tr.find_all("td")]
                    rows.append(" | ".join(cols))
                info["Reserved Seat Information"] = "\n".join(rows)

            # Compose details text
            parts = []
            for k, v in info.items():
                parts.append(f"{k}: {v}")
            details_text = "\n".join(parts)

        # ------------------ COMBINE BOTH ------------------
        if not results_text and not details_text:
            print(f"⚠️ No data extracted from {page_url}")
            return ""

        combined = [f"📚 TERM: {semester}", f"URL: {page_url}"]
        if results_text:
            combined.append("=== COURSE LIST ===")
            combined.append(results_text)
        if details_text:
            combined.append("\n=== COURSE DETAILS ===")
            combined.append(details_text)

        print(f"✅ Extracted all info for {semester} from {page_url}")
        return "\n".join(combined).strip()

    except Exception as e:
        print(f"⚠️ Selenium error for {page_url}: {e}")
        return ""




def scrape_faculty_and_children(faculty_list):
    """Main function to scrape faculty and their catalog child pages."""
    for faculty in faculty_list:
        print(f"\n👩‍🏫 Faculty: {faculty}")
        faculty_text = extract_faculty_text(faculty)

        # Fetch course links (catalog child pages)
        child_links = get_relevant_links(faculty)
        all_course_text = []

        for child in child_links:
            print(f"   🌿 Course link: {child}")
            course_text = extract_course_details(child)
            if course_text:
                all_course_text.append(course_text)
            time.sleep(0.8)

        # Combine all content into one text file
        all_text = f"FACULTY PROFILE: {faculty}\n\n{faculty_text}\n\n"
        if all_course_text:
            all_text += "\n\n=== COURSES ===\n\n" + "\n\n".join(all_course_text)

        # Save output
        title = faculty.split("/")[-1] or "faculty"
        fname = f"{title}.txt"
        filepath = os.path.join(SAVE_DIR, fname)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(all_text)

        print(f"✅ Saved: {filepath}")
        time.sleep(1.2)

    print("\n✅ Completed scraping all faculty and courses.")


if __name__ == "__main__":
    scrape_faculty_and_children(faculty_tree)
