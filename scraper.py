# Source I referenced: GLOCAL-scraping-guide/glocal-scraping-guideline/scraping

#following GLOCAL scraping guide
#from ast import If : NOT USED
#from pickle import APPEND: NOT USED
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
    response = requests.get(url) #not url, check
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    
    ministry_links = []
    
    ministry_list=soup.find("div", id="ministrylistcontainer") #div with all ministry <a>s
    if not ministry_list:
        print("Could not find ministry list")
        return []
    
    
    
    
    # found the list of ministries under <div id="body" class="styled-h2"><ul>
    for a in ministry_list.find_all("a", href=True):
        # NOTES: check if 'a' works, exists in this format: <a href="url" target="_self"> ministry_name </a>
        name = a.get_text(strip=True)
        link = a["href"]
        
        if link.startswith("/"):
            link="https://www2.gov.bc.ca" + link
        ministry_links.append({"name": name, "url":link})
        
    return ministry_links
       

def scrape_one_ministry(ministry):
    response = requests.get(ministry["url"])
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    
    data = {}
    data["name"] = ministry["name"]
    data["url"] = ministry["url"]
    
    desc = soup.find("meta", attrs={"name": "description"})
    
    if desc:
        data["description"] = desc["content"]
    else: 
        data["description"] = "N/A"
        
    return data
    
    
    #to be continued..

def scrape_all():
    ministries = scrape_ministries(BASE_URL)
    final_data = []

    for ministry in ministries:
        try:
            print(f"Scraping: {ministry['name']}")
            scraped = scrape_one_ministry(ministry)
            final_data.append(scraped)
            
        except Exception as e:
            print(f"Failed to scrape {ministry['name']}: {e}")
            
    with open("ministries_data.json", "w", encoding="utf-8") as f:
        json.dump(final_data,f, indent=5, ensure_ascii=False)
        
        
if __name__ == "__main__":
    scrape_all()



#def init_scrape(): 
 #   response = requests.get(BASE_URL)
  #  response.raise_for_status()
   # html = response.text

    #feeding soup my HTML and choosing BeautifulSoup parser
    #soup = BeautifulSoup(html, "html.parser")
    
    
