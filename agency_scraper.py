#!/usr/bin/env python3
# agency_scraper.py — CivicInfo BC detail crawler (follows "Next >", extracts robustly)

import argparse
import csv
import json
import random
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from curl_cffi import requests  # HTTP/2 + Chrome JA3, avoids most 403s

BASE        = "https://www.civicinfo.bc.ca"
DETAIL_BASE = f"{BASE}/ministries-and-crowns"

OUT_JSON = "agencies_data.json"
OUT_CSV  = "agencies_data.csv"

SLEEP_MIN = 0.6
SLEEP_MAX = 1.4
TIMEOUT   = 25

# Keep only items whose classification CONTAINS this phrase (case-insensitive)
ONLY_AGENCIES = True
AGENCY_MATCH  = "provincial central agency"

# Label variants 
LABELS = {
    "mail":   ("mail:", "mailing:", "mailing address:"),
    "street": ("street:",),
    "phone":  ("phone:", "ph:", "tel:"),
    "fax":    ("fax:", "fx:"),
}

TITLE_PARENS = re.compile(r"\(([^)]+)\)")

def _norm(s: str) -> str:
    return " ".join((s or "").split())

#  HTTP 
def make_session() -> requests.Session:
    return requests.Session(impersonate="chrome")

SESSION = make_session()

def get_html(url: str, referer: str) -> str:
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/126.0.0.0 Safari/537.36"),
        "Referer": referer,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Host": urlparse(url).netloc,
    }
    attempts, last = 5, None
    for i in range(1, attempts + 1):
        try:
            r = SESSION.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code in (403, 429) and i < attempts:
                time.sleep((1.35 ** i) + random.uniform(0.2, 0.7))
                continue
            r.raise_for_status()
            return r.text
        except (requests.HTTPError, requests.RequestsError) as e:
            last = e
            if i < attempts:
                time.sleep((1.35 ** i) + random.uniform(0.2, 0.7))
                continue
            raise
    raise last or RuntimeError("Failed to fetch")

# Parsing helpers 
def _is_mail_label(text: str) -> bool:
    """True if text starts with any Mail/Mailing label variant."""
    low = (text or "").strip().lower()
    return any(low.startswith(v) for v in LABELS["mail"])

def _best_header(main: Tag) -> Tag | None:
    """
    Find the REAL agency header by locating the first 'Mail:' label and walking
    backward to the nearest H1/H2/H3. This avoids the page chrome header.
    """
    mail_node = main.find(string=lambda s: isinstance(s, str) and _is_mail_label(s))
    if mail_node:
        anchor = mail_node if isinstance(mail_node, Tag) else mail_node.parent
        hdr = anchor.find_previous(lambda t: isinstance(t, Tag) and t.name in ("h1", "h2", "h3"))
        if hdr:
            return hdr

    # Fallback: pick  first H1/H2 with section contains a Mail label
    for hdr in main.find_all(["h1", "h2"]):
        for el in hdr.next_elements:
            if isinstance(el, Tag) and el.name in ("h1", "h2", "h3") and el is not hdr:
                break
            if isinstance(el, NavigableString) and _is_mail_label(str(el)):
                return hdr
            if isinstance(el, Tag) and _is_mail_label(el.get_text(" ", strip=True)):
                return hdr

    # Last-ditch fallback
    hs2 = main.find_all("h2")
    if hs2:
        return hs2[-1]
    hs1 = main.find_all("h1")
    if hs1:
        return hs1[-1]
    return None

def _pick_description(hdr: Tag) -> str:
    """First substantial <p> after the header, before the next header."""
    for el in hdr.next_elements:
        if isinstance(el, Tag) and el.name in ("h1", "h2", "h3") and el is not hdr:
            break
        if isinstance(el, Tag) and el.name == "p":
            txt = _norm(el.get_text(" ", strip=True))
            if len(txt) >= 60:
                return txt
    return ""

def _extract_classification(soup: BeautifulSoup, hdr: Tag) -> str:
    """
    1) Scan forward from H1/H2 until 'Mail:' line; take a short line with
       'agency/corporation/ministry/office' as classification.
    2) Fallback to last (...) in <title>.
    """
    for el in hdr.next_elements:
        if isinstance(el, Tag) and el.name in ("h1", "h2", "h3") and el is not hdr:
            break
        text = ""
        if isinstance(el, NavigableString):
            text = _norm(str(el))
        elif isinstance(el, Tag):
            text = _norm(el.get_text(" ", strip=True))
        if not text:
            continue
        if _is_mail_label(text):
            break
        low = text.lower()
        if any(k in low for k in ("agency", "corporation", "ministry", "office")) and len(text) <= 80:
            return text.strip()

    t = soup.find("title")
    if t and t.get_text(strip=True):
        m_all = TITLE_PARENS.findall(t.get_text(strip=True))
        if m_all:
            return _norm(m_all[-1])
    return "N/A"

#  Detail page 
def parse_detail(detail_url: str, referer: str) -> tuple[dict, str | None]:
    html = get_html(detail_url, referer=referer)
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find(id="main") or soup

    hdr = _best_header(main) or main.find(["h1", "h2"])
    name = _norm(hdr.get_text(strip=True)) if hdr else "N/A"
    classification = _extract_classification(soup, hdr) if hdr else "N/A"

    mailing_address = street_address = phone = fax = email = website = region = "N/A"

    if hdr:
        for el in hdr.next_elements:
            # stop at next header block
            if isinstance(el, Tag) and el.name in ("h1", "h2", "h3") and el is not hdr:
                break

            if isinstance(el, Tag) and el.name == "a" and el.has_attr("href"):
                href = (el["href"] or "").strip()
                txt  = _norm(el.get_text(" ", strip=True))
                if href.lower().startswith("mailto:") and email == "N/A":
                    email = href.split(":", 1)[1]
                elif href.lower().startswith("http") and website == "N/A":
                    host = urlparse(href).netloc.lower()
                    if host and "civicinfo.bc.ca" not in host:
                        website = href
                if region == "N/A" and txt and "," in txt and "bc" in txt.lower():
                    region = txt

            if isinstance(el, NavigableString):
                line = _norm(str(el))
                if not line:
                    continue
                low = line.lower()
                for key, variants in LABELS.items():
                    for v in variants:
                        if low.startswith(v):
                            val = line[len(v):].strip()
                            if key == "mail"   and mailing_address == "N/A": mailing_address = val
                            if key == "street" and street_address == "N/A":  street_address  = val
                            if key == "phone"  and phone == "N/A":           phone           = val
                            if key == "fax"    and fax == "N/A":             fax             = val

    description = _pick_description(hdr) if hdr else "N/A"
    if not description:
        description = "N/A"

    rec = {
        "name": name,
        "classification": classification,
        "mailing_address": mailing_address,
        "street_address": street_address,
        "phone": phone,
        "fax": fax,
        "email": email,
        "website": website,
        "region": region,
        "description": description,
        "url": detail_url,
    }

    # Find “Next >” link
    next_url = None
    for a in soup.select("a[href]"):
        txt = (a.get_text(" ", strip=True) or "").lower()
        if "next" in txt:  # matches "Next >"
            href = a.get("href") or ""
            if href:
                next_url = href if bool(urlparse(href).netloc) else urljoin(BASE, href)
            break

    return rec, next_url

#  Writers 
def write_json(rows, path=OUT_JSON):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

def write_csv(rows, path=OUT_CSV):
    cols = [
        "name","classification","mailing_address","street_address",
        "phone","fax","email","website","region","description","url"
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})

#
def crawl_details(start_id: int, limit: int | None, only_agencies: bool) -> list[dict]:
    """
    Start from ?id=<start_id>, follow “Next >” links until exhausted or `limit`.
    `limit` = pages visited (not kept). De-dupe by id.
    """
    start_url = f"{DETAIL_BASE}?id={start_id}"
    referer   = BASE
    visited   = set()
    out       = []
    url       = start_url
    steps     = 0

    while url:
        p  = urlparse(url)
        qs = parse_qs(p.query or "")
        cur_id = int(qs.get("id", ["0"])[0]) if "id" in qs and qs["id"][0].isdigit() else None
        if cur_id is not None:
            if cur_id in visited:
                break
            visited.add(cur_id)

        rec, next_url = parse_detail(url, referer=referer)

        # Filter: contains, not strict equality (handles spacing/case)
        keep = (not only_agencies) or (AGENCY_MATCH in rec.get("classification","").strip().lower())
        if keep:
            out.append(rec)
            print(f"Scraped: {rec['name']}  [{rec['classification']}]")
        else:
            
            
            pass

        steps += 1
        if limit and steps >= limit:
            break

        referer = url
        url     = next_url

    return out

def main():
    ap = argparse.ArgumentParser(description="CivicInfo BC — crawl details via Next, extract fields.")
    ap.add_argument("--start-id", type=int, default=812, help="Seed detail id (default: 812 = ALC)")
    ap.add_argument("--limit", type=int, default=None, help="Max detail pages to visit (safety cap)")
    ap.add_argument("--all", action="store_true", help="Do NOT filter; include all classifications")
    ap.add_argument("--out-json", default=OUT_JSON)
    ap.add_argument("--out-csv",  default=OUT_CSV)
    args = ap.parse_args()

    rows = crawl_details(
        start_id=args.start_id,
        limit=args.limit,
        only_agencies=(not args.all),
    )
    print(f"\nTotal kept: {len(rows)}")
    write_json(rows, path=args.out_json)
    write_csv(rows,  path=args.out_csv)

if __name__ == "__main__":
    main()
