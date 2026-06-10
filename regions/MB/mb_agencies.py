import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    open_writer, duckduckgo, parallel_scrape, AGENCY_FIELDS,
)

BASE = "https://www.gov.mb.ca"
SOURCES = [
    ("https://www.gov.mb.ca/cca/crown_corps.html", "Crown Corporation"),
    ("https://www.gov.mb.ca/cca/", "Crown Agency"),
]

MB_ENTITIES = [
    ("Manitoba Hydro", "https://www.hydro.mb.ca/", "Crown Corporation", "Crown Services"),
    ("Manitoba Public Insurance", "https://www.mpi.mb.ca/", "Crown Corporation", "Crown Services"),
    ("Liquor, Gaming and Cannabis Authority of Manitoba", "https://www.lgcamb.ca/", "Crown Corporation", "Finance"),
    ("Manitoba Liquor and Lotteries", "https://www.mbll.ca/", "Crown Corporation", "Finance"),
    ("Workers Compensation Board of Manitoba", "https://www.wcb.mb.ca/", "Crown Corporation", "Labour and Immigration"),
    ("Manitoba Housing", "https://www.gov.mb.ca/housing/", "Crown Agency", "Housing, Addictions and Homelessness"),
    ("Manitoba Museum", "https://manitobamuseum.ca/", "Museum", "Sport, Culture, Heritage and Tourism"),
    ("Winnipeg Art Gallery", "https://www.wag.ca/", "Museum / Gallery", "Sport, Culture, Heritage and Tourism"),
    ("Archives of Manitoba", "https://www.gov.mb.ca/chc/archives/", "Archives", "Sport, Culture, Heritage and Tourism"),
    ("Legal Aid Manitoba", "https://www.legalaid.mb.ca/", "Agency", "Justice and Attorney General"),
    ("Manitoba Human Rights Commission", "https://www.manitobahumanrights.ca/", "Commission", "Justice and Attorney General"),
    ("Ombudsman Manitoba", "https://www.ombudsman.mb.ca/", "Independent Agency", "Justice and Attorney General"),
    ("Manitoba Advocate for Children and Youth", "https://manitobaadvocate.ca/", "Independent Agency", "Families"),
    ("Information and Privacy Adjudicator", "https://ipc.mb.ca/", "Independent Agency", "Justice and Attorney General"),
    ("Manitoba Agricultural Services Corporation", "https://www.masc.mb.ca/", "Crown Corporation", "Agriculture"),
    ("Manitoba Film & Music", "https://mbfilmmusic.ca/", "Crown Agency", "Economic Development, Investment, Trade and Natural Resources"),
    ("Manitoba Chambers of Commerce", "https://mbchamber.mb.ca/", "Association", "Economic Development, Investment, Trade and Natural Resources"),
]


def _harvest_from_web(session):
    extra = []
    for url, etype in SOURCES:
        soup = get_soup(session, url)
        if not soup:
            continue
        content = soup.find("main") or soup.find("div", {"id": "content"}) or soup
        for li in content.find_all("li"):
            a = li.find("a", href=True)
            if not a:
                continue
            name = a.get_text(strip=True)
            href = a["href"]
            if not name or len(name) < 4:
                continue
            full = href if href.startswith("http") else BASE + href
            extra.append({
                "province": "MB", "type": etype, "name": name, "description": "",
                "website": full, "phone": "", "email": "", "address": "", "parent_ministry": "",
            })
    return extra


def _enrich(session, row):
    if not row["website"]:
        row["website"] = duckduckgo(f"{row['name']} Manitoba", session) or ""
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


def scrape_agencies(output_file="data/MB/agencies_mb.csv"):
    session = make_session()
    all_rows = [{
        "province": "MB", "type": etype, "name": name, "description": "",
        "website": website, "phone": "", "email": "", "address": "",
        "parent_ministry": ministry,
    } for name, website, etype, ministry in MB_ENTITIES]

    web_rows = _harvest_from_web(session)
    existing = {r["name"].lower() for r in all_rows}
    for r in web_rows:
        if r["name"].lower() not in existing:
            all_rows.append(r)

    print(f"[MB] Enriching {len(all_rows)} records concurrently…")
    enriched = parallel_scrape(session, all_rows, _enrich, max_workers=10)
    f, writer = open_writer(output_file, AGENCY_FIELDS)
    writer.writerows(enriched)
    f.close()
    print(f"[MB] Saved {len(enriched)} → {output_file}")
