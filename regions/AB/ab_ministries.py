import re
import csv
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

SOCIAL_SELECTORS = {
    'twitter': "a[href*='twitter.com']",
    'facebook': "a[href*='facebook.com']",
    'youtube': "a[href*='youtube.com']",
    'instagram': "a[href*='instagram.com']"
}


def get_ministry_data(soup, url, ministry_name):
    about = soup.select_one('p.goa-page-header--lede')
    socials = {
        platform: (
            tag["href"] if (tag := soup.select_one(selector)) and tag.has_attr("href") else ""
        )
        for platform, selector in SOCIAL_SELECTORS.items()
    }
    return {
        "type": ministry_name,
        "about": about.get_text(strip=True) if about else "",
        "priorities": "",
        "website": url,
        **socials
    }


def get_minister_data(soup, base_url):
    name_tag = soup.select_one("div.goa-text h2")
    img_tag = soup.select_one("div.goa-thumb img")

    name = " ".join(re.findall(r"[A-Za-z]+", name_tag.get_text(" ", strip=True))) if name_tag else ""
    photo_url = urljoin(base_url, img_tag["src"]) if img_tag and img_tag.has_attr("src") else ""

    return {
        "name": name,
        "photo_url": photo_url,
        "minister_contact_number": "",
        "minister_url": base_url
    }


def scrape_ministries_from_directory(directory_list, output_file="data/AB/ministries.csv"):
    session = requests.Session()

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "type", "about", "priorities", "website",
            "twitter", "facebook", "youtube", "instagram",
            "name", "photo_url", "minister_contact_number", "minister_url"
        ])
        writer.writeheader()

        for entry in directory_list:
            url = entry["href"]
            name = entry["text"]
            print(f"Scraping: {name} ({url})")

            resp = session.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            ministry_data = get_ministry_data(soup, url, name)
            minister_data = get_minister_data(soup, url)
            writer.writerow({**ministry_data, **minister_data})
