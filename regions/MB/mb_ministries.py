import requests
from bs4 import BeautifulSoup
import csv
import re

url = 'https://www.gov.mb.ca/minister/index.html'
base_url = 'https://www.gov.mb.ca/minister/' #used to splict contact URLs

def extract_ministry_name(info):
    # Extracts which ministry the minister is associated with. Some will have to be manually checked but most follow standardized format
    pattern = r"Minister of (.*?) on"
    match = re.search(pattern, info)
    if match:
        return match.group(1).strip()
    return ""

def extract_contact_url(td_tag):
    # Extracts the contact URL for the minister from the td tag then returns the full URL
    a_tag = td_tag.find("a", href=True)
    if a_tag:
        href = a_tag["href"]
        if href.startswith("../minister/"):
            slug = href.replace("../minister/", "").strip("/")
            return base_url + slug + "/"
    return ""

def scrape_minister(url):
    # Scrapes the minister page to extract names, ministries, and contact URLs
    response = requests.get(url)
    response.raise_for_status()
    html = response.text

    soup = BeautifulSoup(html, 'html.parser')
    records = []

    for td in soup.find_all("td", class_="minister-text"):
        p_tag = td.find("p")
        if not p_tag:
            continue

        full_text = p_tag.get_text(strip=True)
        words = full_text.split()

        # Extract minister name
        if len(words) >= 3 and words[0] == "Hon.":
            minister_name = " ".join(words[:3])
            remaining_info = " ".join(words[3:])
        else:
            minister_name = ""
            remaining_info = full_text

        # Extract ministry name and contact info URL
        ministry_name = extract_ministry_name(remaining_info)
        contact_url = extract_contact_url(td)

        records.append((minister_name, ministry_name, contact_url))

    return records

def save_csv(data, path="ministers.csv"):
    with open(path, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Minister Name", "Ministry Name", "Contact Info URL"])
        writer.writerows(data)

if __name__ == "__main__":
    data = scrape_minister(url)
    save_csv(data)
