"""Quebec entry point — fixes output path and adds agencies."""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scraper as qc_scraper
import csv
from qc_agencies import scrape_agencies


def main():
    os.makedirs("data/QC", exist_ok=True)

    # Ministries
    print("[QC] Scraping ministries…")
    all_dept_links = qc_scraper.get_dep_links(qc_scraper.BASE_URL)
    all_data = []
    for idx, link in enumerate(all_dept_links):
        print(f"  Department #{idx + 1}: {link}")
        try:
            dept_data = qc_scraper.scrape_ministries(link)
            all_data.extend(dept_data)
        except Exception as e:
            print(f"  [WARN] {link}: {e}")

    output = "data/QC/ministries.csv"
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Type", "Ministry", "About", "Priorities", "Website",
            "Minister(s)", "Deputy Ministers", "Contact", "Agenda", "Biography",
        ])
        writer.writeheader()
        writer.writerows(all_data)
    print(f"[QC] Saved {len(all_data)} ministry records → {output}")

    # Agencies
    scrape_agencies()


if __name__ == "__main__":
    main()
