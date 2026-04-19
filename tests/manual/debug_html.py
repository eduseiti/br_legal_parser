"""Debug script to inspect HTML structure."""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Initialize Chrome
chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

url = "https://normas.leg.br/?urn=urn:lex:br:federal:constituicao:1988-10-05;1988"
print(f"Loading: {url}")
driver.get(url)

# Wait a bit for JavaScript to load
time.sleep(5)

# Try to find shadow DOM elements
print("\n=== Looking for shadow host elements ===")
shadow_hosts = [
    "sf-unstructured-legislation-viewer",
    "sf-structured-legislation-viewer",
    "app-legislacao",
    "sf-legislation-viewer"
]

for tag in shadow_hosts:
    try:
        elements = driver.find_elements(By.TAG_NAME, tag)
        if elements:
            print(f"✓ Found {len(elements)} element(s) with tag: {tag}")
            for i, elem in enumerate(elements):
                # Try to access shadow root
                shadow_root = driver.execute_script('return arguments[0].shadowRoot', elem)
                if shadow_root:
                    shadow_html = driver.execute_script('return arguments[0].innerHTML', shadow_root)
                    print(f"  - Element {i}: Has shadow DOM ({len(shadow_html)} bytes)")
                    # Print first 500 chars of shadow content
                    print(f"    Preview: {shadow_html[:500]}...")
                else:
                    print(f"  - Element {i}: No shadow root accessible")
        else:
            print(f"✗ No elements found with tag: {tag}")
    except Exception as e:
        print(f"✗ Error searching for {tag}: {e}")

# Check page source
print(f"\n=== Page source info ===")
page_source = driver.page_source
print(f"Total page source: {len(page_source)} bytes")

# Look for specific markers in the page source
if "CONSTITUIÇÃO DA REPÚBLICA" in page_source.upper():
    print("✓ Found 'CONSTITUIÇÃO' text in page source")
else:
    print("✗ 'CONSTITUIÇÃO' not found in page source")

# Save page source for inspection
with open('/work/doutorado/artigos/RAG_evaluation/br_legal_parser/debug_page_source.html', 'w', encoding='utf-8') as f:
    f.write(page_source)
print("\n✓ Saved page source to debug_page_source.html")

driver.quit()
