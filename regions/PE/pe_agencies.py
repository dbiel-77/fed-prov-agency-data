import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    open_writer, duckduckgo, parallel_scrape, AGENCY_FIELDS,
)

BASE = "https://www.princeedwardisland.ca"
SOURCES = [
    ("https://www.princeedwardisland.ca/en/topic/agencies-boards-and-commissions", "Agency / Board / Commission"),
    ("https://www.princeedwardisland.ca/en/topic/crown-corporations", "Crown Corporation"),
]
PE_MUSEUMS = [
    ("Confederation Centre of the Arts", "https://confederationcentre.com/", "Museum / Arts Centre", "Tourism and Culture"),
    ("PEI Museum and Heritage Foundation", "https://peimuseum.ca/", "Museum", "Tourism and Culture"),
    ("Public Archives and Records Office of PEI", "https://www.princeedwardisland.ca/en/information/paro", "Archives", "Education and Lifelong Learning"),
]


def _harvest(session, url, default_type):
    soup = get_soup(session, url)
    if not soup:
        return []
    content = soup.find("main") or soup.find("div", {"class": "view-content"}) or soup
    rows = []
    for a in content.find_all("a", href=True):
        name = a.get_text(strip=True)
        href = a["href"]
        if not name or len(name) < 5:
            continue
        full = href if href.startswith("http") else BASE + href
        rows.append({
            "province": "PE", "type": default_type, "name": name,
            "description": "", "website": full,
            "phone": "", "email": "", "address": "", "parent_ministry": "",
        })
    seen = set()
    return [r for r in rows if r["name"] not in seen and not seen.add(r["name"])]


def _enrich(session, row):
    if not row["website"]:
        row["website"] = duckduckgo(f"{row['name']} Prince Edward Island", session) or ""
    if row["website"] and row["website"].startswith("http"):
        s = get_soup(session, row["website"], timeout=10)
        if s:
            pt = s.get_text(" ", strip=True)
            row["phone"] = extract_phone(pt)
            row["email"] = extract_email(pt)
            for p in s.find_all("p"):
                t = p.get_text(strip=True)
                if len(t) > 60:
                    row["description"] = t
                    break
    return row


def scrape_agencies(output_file="data/PE/agencies_pe.csv"):
    session = make_session()
    all_rows = []
    for url, etype in SOURCES:
        all_rows.extend(_harvest(session, url, etype))
    for name, website, etype, ministry in PE_MUSEUMS:
        all_rows.append({
            "province": "PE", "type": etype, "name": name, "description": "",
            "website": website, "phone": "", "email": "", "address": "",
            "parent_ministry": ministry,
        })
    print(f"[PE] Enriching {len(all_rows)} records concurrently…")
    enriched = parallel_scrape(session, all_rows, _enrich, max_workers=10)
    f, writer = open_writer(output_file, AGENCY_FIELDS)
    writer.writerows(enriched)
    f.close()
    print(f"[PE] Saved {len(enriched)} → {output_file}")
