from bs4 import BeautifulSoup
import requests
import pandas as pd
import json
import os
import re


def scrape_minister_details(ministry_url, headers):
    """Extract minister details from a ministry page"""
    minister_data = {
        "name": "N/A",
        "phone": "N/A",
        "fax": "N/A",
        "email": "N/A",
        "office_address": "N/A",
        "image_url": "N/A",
        "ministry_url": ministry_url
    }
    
    try:
        page = requests.get(ministry_url, headers=headers, timeout=10)
        page.raise_for_status()
        soup = BeautifulSoup(page.text, "html.parser")
        
        # First, try to find name using itemprop="name"
        name_itemprop = soup.find(attrs={"itemprop": "name"})
        if name_itemprop:
            name_text = name_itemprop.get_text(strip=True)
            if name_text and len(name_text) > 3:
                minister_data["name"] = name_text
        
        # First, try to find address using itemprop="address"
        address_itemprop = soup.find(attrs={"itemprop": "address"})
        if address_itemprop:
            # itemprop="address" might be a parent element with nested itemprop attributes
            # Try to get the full address text, or look for itemprop="streetAddress", etc.
            address_text = address_itemprop.get_text(separator=" ", strip=True)
            if address_text and len(address_text) > 10:
                minister_data["office_address"] = address_text
            else:
                # Try to find nested address properties
                street_address = address_itemprop.find(attrs={"itemprop": "streetAddress"})
                address_locality = address_itemprop.find(attrs={"itemprop": "addressLocality"})
                address_region = address_itemprop.find(attrs={"itemprop": "addressRegion"})
                postal_code = address_itemprop.find(attrs={"itemprop": "postalCode"})
                
                address_parts = []
                if street_address:
                    address_parts.append(street_address.get_text(strip=True))
                if address_locality:
                    address_parts.append(address_locality.get_text(strip=True))
                if address_region:
                    address_parts.append(address_region.get_text(strip=True))
                if postal_code:
                    address_parts.append(postal_code.get_text(strip=True))
                
                if address_parts:
                    minister_data["office_address"] = ", ".join(address_parts)
        
        # Try to find minister name - common patterns (fallback if itemprop not found)
        if minister_data["name"] == "N/A":
            name_selectors = [
                "h1",
                "h2",
                ".minister-name",
                "[class*='minister']",
                "[class*='contact'] h1",
                "[class*='contact'] h2"
            ]
            
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem:
                    text = name_elem.get_text(strip=True)
                    # Filter out generic titles
                    if text and len(text) > 3 and "minister" not in text.lower():
                        minister_data["name"] = text
                        break
        
        # Try to find image
        img_selectors = [
            "img[class*='minister']",
            "img[class*='photo']",
            ".minister img",
            ".contact img",
            "main img",
            "article img"
        ]
        
        for selector in img_selectors:
            img = soup.select_one(selector)
            if img and img.get("src"):
                img_src = img.get("src")
                if img_src.startswith("http"):
                    minister_data["image_url"] = img_src
                elif img_src.startswith("/"):
                    minister_data["image_url"] = "https://www.saskatchewan.ca" + img_src
                else:
                    minister_data["image_url"] = ministry_url.rsplit("/", 1)[0] + "/" + img_src
                break
        
        # Extract contact information - look for phone, fax, email, address
        page_text = soup.get_text()
        
        # Phone pattern
        phone_patterns = [
            r'Phone[:\s]+([\d\s\-\(\)]+)',
            r'Tel[:\s]+([\d\s\-\(\)]+)',
            r'Telephone[:\s]+([\d\s\-\(\)]+)',
            r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',
            r'\((\d{3})\)\s*(\d{3})[-.\s]?(\d{4})'
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                if match.groups():
                    # If pattern has groups, use the first group or join all groups
                    if len(match.groups()) == 1:
                        phone = match.group(1)
                    else:
                        phone = ''.join(match.groups())
                else:
                    phone = match.group(0)
                # Clean and validate phone number
                clean_phone = re.sub(r'[\s\-\(\)\.]', '', phone)
                if len(clean_phone) >= 10:
                    minister_data["phone"] = phone.strip()
                    break
        
        # Fax pattern
        fax_patterns = [
            r'Fax[:\s]+([\d\s\-\(\)]+)',
            r'F[:\s]+([\d\s\-\(\)]+)'
        ]
        
        for pattern in fax_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                fax = match.group(1) if match.groups() else match.group(0)
                if len(re.sub(r'[\s\-\(\)]', '', fax)) >= 10:
                    minister_data["fax"] = fax.strip()
                    break
        
        # Email pattern
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        email_match = re.search(email_pattern, page_text)
        if email_match:
            minister_data["email"] = email_match.group(0)
        
        # Address - look for common address patterns (fallback if itemprop not found)
        if minister_data["office_address"] == "N/A":
            address_selectors = [
                "[class*='address']",
                "[class*='contact']",
                "[class*='office']",
                "address"
            ]
            
            for selector in address_selectors:
                addr_elem = soup.select_one(selector)
                if addr_elem:
                    addr_text = addr_elem.get_text(strip=True)
                    # Filter out email/phone from address
                    if addr_text and len(addr_text) > 10 and "@" not in addr_text:
                        # Check if it looks like an address (has numbers or common address words)
                        if re.search(r'\d+|street|avenue|ave|st|road|rd|drive|dr|boulevard|blvd', addr_text, re.IGNORECASE):
                            minister_data["office_address"] = addr_text
                            break
        
        # Alternative: look for structured contact sections
        contact_sections = soup.find_all(["div", "section"], class_=re.compile(r'contact|address|office', re.I))
        for section in contact_sections:
            text = section.get_text(separator=" ", strip=True)
            
            # Extract phone if not found
            if minister_data["phone"] == "N/A":
                phone_match = re.search(r'Phone[:\s]+([\d\s\-\(\)]+)', text, re.IGNORECASE)
                if phone_match:
                    minister_data["phone"] = phone_match.group(1).strip()
            
            # Extract fax if not found
            if minister_data["fax"] == "N/A":
                fax_match = re.search(r'Fax[:\s]+([\d\s\-\(\)]+)', text, re.IGNORECASE)
                if fax_match:
                    minister_data["fax"] = fax_match.group(1).strip()
            
            # Extract email if not found
            if minister_data["email"] == "N/A":
                email_match = re.search(email_pattern, text)
                if email_match:
                    minister_data["email"] = email_match.group(0)
            
            # Extract address if not found
            if minister_data["office_address"] == "N/A":
                # Look for address-like text (has street numbers, postal codes, etc.)
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if (re.search(r'\d+.*(street|avenue|ave|st|road|rd|drive|dr|boulevard|blvd|saskatoon|regina)', line, re.IGNORECASE) or
                        re.search(r'[A-Z]\d[A-Z]\s?\d[A-Z]\d', line)):  # Canadian postal code
                        if "@" not in line and len(line) > 10:
                            minister_data["office_address"] = line
                            break
        
    except Exception as e:
        print(f"Error scraping minister details from {ministry_url}: {e}")
    
    return minister_data


def scrape_site(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0 Safari/537.36"
    }

    page = requests.get(url, headers=headers, timeout=10)
    page.raise_for_status()
    soup = BeautifulSoup(page.text, "html.parser")

    # Find all section elements with class "links"
    links_sections = soup.find_all("section", class_="links")
    
    details = []
    for section in links_sections:
        # Find only direct child div.row elements (section.links > div.row)
        row_divs = section.find_all("div", class_="row", recursive=False)
        
        for row_div in row_divs:
            # Find all links within each div.row
            links = row_div.find_all("a", href=True)
            
            for link in links:
                ministry_name = link.get_text(strip=True)
                href = link.get("href", "")
                
                # Build full URL if relative
                if href.startswith("http"):
                    full_link = href
                elif href.startswith("/"):
                    full_link = "https://www.saskatchewan.ca" + href
                else:
                    full_link = url.rsplit("/", 1)[0] + "/" + href
                
                if not ministry_name:
                    continue
                    
                print(f"Found: {ministry_name} - {full_link}")
                
                # Try to get description from parent or nearby elements
                description = "N/A"
                try:
                    # Look for description in parent element or sibling
                    parent = link.find_parent()
                    if parent:
                        # Try to find description text nearby
                        desc_elem = parent.find_next("p") or parent.find("p")
                        if desc_elem:
                            description = desc_elem.get_text(strip=True)
                except Exception:
                    pass
                
                details.append({
                    "ministry_name": ministry_name,
                    "ministry_url": full_link,
                    "description": description
                })

    return details


def save_json(data, path="data/SK/ministries_sk.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_csv(data, path="data/SK/ministries_sk.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = pd.DataFrame(data)
    df.to_csv(path, index=False, encoding="utf-8")


def scrape_ministers(ministries_data):
    """Scrape minister details from all ministry pages"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0 Safari/537.36"
    }
    
    ministers = []
    for ministry in ministries_data:
        ministry_url = ministry.get("ministry_url")
        if ministry_url:
            print(f"Scraping minister details from: {ministry_url}")
            minister_data = scrape_minister_details(ministry_url, headers)
            minister_data["ministry_name"] = ministry.get("ministry_name", "N/A")
            ministers.append(minister_data)
    
    return ministers


def save_minister_json(data, path="data/SK/ministers_sk.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_minister_csv(data, path="data/SK/ministers_sk.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = pd.DataFrame(data)
    df.to_csv(path, index=False, encoding="utf-8")


if __name__ == "__main__":
    # Scrape ministries
    ministries = scrape_site("https://www.saskatchewan.ca/government/government-structure/ministries")
    save_json(ministries)
    save_csv(ministries)
    
    # Scrape minister details
    print("\nScraping minister details...")
    ministers = scrape_ministers(ministries)
    save_minister_json(ministers)
    save_minister_csv(ministers)
    print(f"\nScraped {len(ministers)} minister records")

