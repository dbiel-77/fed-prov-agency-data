"""Federal entry point — ministries (from .FED/) + agencies/crown corps/museums."""
import sys
from pathlib import Path

# Add both the project root and the hidden .FED directory to path
_root = Path(__file__).resolve().parents[2]
_fed_dir = Path(__file__).resolve().parent.parent / ".FED"
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_fed_dir))

from fed_ministries import scrape_ministries
from fed_agencies import scrape_federal_agencies


def main():
    scrape_ministries()
    scrape_federal_agencies()


if __name__ == "__main__":
    main()
