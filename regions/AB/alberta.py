# from regions.AB import ab_agencies, ab_ministries
import ab_agencies
import ab_ministries

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import time

def main() -> None:

    ab_agencies.scrape_agencies()
    
    ministries = create_directory("https://www.alberta.ca/ministries", ".goa-title", ".goa-text")
    ab_ministries.scrape_ministries_from_directory(ministries)

    

def create_directory(url, title_selector, description_selector, base_url=None):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    titles = soup.select(title_selector)
    descriptions = soup.select(description_selector)

    for title_elem, desc_elem in zip(titles, descriptions):
        a_tag = title_elem.find("a")
        if a_tag and a_tag.get("href"):
            full_url = urljoin(base_url or url, a_tag["href"])
            results.append({
                "text": a_tag.get_text(strip=True),
                "href": full_url,
                "description": desc_elem.get_text(separator=" ", strip=True).replace('\n', ' ')
            })

            print(f"Found: {results[-1]['text']} - {results[-1]['href']}")

    return results

if __name__ == "__main__":
    main()