"""Test with longer wait times for shadow DOM."""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# This URL is known to work with shadow DOM
url = "https://normas.leg.br/?urn=urn:lex:br:federal:lei:2000-12-19;10101"
print(f"Testing: {url}")
driver.get(url)

# Wait with WebDriverWait for shadow host
wait = WebDriverWait(driver, 20)

try:
    element = wait.until(
        EC.presence_of_element_located((By.TAG_NAME, "sf-unstructured-legislation-viewer"))
    )
    print("✓ Found sf-unstructured-legislation-viewer with WebDriverWait")

    shadow_root = driver.execute_script('return arguments[0].shadowRoot', element)
    if shadow_root:
        shadow_html = driver.execute_script('return arguments[0].innerHTML', shadow_root)
        print(f"✓ Shadow DOM content: {len(shadow_html)} bytes")

        # Parse and check structure
        shadow_soup = BeautifulSoup(shadow_html, 'html.parser')

        # Look for main div
        main_divs = [elem for elem in shadow_soup.children if hasattr(elem, 'name') and elem.name == 'div']
        print(f"✓ Main divs in shadow root: {len(main_divs)}")

        if main_divs:
            main_div = main_divs[0]
            print(f"  Main div classes: {main_div.get('class', [])}")
            paragraphs = main_div.find_all('p')
            print(f"  Paragraphs in main div: {len(paragraphs)}")

            # Show first paragraph
            if paragraphs:
                first_p = paragraphs[0].get_text(strip=True)[:200]
                print(f"  First paragraph: {first_p}")
    else:
        print("✗ Could not access shadow root")

except Exception as e:
    print(f"✗ Shadow DOM not found: {e}")

    # Check if content is in regular DOM instead
    print("\n--- Checking regular DOM ---")
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    articulation = soup.select_one("sf-legislation-articulation-text")
    if articulation:
        print("✓ Found sf-legislation-articulation-text in regular DOM")
        paragraphs = articulation.find_all('p')
        print(f"  Paragraphs: {len(paragraphs)}")

driver.quit()
