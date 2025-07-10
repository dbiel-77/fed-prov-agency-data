import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

url1 = "https://www.quebec.ca/gouvernement/ministeres-organismes/affaires-municipales"
url2 = "https://www.quebec.ca/gouvernement/ministeres-organismes/agriculture-pecheries-alimentation"
url3 = "https://www.quebec.ca/gouvernement/ministere/conseil-executif"
url4 = "https://www.quebec.ca/en/government/ministere/emploi-solidarite-sociale"
BASE_URL = "https://www.quebec.ca/en/government/departments-agencies"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def get_dep_links(index_url):
    resp = requests.get(index_url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    links = []
    ul = soup.find("ul", class_="listeCategoriesMinisteres")
    if not ul:
        print("Could not find ministry links")
        return links
    
    for li in ul.find_all("li"):
        a = li.find("a", href=True)
        if a:
            full_url = urljoin(index_url, a["href"])
            links.append(full_url)
    
    print(f"Found {len(links)} departments")
    return links

def scrape_ministries(url):
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = 'utf-8'
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # --- VALUES ---
    ent_type = "Ministry" #need to code
    page_title = soup.title.string if soup.title else ""
    about = ""
    website_link = url
    minister = ""
    desc = ""
    bio_url = "N/A"
    contact_url = ""
    agenda_url = ""
    
    # --- ENTITY TYPE ---
    print("Type: ", ent_type)

    # --- TITLE ---
    if "|" in page_title:
        page_title = page_title.split("|")[0].strip()

    prefixes = ["Ministère des ", "Ministère de la ", "Ministère du "]
    for prefix in prefixes:
        if page_title.startswith(prefix):
            page_title = page_title[len(prefix):].strip()

    print("Title: ", page_title)

    # --- ABOUT ---
    desc = soup.find("div", class_="ce-bodytext")
    if desc:
        p = desc.find("p")
        if p and p.get_text(strip=True):
            about = p.get_text(strip=True)
        else:
            about = "N/A"

    print("About: ", about)

    # --- WEBSITE ---
    print("Website: ", website_link)

    # --- MINISTERS + DESC + CONTACT + AGENDA ---
    blocs = soup.find_all("div", class_="bloc-profil")
    fallback_found = False

    if not blocs:
        containers = soup.find_all("div", class_="ce-textpic ce-left ce-intext ce-nowrap") 
        for container in containers:
            body = container.find("div", class_="ce-bodytext")
            if body:
                h3 = body.find("h3")
                if h3:
                    minister = h3.get_text(strip=True)
                
                ps = body.find("p")
                desc = ", ".join(p.get_text(strip=True) for p in ps if p.get_text(strip=True))
                if not desc:
                    desc = "N/A"
            
            links = container.find_all("a", href=True)
            for link in links:
                href = urljoin(url, link["href"])
                link_text = link.get_text(strip=True).lower()

                if "biography" in link_text or "biographie" in link_text:
                    bio_url = href
                elif "comminucate" in link_text or "communiquer" in link_text:
                    contact_url = href
                elif "agenda" in link_text:
                    agenda_url = href
            
            print("Minister: ", minister)
            print("Description: ", desc)
            print("Biography URL: ", bio_url)
            print("Contact URL: ", contact_url)
            print("Agenda URL: ", agenda_url)
            if fallback_found:
                return

    for bloc in blocs:
        name_div = bloc.find("div", class_="profil-name")
        if name_div:
            h4 = name_div.find("h4")
            if h4:
                minister = h4.get_text(strip=True)
        
        desc_div = bloc.find("div", class_="description")
        if desc_div:
            ps = desc_div.find_all("p")
            desc = ", ".join(p.get_text(strip=True) for p in ps if p.get_text(strip=True))
        if not desc:
                desc = "N/A"
        
        links = bloc.find_all("a", href=True)
        if links:
            contact_url = links[0]["href"]
            if len(links) > 1:
                agenda_url = links[1]["href"]
        
        print("Minister: ", minister)
        print("Description: ", desc)
        print("Contact URL: ", contact_url)
        print("Agenda URL: ", agenda_url)

all_dept_links = get_dep_links(BASE_URL)

for idx, link in enumerate(all_dept_links):
    print(f"\n--- Department #{idx + 1} ---")
    scrape_ministries(link)

'''
print("----- URL 1 -----") #format 1: mult members
scrape_ministries(url1) 
print("----- URL 2 -----") #format 1: one members
scrape_ministries(url2)
print("----- URL 3 -----") #format 2: one member
scrape_ministries(url3)
print("----- URL 4 -----") #format 2: mult members
scrape_ministries(url4)
'''

