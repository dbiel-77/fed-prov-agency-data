import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    open_writer, parallel_scrape, AGENCY_FIELDS,
)

BASE = "https://www.gov.nl.ca"
SOURCES = [
    ("https://www.gov.nl.ca/agencies/", "Agency / Board / Crown Corporation"),
    ("https://www.gov.nl.ca/crown-agencies-and-corporations/", "Crown Corporation"),
]

NL_ENTITIES = [
    ("Newfoundland and Labrador Hydro", "https://nlhydro.com/", "Crown Corporation", "Industry, Energy and Technology"),
    ("Newfoundland and Labrador Liquor Corporation", "https://www.nlliquor.com/", "Crown Corporation", "Finance"),
    ("Newfoundland and Labrador Housing Corporation", "https://nlhc.nl.ca/", "Crown Corporation", "Housing"),
    ("College of the North Atlantic", "https://www.cna.nl.ca/", "Crown Corporation", "Advanced Education, Skills and Labour"),
    ("The Rooms Corporation of Newfoundland and Labrador", "https://therooms.ca/", "Museum / Archives / Gallery", "Tourism, Culture, Arts and Recreation"),
    ("Newfoundland and Labrador Film Development Corporation", "https://nlfdc.ca/", "Crown Corporation", "Tourism, Culture, Arts and Recreation"),
    ("Human Rights Commission of Newfoundland and Labrador", "https://thinkhumanrights.ca/", "Commission", "Justice and Public Safety"),
    ("Office of the Citizens' Representative", "https://citizensrep.nl.ca/", "Independent Agency", "Justice and Public Safety"),
    ("Office of the Child and Youth Advocate", "https://cya.nl.ca/", "Independent Agency", "Families"),
    ("Privacy Commissioner of Newfoundland and Labrador", "https://oipc.nl.ca/", "Independent Agency", "Justice and Public Safety"),
    ("Newfoundland and Labrador English School District", "https://www.nlesd.ca/", "Crown Agency", "Education"),
    ("Legal Aid Commission", "https://legalaid.nl.ca/", "Agency", "Justice and Public Safety"),
    ("Newfoundland and Labrador Arts Council", "https://nlac.ca/", "Agency", "Tourism, Culture, Arts and Recreation"),
    ("Newfoundland and Labrador Tourism", "https://www.newfoundlandlabrador.com/", "Crown Agency", "Tourism, Culture, Arts and Recreation"),
    ("Newfoundland and Labrador Archives", "https://therooms.ca/provincial-archives/", "Archives", "Tourism, Culture, Arts and Recreation"),
]


def _harvest_from_web(session):
    extra = []
    for url, etype in SOURCES:
        soup = get_soup(session, url)
        if not soup:
            continue
        content = soup.find("main") or soup.find("div", {"id": "content"}) or soup
        for a in content.find_all("a", href=True):
            name = a.get_text(strip=True)
            href = a["href"]
            if not name or len(name) < 5:
                continue
            full = href if href.startswith("http") else urljoin(BASE, href)
            extra.append({
                "province": "NL", "type": etype, "name": name, "description": "",
                "website": full, "phone": "", "email": "", "address": "", "parent_ministry": "",
            })
    return extra


def _enrich(session, row):
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


def scrape_agencies(output_file="data/NL/agencies_nl.csv"):
    session = make_session()
    all_rows = [{
        "province": "NL", "type": etype, "name": name, "description": "",
        "website": website, "phone": "", "email": "", "address": "",
        "parent_ministry": ministry,
    } for name, website, etype, ministry in NL_ENTITIES]

    web_rows = _harvest_from_web(session)
    existing = {r["name"].lower() for r in all_rows}
    for r in web_rows:
        if r["name"].lower() not in existing:
            all_rows.append(r)

    print(f"[NL] Enriching {len(all_rows)} records concurrently…")
    enriched = parallel_scrape(session, all_rows, _enrich, max_workers=10)
    f, writer = open_writer(output_file, AGENCY_FIELDS)
    writer.writerows(enriched)
    f.close()
    print(f"[NL] Saved {len(enriched)} → {output_file}")
