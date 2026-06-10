"""
Alberta — public agencies, boards, commissions and Crown corporations.
Source: https://public-agency-list.alberta.ca/ (paginated, 25/page)
"""
import sys
import re
from pathlib import Path
from urllib.parse import urljoin

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    open_writer, duckduckgo, parallel_scrape, AGENCY_FIELDS,
)

BASE_URL = "https://public-agency-list.alberta.ca"
AB_BASE = "https://www.alberta.ca"


def _page_url(page_num):
    if page_num == 0:
        return BASE_URL + "/"
    return (
        f"{BASE_URL}/?currentPage={page_num}"
        f"&selectedPage={page_num + 1}"
        "&AgencyId=All&SearchFor=#frmSearch"
    )


def _parse_page(soup):
    """Extract (name, ministry, description) triples from one listing page."""
    grids = (soup.find("main") or soup).find_all("div", class_="goa-grid-100-100-100")
    agencies = []
    i = 0
    while i < len(grids):
        g = grids[i]
        strong = g.find("strong")
        if strong and not g.find("input", attrs={"name": "agencyIDInput"}):
            # This is a name+ministry grid
            name = strong.get_text(strip=True)
            h3s = g.find_all("h3")
            ministry = ""
            for h3 in h3s:
                t = h3.get_text(strip=True)
                if t != name and t:
                    ministry = t
                    break
            # The very next grid with agencyIDInput is the description
            desc = ""
            if i + 1 < len(grids):
                next_g = grids[i + 1]
                if next_g.find("input", attrs={"name": "agencyIDInput"}):
                    p = next_g.find("p")
                    if p:
                        desc = p.get_text(strip=True)
            if name:
                agencies.append((name, ministry, desc))
        i += 1
    return agencies


def _collect_all(session):
    """Walk all pagination pages and return all (name, ministry, desc) triples."""
    all_agencies = []
    for page_num in range(20):  # max 20 pages
        url = _page_url(page_num)
        soup = get_soup(session, url, timeout=15)
        if not soup:
            break
        batch = _parse_page(soup)
        if not batch:
            break
        all_agencies.extend(batch)
        print(f"[AB] Page {page_num}: {len(batch)} agencies")
    return all_agencies


def _name_to_slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _enrich(session, item):
    name, ministry, desc = item
    row = {
        "province": "AB", "name": name,
        "type": "Public Agency",
        "description": desc,
        "website": "",
        "phone": "", "email": "", "address": "",
        "parent_ministry": ministry,
    }

    # Try alberta.ca/{slug} first
    slug = _name_to_slug(name)
    candidate = f"{AB_BASE}/{slug}"
    soup = get_soup(session, candidate, timeout=8)
    if soup and soup.find("h1"):
        h1 = soup.find("h1").get_text(strip=True)
        # Confirm it's actually the right page
        if any(w.lower() in h1.lower() for w in name.split()[:2]):
            row["website"] = candidate
            pt = soup.get_text(" ", strip=True)
            row["phone"] = extract_phone(pt)
            row["email"] = extract_email(pt)
            return row

    # Fall back to DuckDuckGo
    found = duckduckgo(f"{name} Alberta government", session)
    if found:
        row["website"] = found
        s = get_soup(session, found, timeout=10)
        if s:
            pt = s.get_text(" ", strip=True)
            row["phone"] = extract_phone(pt)
            row["email"] = extract_email(pt)

    return row


def scrape_agencies(output_file="data/AB/agencies_ab.csv"):
    session = make_session()
    print("[AB] Collecting agencies from public-agency-list.alberta.ca…")
    triples = _collect_all(session)
    print(f"[AB] Enriching {len(triples)} agencies concurrently…")
    enriched = parallel_scrape(session, triples, _enrich, max_workers=6)
    f, writer = open_writer(output_file, AGENCY_FIELDS)
    writer.writerows(enriched)
    f.close()
    print(f"[AB] Saved {len(enriched)} -> {output_file}")
