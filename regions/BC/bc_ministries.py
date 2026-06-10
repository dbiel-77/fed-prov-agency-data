import sys
import re
from pathlib import Path
from urllib.parse import urljoin

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    extract_socials, open_writer, parallel_scrape, MINISTRY_FIELDS,
)

INDEX_URL = (
    "https://www2.gov.bc.ca/gov/content/governments/"
    "organizational-structure/ministries-organizations"
)
BASE = "https://www2.gov.bc.ca"


def _ministry_links(session):
    soup = get_soup(session, INDEX_URL)
    if not soup:
        return []
    links = []
    content = soup.find("div", {"id": "content"}) or soup.find("main") or soup
    for a in content.find_all("a", href=True):
        href = a["href"]
        if "/ministries-organizations/" in href and href.count("/") > 6:
            full = href if href.startswith("http") else BASE + href
            text = a.get_text(strip=True)
            if text and (full, text) not in links:
                links.append((full, text))
    return links


def _scrape_ministry(session, item):
    url, name = item
    row = {
        "province": "BC", "type": "Ministry", "name": name,
        "about": "", "priorities": "", "website": url,
        "phone": "", "email": "", "address": "",
        "minister_name": "", "minister_phone": "", "minister_email": "",
        "minister_url": "", "minister_photo_url": "",
    }
    soup = get_soup(session, url)
    if not soup:
        return {**row, **{"twitter": "", "facebook": "", "youtube": "", "instagram": ""}}

    main = soup.find("div", {"id": "content"}) or soup.find("main") or soup
    for p in main.find_all("p"):
        t = p.get_text(strip=True)
        if len(t) > 60:
            row["about"] = t
            break

    for tag in soup.find_all(["h2", "h3", "h4"]):
        t = tag.get_text(strip=True)
        if re.match(r"^(Hon\.|Honourable\s)?[A-Z][a-z]+ [A-Z][a-z]+", t):
            row["minister_name"] = t
            break

    img = soup.find("img", src=re.compile(r"minister|portrait|headshot", re.I))
    if img:
        src = img.get("src", "")
        row["minister_photo_url"] = src if src.startswith("http") else BASE + src

    page_text = soup.get_text(" ", strip=True)
    row["phone"] = extract_phone(page_text)
    row["email"] = extract_email(page_text)

    for a in soup.find_all("a", href=True, string=re.compile(r"contact|minister", re.I)):
        href = a["href"]
        full = href if href.startswith("http") else BASE + href
        row["minister_url"] = full
        cs = get_soup(session, full)
        if cs:
            ct = cs.get_text(" ", strip=True)
            row["minister_phone"] = extract_phone(ct)
            row["minister_email"] = extract_email(ct)
        break

    return {**row, **extract_socials(soup)}


def scrape_ministries(output_file="data/BC/ministries.csv"):
    session = make_session()
    print("[BC] Fetching ministry list…")
    links = _ministry_links(session)
    print(f"[BC] Scraping {len(links)} ministries concurrently…")
    rows = parallel_scrape(session, links, _scrape_ministry)
    f, writer = open_writer(output_file, MINISTRY_FIELDS)
    writer.writerows(rows)
    f.close()
    print(f"[BC] Saved {len(rows)} ministries → {output_file}")
