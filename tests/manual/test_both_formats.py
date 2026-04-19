"""Test script to compare both URL formats."""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def test_url_structure(url, name):
    """Test a URL and report its structure."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print('='*60)

    # Initialize Chrome
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(url)
    time.sleep(5)  # Wait for JavaScript

    # Check for Shadow DOM
    print("\n--- Shadow DOM Check ---")
    try:
        element = driver.find_element(By.TAG_NAME, "sf-unstructured-legislation-viewer")
        print("✓ Found sf-unstructured-legislation-viewer")
        shadow_root = driver.execute_script('return arguments[0].shadowRoot', element)
        if shadow_root:
            shadow_html = driver.execute_script('return arguments[0].innerHTML', shadow_root)
            print(f"✓ Shadow DOM accessible ({len(shadow_html)} bytes)")

            # Parse shadow DOM content
            shadow_soup = BeautifulSoup(shadow_html, 'html.parser')
            divs = shadow_soup.find_all('div')
            print(f"  Divs in shadow DOM: {len(divs)}")
            if divs:
                print(f"  First div classes: {divs[0].get('class', [])}")
    except Exception as e:
        print(f"✗ No sf-unstructured-legislation-viewer or shadow DOM: {e}")

    # Check regular DOM
    print("\n--- Regular DOM Check ---")
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    selectors = [
        "sf-legislation-articulation-text",
        "div.content-text",
        "sf-unstructured-legislation-viewer",
        "app-legislacao",
        "div.texto",
    ]

    for selector in selectors:
        results = soup.select(selector)
        if results:
            print(f"✓ {selector}: {len(results)} element(s)")
            if len(results) == 1:
                # Check for paragraphs
                paragraphs = results[0].find_all('p')
                print(f"  Contains {len(paragraphs)} <p> tags")
        else:
            print(f"✗ {selector}: Not found")

    driver.quit()

# Test both formats
test_url_structure(
    "https://normas.leg.br/?urn=urn:lex:br:federal:constituicao:1988-10-05;1988",
    "Constitution (NEW FORMAT - failing)"
)

test_url_structure(
    "https://normas.leg.br/?urn=urn:lex:br:federal:lei:2003-10-01;10741",
    "Lei 10.741 (OLD FORMAT - working)"
)
