import requests
from bs4 import BeautifulSoup
import time

from urllib.parse import urlparse, parse_qs, unquote

# Sample input list
AGENCIES = [
    "Accessibility Advisory Council",
    "Adult Abuse Registry Committee",
    "Agriculture Research and Innovation Committee",
    "Apprenticeship and Certification Appeal Board",
    "Assiniboine Community College Board of Governors",
    "Association of Optometrists Manitoba",
]


def url_extractinator(ddg_url):
    parsed = urlparse(ddg_url)
    qs = parse_qs(parsed.query)
    if "uddg" in qs:
        return unquote(qs["uddg"][0])
    return ddg_url

def search_duckduckgo(query):
    base_url = "https://duckduckgo.com/html/"
    params = {"q": query}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        result = soup.select_one("a.result__a")
        return result["href"] if result else None
    except Exception as e:
        print(f"Error for '{query}': {e}")
        return None

def main():
    for agency in AGENCIES:
        query = f"{agency} Manitoba site"
        print(f"\nSearching for: {agency}")
        raw_url = search_duckduckgo(query)
        if raw_url:
            clean_url = url_extractinator(raw_url)
            print(f"Likely site: {clean_url}")
        else:
            print("No site found.")
        time.sleep(1)

if __name__ == "__main__":
    main()
