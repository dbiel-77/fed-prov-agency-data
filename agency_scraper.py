#!/usr/bin/env python3
# civicinfo_agencies_scraper.py — curl_cffi + strict "(Provincial Central Agency)" filter

import argparse
import csv
import json
import random
import time
import itertools
import re
from urllib.parse import urljoin, urlparse
import re
from bs4.element import NavigableString, Tag

AGENCY_PHRASE = "Provincial Central Agency"  # keep it strict
LINE_BLOCKS = {"li","p","td","th","div","section","article"}

from bs4 import BeautifulSoup
from curl_cffi import requests  # single requests import (Chrome impersonation)

# --- Config ---
BASE = "https://www.civicinfo.bc.ca"
LIST_URL = f"{BASE}/ministries-and-crowns"

OUT_JSON = "agencies_data.json"
OUT_CSV = "agencies_data.csv"

SLEEP_MIN = 0.8
SLEEP_MAX = 1.8
TIMEOUT = 25

# If you later want *all* agency types, set this to None and we’ll just look for "(...Agency...)"
AGENCY_PHRASE = "Provincial Central Agency"  # current ask: exactly these

# --- UA pool + headers ---
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
]
_UA_ITER = itertools.cycle(UA_POOL)


# HELPER
def _closest_anchor_for_label(node, stop_at):
    """
    Given a text node that equals "(Provincial Central Agency)",
    find the nearest <a> in the same block or immediate siblings.
    """
    # 1) same parent block
    parent = node.parent
    while parent and parent != stop_at and parent.name not in LINE_BLOCKS:
        parent = parent.parent

    # try in the block first
    if parent:
        a = parent.find("a", href=True)
        if a and a.get_text(strip=True):
            return a

    # 2) search a few previous siblings for an <a>
    cur = parent.previous_sibling if parent else node.previous_sibling
    hops = 0
    while cur and hops < 8:
        if getattr(cur, "name", None) in ("a",):
            a = cur if cur.has_attr("href") else None
            if a and a.get_text(strip=True):
                return a
        a = cur.find("a", href=True) if hasattr(cur, "find") else None
        if a and a.get_text(strip=True):
            return a
        cur = cur.previous_sibling
        hops += 1

    # 3) try next siblings (some markup puts label before/after link)
    cur = parent.next_sibling if parent else node.next_sibling
    hops = 0
    while cur and hops < 8:
        if getattr(cur, "name", None) in ("a",):
            a = cur if cur.has_attr("href") else None
            if a and a.get_text(strip=True):
                return a
        a = cur.find("a", href=True) if hasattr(cur, "find") else None
        if a and a.get_text(strip=True):
            return a
        cur = cur.next_sibling
        hops += 1

    return None




def _default_headers(url: str, referer: str):
    host = urlparse(url).netloc
    return {
        "User-Agent": next(_UA_ITER),
        "Referer": referer,
        "Host": host,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

def make_session() -> requests.Session:
    return requests.Session(impersonate="chrome")

SESSION = make_session()

def warm_up_session():
    try:
        SESSION.get(
            "https://www.civicinfo.bc.ca/",
            headers=_default_headers("https://www.civicinfo.bc.ca/", "https://www.civicinfo.bc.ca/"),
            timeout=TIMEOUT, allow_redirects=True,
        )
        time.sleep(random.uniform(0.6, 1.2))
        SESSION.get(
            LIST_URL,
            headers=_default_headers(LIST_URL, "https://www.civicinfo.bc.ca/"),
            timeout=TIMEOUT, allow_redirects=True,
        )
        time.sleep(random.uniform(0.6, 1.2))
    except requests.RequestsError:
        pass  # non-fatal

def get_html(url: str, referer: str = "https://www.civicinfo.bc.ca/") -> str:
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
    headers = _default_headers(url, referer)
    attempts = 5
    last_err = None
    for i in range(1, attempts + 1):
        try:
            r = SESSION.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code in (403, 429) and i < attempts:
                headers["User-Agent"] = next(_UA_ITER)
                time.sleep((1.4 ** i) + random.uniform(0.2, 0.8))
                continue
            r.raise_for_status()
            return r.text
        except (requests.HTTPError, requests.RequestsError) as e:
            last_err = e
            if i < attempts:
                time.sleep((1.4 ** i) + random.uniform(0.2, 0.8))
                continue
            raise
    raise last_err or RuntimeError("Failed to fetch URL")

# --- Agency extraction helpers ---

# Generic "(...Agency...)" detector (used if AGENCY_PHRASE is None)
AGENCY_IN_PARENS = re.compile(r"\((?:[^)]*?)agency[^)]*\)", re.I)
# Strip trailing "(...)" from the name
TRAILING_PARENS = re.compile(r"\s*\([^)]*\)\s*$")

BLOCK_BREAKS = {"div","section","article","header","footer","nav","table","thead","tbody","tfoot","tr"}

def _norm(s: str) -> str:
    return " ".join((s or "").split())

def _line_around_anchor(a, stop_at):
    """
    Build a 'line' by concatenating:
      - immediate previous siblings (until a block break / another <a> / <br>)
      - the anchor text
      - immediate next siblings (until a block break / another <a> / <br>)
    Captures cases where "(Provincial Central Agency)" is a sibling text node.
    """
    parts_before = []
    cur = a.previous_sibling
    hops = 0
    while cur and hops < 12:
        name = getattr(cur, "name", None)
        if name in BLOCK_BREAKS or name == "a" or name == "br":
            break
        text = cur.get_text(" ", strip=True) if hasattr(cur, "get_text") else str(cur)
        if text.strip():
            parts_before.append(text.strip())
        cur = cur.previous_sibling
        hops += 1
    parts_before.reverse()

    link_text = a.get_text(" ", strip=True)

    parts_after = []
    cur = a.next_sibling
    hops = 0
    while cur and hops < 12:
        name = getattr(cur, "name", None)
        if name in BLOCK_BREAKS or name == "a" or name == "br":
            break
        text = cur.get_text(" ", strip=True) if hasattr(cur, "get_text") else str(cur)
        if text.strip():
            parts_after.append(text.strip())
        cur = cur.next_sibling
        hops += 1

    return _norm(" ".join(parts_before + [link_text] + parts_after)), link_text

# --- FULL REPLACEMENT FOR scrape_agencies() ---
def scrape_agencies():
    html = get_html(LIST_URL, referer="https://www.civicinfo.bc.ca/")
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find(id="main") or soup

    seen = set()
    agencies = []

    phrase_rx = re.compile(r"\(\s*"+re.escape(AGENCY_PHRASE)+r"\s*\)", re.I)

    last_anchor = None

    for node in main.descendants:
        # Track last good <a>
        if isinstance(node, Tag) and node.name == "a" and node.has_attr("href"):
            txt = node.get_text(" ", strip=True)
            href = (node.get("href") or "").strip()
            if txt and href and not href.startswith("#"):
                last_anchor = node
            else:
                continue

        # When we encounter the label text, pair it with the last seen anchor
        elif isinstance(node, NavigableString):
            s = " ".join(str(node).split())
            if not s:
                continue
            if phrase_rx.search(s) and last_anchor:
                name = last_anchor.get_text(" ", strip=True)
                href = (last_anchor.get("href") or "").strip()
                if not name or not href:
                    continue

                abs_url = href if bool(urlparse(href).netloc) else urljoin(BASE, href)
                low = abs_url.lower().rstrip("/")

                # Skip chrome/self
                if low in (LIST_URL.lower().rstrip("/"), BASE.lower().rstrip("/")):
                    continue
                if any(x in low for x in ("/contact", "/login", "/privacy", "/terms", "/sitemap")):
                    continue
                if low in seen:
                    continue

                seen.add(low)
                agencies.append({
                    "name": name.strip(),
                    "url": abs_url,
                    "section": AGENCY_PHRASE,
                })

                # prevent one link from pairing with multiple nearby labels
                last_anchor = None

    if not agencies:
        # Debug: show a few doc-order snippets that include the phrase
        samples = []
        for node in main.strings:
            st = " ".join(str(node).split())
            if AGENCY_PHRASE.lower() in st.lower():
                samples.append(st)
                if len(samples) >= 10:
                    break
        hint = "\n- ".join(samples) if samples else "(no matching text nodes)"
        raise RuntimeError("No agencies found via streaming match. Sample texts:\n- " + hint)

    return agencies



# --- Detail page (best-effort title/description only) ---
def scrape_one_agency(item: dict) -> dict:
    record = {
        "name": item.get("name", "").strip(),
        "url": item.get("url", "").strip(),
        "section": item.get("section", "N/A").strip(),
        "title": "N/A",
        "description": "N/A",
    }

    try:
        html = get_html(record["url"], referer=LIST_URL)
    except (requests.RequestsError, requests.HTTPError) as e:
        record["description"] = f"ERROR: {type(e).__name__}: {e}"
        return record

    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        record["title"] = h1.get_text(strip=True)
    else:
        t = soup.find("title")
        if t and t.get_text(strip=True):
            record["title"] = t.get_text(strip=True)

    desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if desc and desc.get("content"):
        record["description"] = desc["content"].strip()
    else:
        p = soup.find("p")
        if p and p.get_text(strip=True):
            record["description"] = " ".join(p.get_text(" ", strip=True).split())[:500]

    return record

# --- Writers ---
def write_json(rows):
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

def write_csv(rows):
    fieldnames = set()
    for r in rows:
        fieldnames.update(r.keys())
    fieldnames = sorted(fieldnames)
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

# --- Orchestrator ---
def scrape_all(limit=None):
    warm_up_session()
    agencies = scrape_agencies()
    if limit is not None:
        agencies = agencies[: int(limit)]

    out = []
    for a in agencies:
        print(f"Scraping: {a['name']} ({a.get('section','N/A')})")
        out.append(scrape_one_agency(a))

    print(f"\nScraped {len(out)} agencies.")
    write_json(out)
    write_csv(out)

def main():
    parser = argparse.ArgumentParser(description="Scrape CivicInfo BC Ministries & Crowns agencies list & details.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of agencies (debug)")
    args = parser.parse_args()
    scrape_all(limit=args.limit)

if __name__ == "__main__":
    main()

# --- REPLACE OR ADD THESE BELOW YOUR OTHER HELPERS ---

