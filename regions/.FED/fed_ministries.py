import os
import re
import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from config import minister_urls

PHONE_RE = re.compile(r'(\+?\d{1,3}[\s-]?)?(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})')
SOCIAL_DOMAINS = {
    'twitter': 'twitter.com',
    'facebook': 'facebook.com',
    'youtube': 'youtube.com',
    'instagram': 'instagram.com'
}
FIELDNAMES = [
    "type", "about", "priorities", "website", "twitter", "facebook", "youtube", "instagram",
    "name", "photo_url", "minister_contact_number", "minister_url"
]
NOTICE_RE = re.compile(r'\b(information about|potential delays|affected by|affected|notice|urgent|alert|news release|news|emergency|wildfire|wildfires|covid|disruption)\b', re.I)
KEYWORDS = ["employment", "social development", "canada", "department", "ministry", "esdc"]

def get_soup(session, url):
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, 'html.parser')

def normalize_text(text):
    if not text:
        return ""
    return text.strip()

def get_about(soup, ministry_name=None, min_len=80):
    meta = soup.find('meta', attrs={"name": "description"})
    if meta and meta.get('content'):
        meta_text = normalize_text(meta['content'])
        if not NOTICE_RE.search(meta_text) and len(meta_text) >= min_len:
            return meta_text

    candidates = []
    intro = soup.find('div', class_='mwsgeneric-base-html') or soup.find('div', class_='gc-intro')
    if intro:
        candidates.extend(intro.find_all('p', recursive=True))
    h1 = soup.find('h1')
    if h1:
        for sib in h1.next_siblings:
            if getattr(sib, "name", None) and sib.name.startswith('h'):
                break
            if getattr(sib, "name", None) == 'p':
                candidates.append(sib)

    keywords = list(KEYWORDS)
    if ministry_name:
        for part in re.split(r'[^A-Za-z]+', ministry_name):
            if len(part) > 2:
                keywords.append(part.lower())

    best_candidate = ""
    best_score = 0

    for p in candidates:
        text = normalize_text(p.get_text(" ", strip=True))
        if not text:
            continue
        if NOTICE_RE.search(text):
            continue
        if len(text) < min_len:
            continue

        score = 0
        lower_text = text.lower()
        for kw in keywords:
            if kw in lower_text:
                score += 2
        score += min(len(text), 100) / 100.0

        if score > best_score:
            best_score = score
            best_candidate = text

    if best_candidate:
        return best_candidate

    longest = ""
    for p in soup.find_all('p'):
        txt = normalize_text(p.get_text(" ", strip=True))
        if not txt or NOTICE_RE.search(txt):
            continue
        if len(txt) > len(longest):
            longest = txt

    return longest

def get_socials(soup):
    found = {k: "" for k in SOCIAL_DOMAINS}
    for a in soup.select("a[href]"):
        href = a['href'].strip()
        for key, domain in SOCIAL_DOMAINS.items():
            if domain in href and not found[key]:
                found[key] = href
    return found

def find_minister_anchor(soup):
    for a in soup.find_all('a', string=True):
        text = a.get_text(" ", strip=True)
        if "the honourable" in text.lower() and 'secretary' not in text.lower() and 'parliamentary' not in text.lower():
            return a
    header = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4'] and 'minister' in tag.get_text(strip=True).lower())
    if header:
        a = header.find_next('a')
        if a and a.get_text(strip=True):
            return a
        next_person_heading = header.find_next(lambda tag: tag.name in ['h2','h3'] and tag.get_text(strip=True))
        if next_person_heading:
            return next_person_heading
    return None

def parse_minister_inline(soup, base_url):
    name = ""
    photo_url = ""
    contact_info = ""

    candidates = []
    for elem in soup.find_all(text=re.compile(r'The Honourable', re.I)):
        parent = elem.parent
        text = elem.strip()
        candidates.append(text)

    for text in candidates:
        match = re.search(r'(?:The Honourable|Minister)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)', text)
        if match:
            name = match.group(1).strip()
            break

    if not name:
        for h in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            h_text = h.get_text(strip=True)
            if 'minister' in h_text.lower():
                parts = re.split(r'[,:-]', h_text)
                if len(parts) > 1:
                    candidate_name = parts[1].strip()
                    if len(candidate_name) > 3:
                        name = candidate_name
                        break

    if name:
        imgs = soup.find_all('img')
        for img in imgs:
            alt = img.get('alt', '').lower()
            title = img.get('title', '').lower()
            src = img.get('src', '')
            if name.lower() in alt or name.lower() in title:
                photo_url = urljoin(base_url, src)
                break

        if not photo_url:
            for elem in soup.find_all(text=re.compile(name.split()[0], re.I)):
                parent = elem.parent
                if parent:
                    img = parent.find('img')
                    if img and img.get('src'):
                        photo_url = urljoin(base_url, img['src'])
                        break

    contacts = []
    for a in soup.select("a[href]"):
        href = a['href'].strip()
        if href.startswith('mailto:') or href.startswith('tel:'):
            contacts.append(href)

    contact_info = "; ".join(contacts)

    return {
        "name": name,
        "photo_url": photo_url,
        "minister_contact_number": contact_info,
        "minister_url": ""
    }

def find_ministers(soup, base_url):
    ministers = []
    for a in soup.select("a[href]"):
        text = a.get_text(" ", strip=True)
        if not text:
            continue
        if not re.search(r'\b(The Honourable|Minister)\b', text, re.I):
            continue
        if re.search(r'Deputy|Parliamentary', text, re.I):
            continue
        ministers.append({
            "name": text,
            "minister_url": urljoin(base_url, a['href'])
        })

    seen = set()
    unique_ministers = []
    for m in ministers:
        if m["minister_url"] not in seen:
            seen.add(m["minister_url"])
            unique_ministers.append(m)

    return unique_ministers

def parse_minister_profile(session, minister_url):
    try:
        soup = get_soup(session, minister_url)
    except Exception:
        return {"name": "", "photo_url": "", "minister_contact_number": "", "minister_url": minister_url}

    name = soup.find('h1')
    name_text = name.get_text(strip=True) if name else ""
    photo_url = ""
    img = soup.find('img', src=True)
    if img and img['src']:
        photo_url = urljoin(minister_url, img['src'])
    bio = ""
    intro = soup.find('div', class_='mwsgeneric-base-html') or soup.find('div', class_='gc-intro')
    if intro:
        p = intro.find('p')
        if p:
            bio = p.get_text(strip=True)
    if not bio and name:
        p = name.find_next('p')
        bio = p.get_text(strip=True) if p else ""
    contacts = []
    for a in soup.select("a[href]"):
        href = a['href'].strip()
        if href.startswith('mailto:'):
            contacts.append(href)
        if href.startswith('tel:'):
            contacts.append(href)
    if not contacts:
        whole_text = soup.get_text(" ", strip=True)
        phones = PHONE_RE.findall(whole_text)
        if phones:
            cleaned = ["".join(filter(None, p)) for p in phones]
            contacts.extend(cleaned)

    contact_info = "; ".join(contacts)

    return {
        "name": name_text,
        "photo_url": photo_url,
        "minister_contact_number": contact_info,
        "minister_url": minister_url
    }

def find_minister_name_by_pattern(soup):
    pattern = re.compile(r'The Honourable\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)')
    for text in soup.stripped_strings:
        match = pattern.search(text)
        if match:
            name = match.group(1).strip()
            return name
    return None

def find_photo_near_name(soup, name, base_url):
    if not name:
        return None
    for img in soup.find_all('img', src=True):
        alt = img.get('alt', '').lower()
        title = img.get('title', '').lower()
        if any(part.lower() in alt or part.lower() in title for part in name.split()):
            return urljoin(base_url, img['src'])
    for text_node in soup.find_all(string=re.compile(re.escape(name.split()[0]), re.I)):
        parent = text_node.parent
        if parent:
            img = parent.find('img', src=True)
            if img:
                return urljoin(base_url, img['src'])
    return None

def get_ministry_data(session, name, url):
    print(f"\n--- Scraping ministry: {name} ---")
    try:
        soup = get_soup(session, url)
    except Exception as e:
        print(f"ERROR fetching {url}: {e}")
        return None

    about = get_about(soup, ministry_name=name)
    socials = get_socials(soup)
    return {
        "type": name,
        "about": about,
        "priorities": "",
        "website": url,
        **socials
    }

def get_minister_data(session, name, ministry_url, minister_url):
    minister_name = None
    minister_photo_url = None
    minister_url = minister_url or ""
    contact_info = ""

    if name == "Public Safety Canada":
        soup = get_soup(session, ministry_url)
        about = get_about(soup, ministry_name=name)
        minister_anchor = find_minister_anchor(soup)
        if minister_anchor and minister_anchor.name == 'a' and minister_anchor.has_attr('href'):
            minister_url = urljoin(ministry_url, minister_anchor['href'])
            minister_data = parse_minister_profile(session, minister_url)
            minister_name = minister_data.get("name", "")
            minister_photo_url = minister_data.get("photo_url", "")
            contact_info = minister_data.get("minister_contact_number", "")
        else:
            minister_inline = parse_minister_inline(soup, ministry_url)
            minister_name = minister_inline.get("name", "")
            minister_photo_url = minister_inline.get("photo_url", "")
            contact_info = minister_inline.get("minister_contact_number", "")
        corp_header = soup.find(lambda tag: tag.name in ['h2', 'h3'] and 'Corporate information' in tag.get_text())
        minister_name = None
        if corp_header:
            for elem in corp_header.find_next_siblings():
                if elem.name and elem.name.startswith('h'):
                    break
                text = elem.get_text(" ", strip=True)
                if 'The Honourable' in text:
                    match = re.search(r'The Honourable\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)', text)
                    if match:
                        minister_name = match.group(1)
                        break
        minister_photo_url = find_photo_near_name(soup, minister_name, ministry_url)

    elif name == 'Fisheries and Oceans Canada':
        soup = get_soup(session, ministry_url)
        pattern = re.compile(r'The Honourable\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)')
        for text in soup.stripped_strings:
            match = pattern.search(text)
            if match:
                minister_name = match.group(1)
                break
        if minister_name:
            for img in soup.find_all('img', src=True):
                alt = img.get('alt', '').lower()
                title = img.get('title', '').lower()
                if minister_name.lower() in alt or minister_name.lower() in title:
                    minister_photo_url = urljoin(ministry_url, img['src'])
                    break
            if not minister_photo_url:
                for elem in soup.find_all(string=re.compile(re.escape(minister_name), re.I)):
                    parent = elem.parent
                    if parent:
                        img = parent.find('img')
                        if img and img.get('src'):
                            minister_photo_url = urljoin(ministry_url, img['src'])
                            break
        contacts = []
        for a in soup.select("a[href]"):
            href = a['href'].strip()
            if href.startswith('mailto:') or href.startswith('tel:'):
                contacts.append(href)
        if not contacts:
            whole_text = soup.get_text(" ", strip=True)
            phones = PHONE_RE.findall(whole_text)
            if phones:
                cleaned = ["".join(filter(None, p)) for p in phones]
                contacts.extend(cleaned)
        contact_info = "; ".join(contacts)

    elif name == "Canadian Heritage":
        soup = get_soup(session, ministry_url)
        minister_name = find_minister_name_by_pattern(soup)
        minister_photo_url = find_photo_near_name(soup, minister_name, ministry_url)
        contacts = []
        for a in soup.select("a[href]"):
            href = a['href'].strip()
            if href.startswith('mailto:') or href.startswith('tel:'):
                contacts.append(href)
        if not contacts:
            whole_text = soup.get_text(" ", strip=True)
            phones = PHONE_RE.findall(whole_text)
            if phones:
                cleaned = ["".join(filter(None, p)) for p in phones]
                contacts.extend(cleaned)
        contact_info = "; ".join(contacts)

    elif name == "Transport Canada":
        soup = get_soup(session, ministry_url)
        minister_name = find_minister_name_by_pattern(soup)
        minister_photo_url = find_photo_near_name(soup, minister_name, ministry_url)
        contacts = []
        for a in soup.select("a[href]"):
            href = a['href'].strip()
            if href.startswith('mailto:') or href.startswith('tel:'):
                contacts.append(href)
        if not contacts:
            whole_text = soup.get_text(" ", strip=True)
            phones = PHONE_RE.findall(whole_text)
            if phones:
                cleaned = ["".join(filter(None, p)) for p in phones]
                contacts.extend(cleaned)
        contact_info = "; ".join(contacts)

    elif name == "Department of Justice Canada":
        soup = get_soup(session, ministry_url)
        corp_header = soup.find(lambda tag: tag.name in ['h2', 'h3'] and 'Corporate information' in tag.get_text(strip=True))
        if corp_header:
            for sib in corp_header.find_all_next():
                if sib.name and sib.name.startswith('h'):
                    break
                if 'The Honourable' in sib.get_text():
                    match = re.search(r'The Honourable\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)', sib.get_text())
                    if match:
                        minister_name = match.group(1)
                        break
        if not minister_name:
            minister_name = find_minister_name_by_pattern(soup)
        minister_photo_url = find_photo_near_name(soup, minister_name, ministry_url)
        contacts = []
        for a in soup.select("a[href]"):
            href = a['href'].strip()
            if href.startswith('mailto:') or href.startswith('tel:'):
                contacts.append(href)
        if not contacts:
            whole_text = soup.get_text(" ", strip=True)
            phones = PHONE_RE.findall(whole_text)
            if phones:
                cleaned = ["".join(filter(None, p)) for p in phones]
                contacts.extend(cleaned)
        contact_info = "; ".join(contacts)

    elif name == "Veterans Affairs Canada":
        about_page_url = "https://www.veterans.gc.ca/en/about-vac/who-we-are/department-officials"
        soup = get_soup(session, about_page_url)
        minister_section = soup.find(lambda tag: tag.name in ["section", "div"] and "Minister’s Office" in tag.get_text())
        if minister_section:
            text_match = re.search(r"The Honourable\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)", minister_section.get_text())
            if text_match:
                minister_name = text_match.group(1).strip()
            img = minister_section.find("img", src=True)
            if img:
                minister_photo_url = urljoin(ministry_url, img["src"])
        if not minister_name:
            minister_name = find_minister_name_by_pattern(soup)
        if not minister_photo_url and minister_name:
            minister_photo_url = find_photo_near_name(soup, minister_name, ministry_url)
        contacts = []
        for a in soup.select("a[href]"):
            href = a['href'].strip()
            if href.startswith('mailto:') or href.startswith('tel:'):
                contacts.append(href)
        if not contacts:
            whole_text = soup.get_text(" ", strip=True)
            phones = PHONE_RE.findall(whole_text)
            if phones:
                cleaned = ["".join(filter(None, p)) for p in phones]
                contacts.extend(cleaned)
        contact_info = "; ".join(contacts)

    else:
        soup = get_soup(session, ministry_url)
        ministers_found = find_ministers(soup, ministry_url)
        if ministers_found:
            first_minister = ministers_found[0]
            if first_minister["minister_url"]:
                minister_data = parse_minister_profile(session, first_minister["minister_url"])
                minister_name = minister_data.get('name', "")
                minister_photo_url = minister_data.get('photo_url', "")
                contact_info = minister_data.get('minister_contact_number', "")
                minister_url = first_minister["minister_url"]
        else:
            minister_anchor = find_minister_anchor(soup)
            if minister_anchor:
                href = None
                if minister_anchor.name == 'a':
                    href = minister_anchor.get('href')
                else:
                    a_in = minister_anchor.find('a', href=True)
                    href = a_in.get('href') if a_in else None
                if href:
                    minister_url = urljoin(ministry_url, href)
                    minister_data = parse_minister_profile(session, minister_url)
                    minister_name = minister_data.get('name', "")
                    minister_photo_url = minister_data.get('photo_url', "")
                    contact_info = minister_data.get('minister_contact_number', "")
                else:
                    minister_name = minister_anchor.get_text(strip=True)
                    minister_photo_url = ""
                    contact_info = ""
                    minister_url = ""

    if minister_name and not minister_name.lower().startswith("the honourable"):
        minister_name = f"The Honourable {minister_name}"

    return {
        "name": minister_name or "",
        "photo_url": minister_photo_url or "",
        "minister_contact_number": contact_info,
        "minister_url": minister_url
    }

def scrape_ministries(output_file="data/FED/ministries_fed.csv"):
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    session = requests.Session()
    headers = FIELDNAMES
    with open(output_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        for ministry, (min_url, minister_url) in minister_urls.items():
            print(f"Scraping ministry: {ministry}")
            data = get_ministry_data(session, ministry, min_url)
            if data:
                data.update(get_minister_data(session, ministry, min_url, minister_url))
                writer.writerow(data)