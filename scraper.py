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

BASE = "https://www2.gov.bc.ca"
LIST_URL = f"{BASE}/gov/content/governments/organizational-structure/ministries-organizations/ministries"
MIN_PREFIX = "/gov/content/governments/organizational-structure/ministries-organizations/ministries/"

OUT_JSON = "ministries_data.json"
OUT_CSV = "ministries_data.csv"

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

def scrape_ministries():
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


def scrape_one_ministry(ministry: dict) -> dict:
    record = {
        "name": ministry.get("name", "").strip(),
        "url": ministry.get("url", "").strip(),
        "title": "N/A",
        "description": "N/A",
        # add more details to scrape here, such as contact info for ex.
        #include minister /attorney general name
    }

    try:
        html = get_html(record["url"])
    except requests.RequestException as e:
        record["description"] = f"ERROR: {type(e).__name__}: {e}"
        return record

    soup = BeautifulSoup(html, "html.parser")

    # Page Title
    h1 = soup.find(["h1", "h2"])
    if h1 and h1.get_text(strip=True):
        record["title"] = h1.get_text(strip=True)

    # Meta description
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        record["description"] = desc["content"].strip()

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
    ministries = scrape_ministries()
    if limit is not None:
        ministries = ministries[: int(limit)]

    out = []
    for m in ministries:
        print(f"Scraping: {m['name']}")
        out.append(scrape_one_ministry(m))

    print(f"\nScraped {len(out)} ministries.")
    write_json(out)
    write_csv(out)


def main():
    parser = argparse.ArgumentParser(description="Scrape BC ministries list & details.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of ministries (debug)")
    args = parser.parse_args()
    scrape_all(limit=args.limit)


if __name__ == "__main__":
    main()