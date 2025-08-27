import argparse
import csv
import json
import random
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://www.civicinfo.bc.ca/ministries-and-crowns"
LIST_URL = f"{BASE}/gov/content/governments/organizational-structure/ministries-organizations/ministries"
MIN_PREFIX = "/gov/content/governments/organizational-structure/ministries-organizations/ministries/"

OUT_JSON = "agencies_data.json"
OUT_CSV = "agencies_data.csv"

SLEEP_MIN = 0.8
SLEEP_MAX = 1.8
TIMEOUT = 25

#to handle runtime error and exceptions
def make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=6,
        connect=6,
        read=6,
        backoff_factor=1.5,  # 0, 1.5, 3.0, 4.5, ...
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD", "OPTIONS"],
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15"
            ),
            "Accept-Language": "en-CA,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    )
    return s


SESSION = make_session()


def get_html(url: str) -> str:
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
    r = SESSION.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text

def scrape_agencies():
    html = get_html(LIST_URL)
    soup = BeautifulSoup(html, "html.parser")

    seen = set()
    ministries = []
    for a in soup.select(f'a[href^="{MIN_PREFIX}"]'):
        href = (a.get("href") or "").strip()
        # Skip the listing page itself; k
        if not href or href == MIN_PREFIX or not href.startswith(MIN_PREFIX):
            continue

        url = urljoin(BASE, href)
        if url in seen:
            continue

        name = a.get_text(strip=True)
    
        if not name:
            continue

        seen.add(url)
        ministries.append({"name": name, "url": url})

    if not ministries:
        raise RuntimeError("No ministry links found; page structure may have changed.")
    return ministries


def scrape_one_agency(ministry: dict) -> dict:
    record = {
        "name": ministry.get("name", "").strip(),
        "url": ministry.get("url", "").strip(),
        "title": "N/A",
        "description": "N/A",
        "minister_name": "N/A",
        "minister_title": "N/A",
        "minister_contact_info": "N/A"
        # add more details to scrape here, such as contact info for ex.
        #include minister /attorney general name
    }
    
    try:
        html = get_html(record["url"])
    except requests.RequestException as e:
        record["description"] = f"ERROR: {type(e).__name__}: {e}"
        return record

    soup = BeautifulSoup(html, "html.parser")

    # Page title (usually H1 → fallback H2)
    h1 = soup.find(["h1", "h2"])
    if h1 and h1.get_text(strip=True):
        record["title"] = h1.get_text(strip=True)

    # Meta description (if available)
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        record["description"] = desc["content"].strip()

    # --- Minister extraction ---
    # Strategy:
    # 1) Find a heading whose text is exactly "Agency" (case-insensitive).
    # 2) The next <h3> is typically the agency name, Note: CivicInfo doesn't include head of agency
    # 3) The following meaningful text often contains the role/title (e.g., "Minister of Health").
    def clean_text(t: str) -> str:
        return " ".join((t or "").split())

    minister_header = soup.find(
        lambda tag: tag.name in ["h2", "h3"] and tag.get_text(strip=True).lower() == "minister"
    )

    if minister_header:
        # Name tag = first <h3> after the "Minister" header
        name_tag = minister_header.find_next("h3")
        if name_tag and name_tag.get_text(strip=True):
            record["minister_name"] = clean_text(name_tag.get_text(strip=True))

        # Title/role: walk forward to first meaningful line of text after the name
        cur = name_tag.find_next() if name_tag else minister_header.find_next()
        while cur and hasattr(cur, "get_text") and clean_text(cur.get_text(strip=True)) in ("", record["minister_name"]):
            cur = cur.find_next()
        if cur and hasattr(cur, "get_text"):
            role_text = clean_text(cur.get_text(strip=True))
            # Heuristic: prefer lines that start with "Minister ..."
            if role_text.lower().startswith("minister"):
                record["minister_title"] = role_text

    # Fallback: if structure differs, try the first h3 on page near "Minister"
    if record["minister_name"] == "N/A":
        any_h3 = soup.find("h3")
        if any_h3 and ("minister" in soup.get_text(" ", strip=True).lower()):
            record["minister_name"] = clean_text(any_h3.get_text(strip=True))

    return record




#writing the json
def write_json(rows):
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)


def write_csv(rows):
    # Collect union of keys for CSV header
    fieldnames = set()
    for r in rows:
        fieldnames.update(r.keys())
    fieldnames = sorted(fieldnames)

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def scrape_all(limit=None):
    agencies = scrape_agencies()
    if limit is not None:
        agencies = agencies[: int(limit)]

    out = []
    for m in agencies:
        print(f"Scraping: {m['name']}")
        out.append(scrape_one_agency(m))

    print(f"\nScraped {len(out)} agencies.")
    write_json(out)
    write_csv(out)


def main():
    parser = argparse.ArgumentParser(description="Scrape BC agencies list & details.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of agencies (debug)")
    args = parser.parse_args()
    scrape_all(limit=args.limit)


if __name__ == "__main__":
    main()