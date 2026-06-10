"""
Federal departments, agencies, Crown corporations, museums.
Source: https://www.canada.ca/en/government/dept.html
"""
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    extract_socials, open_writer, parallel_scrape, AGENCY_FIELDS,
)

INDEX_URL = "https://www.canada.ca/en/government/dept.html"
MUSEUMS_URL = "https://www.canada.ca/en/canadian-heritage/services/funding/museums.html"


def _scrape_dept_index(session):
    soup = get_soup(session, INDEX_URL)
    if not soup:
        return []
    rows = []
    content = soup.find("main") or soup.find("div", {"id": "wb-cont"}) or soup
    for li in content.find_all("li"):
        a = li.find("a", href=True)
        if not a:
            continue
        name = a.get_text(strip=True)
        if not name or len(name) < 4:
            continue
        href = a["href"]
        if not href.startswith("http"):
            href = urljoin(INDEX_URL, href)
        li_text = li.get_text(" ", strip=True)
        entity_type = li_text.replace(name, "").strip(" -–—|,") or "Department / Agency"
        rows.append({
            "province": "FED", "type": entity_type, "name": name,
            "description": "", "website": href,
            "phone": "", "email": "", "address": "", "parent_ministry": "",
        })
    return rows


def _scrape_museums(session):
    soup = get_soup(session, MUSEUMS_URL)
    if not soup:
        return []
    rows = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http") or "canada.ca" in href:
            continue
        name = a.get_text(strip=True)
        if len(name) < 6 or href in seen:
            continue
        seen.add(href)
        rows.append({
            "province": "FED", "type": "Federal Museum", "name": name,
            "description": "", "website": href,
            "phone": "", "email": "", "address": "", "parent_ministry": "Canadian Heritage",
        })
    return rows


def _enrich(session, row):
    url = row.get("website", "")
    if not url or not url.startswith("http"):
        return row
    soup = get_soup(session, url, timeout=12)
    if not soup:
        return row
    text = soup.get_text(" ", strip=True)
    row["phone"] = extract_phone(text)
    row["email"] = extract_email(text)
    # Stash social media in description since AGENCY_FIELDS has no social columns
    socials = extract_socials(soup)
    social_str = "; ".join(f"{k}: {v}" for k, v in socials.items() if v)
    if social_str:
        row["description"] = (row.get("description") or "") + " | " + social_str
    return row


def scrape_federal_agencies(output_file="data/FED/agencies_fed.csv"):
    session = make_session()
    print("[FED] Fetching federal agency index…")
    rows = _scrape_dept_index(session)
    museums = _scrape_museums(session)
    print(f"[FED] Found {len(rows)} entities + {len(museums)} museums")
    rows.extend(museums)

    print(f"[FED] Enriching {len(rows)} records concurrently…")
    enriched = parallel_scrape(session, rows, _enrich, max_workers=8)
    f, writer = open_writer(output_file, AGENCY_FIELDS)
    writer.writerows(enriched)
    f.close()
    print(f"[FED] Saved {len(enriched)} → {output_file}")
