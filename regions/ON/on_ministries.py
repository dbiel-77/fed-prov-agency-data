import sys
import re
from pathlib import Path
from urllib.parse import urljoin

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    extract_socials, open_writer, parallel_scrape, MINISTRY_FIELDS,
)

INDEX_URL = "https://www.ontario.ca/page/ministries"
BASE = "https://www.ontario.ca"


def _ministry_links(session):
    soup = get_soup(session, INDEX_URL)
    if not soup:
        return []
    links = []
    for a in (soup.find("main") or soup).find_all("a", href=True):
        href = a["href"]
        name = a.get_text(strip=True)
        if re.search(r"/page/ministry", href, re.I) and name:
            full = href if href.startswith("http") else BASE + href
            links.append((full, name))
    seen = set()
    return [(u, n) for u, n in links if u not in seen and not seen.add(u)]


def _scrape_ministry(session, item):
    url, name = item
    row = {
        "province": "ON", "type": "Ministry", "name": name,
        "about": "", "priorities": "", "website": url,
        "phone": "", "email": "", "address": "",
        "minister_name": "", "minister_phone": "", "minister_email": "",
        "minister_url": "", "minister_photo_url": "",
    }
    soup = get_soup(session, url)
    if not soup:
        return {**row, **{"twitter": "", "facebook": "", "youtube": "", "instagram": ""}}

    main = soup.find("main") or soup
    for p in main.find_all("p"):
        t = p.get_text(strip=True)
        if len(t) > 80:
            row["about"] = t
            break

    page_text = soup.get_text(" ", strip=True)
    row["phone"] = extract_phone(page_text)
    row["email"] = extract_email(page_text)

    for tag in soup.find_all(["h2", "h3", "h4", "p"]):
        t = tag.get_text(strip=True)
        if re.match(r"^(Hon\.|The Honourable\s)?[A-Z][a-z]+ [A-Z][a-z]+", t):
            row["minister_name"] = t
            break

    img = soup.find("img", src=re.compile(r"minister|portrait|headshot|photo", re.I))
    if img:
        src = img.get("src", "")
        row["minister_photo_url"] = src if src.startswith("http") else BASE + src

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"/page/minister-of", href, re.I):
            full = href if href.startswith("http") else BASE + href
            row["minister_url"] = full
            ms = get_soup(session, full)
            if ms:
                mt = ms.get_text(" ", strip=True)
                row["minister_phone"] = extract_phone(mt)
                row["minister_email"] = extract_email(mt)
                mimg = ms.find("img", src=re.compile(r"minister|portrait|headshot", re.I))
                if mimg and not row["minister_photo_url"]:
                    src = mimg.get("src", "")
                    row["minister_photo_url"] = src if src.startswith("http") else BASE + src
            break

    addr = re.search(
        r'\d+\s+\w[\w\s]+(?:Street|Ave|Avenue|Blvd|Drive|Road|St\.?),?\s*\w[\w\s]*,\s*ON',
        page_text, re.I,
    )
    if addr:
        row["address"] = addr.group(0).strip()

    return {**row, **extract_socials(soup)}


def scrape_ministries(output_file="data/ON/ministries.csv"):
    session = make_session()
    print("[ON] Fetching ministry list…")
    links = _ministry_links(session)
    print(f"[ON] Scraping {len(links)} ministries concurrently…")
    rows = parallel_scrape(session, links, _scrape_ministry)
    f, writer = open_writer(output_file, MINISTRY_FIELDS)
    writer.writerows(rows)
    f.close()
    print(f"[ON] Saved {len(rows)} → {output_file}")
