import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from scripts.common import (
    make_session, get_soup, extract_phone, extract_email,
    open_writer, duckduckgo, parallel_scrape, AGENCY_FIELDS,
)

BASE = "https://www.quebec.ca"

QC_ENTITIES = [
    ("Hydro-Québec", "https://www.hydroquebec.com/", "Crown Corporation", "Natural Resources and Forestry"),
    ("Société des alcools du Québec (SAQ)", "https://www.saq.com/", "Crown Corporation", "Finance"),
    ("Loto-Québec", "https://www.lotoquebec.com/", "Crown Corporation", "Finance"),
    ("Investissement Québec", "https://www.investissement-quebec.com/", "Crown Corporation", "Economy and Innovation"),
    ("Caisse de dépôt et placement du Québec", "https://www.cdpq.com/", "Crown Corporation", "Finance"),
    ("Société québécoise d'information juridique (SOQUIJ)", "https://soquij.qc.ca/", "Crown Corporation", "Justice"),
    ("Régie de l'énergie", "https://www.regie-energie.qc.ca/", "Regulatory Agency", "Natural Resources and Forestry"),
    ("RECYC-QUÉBEC", "https://www.recyc-quebec.gouv.qc.ca/", "Crown Agency", "Environment and the Fight against Climate Change"),
    ("Revenu Québec", "https://www.revenuquebec.ca/", "Government Agency", "Finance"),
    ("Musée national des beaux-arts du Québec", "https://www.mnbaq.org/", "Museum / Gallery", "Culture and Communications"),
    ("Musée de la civilisation", "https://www.mcq.org/", "Museum", "Culture and Communications"),
    ("Musée McCord d'histoire canadienne", "https://www.musee-mccord-stewart.ca/", "Museum", "Culture and Communications"),
    ("Musée Pointe-à-Callière", "https://pacmusee.qc.ca/", "Museum", "Culture and Communications"),
    ("Bibliothèque et Archives nationales du Québec (BAnQ)", "https://www.banq.qc.ca/", "Archives / Library", "Culture and Communications"),
    ("Conseil des arts et des lettres du Québec", "https://www.calq.gouv.qc.ca/", "Crown Agency", "Culture and Communications"),
    ("Commission des droits de la personne et des droits de la jeunesse", "https://www.cdpdj.qc.ca/", "Commission", "Justice"),
    ("Protecteur du citoyen", "https://www.protecteurducitoyen.qc.ca/", "Independent Agency / Ombudsman", "Justice"),
    ("Office québécois de la langue française", "https://www.oqlf.gouv.qc.ca/", "Agency", "Culture and Communications"),
    ("Commission québécoise des libérations conditionnelles", "https://www.cqlc.gouv.qc.ca/", "Commission", "Public Safety"),
    ("Société immobilière du Québec", "https://www.siq.gouv.qc.ca/", "Crown Corporation", "Treasury Board"),
    ("Commissaire à la santé et au bien-être", "https://www.csbe.gouv.qc.ca/", "Independent Agency", "Health and Social Services"),
    ("Infrastructure Québec", "https://www.infras.gouv.qc.ca/", "Crown Agency", "Treasury Board"),
]


def _dynamic_scrape(session):
    url = "https://www.quebec.ca/en/government/departments-agencies"
    soup = get_soup(session, url)
    if not soup:
        return []
    rows = []
    content = soup.find("ul", class_="listeCategoriesMinisteres") or soup.find("main") or soup
    for a in content.find_all("a", href=True):
        name = a.get_text(strip=True)
        href = a["href"]
        if not name or len(name) < 6:
            continue
        full = href if href.startswith("http") else BASE + href
        rows.append({
            "province": "QC", "type": "Agency / Department", "name": name,
            "description": "", "website": full,
            "phone": "", "email": "", "address": "", "parent_ministry": "",
        })
    return rows


def _enrich(session, row):
    if not row["website"]:
        row["website"] = duckduckgo(f"{row['name']} Québec gouvernement", session) or ""
    if row["website"] and row["website"].startswith("http"):
        s = get_soup(session, row["website"], timeout=10)
        if s:
            pt = s.get_text(" ", strip=True)
            row["phone"] = extract_phone(pt)
            row["email"] = extract_email(pt)
            for p in s.find_all("p"):
                t = p.get_text(strip=True)
                if len(t) > 60:
                    row["description"] = t
                    break
    return row


def scrape_agencies(output_file="data/QC/agencies_qc.csv"):
    session = make_session()
    all_rows = [{
        "province": "QC", "type": etype, "name": name, "description": "",
        "website": website, "phone": "", "email": "", "address": "",
        "parent_ministry": ministry,
    } for name, website, etype, ministry in QC_ENTITIES]

    dynamic = _dynamic_scrape(session)
    existing = {r["name"].lower() for r in all_rows}
    for r in dynamic:
        if r["name"].lower() not in existing:
            all_rows.append(r)

    print(f"[QC] Enriching {len(all_rows)} records concurrently…")
    enriched = parallel_scrape(session, all_rows, _enrich, max_workers=10)
    f, writer = open_writer(output_file, AGENCY_FIELDS)
    writer.writerows(enriched)
    f.close()
    print(f"[QC] Saved {len(enriched)} → {output_file}")
