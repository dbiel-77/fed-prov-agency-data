import sys
import re
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    extract_socials, open_writer, parallel_scrape, MINISTRY_FIELDS,
)

INDEX_URL = "https://www.saskatchewan.ca/government/government-structure/ministries"
BASE = "https://www.saskatchewan.ca"


def _ministry_links(session):
    soup = get_soup(session, INDEX_URL)
    if not soup:
        return []
    links = []
    content = soup.find("main") or soup.find("div", {"id": "main-content"}) or soup
    for a in content.find_all("a", href=True):
        href = a["href"]
        name = a.get_text(strip=True)
        if "/government/government-structure/ministries/" in href and name and len(name) > 4:
            full = href if href.startswith("http") else BASE + href
            links.append((full, name))
    seen = set()
    return [(u, n) for u, n in links if u not in seen and not seen.add(u)]


def _scrape_ministry(session, item):
    url, name = item
    row = {
        "province": "SK", "type": "Ministry", "name": name,
        "about": "", "priorities": "", "website": url,
        "phone": "", "email": "", "address": "",
        "minister_name": "", "minister_phone": "", "minister_email": "",
        "minister_url": "", "minister_photo_url": "",
    }
    soup = get_soup(session, url)
    if not soup:
        return {**row, **{"twitter": "", "facebook": "", "youtube": "", "instagram": ""}}

    main = soup.find("main") or soup.find("div", {"id": "main-content"}) or soup
    page_text = soup.get_text(" ", strip=True)
    for p in main.find_all("p"):
        t = p.get_text(strip=True)
        if len(t) > 80:
            row["about"] = t
            break

    row["phone"] = extract_phone(page_text)
    row["email"] = extract_email(page_text)

    for tag in soup.find_all(["h2", "h3", "h4"]):
        t = tag.get_text(strip=True)
        if re.match(r"^(Hon\.|Honourable\s+)?[A-Z][a-z]+ [A-Z][a-z]+", t):
            row["minister_name"] = t
            break

    img = soup.find("img", src=re.compile(r"minister|portrait|headshot", re.I))
    if not img:
        img = soup.find("img", alt=re.compile(r"minister|portrait", re.I))
    if img:
        src = img.get("src", "")
        row["minister_photo_url"] = src if src.startswith("http") else BASE + src

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

    addr = re.search(
        r'\d+\s+\w[\w\s]+(?:Street|Ave|Avenue|Drive|Road|St\.?),?\s*\w[\w\s]*,?\s*SK',
        page_text, re.I,
    )
    if addr:
        row["address"] = addr.group(0).strip()

    return {**row, **extract_socials(soup)}


def scrape_ministries(output_file="data/SK/ministries.csv"):
    session = make_session()
    print("[SK] Fetching ministry list…")
    links = _ministry_links(session)
    print(f"[SK] Scraping {len(links)} ministries concurrently…")
    rows = parallel_scrape(session, links, _scrape_ministry)
    f, writer = open_writer(output_file, MINISTRY_FIELDS)
    writer.writerows(rows)
    f.close()
    print(f"[SK] Saved {len(rows)} → {output_file}")
