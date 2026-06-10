import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    open_writer, duckduckgo, parallel_scrape, AGENCY_FIELDS,
)

BASE = "https://www2.gnb.ca"
SOURCES = [
    ("https://www2.gnb.ca/content/gnb/en/departments/executive_council_office/crown_corporations_and_agencies.html", "Crown Corporation / Agency"),
    ("https://www2.gnb.ca/content/gnb/en/departments/executive_council_office/boards_commissions.html", "Board / Commission"),
]
NB_MUSEUMS = [
    ("New Brunswick Museum", "https://www.nbm-mnb.ca/", "Museum", "Tourism, Heritage and Culture"),
    ("Beaverbrook Art Gallery", "https://beaverbrookartgallery.org/", "Museum / Gallery", "Tourism, Heritage and Culture"),
    ("Provincial Archives of New Brunswick", "https://archives.gnb.ca/", "Archives", "Tourism, Heritage and Culture"),
]


def _harvest(session, url, default_type):
    soup = get_soup(session, url)
    if not soup:
        return []
    content = soup.find("main") or soup.find("div", {"class": "parsys"}) or soup
    rows = []
    current_ministry = ""
    for tag in content.find_all(["h2", "h3", "h4", "li"]):
        tn, text = tag.name, tag.get_text(strip=True)
        if tn in ("h2", "h3", "h4"):
            current_ministry = text
            continue
        if tn == "li":
            a = tag.find("a", href=True)
            name = a.get_text(strip=True) if a else text
            href = a["href"] if a else ""
            if not name or len(name) < 4:
                continue
            full = href if href.startswith("http") else (BASE + href if href.startswith("/") else "")
            rows.append({
                "province": "NB", "type": default_type, "name": name,
                "description": "", "website": full,
                "phone": "", "email": "", "address": "", "parent_ministry": current_ministry,
            })
    seen = set()
    return [r for r in rows if r["name"] not in seen and not seen.add(r["name"])]


def _enrich(session, row):
    if not row["website"]:
        row["website"] = duckduckgo(f"{row['name']} New Brunswick", session) or ""
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


def scrape_agencies(output_file="data/NB/agencies_nb.csv"):
    session = make_session()
    all_rows = []
    for url, etype in SOURCES:
        all_rows.extend(_harvest(session, url, etype))
    for name, website, etype, ministry in NB_MUSEUMS:
        all_rows.append({
            "province": "NB", "type": etype, "name": name, "description": "",
            "website": website, "phone": "", "email": "", "address": "",
            "parent_ministry": ministry,
        })
    print(f"[NB] Enriching {len(all_rows)} records concurrently…")
    enriched = parallel_scrape(session, all_rows, _enrich, max_workers=10)
    f, writer = open_writer(output_file, AGENCY_FIELDS)
    writer.writerows(enriched)
    f.close()
    print(f"[NB] Saved {len(enriched)} → {output_file}")
