# Canadian Federal & Provincial Government Agency Data

Web scraper that collects structured data on ministries, departments, agencies, and Crown corporations from Canada's federal government and all 13 provinces and territories. Produces per-jurisdiction CSVs and a unified master dataset.

## Coverage

| Code | Jurisdiction             |
|------|--------------------------|
| FED  | Federal                  |
| AB   | Alberta                  |
| BC   | British Columbia         |
| MB   | Manitoba                 |
| NB   | New Brunswick            |
| NL   | Newfoundland & Labrador  |
| NS   | Nova Scotia              |
| NT   | Northwest Territories    |
| NU   | Nunavut                  |
| ON   | Ontario                  |
| PE   | Prince Edward Island     |
| QC   | Québec                   |
| SK   | Saskatchewan             |
| YT   | Yukon                    |

## Output Schema

The unified dataset (`data/all_entities.csv`) normalizes all regional output into a single schema:

| Field               | Description                                       |
|---------------------|---------------------------------------------------|
| `province`          | 2–3 letter jurisdiction code                      |
| `type`              | Ministry / Department · Agency · Crown Corporation |
| `name`              | Organization name                                 |
| `about`             | Description / mandate                             |
| `priorities`        | Listed priorities                                 |
| `website`           | Official website URL                              |
| `phone`             | General contact phone                             |
| `email`             | General contact email                             |
| `address`           | Physical address                                  |
| `parent_ministry`   | Overseeing ministry (agencies only)               |
| `minister_name`     | Minister's full name                              |
| `minister_phone`    | Minister's phone number                           |
| `minister_email`    | Minister's email address                          |
| `minister_url`      | Minister's profile page URL                       |
| `minister_photo_url`| Minister's headshot URL                           |
| `twitter`           | Twitter / X profile URL                           |
| `facebook`          | Facebook page URL                                 |
| `youtube`           | YouTube channel URL                               |
| `instagram`         | Instagram profile URL                             |

## Usage

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run all scrapers

```bash
python main.py
```

Runs all 14 regional scrapers concurrently (6 workers), then merges output into `data/all_entities.csv`.

### Run a single region

```bash
python -m regions.BC.bc
python -m regions.FED.federal
```

### Re-merge existing CSVs without re-scraping

```bash
python combine.py
```

## Project Structure

```
fed-prov-agency-data/
├── main.py                  # Orchestrator — runs all regions then combines
├── combine.py               # Merges regional CSVs into data/all_entities.csv
├── scripts/
│   ├── common.py            # HTTP session, rate limiting, field definitions
│   ├── bs4_helpers.py       # BeautifulSoup fetch/parse utilities
│   ├── find_url.py          # DuckDuckGo search helper for finding ministry URLs
│   └── csv_check.py         # Data quality validator (hidden Unicode chars)
├── regions/
│   ├── .FED/                # Federal ministry config and scraper
│   ├── FED/                 # Federal entry point and agency scraper
│   └── [AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT]/
│       ├── [xx].py          # Region entry point
│       ├── [xx]_ministries.py
│       └── [xx]_agencies.py
└── data/
    ├── [XX]/
    │   ├── ministries.csv
    │   └── agencies_[xx].csv
    └── all_entities.csv     # Unified output (~680+ organizations)
```

## Notes

- Rate-limited to 5 concurrent requests per domain to avoid overloading government servers.
- Nunavut ministries are parsed from cached HTML (`regions/NU/ministry_pages/`) due to the site's structure requiring pre-fetched pages.
- Manitoba includes some hardcoded ministry descriptions (`ministry_about_hardcode.csv`) where live data is unavailable.
- Federal data is split: ministries from a hardcoded URL config (`regions/.FED/config.py`), agencies scraped live.

## License

[GNU General Public License v3.0](LICENSE)
