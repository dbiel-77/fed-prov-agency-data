# Saskatchewan Agencies Scraper - Scrapes agency information from Saskatchewan government website

from bs4 import BeautifulSoup
import requests
import pandas as pd
import os


def scrape_site(url):
    """Scrapes agency information from the Saskatchewan government website."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0 Safari/537.36"
    }

    page = requests.get(url, headers=headers, timeout=10)
    page.raise_for_status()
    soup = BeautifulSoup(page.text, "html.parser")

    links_sections = soup.find_all("section", class_="links")
    
    details = []
    for section in links_sections:
        row_divs = section.find_all("div", class_="row", recursive=False)
        
        for row_div in row_divs:
            links = row_div.find_all("a", href=True)
            
            for link in links:
                agency_name = link.get_text(strip=True)
                href = link.get("href", "")
                
                # Build full URL if relative
                if href.startswith("http"):
                    full_link = href
                elif href.startswith("/"):
                    full_link = "https://www.saskatchewan.ca" + href
                else:
                    full_link = url.rsplit("/", 1)[0] + "/" + href
                
                if not agency_name:
                    continue
                    
                print(f"Found: {agency_name} - {full_link}")
                
                # Try to get description from nearby elements
                description = "N/A"
                try:
                    parent = link.find_parent()
                    if parent:
                        desc_elem = parent.find_next("p") or parent.find("p")
                        if desc_elem:
                            description = desc_elem.get_text(strip=True)
                except Exception:
                    pass
                
                details.append({
                    "agency_name": agency_name,
                    "agency_url": full_link,
                    "description": description
                })

    return details


def save_csv(data, path="data/SK/agencies_sk.csv"):
    """Saves scraped agency data to a CSV file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = pd.DataFrame(data)
    df.to_csv(path, index=False, encoding="utf-8")


if __name__ == "__main__":
    scrape = scrape_site("https://www.saskatchewan.ca/government/government-structure/boards-commissions-and-agencies")
    save_csv(scrape)
