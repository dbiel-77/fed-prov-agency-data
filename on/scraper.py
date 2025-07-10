import requests
import time
import pandas as pd
from bs4 import BeautifulSoup


ontario_url = "https://www.ontario.ca"

SOCIAL_SELECTORS = {
    'twitter': "a[href*='twitter.com']",
    'twitter': "a[href*='x.com']",
    'facebook': "a[href*='facebook.com']",
    'youtube': "a[href*='youtube.com']",
    'instagram': "a[href*='instagram.com']"
}

ministry_rows = []
minister_rows = []

save_ministries_csv="on/data/ministries_on.csv"
save_minister_csv="on/data/ministers_on.csv"

def scrape_ministry(name, url):

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except (requests.exceptions.Timeout, requests.exceptions.RequestException):
        print("womp")
        return

    soup = BeautifulSoup(resp.text, "html.parser")

    # about section, which is nested in an empty div
    about = soup.find_all("div", {"class": "banner__intro--text"})[0].find_all("div")[0].find_all("p")[0].get_text(strip=True)
    
    # socials
    socials = {
        key: (tag['href'] if (tag := soup.select_one(sel)) and tag.has_attr('href') else '')
        for key, sel in SOCIAL_SELECTORS.items()
    }

    data = {
        'type': name,
        'about': about if about else '',
        'priorities': '',
        'website': url,
        **socials
    }

    ministry_rows.append(data)
    



def main() -> None:

    ministries_page = "/page/ministries"
    ministries_url = ontario_url + ministries_page

    try:
        resp = requests.get(ministries_url, timeout=10)
        resp.raise_for_status()
    except (requests.exceptions.Timeout, requests.exceptions.RequestException):
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    # section with all ministries has the body field (find_next doesnt work for some reason but find_all does)
    body_field = soup.find_all("div", {"class": "body-field"})
    if not body_field:
        print("did not find body-field")
        return
    body_field = body_field[0]
    # each ministry is an h3 that has an <a href> tag inside
    headers = body_field.find_all("h3")
    for h3 in headers:
        anchor = h3.find_all("a")
        if not anchor:
            continue
        anchor = anchor[0]
        ministries_page = anchor.get("href")
        url = ontario_url + ministries_page
        name = anchor.get_text()
        scrape_ministry(name, url)

    # Convert to DataFrame and save CSVs
    ministries_df = pd.DataFrame(ministry_rows)
    ministers_df = pd.DataFrame(minister_rows)

    ministries_df.to_csv(save_ministries_csv, index=False)
    ministers_df.to_csv(save_minister_csv, index=False)
    print(f"Saved {len(ministries_df)} agencies to '{save_ministries_csv}'")
    print(f"Saved {len(ministers_df)} minister records to '{save_minister_csv}'")



main()