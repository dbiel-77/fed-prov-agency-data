import sys
import re
from pathlib import Path
from urllib.parse import urljoin

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    open_writer, parallel_scrape, AGENCY_FIELDS,
)

BASE = "https://www2.gov.bc.ca"
SOURCES = [
    (
        "https://www2.gov.bc.ca/gov/content/governments/organizational-structure/crown-corporations",
        "Crown Corporation",
    ),
    (
        "https://www2.gov.bc.ca/gov/content/governments/organizational-structure/boards-commissions-and-tribunals",
        "Board / Commission / Tribunal",
    ),
    (
        "https://www2.gov.bc.ca/gov/content/governments/organizational-structure/ministries-organizations",
        "Agency / Organization",
    ),
]


def _harvest_links(session, url, default_type):
    soup = get_soup(session, url)
    if not soup:
        return []
    content = soup.find("div", {"id": "content"}) or soup.find("main") or soup
    results = []
    for a in content.find_all("a", href=True):
        href = a["href"]
        name = a.get_text(strip=True)
        if not name or len(name) < 5:
            continue
        if any(x in href for x in ["#", "login", "search"]):
            continue
        if href.startswith("/") or href.startswith("http"):
            full = href if href.startswith("http") else BASE + href
            if full in (s[0] for s in SOURCES):
                continue
            results.append((full, name, default_type))
    seen = set()
    return [(u, n, t) for u, n, t in results if u not in seen and not seen.add(u)]


def _enrich(session, row):
    url = row["website"]
    if not url or not url.startswith("http"):
        return row
    soup = get_soup(session, url, timeout=12)
    if not soup:
        return row
    text = soup.get_text(" ", strip=True)
    row["phone"] = extract_phone(text)
    row["email"] = extract_email(text)
    main = soup.find("main") or soup.find("div", {"id": "content"}) or soup
    for p in main.find_all("p"):
        t = p.get_text(strip=True)
        if len(t) > 60:
            row["description"] = t
            break
    return row


def scrape_agencies(output_file="data/BC/agencies_bc.csv"):
    session = make_session()
    all_rows = []
    for url, etype in SOURCES:
        print(f"[BC] Harvesting {etype}…")
        for site_url, name, entity_type in _harvest_links(session, url, etype):
            all_rows.append({
                "province": "BC", "type": entity_type, "name": name,
                "description": "", "website": site_url,
                "phone": "", "email": "", "address": "", "parent_ministry": "",
            })

    print(f"[BC] Enriching {len(all_rows)} agency records concurrently…")
    enriched = parallel_scrape(session, all_rows, _enrich, max_workers=10)
    f, writer = open_writer(output_file, AGENCY_FIELDS)
    writer.writerows(enriched)
    f.close()
    print(f"[BC] Saved {len(enriched)} agencies → {output_file}")
