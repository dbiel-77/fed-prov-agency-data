# Source I referenced: GLOCAL-scraping-guide/glocal-scraping-guideline/scraping

#following GLOCAL scraping guide
import requests
from bs4 import BeautifulSoup
import json


# retrieving raw HTML of "Ministries" page from official BC Government page
response = requests.get("https://www2.gov.bc.ca/gov/content/governments/organizational-structure/ministries-organizations/ministries")
response.raise_for_status()
html = response.text

#feeding soup my HTML and choosing BeautifulSoup parser
soup = BeautifulSoup(html, "html.parser")
