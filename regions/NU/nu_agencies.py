import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root_dir))
import csv
import time


from scripts.find_url import find_ministry_url

agencies = {
    "District Education Authorities": "agency",
    "Inuit Uqausinginnik Taiguusiliuqtiit": "agency",
    "Labour Standards Board": "agency",
    "Legal Services Board of Nunavut": "agency",
    "Nunavut Liquor and Commission": "agency",
    "Nunavut Liquor and Cannabis Board": "agency",
    "Human Rights Tribunal": "agency",
    "Qulliit Nunavut Status of Women Council": "agency",
    "Nunavut Arctic College": "crown_corp",
    "Nunavut Business Credit Corporation": "crown_corp",
    "Nunavut Development Corporation": "crown_corp",
    "Nunavut Housing Corporation": "crown_corp",
    "Qulliq Energy Corporation": "crown_corp",
    "Workers’ Safety and Compensation Commission": "agency"
}


rows = []
for name, org_type in agencies.items():
    url = find_ministry_url(name, "nunavut official website")
    print(url)
    rows.append({
        "name": name,
        "type": org_type,
        "url": url
    })
    time.sleep(3)

with open("data/nu/nunavut_agencies.csv", mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["name", "type", "url"])
    writer.writeheader()
    writer.writerows(rows)