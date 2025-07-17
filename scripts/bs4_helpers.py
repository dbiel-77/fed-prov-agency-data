import requests
from bs4 import BeautifulSoup

def get_soup(source, parser="html.parser", from_url=True, headers=None):
    """
    Returns a BeautifulSoup object from a URL or raw HTML string.
    
    Parameters:
        source (str): The URL or raw HTML content.
        parser (str): Parser to use ('html.parser', 'lxml', etc.)
        from_url (bool): If True, treats `source` as URL. If False, treats it as raw HTML.
        headers (dict): Optional headers for requests.get().
    
    Returns:
        BeautifulSoup object

    Sampel Usage:

        from bs4_helper import get_soup
        -------------------------------
        url = "https://example.com"
        soup = get_soup(url)
        
    """
    if from_url:
        if headers is None:
            headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(source, headers=headers)
        response.raise_for_status()
        html = response.text
    else:
        html = source
    
    return BeautifulSoup(html, parser)