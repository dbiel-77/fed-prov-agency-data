import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv

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
        return []
    
    for li in ul.find_all("li"):
        a = li.find("a", href=True)
        if a:
            full_url = urljoin(index_url, a["href"])
            links.append(full_url)
    
    print(f"Found {len(links)} departments")
    return list(links)

def scrape_ministries(url):
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = 'utf-8'
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # --- TITLE ---
    page_title = soup.title.string.split("|")[0].strip() if soup.title else ""
    for prefix in ["Ministère des ", "Ministère de la ", "Ministère du "]:
        if page_title.startswith(prefix):
            page_title = page_title[len(prefix):].strip()

    # --- ABOUT ---
    about = "N/A"
    desc = soup.find("div", class_="ce-bodytext")
    if desc:
        p = desc.find("p")
        if p and p.get_text(strip=True):
            about = p.get_text(strip=True)

    # --- MINISTERS + DESC + CONTACT + AGENDA ---
    blocs = soup.find_all("div", class_="bloc-profil")
    if not blocs:
        blocs = soup.find_all("div", class_="ce-textpic ce-left ce-intext ce-nowrap")

    results = []
    for bloc in blocs:
        name_tag = bloc.find("h4") or bloc.find("h3")
        if not name_tag:
            continue
        minister = name_tag.get_text(strip=True)

        body = bloc.find("div", class_="description") or bloc.find("div", class_="ce-bodytext")
        desc = "N/A"
        if body:
                ps = body.find_all("p")
                clean_paragraphs = []
                for p in ps:
                    if p.find("a") or any(word in p.get_text(strip=True).lower() for word in ["email", "courriel", "agenda", "contact"]):
                        continue
                    for br in p.find_all("br"):
                        br.replace_with(", ")
                    text = p.get_text(" ", strip=True)
                    if text:
                        clean_paragraphs.append(text)

                desc = ", ".join(clean_paragraphs).strip().replace(",,", ",").replace(" ,", ",") if clean_paragraphs else "N/A"

        
        bio_url = contact_url = agenda_url = "N/A"
        contact_keywords = ["contact", "communicate", "communiquer", "joindre", "write"]
        for link in bloc.find_all("a", href=True):
            href = urljoin(url, link["href"])
            link_text = link.get_text(strip=True).lower()
            if "biography" in link_text or "biographie" in link_text:
                bio_url = href
            elif any(word in link_text for word in contact_keywords):
                contact_url = href
            elif "agenda" in link_text:
                agenda_url = href
        
        results.append({
            "Type": "Ministry",
            "Ministry": page_title,
            "About": about,
            "Priorities": "",
            "Website": url,
            "Minister(s)": minister,
            "Deputy Ministers": "",
            "Contact": contact_url,
            "Agenda": agenda_url,
            "Biography": bio_url
        })

    return results

def main():
    all_dept_links = get_dep_links(BASE_URL)
    all_data = []

    for idx, link in enumerate(all_dept_links):
        print(f"\n--- Department #{idx + 1} ---")
        try:
            dept_data = scrape_ministries(link)
            all_data.extend(dept_data)
        except Exception as e:
            print(f"Error scraping {link}: {e}")
    
    with open("quebec_ministries.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Type", "Ministry", "About", "Priorities", "Website",
            "Minister(s)", "Deputy Ministers", "Contact", "Agenda", "Biography"
        ])
        writer.writeheader()
        writer.writerows(all_data)

    print("Saved to quebec_ministries.csv")


main()