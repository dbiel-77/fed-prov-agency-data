import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urlparse, parse_qs, unquote

def scrape_agencies(save_agency_csv="data/ab/agencies_ab.csv",
                        save_minister_csv="data/ab/agency_members_ab.csv"):
    agency_rows = []
    minister_rows = []
    page_num = 0
    consecutive_timeouts = 0

    while consecutive_timeouts < 2 and page_num < 15:
        if page_num == 0:
            url = "https://public-agency-list.alberta.ca/"
        else:
            url = (
                "https://public-agency-list.alberta.ca/"
                f"?currentPage={page_num}"
                f"&selectedPage={page_num+1}"
                "&AgencyId=All&SearchFor=#frmSearch"
            )

        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            consecutive_timeouts = 0
        except (requests.exceptions.Timeout, requests.exceptions.RequestException):
            consecutive_timeouts += 1
            page_num += 1
            time.sleep(1)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        print(url)

        # all <div class="goa-grid-100-100-100"> that contain <input name="agencyIDInput">
        all_grids = soup.find_all("div", class_="goa-grid-100-100-100")
        for idx, grid in enumerate(all_grids):
            if not grid.find("input", attrs={"name": "agencyIDInput"}):
                continue

            # agency_name comes from the previous goa-grid-100-100-100's <h3><strong>…</strong></h3>
            agency_name = None
            if idx > 0:
                prev_grid = all_grids[idx - 1]
                strong_tag = prev_grid.select_one("h3 strong")
                if strong_tag:
                    agency_name = strong_tag.get_text(strip=True)

            # description = first <p> inside this grid
            desc_tag = grid.find("p")
            description = desc_tag.get_text(strip=True) if desc_tag else None

            # next <h4> with text "Classification"
            classification = None
            cls_h4 = grid.find_next("h4", string=lambda t: t and t.strip() == "Classification")
            if cls_h4:
                li = cls_h4.find_next("ul").find("li")
                classification = li.get_text(strip=True) if li else None


            query = f"{agency_name} alberta site"
            raw_url = search_duckduckgo(query)
            if raw_url:
                clean_url = url_extractinator(raw_url)
            else:
                print("No site found.")
            time.sleep(1)

            agency_rows.append({
                "agency_name": agency_name,
                "agency_url": clean_url if raw_url else None,
                "classification": classification,
                "description": description
            })

            print(agency_name)

            # ministers: next <table class="boardListing">
            table = grid.find_next("table", class_="boardListing")
            if table:
                for tr in table.find_all("tr")[1:]:
                    tds = tr.find_all("td")
                    if len(tds) < 5:
                        continue
                    minister_rows.append({
                        "agency_name":        agency_name,
                        "position":           tds[0].get_text(strip=True),
                        "name":               tds[1].get_text(strip=True),
                        "appointment_date":   tds[2].get_text(strip=True),
                        "expiry_date":        tds[3].get_text(strip=True),
                        "appointment_method": tds[4].get_text(strip=True)
                    })

        page_num += 1
        time.sleep(0.5)

    # Convert to DataFrame and save CSVs
    agency_df = pd.DataFrame(agency_rows)
    ministers_df = pd.DataFrame(minister_rows)

    agency_df.to_csv(save_agency_csv, index=False)
    ministers_df.to_csv(save_minister_csv, index=False)
    print(f"Saved {len(agency_df)} agencies to '{save_agency_csv}'")
    print(f"Saved {len(ministers_df)} minister records to '{save_minister_csv}'")


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
