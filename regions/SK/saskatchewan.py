"""
Main script to run both Sk_agencies.py and sk_ministries.py scrapers
"""
import sk_agencies as agencies_module
import sk_ministries as ministries_module


def main():
    print("=" * 60)
    print("Starting Saskatchewan Government Data Scraper")
    print("=" * 60)
    
    # Scrape agencies
    print("\n[1/3] Scraping agencies...")
    print("-" * 60)
    agencies_url = "https://www.saskatchewan.ca/government/government-structure/boards-commissions-and-agencies"
    agencies_data = agencies_module.scrape_site(agencies_url)
    agencies_module.save_csv(agencies_data)
    print(f"✓ Scraped {len(agencies_data)} agencies")
    print(f"✓ Saved to data/SK/agencies_sk.csv")
    
    # Scrape ministries
    print("\n[2/3] Scraping ministries...")
    print("-" * 60)
    ministries_url = "https://www.saskatchewan.ca/government/government-structure/ministries"
    ministries_data = ministries_module.scrape_site(ministries_url)
    ministries_module.save_json(ministries_data)
    ministries_module.save_csv(ministries_data)
    print(f"✓ Scraped {len(ministries_data)} ministries")
    print(f"✓ Saved to data/SK/ministries_sk.json")
    print(f"✓ Saved to data/SK/ministries_sk.csv")
    
    # Scrape minister details
    print("\n[3/3] Scraping minister details...")
    print("-" * 60)
    ministers_data = ministries_module.scrape_ministers(ministries_data)
    ministries_module.save_minister_json(ministers_data)
    ministries_module.save_minister_csv(ministers_data)
    print(f"✓ Scraped {len(ministers_data)} minister records")
    print(f"✓ Saved to data/SK/ministers_sk.json")
    print(f"✓ Saved to data/SK/ministers_sk.csv")
    
    print("\n" + "=" * 60)
    print("Scraping completed successfully!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  - Agencies: {len(agencies_data)}")
    print(f"  - Ministries: {len(ministries_data)}")
    print(f"  - Ministers: {len(ministers_data)}")


if __name__ == "__main__":
    main()

