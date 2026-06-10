"""
Yukon Territory — departments.
yukon.ca returns 403 for automated requests, so we seed from a known list
and attempt to enrich each page (best-effort).
"""
import sys
import re
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    extract_socials, open_writer, parallel_scrape, MINISTRY_FIELDS,
)

BASE = "https://yukon.ca"

YT_DEPARTMENTS = [
    ("Community Services", "https://yukon.ca/en/community-services"),
    ("Economic Development", "https://yukon.ca/en/economic-development"),
    ("Education", "https://yukon.ca/en/education"),
    ("Energy, Mines and Resources", "https://yukon.ca/en/energy-mines-and-resources"),
    ("Environment", "https://yukon.ca/en/environment-and-natural-resources"),
    ("Finance", "https://yukon.ca/en/finance"),
    ("French Language Services Directorate", "https://yukon.ca/en/french-language-services"),
    ("Health and Social Services", "https://yukon.ca/en/health-and-social-services"),
    ("Highways and Public Works", "https://yukon.ca/en/highways-and-public-works"),
    ("Justice", "https://yukon.ca/en/justice"),
    ("Tourism and Culture", "https://yukon.ca/en/tourism-and-culture"),
    ("Executive Council Office", "https://yukon.ca/en/executive-council-office"),
    ("Public Service Commission", "https://yukon.ca/en/public-service-commission"),
    ("Women's Directorate", "https://yukon.ca/en/womens-directorate"),
    ("Yukon Housing Corporation", "https://yukon.ca/en/yukon-housing-corporation"),
    ("Yukon Liquor Corporation", "https://yukon.ca/en/yukon-liquor-corporation"),
    ("Workers' Safety and Compensation Board", "https://wcb.yk.ca/"),
]


def _scrape_dept(session, item):
    name, url = item
    row = {
        "province": "YT", "type": "Department", "name": name,
        "about": "", "priorities": "", "website": url,
        "phone": "", "email": "", "address": "",
        "minister_name": "", "minister_phone": "", "minister_email": "",
        "minister_url": "", "minister_photo_url": "",
    }
    soup = get_soup(session, url)
    if not soup:
        return {**row, **{"twitter": "", "facebook": "", "youtube": "", "instagram": ""}}

    page_text = soup.get_text(" ", strip=True)
    main = soup.find("main") or soup
    for p in main.find_all("p"):
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
            href = a["href"]
            full = href if href.startswith("http") else BASE + href
            if full != url:
                row["minister_url"] = full
                cs = get_soup(session, full)
                if cs:
                    ct = cs.get_text(" ", strip=True)
                    row["minister_phone"] = extract_phone(ct)
                    row["minister_email"] = extract_email(ct)
                break

    addr = re.search(
        r"\d+\s+\w[\w\s,]+(?:Street|Ave|Avenue|Drive|Road|St\.?)[^\n]{0,60}(?:YT|Yukon|Whitehorse)",
        page_text, re.I,
    )
    if addr:
        row["address"] = addr.group(0).strip()

    return {**row, **extract_socials(soup)}


def scrape_ministries(output_file="data/YT/ministries.csv"):
    session = make_session()
    print(f"[YT] Scraping {len(YT_DEPARTMENTS)} departments concurrently…")
    rows = parallel_scrape(session, YT_DEPARTMENTS, _scrape_dept)
    f, writer = open_writer(output_file, MINISTRY_FIELDS)
    writer.writerows(rows)
    f.close()
    print(f"[YT] Saved {len(rows)} -> {output_file}")
