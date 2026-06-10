import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    open_writer, duckduckgo, parallel_scrape, AGENCY_FIELDS,
)

BASE = "https://www.novascotia.ca"
SOURCES = [
    ("https://www.novascotia.ca/government/agencies-and-crown-corporations/", "Agency / Crown Corporation"),
    ("https://www.novascotia.ca/government/boards-commissions-and-panels/", "Board / Commission"),
]
NS_MUSEUMS = [
    ("Nova Scotia Museum", "https://museum.novascotia.ca/", "Museum", "Communities, Culture, Tourism and Heritage"),
    ("Art Gallery of Nova Scotia", "https://artgalleryofnovascotia.ca/", "Museum / Gallery", "Communities, Culture, Tourism and Heritage"),
    ("Nova Scotia Archives", "https://archives.novascotia.ca/", "Archives", "Communities, Culture, Tourism and Heritage"),
]


def _harvest(session, url, default_type):
    soup = get_soup(session, url)
    if not soup:
        return []
    content = soup.find("main") or soup.find("div", {"id": "content"}) or soup
    rows = []
    current_ministry = ""
    for tag in content.find_all(["h2", "h3", "h4", "li"]):
        tn = tag.name
        text = tag.get_text(strip=True)
        if tn in ("h2", "h3", "h4"):
            current_ministry = text
            continue
        if tn == "li":
            a = tag.find("a", href=True)
            if not a:
                continue
            name = a.get_text(strip=True)
            href = a["href"]
            if not name or len(name) < 4:
                continue
            full = href if href.startswith("http") else urljoin(BASE, href)
            rows.append({
                "province": "NS", "type": default_type, "name": name,
                "description": "", "website": full,
                "phone": "", "email": "", "address": "", "parent_ministry": current_ministry,
            })
    seen = set()
    return [r for r in rows if r["name"] not in seen and not seen.add(r["name"])]


def _enrich(session, row):
    if not row["website"]:
        row["website"] = duckduckgo(f"{row['name']} Nova Scotia", session) or ""
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


def scrape_agencies(output_file="data/NS/agencies_ns.csv"):
    session = make_session()
    all_rows = []
    for url, etype in SOURCES:
        all_rows.extend(_harvest(session, url, etype))
    for name, website, etype, ministry in NS_MUSEUMS:
        all_rows.append({
            "province": "NS", "type": etype, "name": name, "description": "",
            "website": website, "phone": "", "email": "", "address": "",
            "parent_ministry": ministry,
        })

    print(f"[NS] Enriching {len(all_rows)} records concurrently…")
    enriched = parallel_scrape(session, all_rows, _enrich, max_workers=10)
    f, writer = open_writer(output_file, AGENCY_FIELDS)
    writer.writerows(enriched)
    f.close()
    print(f"[NS] Saved {len(enriched)} → {output_file}")
