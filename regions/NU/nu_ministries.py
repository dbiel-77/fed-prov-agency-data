import re
import csv
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin

NU_PAGE_DIR = "regions/NU/nunavut_pages"
OUTPUT_CSV = "data/NU/ministries.csv"

HEADERS = [
    "type", "about", "priorities", "website",
    "twitter", "facebook", "youtube", "instagram",
    "name", "photo_url", "minister_contact_number", "minister_url",
    "emails"
]

def normalize_title(text):
    return re.sub(r"[^a-z0-9]+", " ", text.strip().lower())

def parse_departments(filepath):
    with open(filepath, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    ministries = {}
    for art in soup.select("article.m-teaser"):
        a = art.select_one("h2.m-teaser__title a")
        desc = art.select_one(".m-wysiwyg p")

        if not a:
            continue

        title = a.get_text(strip=True)
        slug = a["href"].strip("/")
        full_url = urljoin("https://www.gov.nu.ca/", slug)
        description = desc.get_text(strip=True) if desc else ""

        ministries[normalize_title(title)] = {
            "type": title,
            "about": description,
            "priorities": "",
            "website": full_url,
            "twitter": "", "facebook": "", "youtube": "", "instagram": "",
            "name": "", "photo_url": "", "minister_contact_number": "",
            "minister_url": f"{full_url}/our-minister",
            "emails": ""
        }

    return ministries

def parse_minister_file(filepath):
    with open(filepath, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    name_tag = soup.select_one("h1.title span.field--name-title")
    name = name_tag.get_text(strip=True) if name_tag else ""

    duties_raw = [d.get_text(strip=True) for d in soup.select(".field--name-field-member-duties .field__item")]
    cleaned_duties = []
    ministry_keys = set()

    for duty in duties_raw:
        clean = re.sub(r"Minister (of|responsible for)", "", duty, flags=re.I).strip()
        if clean:
            cleaned_duties.append(duty)
            ministry_keys.add(normalize_title(f"Department of {clean}"))

    img_tag = soup.select_one(".field--name-field-member-photo img")
    photo_url = urljoin("https://www.assembly.nu.ca/", img_tag["src"]) if img_tag and img_tag.get("src") else ""

    contact_blocks = soup.select(".field--name-field-member-legislative, .field--name-field-member-constituency")
    phone = ""
    emails = set()

    for block in contact_blocks:
        text = block.get_text(separator=" ", strip=True)

        if not phone:
            match = re.search(r"\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}", text)
            if match:
                phone = match.group()

        emails.update(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text))

    bio_tag = soup.select_one(".field--name-body")
    bio = bio_tag.get_text(separator=" ", strip=True) if bio_tag else ""

    return {
        "name": name,
        "photo_url": photo_url,
        "minister_contact_number": phone,
        "emails": "; ".join(sorted(emails)),
        "ministry_keys": ministry_keys
    }


def scrape_nunavut_ministries():
    ministries = parse_departments(os.path.join(NU_PAGE_DIR, "departments.html"))

    for fname in os.listdir(NU_PAGE_DIR):
        if not re.match(r"\d{4}\.html$", fname):
            continue

        path = os.path.join(NU_PAGE_DIR, fname)
        data = parse_minister_file(path)

        matched = False
        for key in data["ministry_keys"]:
            if key in ministries:
                ministries[key].update({k: data[k] for k in data if k != "ministry_keys"})
                matched = True

        if not matched:
            print(f"WARNING: No match for {data['name']} — {data['duties']}")

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(ministries.values())
