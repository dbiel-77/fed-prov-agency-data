# Source I referenced: GLOCAL-scraping-guide/glocal-scraping-guideline/scraping

#following GLOCAL scraping guide
from ast import If
from pickle import APPEND
import requests
from bs4 import BeautifulSoup
import json
import unicodedata #to normalize text
from bs4 import SoupStrainer #parse-time filtering


BASE_URL = "https://www2.gov.bc.ca/gov/content/governments/organizational-structure/ministries-organizations/ministries"

# Citation: https://www.geeksforgeeks.org/python/extract-all-the-urls-from-the-webpage-using-python/


# function to scrape through the ministries page for each ministry hyperlink
def scrape_ministries(url):
# retrieving raw HTML of "Ministries" page from official BC Government page
    response = requests.get(BASE_URL)
    response.raise_for_status()
    html = response.text

    #feeding soup my HTML and choosing BeautifulSoup parser
    soup = BeautifulSoup(html, "html.parser")
    
    ministries = []
    # found the list of ministries under <div id="body" class="styled-h2"><ul>
    for div in soup.find_all("div", id="body", class_= "styled-h2"):
        # NOTES: check if 'a' works, exists in this format: <a href="url" target="_self"> ministry_name </a>
        name = div.find("a").get_text(strip=True)
        
        # Loop to scrape through each hyperlink to a ministry
         # NOTES: Refered to glocal-scraping-guide -> web-fundamentals -> http-fundamentals on how to scrape through identical links on a page: 
        for link in soup.find_all("a"): # goes from 1st to 23rd ministry hyperlink
            URL = link.get("href")
            scraped_mini = scrape_one_ministry(url)
            if scraped_mini != None:
                ministries.append(scraped_mini)
       

def scrape_one_ministry(url):
    init_scrape()
    data = []
    #to be continued..
    
    
    
    
def init_scrape(): 
    response = requests.get(BASE_URL)
    response.raise_for_status()
    html = response.text

    #feeding soup my HTML and choosing BeautifulSoup parser
    soup = BeautifulSoup(html, "html.parser")
    
    
