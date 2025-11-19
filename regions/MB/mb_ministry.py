from bs4 import BeautifulSoup
import requests
import pandas as pd
import json
import os
import re


def scrape_manitoba_ministers(url):
    """Scrape minister data from Manitoba government page and save directly to JSON and CSV"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0 Safari/537.36"
    }

    try:
        page = requests.get(url, headers=headers, timeout=10)
        page.raise_for_status()
        soup = BeautifulSoup(page.text, "html.parser")

        # Find table with class "ministers"
        ministers_table = soup.find("table", class_="ministers")
        
        if not ministers_table:
            print("Error: Could not find table with class 'ministers'")
            return []

        # Get all tr tags except those with class "col_heading even"
        tr_tags = ministers_table.find_all("tr")
        
        ministers_data = []
        
        for tr in tr_tags:
            # Skip tr tags with class "col_heading even"
            if tr.get("class") and "col_heading" in tr.get("class") and "even" in tr.get("class"):
                continue
            
            # Get all td tags in this row
            td_tags = tr.find_all("td")
            
            if len(td_tags) < 3:
                continue
            
            # First td: image
            image_td = td_tags[0]
            image_url = "N/A"
            img_tag = image_td.find("img")
            if img_tag:
                img_src = img_tag.get("src", "")
                if img_src:
                    if img_src.startswith("http"):
                        image_url = img_src
                    elif img_src.startswith("/"):
                        image_url = "https://www.gov.mb.ca" + img_src
                    else:
                        image_url = url.rsplit("/", 1)[0] + "/" + img_src
            
            # Second td: name and related ministry
            name_td = td_tags[1]
            name_text = name_td.get_text(strip=True)
            
            # Try to extract name and ministry separately
            name = "N/A"
            ministry = "N/A"
            
            # Step 1: Extract name from "Honourable [Name]" pattern
            # Pattern to match "Honourable" followed by 1-3 capitalized words
            honourable_pattern = r'Honourable[\s\t]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})'
            honourable_match = re.search(honourable_pattern, name_text)
            
            if honourable_match:
                name = honourable_match.group(1).strip()
                # Remove the "Honourable [Name]" part from text to get ministry
                name_with_honourable = honourable_match.group(0)
                remaining_text = name_text.replace(name_with_honourable, "").strip()
                
                # Step 2: Extract ministry from remaining text
                # Split by common delimiters and filter for ministry-related content
                ministry_parts = []
                
                # Split by newlines, tabs, or when "Minister"/"Premier" appears
                parts = re.split(r'\n|\t|(?=(?:Minister|Premier|Deputy Premier|President|Keeper|responsible for))', remaining_text)
                
                for part in parts:
                    part = part.strip()
                    if not part or len(part) < 5:
                        continue
                    
                    # Check if this part contains ministry keywords
                    if re.search(r'(?:Premier|Minister|Deputy Premier|President|Keeper|responsible for)', part, re.IGNORECASE):
                        # Clean up the part
                        part = re.sub(r'^[;\s\t]+|[;\s\t]+$', '', part)
                        if part:
                            ministry_parts.append(part)
                
                if ministry_parts:
                    # Join ministry parts, handling the case where they might be concatenated
                    ministry = "; ".join(ministry_parts)
                else:
                    # If no parts found, use remaining text as ministry
                    remaining_text = re.sub(r'\s+', ' ', remaining_text).strip()
                    if remaining_text:
                        ministry = remaining_text
            else:
                # Fallback: Name doesn't start with "Honourable"
                # Try to find a name pattern (2-3 capitalized words) that's not ministry-related
                words = name_text.split()
                
                for i in range(len(words) - 1):
                    # Try 2-3 word combinations
                    for length in [2, 3]:
                        if i + length <= len(words):
                            potential_name = " ".join(words[i:i+length])
                            
                            # Check if it looks like a name (no ministry keywords, proper capitalization)
                            if (not re.search(r'(?:Minister|Premier|Deputy|President|Keeper|responsible|of)', potential_name, re.IGNORECASE) and
                                all(word and word[0].isupper() for word in words[i:i+length])):
                                name = potential_name
                                
                                # Extract ministry from the rest
                                remaining_text = name_text.replace(potential_name, "").strip()
                                remaining_text = re.sub(r'^[;\s\t]+|[;\s\t]+$', '', remaining_text)
                                
                                if remaining_text and len(remaining_text) > 5:
                                    ministry = remaining_text
                                break
                    
                    if name != "N/A":
                        break
            
            # Step 3: Clean up and normalize
            if name != "N/A":
                name = re.sub(r'\s+', ' ', name).strip()
            if ministry != "N/A":
                # Clean up ministry: remove extra whitespace, handle concatenated titles
                ministry = re.sub(r'\s+', ' ', ministry).strip()
                # Split concatenated ministry titles (e.g., "Premier of ManitobaMinister of X" -> "Premier of Manitoba; Minister of X")
                ministry = re.sub(r'([a-z])([A-Z])', r'\1; \2', ministry)
                ministry = re.sub(r'([A-Z][a-z]+\s+of\s+[A-Z][a-z]+)([A-Z])', r'\1; \2', ministry)
                ministry = re.sub(r'\s+', ' ', ministry).strip()
            
            # Third td: contact information
            contact_td = td_tags[2]
            contact_text = contact_td.get_text(strip=True)
            
            # Try to extract phone, email, and address from contact information
            phone = "N/A"
            email = "N/A"
            address = "N/A"
            
            # Extract email
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            email_match = re.search(email_pattern, contact_text)
            if email_match:
                email = email_match.group(0)
            
            # Extract phone
            phone_patterns = [
                r'Phone[:\s]+([\d\s\-\(\)]+)',
                r'Tel[:\s]+([\d\s\-\(\)]+)',
                r'Telephone[:\s]+([\d\s\-\(\)]+)',
                r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',
                r'\((\d{3})\)\s*(\d{3})[-.\s]?(\d{4})'
            ]
            
            for pattern in phone_patterns:
                match = re.search(pattern, contact_text, re.IGNORECASE)
                if match:
                    if match.groups():
                        if len(match.groups()) == 1:
                            phone = match.group(1)
                        else:
                            phone = ''.join(match.groups())
                    else:
                        phone = match.group(0)
                    clean_phone = re.sub(r'[\s\-\(\)\.]', '', phone)
                    if len(clean_phone) >= 10:
                        phone = phone.strip()
                        break
            
            # Address - remaining text after removing email and phone
            address = contact_text
            if email != "N/A":
                address = address.replace(email, "").strip()
            if phone != "N/A":
                address = address.replace(phone, "").strip()
                # Remove "Phone:" or "Tel:" labels
                address = re.sub(r'Phone[:\s]*', '', address, flags=re.IGNORECASE)
                address = re.sub(r'Tel[:\s]*', '', address, flags=re.IGNORECASE)
            
            address = address.strip()
            if not address or len(address) < 5:
                address = "N/A"
            
            minister_data = {
                "name": name,
                "ministry": ministry,
                "image_url": image_url,
                "phone": phone,
                "email": email,
                "address": address,
                "contact_info": contact_text
            }
            
            ministers_data.append(minister_data)
            print(f"Scraped: {name} - {ministry}")
        
        # Save directly to JSON and CSV files
        if ministers_data:
            save_json(ministers_data)
            save_csv(ministers_data)
            print(f"\n✓ Successfully scraped and saved {len(ministers_data)} minister records")
        else:
            print("\n✗ No data was scraped. Please check the URL and table structure.")
        
        return ministers_data
    
    except Exception as e:
        print(f"Error scraping Manitoba ministers: {e}")
        return []


def save_json(data, path="data/minitoba/ministers_manitoba.json"):
    """Save data to JSON file"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved {len(data)} records to {path}")


def save_csv(data, path="data/minitoba/ministers_manitoba.csv"):
    """Save data to CSV file"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = pd.DataFrame(data)
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"✓ Saved {len(data)} records to {path}")


if __name__ == "__main__":
    url = "https://www.gov.mb.ca/legislature/members/cabinet_ministers.html"
    
    print("Scraping Manitoba ministers...")
    print("-" * 60)
    
    scrape_manitoba_ministers(url)
