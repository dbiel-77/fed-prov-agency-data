"""
New Brunswick — departments and minister contact info.
Index migrated to: https://www.gnb.ca/en/org.html
Dept pages: https://www.gnb.ca/en/org/{slug}.html
"""
import sys
import re
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    extract_socials, open_writer, parallel_scrape, MINISTRY_FIELDS,
)

INDEX_URL = "https://www.gnb.ca/en/org.html"
BASE = "https://www.gnb.ca"


def _dept_links(session):
    soup = get_soup(session, INDEX_URL)
    if not soup:
        return []
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        name = a.get_text(strip=True)
        if not name or len(name) < 4:
            continue
        # Department pages live at /en/org/*.html
        if re.match(r"^/en/org/[a-z0-9\-]+\.html$", href):
            full = BASE + href
            links.append((full, name))
    seen = set()
    return [(u, n) for u, n in links if u not in seen and not seen.add(u)]


def _scrape_dept(session, item):
    url, name = item
    row = {
        "province": "NB", "type": "Department", "name": name,
        "about": "", "priorities": "", "website": url,
        "phone": "", "email": "", "address": "",
        "minister_name": "", "minister_phone": "", "minister_email": "",
        "minister_url": "", "minister_photo_url": "",
    }
    soup = get_soup(session, url)
    if not soup:
        return {**row, **{"twitter": "", "facebook": "", "youtube": "", "instagram": ""}}

    page_text = soup.get_text(" ", strip=True)
    for p in soup.find_all("p"):
        t = p.get_text(strip=True)
        if len(t) > 80:
            row["about"] = t
            break

    row["phone"] = extract_phone(page_text)
    row["email"] = extract_email(page_text)

    for tag in soup.find_all(["h1", "h2", "h3", "h4", "strong"]):
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
        if "minister" in lt or "contact" in lt:
            href = a["href"]
            full = href if href.startswith("http") else BASE + href
            if full != url:
                row["minister_url"] = full
                cs = get_soup(session, full)
                if cs:
                    ct = cs.get_text(" ", strip=True)
                    if not row["minister_phone"]:
                        row["minister_phone"] = extract_phone(ct)
                    if not row["minister_email"]:
                        row["minister_email"] = extract_email(ct)
                break

    addr = re.search(
        r"\d+\s+\w[\w\s,]+(?:Street|Ave|Avenue|Drive|Road|St\.?)[^\n]{0,60}(?:NB|New Brunswick)",
        page_text, re.I,
    )
    if addr:
        row["address"] = addr.group(0).strip()

    return {**row, **extract_socials(soup)}


def scrape_ministries(output_file="data/NB/ministries.csv"):
    session = make_session()
    print("[NB] Fetching department list from gnb.ca/en/org.html…")
    links = _dept_links(session)
    print(f"[NB] Scraping {len(links)} departments concurrently…")
    rows = parallel_scrape(session, links, _scrape_dept)
    f, writer = open_writer(output_file, MINISTRY_FIELDS)
    writer.writerows(rows)
    f.close()
    print(f"[NB] Saved {len(rows)} -> {output_file}")
