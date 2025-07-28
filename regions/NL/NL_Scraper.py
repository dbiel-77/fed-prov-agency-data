from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import re
import time

service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome(service=service)

base_url = 'https://www.gov.nl.ca/departments/'

driver.get(base_url)

# Implement 5 sec wait time, if no name tag is found, skip this block
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CLASS_NAME, "post-list"))
)

# Find the parent div
parent_div = driver.find_element(By.CSS_SELECTOR, "div.content-column.one_half")

# Search for the <a> inside <ul class="post-list"> within parent div only
link_element = parent_div.find_elements(By.CSS_SELECTOR, "ul.post-list li a")

departments = []
dept_url = []
ministers = []
abouts = []
contact_emails = []
i = 0

# Method to extract Minister info
def gather_ministers():
    try:
        strong_tags = driver.find_elements(By.CSS_SELECTOR, 
                                           "div.textwidget strong," \
                                           "div.footer-content-col strong," \
                                           "div.widget-section strong")
        found = False
        for tag in strong_tags:
            text = tag.text.strip()
            if (text.startswith("Honourable") or 
                "Minister" in text or
                "Premier" in text
            ):
                print(f"Found minister: {text}")
                ministers.append(text)
                found = True
                break
        if not found:
            print("Minister not found.")
            ministers.append("Minister not found")
    except NoSuchElementException:
        print("Minister not found")
        ministers.append("Minister not found")

# Method to extract ministry contact email
def gather_emails():
        elements = driver.find_elements(By.CSS_SELECTOR, "footer-content, " \
                                                        "div.textwidget a, " \
                                                        "a.email" 
                                                        )

        emailPattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}"
        
        for tag in elements:
            text = tag.text.strip()
            match = re.search(emailPattern, text)
            
            if match:
                email = match.group(0)
                contact_emails.append(email)
                print(f"Found email: {email}")
                found = True
                break
        if not found:
            print("Email not found")
            contact_emails.append("Email not found")

# Method to visit each url and call scraping methods
def scraping():
    """Visit ministry website and perform scraping"""
    for idx, (link, dept_name) in enumerate(zip(dept_url, departments), start=1):
        driver.get(link)

        # Print department info
        print(f"\n    -- Department {idx} - {dept_name} --")

        # Wait and extract the about info of the ministry
        try:
            about = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, 
                "div.entry-content > p,"
                "div.entry-content > header,"
                "div#gnlcontent > p,"
                "div.aboutsite > p,"
                "div.landing-introduction > p"
                ))
            )
            abouts.append(about.text)
            print(f'\n{about.text}\n')

            # Gather Minister info
            gather_ministers()
            
            # Gather ministry contact emails
            gather_emails()
            
        except TimeoutException:
            print("Paragraph not found")
            abouts.append("Paragraph not found")
            continue
        
        # Resting
        time.sleep(1)

# 1) Gather department names and urls
for element in link_element:
    """Gather ministry urls"""
    # From each element, extract the department name
    departments.append(element.text)                     

    # From each element, extract the url located by "href"
    dept_url.append(element.get_attribute("href"))

# 2) Scraping
scraping()

# 3) End Driver
driver.quit()

# 4) Writing to CSV
if len({len(departments), len(ministers), len(abouts), len(contact_emails), len(dept_url)}) != 1:
    print('\nError: List length mismatch; sites might have been updated - Check html tag identifiers')
    print('\nLengths of lists:')
    print(f'departments: {len(departments)}, ministers: {len(ministers)}, about: {len(abouts)}, contact emails: {len(contact_emails)} urls: {len(dept_url)}')
else:
    dict = {'Department': departments,
            'Minister': ministers,
            'About': abouts,
            'Contact emails': contact_emails,
            'URL': dept_url}

    result = pd.DataFrame(dict)
    result.to_csv("result.csv")

    print(result.head())










