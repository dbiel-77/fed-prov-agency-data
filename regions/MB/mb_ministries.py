"""
Manitoba — departments scraped from gov.mb.ca/government/departments.html
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

INDEX_URL = "https://www.gov.mb.ca/government/departments.html"
BASE = "https://www.gov.mb.ca"


def _fix_href(href):
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return BASE + href
    return href


def _dept_links(session):
    soup = get_soup(session, INDEX_URL)
    if not soup:
        return []
    links = []
    content = soup.find("main") or soup.find("div", {"id": "content"}) or soup
    for a in content.find_all("a", href=True):
        href = _fix_href(a["href"])
        name = a.get_text(strip=True)
        if not name or len(name) < 5:
            continue
        if re.search(r"gov\.mb\.ca|manitoba\.ca", href, re.I):
            if not re.search(r"#|login|search|news|media|feedback", href, re.I):
                links.append((href, name))
    seen = set()
    return [(u, n) for u, n in links if u not in seen and not seen.add(u)]


def _scrape_dept(session, item):
    url, name = item
    row = {
        "province": "MB", "type": "Department", "name": name,
        "about": "", "priorities": "", "website": url,
        "phone": "", "email": "", "address": "",
        "minister_name": "", "minister_phone": "", "minister_email": "",
        "minister_url": "", "minister_photo_url": "",
    }
    soup = get_soup(session, url)
    if not soup:
        return {**row, **{"twitter": "", "facebook": "", "youtube": "", "instagram": ""}}

    page_text = soup.get_text(" ", strip=True)
    content = soup.find("main") or soup.find("div", {"id": "content"}) or soup
    for p in content.find_all("p"):
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
        if re.search(r"minister|portrait|headshot", src + alt, re.I):
            row["minister_photo_url"] = src if src.startswith("http") else BASE + src
            break

    for a in soup.find_all("a", href=True):
        lt = a.get_text(strip=True).lower()
        if "contact" in lt or "minister" in lt:
            href = _fix_href(a["href"])
            full = href if href.startswith("http") else urljoin(BASE + "/", href)
            if full != url:
                row["minister_url"] = full
                cs = get_soup(session, full)
                if cs:
                    ct = cs.get_text(" ", strip=True)
                    row["minister_phone"] = extract_phone(ct)
                    row["minister_email"] = extract_email(ct)
                break

    addr = re.search(
        r"\d+\s+\w[\w\s,]+(?:Street|Ave|Avenue|Drive|Road|St\.?)[^\n]{0,60}(?:MB|Manitoba|Winnipeg)",
        page_text, re.I,
    )
    if addr:
        row["address"] = addr.group(0).strip()

    return {**row, **extract_socials(soup)}


def scrape_ministries(output_file="data/MB/ministries.csv"):
    session = make_session()
    print("[MB] Fetching department list from gov.mb.ca…")
    links = _dept_links(session)
    print(f"[MB] Scraping {len(links)} departments concurrently…")
    rows = parallel_scrape(session, links, _scrape_dept)
    f, writer = open_writer(output_file, MINISTRY_FIELDS)
    writer.writerows(rows)
    f.close()
    print(f"[MB] Saved {len(rows)} -> {output_file}")
