"""
Ontario — classified agencies, boards and commissions.
Source: https://www.pas.gov.on.ca/Home/Agencies-list
Detail pages have structured dl with URL, Address, Phone, Function.
"""
import sys
import re
from pathlib import Path
from urllib.parse import urljoin

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    open_writer, parallel_scrape, AGENCY_FIELDS,
)

INDEX_URL = "https://www.pas.gov.on.ca/Home/Agencies-list"
BASE = "https://www.pas.gov.on.ca"


def _build_rows(session):
    soup = get_soup(session, INDEX_URL)
    if not soup:
        return []

    rows = []
    table = soup.find("table")
    if not table:
        return []

    for tr in table.find("tbody").find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        ministry = tds[0].get_text(strip=True)
        a_tag = tds[1].find("a", href=True)
        if not a_tag:
            continue
        name = a_tag.get_text(strip=True)
        detail_url = urljoin(BASE, a_tag["href"])
        if not name or len(name) < 4:
            continue
        rows.append({
            "province": "ON", "name": name, "type": "Agency",
            "description": "", "website": detail_url,
            "phone": "", "email": "", "address": "",
            "parent_ministry": ministry,
        })
    return rows


def _dl_value(soup, label):
    """Extract value from <dl> where the preceding <dt> matches label."""
    for dt in soup.find_all("dt"):
        if label.lower() in dt.get_text(strip=True).lower():
            dd = dt.find_next_sibling("dd")
            if dd:
                return dd.get_text(" ", strip=True)
    return ""


def _enrich(session, row):
    detail_url = row.get("website", "")
    if not detail_url.startswith("http"):
        return row

    soup = get_soup(session, detail_url, timeout=12)
    if not soup:
        return row

    # Parse structured dl fields on PAS detail pages
    external_url = _dl_value(soup, "URL")
    if external_url:
        # Clean up — sometimes it's the display text not the href
        a = soup.find("dt", string=re.compile(r"^url$", re.I))
        if a:
            dd = a.find_next_sibling("dd")
            if dd:
                link = dd.find("a", href=True)
                external_url = link["href"] if link else external_url
        row["website"] = external_url.strip()

    addr_text = _dl_value(soup, "Address")
    if addr_text:
        row["address"] = " ".join(addr_text.split())

    phone_text = _dl_value(soup, "Phone")
    if phone_text:
        row["phone"] = extract_phone(phone_text) or phone_text[:50]

    func_text = _dl_value(soup, "Function")
    if func_text:
        row["description"] = func_text[:500]

    cls_text = _dl_value(soup, "Classification")
    if cls_text:
        row["type"] = cls_text

    if not row["email"]:
        row["email"] = extract_email(soup.get_text(" ", strip=True))

    return row


def scrape_agencies(output_file="data/ON/agencies_on.csv"):
    session = make_session()
    print("[ON] Building agency list from pas.gov.on.ca…")
    rows = _build_rows(session)
    print(f"[ON] Enriching {len(rows)} agencies concurrently…")
    enriched = parallel_scrape(session, rows, _enrich, max_workers=10)
    f, writer = open_writer(output_file, AGENCY_FIELDS)
    writer.writerows(enriched)
    f.close()
    print(f"[ON] Saved {len(enriched)} -> {output_file}")
