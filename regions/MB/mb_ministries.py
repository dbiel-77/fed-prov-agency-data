import requests
from bs4 import BeautifulSoup
import csv
import re

url = 'https://www.gov.mb.ca/minister/index.html'
base_url = 'https://www.gov.mb.ca/minister/'  # used to split contact URLs

def extract_ministry_name(info):
    # Extract which ministry the minister is associated with
    pattern = r"(Minister of .*?)(?: on|$)"
    match = re.search(pattern, info)
    if match:
        ministry = match.group(1).strip()

        # Replace only the first "Minister" with "Ministry"
        ministry = re.sub(r"\bMinister\b", "Ministry", ministry, count=1)

        # Cut off at the second "Minister" (if it exists)
        ministry = re.split(r"\bMinister\b", ministry)[0].strip()

        # Remove trailing "and" or commas
        ministry = re.sub(r"(,|and)$", "", ministry).strip()

        return ministry
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

def load_about_file(path="ministry_about_hardcode.csv"):
    about_list = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if row:  # skip empty rows
                about_list.append(row[0])  # assume first column has the text
    return about_list

def save_csv(data, about_list, path="mb_ministers.csv"):
    with open(path, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        # Reordered header
        writer.writerow(["Ministry Name", "About", "Minister Name", "Contact Info URL"])

        # Combine row-by-row in new order
        for i, row in enumerate(data):
            minister_name, ministry_name, contact_url = row
            about_text = about_list[i] if i < len(about_list) else ""
            writer.writerow([ministry_name, about_text, minister_name, contact_url])

if __name__ == "__main__":
    data = scrape_minister(url)
    about_list = load_about_file("ministry_about_hardcode.csv")
    save_csv(data, about_list)
