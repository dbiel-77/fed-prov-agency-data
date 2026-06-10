"""
Alberta — ministries scraped from alberta.ca/ministries
"""
import sys
import re
from pathlib import Path
from urllib.parse import urljoin

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    extract_socials, open_writer, parallel_scrape, MINISTRY_FIELDS,
)

INDEX_URL = "https://www.alberta.ca/ministries"
BASE = "https://www.alberta.ca"


def _ministry_links(session):
    soup = get_soup(session, INDEX_URL)
    if not soup:
        return []
    links = []
    for title in soup.select(".goa-title"):
        a = title.find("a", href=True)
        if not a:
            continue
        name = a.get_text(strip=True)
        href = a["href"]
        if not name:
            continue
        full = href if href.startswith("http") else urljoin(BASE, href)
        links.append((full, name))
    seen = set()
    return [(u, n) for u, n in links if u not in seen and not seen.add(u)]


def _scrape_ministry(session, item):
    url, name = item
    row = {
        "province": "AB", "type": "Ministry", "name": name,
        "about": "", "priorities": "", "website": url,
        "phone": "", "email": "", "address": "",
        "minister_name": "", "minister_phone": "", "minister_email": "",
        "minister_url": "", "minister_photo_url": "",
    }
    soup = get_soup(session, url)
    if not soup:
        return {**row, **{"twitter": "", "facebook": "", "youtube": "", "instagram": ""}}

    # About text
    about_tag = soup.select_one("p.goa-page-header--lede")
    if about_tag:
        row["about"] = about_tag.get_text(strip=True)

    page_text = soup.get_text(" ", strip=True)
    row["phone"] = extract_phone(page_text)
    row["email"] = extract_email(page_text)

    # Minister name: h3 containing "Minister" prefix
    for h3 in soup.find_all("h3"):
        t = h3.get_text(strip=True)
        if t.startswith("Minister"):
            # Remove the word "Minister" prefix to get just the name
            minister = re.sub(r"^Ministers?\s*", "", t).strip()
            if minister:
                row["minister_name"] = minister
                break

    # Photo from goa-thumb div
    thumb = soup.select_one("div.goa-thumb img")
    if thumb:
        src = thumb.get("src", "")
        row["minister_photo_url"] = src if src.startswith("http") else BASE + src

    # Minister contact page
    for a in soup.find_all("a", href=True):
        lt = a.get_text(strip=True).lower()
        if "minister" in lt and "contact" in lt:
            href = a["href"]
            full = href if href.startswith("http") else urljoin(BASE, href)
            if full != url:
                row["minister_url"] = full
                ms = get_soup(session, full)
                if ms:
                    mt = ms.get_text(" ", strip=True)
                    row["minister_phone"] = extract_phone(mt)
                    row["minister_email"] = extract_email(mt)
                break

    addr = re.search(
        r"\d+\s+\w[\w\s,]+(?:Street|Ave|Avenue|Drive|Road|St\.?)[^\n]{0,80}(?:AB|Alberta|Edmonton|Calgary)",
        page_text, re.I,
    )
    if addr:
        row["address"] = addr.group(0).strip()

    return {**row, **extract_socials(soup)}


def scrape_ministries(output_file="data/AB/ministries.csv"):
    session = make_session()
    print("[AB] Fetching ministry list from alberta.ca/ministries…")
    links = _ministry_links(session)
    print(f"[AB] Scraping {len(links)} ministries concurrently…")
    rows = parallel_scrape(session, links, _scrape_ministry)
    f, writer = open_writer(output_file, MINISTRY_FIELDS)
    writer.writerows(rows)
    f.close()
    print(f"[AB] Saved {len(rows)} -> {output_file}")
