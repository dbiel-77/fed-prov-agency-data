import sys
import re
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    open_writer, duckduckgo, parallel_scrape, AGENCY_FIELDS,
)

BASE = "https://yukon.ca"
INDEX_URL = "https://yukon.ca/en/government/departments-and-entities"

YUKON_ENTITIES = [
    ("Yukon Housing Corporation", "https://yukonhousing.ca/", "Crown Corporation", "Community Services"),
    ("Yukon Development Corporation", "https://ydc.yk.ca/", "Crown Corporation", "Energy, Mines and Resources"),
    ("Yukon Energy Corporation", "https://yukonenergy.ca/", "Crown Corporation", "Energy, Mines and Resources"),
    ("Yukon Lottery Commission", "https://yukonlottery.ca/", "Crown Corporation", "Finance"),
    ("Yukon Workers' Compensation Health and Safety Board", "https://wcb.yk.ca/", "Crown Corporation", "Community Services"),
    ("Yukon Human Rights Commission", "https://yukonhumanrights.ca/", "Independent Agency", "Justice"),
    ("Yukon Environmental and Socio-Economic Assessment Board", "https://yesab.ca/", "Independent Agency", "Energy, Mines and Resources"),
    ("Yukon Archives", "https://yukon.ca/en/archives", "Archives", "Tourism and Culture"),
    ("Yukon Arts Centre", "https://yukonartscentre.com/", "Crown Agency", "Tourism and Culture"),
    ("MacBride Museum of Yukon History", "https://macbridemuseum.com/", "Museum", "Tourism and Culture"),
    ("Yukon Transportation Museum", "https://yukon.ca/en/transportation-museum", "Museum", "Highways and Public Works"),
    ("Old Log Church Museum", "https://oldlogchurch.ca/", "Museum", "Tourism and Culture"),
    ("Dawson City Museum", "https://dawsonmuseum.ca/", "Museum", "Tourism and Culture"),
    ("Yukon Beringia Interpretive Centre", "https://beringia.com/", "Museum", "Tourism and Culture"),
    ("SS Klondike National Historic Site", "https://parks.canada.ca/lhn-nhs/yt/klondike", "Museum / Historic Site", "Tourism and Culture"),
    ("Yukon Child and Youth Advocate Office", "https://ycya.ca/", "Independent Agency", "Justice"),
    ("Yukon Information and Privacy Commissioner", "https://ipc.gov.yk.ca/", "Independent Agency", "Justice"),
    ("Yukon Ombudsman", "https://ombudsman.yk.ca/", "Independent Agency", "Justice"),
    ("Yukon Land Use Planning Council", "https://ylupc.ca/", "Board / Commission", "Energy, Mines and Resources"),
    ("Yukon Public Utilities Board", "https://yukon.ca/en/public-utilities-board", "Board / Commission", "Finance"),
]


def _dynamic_harvest(session):
    soup = get_soup(session, INDEX_URL)
    if not soup:
        return []
    rows = []
    current_section = ""
    for tag in (soup.find("main") or soup).find_all(["h2", "h3", "li"]):
        tn, text = tag.name, tag.get_text(strip=True)
        if tn in ("h2", "h3"):
            current_section = text
            continue
        if tn == "li":
            a = tag.find("a", href=True)
            name = a.get_text(strip=True) if a else text
            href = a["href"] if a else ""
            if not name or len(name) < 5:
                continue
            full = href if href.startswith("http") else BASE + href
            if re.search(r"crown|corporation", current_section, re.I):
                etype = "Crown Corporation"
            elif re.search(r"board|commission|tribunal", current_section, re.I):
                etype = "Board / Commission"
            else:
                etype = "Agency"
            rows.append({
                "province": "YT", "type": etype, "name": name,
                "description": "", "website": full,
                "phone": "", "email": "", "address": "", "parent_ministry": current_section,
            })
    return rows


def _enrich(session, row):
    if not row["website"]:
        row["website"] = duckduckgo(f"{row['name']} Yukon", session) or ""
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


def scrape_agencies(output_file="data/YT/agencies_yt.csv"):
    session = make_session()
    all_rows = [{
        "province": "YT", "type": etype, "name": name, "description": "",
        "website": website, "phone": "", "email": "", "address": "",
        "parent_ministry": ministry,
    } for name, website, etype, ministry in YUKON_ENTITIES]

    dynamic = _dynamic_harvest(session)
    existing = {r["name"].lower() for r in all_rows}
    for r in dynamic:
        if r["name"].lower() not in existing:
            all_rows.append(r)

    print(f"[YT] Enriching {len(all_rows)} records concurrently…")
    enriched = parallel_scrape(session, all_rows, _enrich, max_workers=10)
    f, writer = open_writer(output_file, AGENCY_FIELDS)
    writer.writerows(enriched)
    f.close()
    print(f"[YT] Saved {len(enriched)} → {output_file}")
