import requests
from bs4 import BeautifulSoup
import time

from urllib.parse import urlparse, parse_qs, unquote
import csv

# input search terms
AGENCIES = [
"Accessibility Advisory Council",
"Adult Abuse Registry Committee",
"Adults Living with an Intellectual Disability Hearing Panel Roster",
"Agriculture Research and Innovation Committee",
"Agricultural Services Corporation (MASC)",
"Animal Care Appeal Board",
"Appeal Tribunal",
"Appointment for Judicial Justices of the Peace",
"Apprenticeship and Certification Appeal Board",
"Apprenticeship and Certification Board",
"Assiniboine Community College Board of Governors",
"Association of Optometrists",
"Association of Registered Respiratory Therapists",
"Automobile Injury Compensation Appeal Commission",
"Beverly and Qamanirjuaq Caribou Management Board",
"Board of Reference",
"Brandon Manitoba Centennial Auditorium",
"Brandon University Board of Governors",
"CancerCare Manitoba",
"Centennial Centre Corporation",
"Centre Culturel Franco-Manitobain",
"Centre Port Canada",
"Certificate Review Committee",
"Certification Advisory Committee",
"Child Care Qualifications and Training Committee",
"Chiropractors Association",
"Civil Service Superannuation Board",
"Clean Environment Commission",
"College of Audiologists and Speech Pathologists of Manitoba",
"College of Dental Hygienists of Manitoba",
"College of Dietitians of Manitoba",
"College of Licensed Practical Nurses of Manitoba",
"College of Medical Laboratory Technologists of Manitoba",
"College of Occupational Therapists of Manitoba",
"College of Paramedics",
"College of Pharmacists of Manitoba",
"College of Physicians and Surgeons of Manitoba",
"College of Physiotherapists of Manitoba",
"College of Registered Nurses of Manitoba",
"College of Registered Psychiatric Nurses of Manitoba",
"Combative Sports Commission",
"Communities Economic Development Fund",
"Community Notification Advisory Committee",
"Companies Office Advisory Board",
"Conservation Agreements Board",
"Convention Centre (RBC)",
"Cooperative Housing Appeal Tribunal",
"Criminal Code Review Board",
"Dental Association",
"Denturist Association of Manitoba - Board of Directors",
"Deposit Guarantee Corporation of Manitoba",
"Disaster Assistance Appeal Board",
"Dispute Resolution Review Committee",
"Efficiency Manitoba",
"Expert Advisory Council",
"Farm Industry Board",
"Farm Products Marketing Council",
"Film and Sound Recording Development Corporation",
"Fish and Wildlife Enhancement Fund and Subcommittees",
"Forks North Portage Partnership (FNPP) Board of Directors 3",
"Francophone Affairs Advisory Council",
"General Child and Family Services Authority – Board of Directors",
"Hazardous Waste Management Corporation Board",
"Health Appeal Board",
"Health Professions Advisory Council",
"Hearing Aid Board",
"Heritage Council",
"Human Rights Commission - Adjudicators",
"Human Rights Commission - Board of Commissioners",
"Hydro-Electric Board",
"Inland Port Special Planning Authority",
"Institute of Trades and Technology Board of Governors",
"Insurance Agents' and Adjusters' Licensing Appeal Board",
"Insurance Council of Manitoba",
"Interlake-Eastern Regional Health Authority",
"Judicial Appointment Committee",
"Judicial Compensation Committee",
"Judicial Council",
"Judicial Inquiry Board",
"Keystone Centre - Board of Directors",
"Labour Board",
"Land Value Appraisal Commission",
"Law Foundation",
"Law Reform Commission",
"Legal Aid Management Council",
"Legislative Building Restoration and Preservation Advisory Council",
"Licence Suspension Appeal Board",
"Liquor and Lotteries Corporation",
"Liquor, Gaming and Cannabis Authority of Manitoba (LGCA)",
"Louis Riel Institute",
"Manitoba Arts Council",
"Manitoba Museum",
"Masters Appointment Committee (Queen's Bench Masters)",
"Medical Review Committee",
"Mental Health Review Board",
"Municipal Board",
"Northern Regional Health Authority",
"Pension Commission",
"Police Boards",
"Police Commission",
"Prairie Agriculture Machinery Institute Board of Directors",
"Prairie Mountain Health",
"Protein Consortium",
"Public Insurance - Board of Directors",
"Public Insurance - Rates Appeal Board",
"Public Library Advisory Board",
"Public Utilities Board",
"Red River College Board of Governors",
"Rehabilitation Centre for Children",
"Research Manitoba",
"Residential Tenancies Commission",
"Resource Tourism Appeal Committee",
"Rural Manitoba Economic Development Corporation",
"Sanatorium Board of Manitoba",
"Securities Commission",
"Seven Oaks General Hospital",
"Shared Health",
"Social Services Appeal Board",
"Southern Health-Santé Sud",
"Sport Manitoba",
"Student Advisory Council",
"Surface Rights Board",
"Tax Appeals Commission",
"Teachers’ Retirement Allowances Fund Board (TRAF)",
"Travel Manitoba",
"Treasury Risk Oversight Committee",
"Universite de Saint-Boniface Board of Governors",
"University College of the North Governing Council Board",
"University of Manitoba Board of Governors",
"University of Winnipeg Board of Regents",
"Veterinary Medical Association Council",
"Veterinary Services Commission",
"Watershed Districts Boards",
"Whiteshell Advisory Board",
"Winnipeg Art Gallery",
"Winnipeg Regional Health Authority",
"Women’s Advisory Council",
"Women’s Institute Provincial Board",
"Workers Compensation Board – Appeal Commission",
"Workers Compensation Board – Board of Directors",
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
    results = []
    for agency in AGENCIES:
        query = f"{agency} Manitoba site"
        raw_url = search_duckduckgo(query)
        if raw_url:
            clean_url = url_extractinator(raw_url)
        else:
            clean_url = ""
        results.append([agency, clean_url])
        time.sleep(1)
    with open("agency_websites.csv", "w", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Agency", "URL"])
        writer.writerows(results)

if __name__ == "__main__":
    main()
