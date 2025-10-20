import os, re, time, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============= CONFIG =============
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
SAVE_DIR = "data_final"
os.makedirs(SAVE_DIR, exist_ok=True)

TERM_MAP = {"2261": "Spring 2026", "2257": "Fall 2025", "2254": "Summer 2025"}
# =================================


# ---------- Faculty helpers ----------
def get_relevant_links(url):
    """Extract catalog classlist links (children) from faculty profile pages."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
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
    """Extract readable text from a faculty profile page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "footer", "header", "nav"]):
            tag.decompose()
        texts = [t.get_text(" ", strip=True) for t in soup.find_all(["h1", "h2", "h3", "p", "li", "span"]) if len(t.get_text(strip=True)) > 30]
        return "\n".join(texts)
    except Exception as e:
        print(f"⚠️ Faculty scrape error {url}: {e}")
        return ""






from selenium.webdriver import ActionChains



from selenium.webdriver import ActionChains



from selenium.webdriver import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, re
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup

TERM_MAP = {"2261": "Spring 2026", "2257": "Fall 2025", "2254": "Summer 2025"}


def extract_course_details(driver, page_url):
    """Extract detailed course info from ASU catalog course page using Selenium."""
    try:
        # Get term
        term_code = parse_qs(urlparse(page_url).query).get("term", [""])[0]
        semester = TERM_MAP.get(term_code, f"Unknown ({term_code})")

        driver.get(page_url)
        print(f"⏳ Waiting for {page_url}")

        # Wait for class results to load
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.ID, "class-results"))
        )
        time.sleep(1)

        courses = driver.find_elements(By.CSS_SELECTOR, "div.class-accordion")
        print(f"🟡 Found {len(courses)} courses on {page_url}")

        all_blocks = []

        # Helper to safely get text from nested selector
        def safe(selector):
            try:
                el = elem.find_element(By.CSS_SELECTOR, selector)
                return el.text.strip()
            except NoSuchElementException:
                return ""
            except Exception:
                return ""

        for idx, elem in enumerate(courses, start=1):
            try:
                # Scroll element into view
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                time.sleep(0.8)

                # Use the exact selector you found for the triangle <svg> expand button
                svg_selector = (
                    "#class-results > div > div.focus.class-accordion.odd > "
                    "div.class-results-cell.course.pointer.text-nowrap.pe-1.pull-left."
                    "d-none.d-lg-inline.border-focus.d-lg-flex.justify-content-between."
                    "align-items-center > i > svg"
                )

                # Try clicking the triangle icon
                try:
                    toggle_button = driver.find_element(By.CSS_SELECTOR, svg_selector)
                except NoSuchElementException:
                    # Fallback: try a generic arrow button
                    toggle_button = elem.find_element(By.CSS_SELECTOR, "svg, i, button")

                actions = ActionChains(driver)
                actions.move_to_element(toggle_button).pause(0.3).click().perform()
                time.sleep(1.5)

                # Wait for expanded content
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div#class-details"))
                )

                html = driver.page_source
                soup = BeautifulSoup(html, "html.parser")
                detail_div = soup.select_one("div#class-details")

                block = {
                    "Term": semester,
                    "URL": page_url,
                    "Course": safe(".class-results-cell.course span"),
                    "Title": safe(".class-results-cell.title span"),
                    "Number": safe(".class-results-cell.number div"),
                    "Instructor": safe(".class-results-cell.instructor a"),
                    "Location": safe(".class-results-cell.location div"),
                    "Dates": safe(".class-results-cell.dates p"),
                    "Units": safe(".class-results-cell.units"),
                    "Seats": safe(".class-results-cell.seats div"),
                }

                # Extract h5 sections (extra info)
                if detail_div:
                    for h5 in detail_div.find_all("h5"):
                        key = h5.get_text(strip=True)
                        vals = []
                        for sib in h5.find_next_siblings():
                            if sib.name == "h5":
                                break
                            text = sib.get_text(" ", strip=True)
                            if text:
                                vals.append(text)
                        if vals:
                            block[key] = " ".join(vals)

                    # Extract reserved seats table
                    table = detail_div.find("table", class_="reserved-seats")
                    if table:
                        rows = []
                        for tr in table.select("tbody tr"):
                            cols = [td.get_text(strip=True) for td in tr.find_all("td")]
                            rows.append(" | ".join(cols))
                        block["Reserved Seat Information"] = "\n".join(rows)

                all_blocks.append(block)
                time.sleep(0.8)

                # Collapse accordion again
                try:
                    actions.move_to_element(toggle_button).pause(0.2).click().perform()
                except Exception:
                    pass

            except Exception as e:
                print(f"⚠️ Error expanding course #{idx}: {e}")
                continue

        if not all_blocks:
            print(f"⚠️ No expanded details found in {page_url}")
            return ""

        # Format output for file
        formatted = []
        for block in all_blocks:
            formatted.append("\n".join(f"{k}: {v}" for k, v in block.items() if v))
        return "\n\n---\n\n".join(formatted)

    except Exception as e:
        print(f"⚠️ Selenium page error for {page_url}: {e}")
        return ""




# ---------- Master orchestrator ----------
def scrape_faculty_and_children(faculty_list):
    options = Options()
    # Comment next line if you want to see Chrome window open
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1600,1000")
    driver = webdriver.Chrome(options=options)

    for faculty in faculty_list:
        print(f"\n👩‍🏫 Faculty: {faculty}")
        faculty_text = extract_faculty_text(faculty)
        child_links = get_relevant_links(faculty)

        all_course_text = []
        for child in child_links:
            print(f"   🌿 Course link: {child}")
            course_text = extract_course_details(driver, child)
            if course_text:
                all_course_text.append(course_text)
            time.sleep(1)

        combined = f"FACULTY PROFILE: {faculty}\n\n{faculty_text}\n\n"
        if all_course_text:
            combined += "\n\n=== COURSES ===\n\n" + "\n\n".join(all_course_text)
        
        print("all Data collected, saving to file...",combined)

        fname = os.path.join(SAVE_DIR, faculty.split('/')[-1] + ".txt")
        with open(fname, "w", encoding="utf-8") as f:
            f.write(combined)
        print(f"✅ Saved: {fname}\n")

    driver.quit()
    print("\n✅ Completed scraping all faculty and courses.")
# ==========================================

if __name__ == "__main__":
    scrape_faculty_and_children(faculty_tree)
