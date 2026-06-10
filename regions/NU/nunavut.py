import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import os
import csv
from nu_ministries import scrape_nunavut_ministries

def main() -> None:
    scrape_nunavut_ministries()



if __name__ == "__main__":
    main()
