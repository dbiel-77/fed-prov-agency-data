import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote

def find_ministry_url(ministry_name, additional_terms):
    """
    Search DuckDuckGo for the most likely website of a given ministry or agency, 
    using both the ministry name and additional search terms to improve accuracy.

    Args:
        ministry_name (str): The name of the ministry or agency (e.g., "Finance").
        additional_terms (str): Extra terms to refine the search (e.g., "Alberta ministry" or "government contact site").

    Returns:
        str or None: The cleaned URL of the top DuckDuckGo result, or None if no result found.
    """
    query = f"{ministry_name} {additional_terms} site"
    base_url = "https://duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(base_url, params={"q": query}, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Select the first search result link
        result = soup.select_one("a.result__a")
        if not result:
            return None

        # Clean DuckDuckGo redirection URL
        parsed = urlparse(result["href"])
        qs = parse_qs(parsed.query)
        return unquote(qs["uddg"][0]) if "uddg" in qs else result["href"]

    except Exception as e:
        print(f"Search failed for '{query}': {e}")
        return None
