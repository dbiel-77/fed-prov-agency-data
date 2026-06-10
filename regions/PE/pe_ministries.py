"""
Prince Edward Island — departments.
PEI's index page is a Drupal search interface, so we seed from a known list
and then enrich each page for contact details.
"""
import sys
import re
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    extract_socials, open_writer, parallel_scrape, MINISTRY_FIELDS,
)

BASE = "https://www.princeedwardisland.ca"

PE_DEPARTMENTS = [
    ("Agriculture", "https://www.princeedwardisland.ca/en/topic/agriculture"),
    ("Economic Development, Tourism and Culture", "https://www.princeedwardisland.ca/en/topic/economic-development-tourism-and-culture"),
    ("Education and Early Years", "https://www.princeedwardisland.ca/en/topic/education-and-early-years"),
    ("Environment, Energy and Climate Action", "https://www.princeedwardisland.ca/en/topic/environment-energy-and-climate-action"),
    ("Finance", "https://www.princeedwardisland.ca/en/topic/finance"),
    ("Health and Wellness", "https://www.princeedwardisland.ca/en/topic/health-and-wellness"),
    ("Housing, Land and Communities", "https://www.princeedwardisland.ca/en/topic/housing-land-and-communities"),
    ("Justice and Public Safety", "https://www.princeedwardisland.ca/en/topic/justice-and-public-safety"),
    ("Natural Resources and Rural Development", "https://www.princeedwardisland.ca/en/topic/natural-resources-and-rural-development"),
    ("Social Development and Housing", "https://www.princeedwardisland.ca/en/topic/social-development-and-housing"),
    ("Transportation and Infrastructure", "https://www.princeedwardisland.ca/en/topic/transportation-and-infrastructure"),
    ("Workforce, Advanced Learning and Population", "https://www.princeedwardisland.ca/en/topic/workforce-advanced-learning-and-population"),
    ("Executive Council Office", "https://www.princeedwardisland.ca/en/topic/executive-council"),
    ("Office of the Auditor General", "https://www.princeedwardisland.ca/en/information/auditor-general/auditor-general"),
]


def _scrape_dept(session, item):
    name, url = item
    row = {
        "province": "PE", "type": "Department", "name": name,
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

    for tag in soup.find_all(["h2", "h3", "strong"]):
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
        r"\d+\s+\w[\w\s,]+(?:Street|Ave|Avenue|Drive|Road|St\.?)[^\n]{0,60}(?:PE|PEI|Charlottetown)",
        page_text, re.I,
    )
    if addr:
        row["address"] = addr.group(0).strip()

    return {**row, **extract_socials(soup)}


def scrape_ministries(output_file="data/PE/ministries.csv"):
    session = make_session()
    print(f"[PE] Scraping {len(PE_DEPARTMENTS)} departments concurrently…")
    rows = parallel_scrape(session, PE_DEPARTMENTS, _scrape_dept)
    f, writer = open_writer(output_file, MINISTRY_FIELDS)
    writer.writerows(rows)
    f.close()
    print(f"[PE] Saved {len(rows)} -> {output_file}")
