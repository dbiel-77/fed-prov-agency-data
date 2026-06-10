import sys
import re
from pathlib import Path
from urllib.parse import urljoin

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    extract_socials, open_writer, parallel_scrape, MINISTRY_FIELDS,
)

INDEX_URL = "https://www.gov.nl.ca/departments/"
BASE = "https://www.gov.nl.ca"


def _dept_links(session):
    soup = get_soup(session, INDEX_URL)
    if not soup:
        return []
    content = soup.find("main") or soup.find("div", {"id": "content"}) or soup
    links = []
    for a in content.find_all("a", href=True):
        href = a["href"]
        name = a.get_text(strip=True)
        if not name or len(name) < 5:
            continue
        if re.search(r"gov\.nl\.ca/[a-z\-]+/?$", href, re.I) and "/departments" not in href:
            full = href if href.startswith("http") else BASE + href
            links.append((full, name))
    seen = set()
    return [(u, n) for u, n in links if u not in seen and not seen.add(u)]


def _scrape_dept(session, item):
    url, name = item
    row = {
        "province": "NL", "type": "Department", "name": name,
        "about": "", "priorities": "", "website": url,
        "phone": "", "email": "", "address": "",
        "minister_name": "", "minister_phone": "", "minister_email": "",
        "minister_url": "", "minister_photo_url": "",
    }
    soup = get_soup(session, url)
    if not soup:
        return {**row, **{"twitter": "", "facebook": "", "youtube": "", "instagram": ""}}

    page_text = soup.get_text(" ", strip=True)
    for p in (soup.find("main") or soup.find("div", {"id": "content"}) or soup).find_all("p"):
        t = p.get_text(strip=True)
        if len(t) > 80:
            row["about"] = t
            break

    row["phone"] = extract_phone(page_text)
    row["email"] = extract_email(page_text)

    for tag in soup.find_all(["h2", "h3", "h4", "strong"]):
        t = tag.get_text(strip=True)
        if re.match(r"^(Hon\.|Honourable\s+)?[A-Z][a-z]+ [A-Z][a-z]+", t):
            row["minister_name"] = t
            break

    for img in soup.find_all("img"):
        src, alt = img.get("src", ""), img.get("alt", "")
        if re.search(r"minister|portrait|headshot|hon\.", src + alt, re.I):
            row["minister_photo_url"] = src if src.startswith("http") else BASE + src
            break

    for a in soup.find_all("a", href=True):
        lt = a.get_text(strip=True).lower()
        if "contact" in lt or "minister" in lt:
            href = a["href"]
            full = href if href.startswith("http") else urljoin(BASE, href)
            if full != url:
                row["minister_url"] = full
                cs = get_soup(session, full)
                if cs:
                    ct = cs.get_text(" ", strip=True)
                    row["minister_phone"] = extract_phone(ct)
                    row["minister_email"] = extract_email(ct)
                break

    addr = re.search(r"\d+\s+\w[\w\s,]+(?:Street|Ave|Avenue|Drive|Road|St\.?),?\s*\w[\w\s]*,?\s*(?:NL|St\. John)", page_text, re.I)
    if addr:
        row["address"] = addr.group(0).strip()

    return {**row, **extract_socials(soup)}


def scrape_ministries(output_file="data/NL/ministries.csv"):
    session = make_session()
    print("[NL] Fetching department list…")
    links = _dept_links(session)
    print(f"[NL] Scraping {len(links)} departments concurrently…")
    rows = parallel_scrape(session, links, _scrape_dept)
    f, writer = open_writer(output_file, MINISTRY_FIELDS)
    writer.writerows(rows)
    f.close()
    print(f"[NL] Saved {len(rows)} → {output_file}")
