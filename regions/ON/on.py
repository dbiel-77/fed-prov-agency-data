import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from on_ministries import scrape_ministries
from on_agencies import scrape_agencies


def main():
    scrape_ministries()
    scrape_agencies()


if __name__ == "__main__":
    main()
