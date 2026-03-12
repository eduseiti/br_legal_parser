# Brazilian Legal Document Parser - Architecture & Feature Reference

## Project Overview

This repository contains a web scraping tool designed to fetch Brazilian federal legal documents from the **normas.leg.br** website, which uses JavaScript-rendered content with Shadow DOM elements. The tool converts legal documents into Microsoft Word (.docx) format for further processing and analysis.

**Primary Use Case**: Automated fetching and conversion of Brazilian federal laws (Leis Federais) for RAG (Retrieval-Augmented Generation) evaluation and legal document analysis.

## Technology Stack

### Core Dependencies
- **Python 3.x**
- **Selenium WebDriver** - Browser automation for JavaScript-rendered pages
- **BeautifulSoup4** - HTML parsing and content extraction
- **python-docx** - Word document generation
- **requests** - HTTP client (fallback for non-JS pages)
- **webdriver-manager** - Automatic ChromeDriver management
- **tqdm** - Progress bar visualization
- **pandas** - Data processing (in notebooks)

### Target Website
- **URL Pattern**: `https://normas.leg.br/?urn=urn:lex:br:federal:lei:{YYYY}-{MM}-{DD};{NUMBER}`
- **Format**: LexML URN (Legal XML) standard for Brazilian legislation
- **Rendering**: JavaScript-based with Angular components and Shadow DOM

## Architecture

### Object-Oriented Design

The system follows a clean, modular OOP architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│          LegalDocumentFetcher (Orchestrator)            │
│  - Manages overall workflow                             │
│  - Coordinates between components                       │
│  - Handles retry logic and error handling               │
└────────┬──────────────────────────────────────┬─────────┘
         │                                      │
         ▼                                      ▼
┌─────────────────────┐            ┌────────────────────────┐
│ HTMLContentExtractor│            │ WordDocumentBuilder    │
│ - Selenium driver   │            │ - HTML to Word         │
│ - Shadow DOM access │            │ - Formatting           │
│ - Content cleaning  │            │ - Images (base64)      │
└─────────────────────┘            │ - Tables, lists        │
                                   └────────────────────────┘

         ┌──────────────────────────────┐
         │ FetcherConfig (Configuration)│
         │ - Settings and parameters    │
         └──────────────────────────────┘

         ┌──────────────────────────────┐
         │ FetchResult (Data Class)     │
         │ - Operation results          │
         └──────────────────────────────┘
```

## Core Classes & Components

### 1. `FetcherConfig` (Configuration)
**File**: `legal_document_fetcher.py:55-72`

Dataclass that holds all configuration settings for the fetcher.

**Key Parameters**:
```python
output_dir: str = "./legal_documents"          # Output directory
request_timeout: int = 30                      # HTTP timeout
retry_attempts: int = 3                        # Retry count
delay_between_requests: float = 2.0            # Rate limiting
user_agent: str = "Mozilla/5.0..."            # Browser UA string
content_selector: str = "div.texto"            # CSS selector
create_output_dir: bool = True                 # Auto-create dirs
use_selenium: bool = True                      # Use Selenium vs requests
selenium_wait_time: int = 20                   # Shadow DOM wait time
```

**Why it matters**: Centralized configuration makes it easy to adjust scraping behavior without modifying code. Critical for handling rate limits and site changes.

---

### 2. `FetchResult` (Result Storage)
**File**: `legal_document_fetcher.py:75-90`

Dataclass for storing individual fetch operation results.

**Attributes**:
- `url: str` - Source URL
- `success: bool` - Operation status
- `law_number: str` - Extracted law identifier
- `filename: str` - Generated output filename
- `error_message: Optional[str]` - Error details if failed
- `fetch_time: float` - Processing time in seconds

**Usage**: Enables detailed reporting and debugging of batch operations.

---

### 3. `HTMLContentExtractor` (Content Extraction)
**File**: `legal_document_fetcher.py:93-233`

Handles all HTML content extraction, including complex Shadow DOM navigation.

#### Key Features:

##### a. Shadow DOM Content Extraction
**Method**: `_get_html_with_shadow_dom()` (line 533-581)

The normas.leg.br website uses the `<sf-unstructured-legislation-viewer>` web component with Shadow DOM to encapsulate legal content. This method:
1. Waits for the shadow host element to load
2. Accesses the shadow root using JavaScript execution
3. Extracts innerHTML from the shadow DOM
4. Merges it with base HTML using special markers

```python
# Markers used to identify shadow content
<!-- SHADOW DOM CONTENT -->
...shadow content here...
<!-- END SHADOW DOM -->
```

##### b. Fallback Selector Strategy
**Method**: `extract_main_content()` (line 115-182)

Implements a robust fallback chain that handles **two different website formats**:

```python
fallback_selectors = [
    "sf-legislation-articulation-text",  # NEW FORMAT (2024+) - structured legislation in regular DOM
    "div.content-text",                  # NEW FORMAT - content div inside Angular component
    "app-legislacao",                    # OLD FORMAT - Angular component
    "div.texto",                         # PRIMARY - generic content div
    "div#texto",
    "article",
    "main",
    "div.content",
    "div#content",
    "div.container"                      # Last resort
]
```

**Two Website Formats Supported**:

1. **Old Format (Shadow DOM)**: Used for most individual laws
   - Component: `<sf-unstructured-legislation-viewer>`
   - Content location: Inside Shadow DOM
   - Extraction: Via `_get_html_with_shadow_dom()` method
   - Example: `lei:2000-12-19;10101`

2. **New Format (Regular DOM)**: Used for constitution and newer documents
   - Component: `<sf-legislation-articulation-text>`
   - Content location: Regular DOM (no shadow)
   - Extraction: Direct CSS selector matching
   - Example: `constituicao:1988-10-05;1988`

The selector priority ensures backward compatibility while supporting new formats.

##### c. Content Cleaning
**Method**: `clean_content()` (line 184-207)

Removes:
- Scripts and styles
- Meta tags and links
- HTML comments
- Empty tags (preserving `<br>`, `<hr>`, `<img>`)

##### d. Title Extraction
**Method**: `get_law_title()` (line 209-233)

Extracts law title using:
1. HTML heading tags (`h1`, `h2`, `title`)
2. Regex pattern matching for "Lei" patterns
3. Fallback to generic "Legal Document"

---

### 4. `WordDocumentBuilder` (Document Generation)
**File**: `legal_document_fetcher.py:236-452`

Converts HTML content to formatted Word documents.

#### Key Features:

##### a. HTML to Word Conversion
**Method**: `add_html_content()` (line 277-339)

Supports:
- **Headings**: `h1`-`h6` → Word heading styles
- **Paragraphs**: `<p>` with inline formatting
- **Lists**: `<ul>`, `<ol>` → Word bullet/numbered lists
- **Tables**: `<table>` → Word tables with styling
- **Images**: Base64-encoded images → embedded pictures
- **Divs**: Recursive processing

##### b. Text Formatting
**Method**: `_add_formatted_text()` (line 341-375)

Preserves:
- **Bold**: `<strong>`, `<b>`
- **Italic**: `<em>`, `<i>`
- **Underline**: `<u>`

##### c. Image Handling
**Method**: `_add_image()` (line 384-414)

- Decodes base64-encoded images from data URIs
- Embeds images in Word document
- Centers images with fixed width (0.71 inches)
- Logs warnings for external URLs (not downloaded)

##### d. Table Conversion
**Method**: `_add_table()` (line 416-434)

- Auto-detects column count
- Applies "Light Grid Accent 1" style
- Preserves cell text content

---

### 5. `LegalDocumentFetcher` (Main Orchestrator)
**File**: `legal_document_fetcher.py:455-870`

Main class that coordinates the entire workflow.

#### Key Features:

##### a. Selenium-Based Fetching
**Method**: `_fetch_with_selenium()` (line 506-531)

Uses headless Chrome with optimizations:
```python
chrome_options:
- --headless=new              # New headless mode
- --no-sandbox                # Docker compatibility
- --disable-dev-shm-usage     # Memory optimization
- --disable-gpu               # Performance
- --disable-blink-features=AutomationControlled  # Anti-detection
- --window-size=1920,1080     # Standard viewport
```

**Why Selenium**: normas.leg.br requires JavaScript execution to render legal content. Traditional HTTP requests (via `requests` library) only retrieve the Angular shell without actual content.

##### b. URN Parsing and Filename Generation
**Method**: `extract_law_number_from_url()` (line 627-661)

Parses LexML URN format:
```
Input:  https://normas.leg.br/?urn=urn:lex:br:federal:lei:2003-10-01;10741
Output: lei_10741_20031001
```

Pattern breakdown:
- `urn:lex:br:federal:lei` - Fixed prefix for federal laws
- `YYYY-MM-DD` - Date of enactment
- `NUMBER` - Law number

##### c. Batch Processing
**Method**: `process_url_list()` (line 771-805)

Features:
- Progress bar with tqdm
- Configurable delays between requests (rate limiting)
- Result aggregation
- Automatic cleanup of Selenium driver
- Error tolerance (continues on failures)

##### d. Error Handling & Retry Logic
**Method**: `fetch_webpage()` (line 583-625)

Implements:
- Exponential backoff (2^attempt seconds)
- Configurable retry attempts
- Specific handling for:
  - Timeout errors
  - HTTP errors
  - Connection errors
  - Generic exceptions

##### e. Statistics and Reporting
**Methods**:
- `get_summary()` (line 818-840) - Aggregated statistics
- `export_results_to_csv()` (line 842-870) - CSV export

Summary includes:
- Total/success/failed counts
- Success rate percentage
- Average fetch time
- List of failed URLs

---

## URN Format for Brazilian Legal Documents

### LexML URN Structure

The project uses the **LexML (Legal XML)** standard for identifying Brazilian legislation.

**Format**:
```
urn:lex:br:federal:lei:YYYY-MM-DD;NUMBER
```

**Components**:
- `urn:lex` - URN scheme for legal documents
- `br` - Brazil
- `federal` - Federal jurisdiction
- `lei` - Document type (law)
- `YYYY-MM-DD` - Date of enactment
- `NUMBER` - Law number (no dots, e.g., 10741)

**Full URL Example**:
```
https://normas.leg.br/?urn=urn:lex:br:federal:lei:2003-10-01;10741
```

This references Lei nº 10.741 (Estatuto do Idoso), enacted on October 1, 2003.

---

## Project Structure

```
br_legal_parser/
├── legal_document_fetcher.py          # Main module (~930 lines)
│   ├── FetcherConfig                  # Configuration dataclass
│   ├── FetchResult                    # Result dataclass
│   ├── HTMLContentExtractor           # Content extraction
│   ├── WordDocumentBuilder            # Word generation
│   └── LegalDocumentFetcher           # Main orchestrator
│
├── test_legal_document_fetcher.py     # Pytest test harness (53 unit tests)
├── conftest.py                        # Pytest marker registration
├── recent_laws_urls.txt               # Sample URL file (6 recent laws)
│
├── explore_legal_documents_fetcher.ipynb  # Usage examples & URN generation
│   ├── URN generation from law titles
│   ├── LexML URL formatting
│   ├── Batch processing examples
│   └── Result analysis
│
├── legal_documents/                   # Output directory
│   ├── *.docx                         # Generated Word files
│   ├── law_rules_URNs.txt            # List of URNs (106 laws)
│   └── fetch_results.csv             # Batch operation results
│
├── requirements.txt                   # Python dependencies (includes pytest)
├── .gitignore                         # Standard Python gitignore
├── LICENSE                            # MIT License
└── README.md                          # Basic project info
```

---

## Key Features

### 1. JavaScript-Rendered Content Support
- Uses Selenium WebDriver with headless Chrome
- Waits for dynamic content to load
- Handles single-page applications (Angular)

### 2. Dual Format Support (Shadow DOM & Regular DOM)
**IMPORTANT UPDATE (December 2024)**: The website now uses two different rendering formats:

- **Shadow DOM Format** (Old): Most individual laws use `<sf-unstructured-legislation-viewer>` with content hidden in Shadow DOM
- **Regular DOM Format** (New): Constitution and some newer documents use `<sf-legislation-articulation-text>` with content directly in regular DOM

The parser automatically detects and handles both formats:
1. First tries Shadow DOM extraction (if markers present)
2. Falls back to new format selectors (`sf-legislation-articulation-text`, `div.content-text`)
3. Continues through legacy selectors for older page structures
4. Ensures **100% backward compatibility** while supporting new formats

### 3. Robust Content Extraction
- Multiple fallback selectors
- Content validation (minimum length check)
- HTML cleaning and normalization

### 4. Word Document Generation
- Preserves text formatting (bold, italic, underline)
- Converts HTML tables to Word tables
- Embeds base64 images
- Maintains document structure (headings, lists)

### 5. Error Handling & Resilience
- Retry logic with exponential backoff
- Graceful degradation on failures
- Detailed error reporting
- Timeout protection

### 6. Rate Limiting & Politeness
- Configurable delays between requests
- User-Agent headers
- Respects server resources

### 7. Progress Tracking
- tqdm progress bars
- Per-document timing
- Success/failure statistics
- CSV export for analysis

### 8. Batch Processing
- Process multiple URLs in one run
- Continue on individual failures
- Aggregate statistics
- Resource cleanup

---

## Usage Patterns

### Basic Single Document Fetch

```python
from legal_document_fetcher import LegalDocumentFetcher, FetcherConfig

# Configure
config = FetcherConfig(
    output_dir='./legal_documents',
    retry_attempts=3,
    delay_between_requests=2.0
)

# Create fetcher
fetcher = LegalDocumentFetcher(config)

# Fetch single document
url = "https://normas.leg.br/?urn=urn:lex:br:federal:lei:2003-10-01;10741"
result = fetcher.process_single_url(url)

print(result)  # ✓ lei_10741_20031001 -> lei_10741_20031001.docx (1.49s)
```

### Batch Processing

```python
# Read URLs from file
with open('legal_documents/law_rules_URNs.txt', 'r') as f:
    urls = [line.strip() for line in f]

# Process all URLs
results = fetcher.process_url_list(urls, show_progress=True)

# Get summary
summary = fetcher.get_summary()
print(f"Success rate: {summary['success_rate']:.2f}%")
print(f"Total: {summary['total']}, Success: {summary['success']}, Failed: {summary['failed']}")

# Export results
fetcher.export_results_to_csv('results.csv')
```

### URN Generation from Law Titles

The Jupyter notebook shows how to convert law titles to URNs:

```python
import re

# Example: "Lei nº 10.741, de 1 de outubro de 2003"
pattern = r"Lei[^0-9]+([0-9\.]+),\sde\s([0-9]+)\sde\s(\w+)\sde\s([0-9]+)"
match = re.match(pattern, title)

# Extract: law_number=10741, day=1, month=outubro, year=2003
# Format: https://normas.leg.br/?urn=urn:lex:br:federal:lei:2003-10-01;10741
```

---

## Configuration Options

### Performance Tuning

```python
config = FetcherConfig(
    request_timeout=30,           # Increase for slow connections
    retry_attempts=3,             # More retries for unreliable networks
    delay_between_requests=2.0,   # Increase to be more polite
    selenium_wait_time=20         # Increase if Shadow DOM loads slowly
)
```

### Output Customization

```python
config = FetcherConfig(
    output_dir='./custom_output',
    content_selector='div.custom-selector',  # Change if site structure changes
    create_output_dir=True
)
```

### Selenium vs Requests

```python
# For JavaScript-rendered pages (default)
config = FetcherConfig(use_selenium=True)

# For static HTML pages (faster, but won't work for normas.leg.br)
config = FetcherConfig(use_selenium=False)
```

---

## Output Files

### Generated Word Documents

**Filename Format**: `lei_{NUMBER}_{YYYYMMDD}.docx`

Example: `lei_10741_20031001.docx` for Lei 10.741 from 2003-10-01

**Document Contents**:
- Title (if successfully extracted)
- Full legal text with formatting
- Embedded images (if present)
- Tables and lists
- Metadata (title, subject)

### Results CSV

**Columns**:
- `URL` - Source URL
- `Success` - True/False
- `Law Number` - Extracted identifier
- `Filename` - Output filename
- `Error` - Error message (if failed)
- `Fetch Time` - Processing time in seconds

**Usage**: Analysis of batch operations, identifying failed fetches, performance metrics

### URNs Text File

**Format**: One URL per line
```
https://normas.leg.br/?urn=urn:lex:br:federal:lei:2000-12-19;10101
https://normas.leg.br/?urn=urn:lex:br:federal:lei:2001-02-14;10200
...
```

**Usage**: Input for batch processing, archival of processed laws

---

## Known Limitations & Challenges

### 1. Multiple Website Formats
- Website uses two different rendering formats (Shadow DOM vs Regular DOM)
- Requires Selenium (slower than requests) for JavaScript-rendered content
- Needs ChromeDriver (additional dependency)
- May fail if site introduces new web component structures

**Current Status**: ✅ RESOLVED (December 2024)
- Now handles both Shadow DOM and Regular DOM formats automatically
- Backward compatible with all existing document types
- Tested with Constitution (2,911 paragraphs) and individual laws (71+ paragraphs)

**Mitigation**: Dual selector strategy, wait time configuration, comprehensive fallback chain

### 2. Rate Limiting
- No built-in respect for robots.txt
- Manual delay configuration required
- No concurrent requests (sequential processing)

**Mitigation**: Configure `delay_between_requests` appropriately

### 3. Image Handling
- Only base64-encoded images are embedded
- External image URLs are skipped
- No size optimization

**Mitigation**: Log warnings for skipped images

### 4. Title Extraction
- Generic fallback if title not found
- May extract incorrect text as title
- Skips very long titles (>200 chars)

**Mitigation**: Regex pattern matching, multiple strategies

### 5. Content Validation
- Minimum length check (100 chars) may reject valid short laws
- No content quality validation
- No legal structure validation

**Mitigation**: Manual review of failed fetches

---

## Future Development Opportunities

### Performance Enhancements
1. **Concurrent Processing**: Use asyncio or multiprocessing for parallel fetches
2. **Caching**: Cache successful fetches to avoid re-downloading
3. **Smart Retry**: Exponential backoff with jitter
4. **Connection Pooling**: Reuse Selenium sessions

### Feature Additions
1. **PDF Export**: Convert to PDF alongside Word
2. **Structured Parsing**: Extract articles, paragraphs, amendments
3. **Version Control**: Track law modifications over time
4. **Metadata Extraction**: Extract law metadata (author, subject, etc.)
5. **Full-Text Search**: Index documents for searching

### Robustness Improvements
1. **robots.txt Compliance**: Check and respect robots.txt
2. **User-Agent Rotation**: Avoid detection
3. **Proxy Support**: Route through proxies
4. **Checkpoint/Resume**: Save progress and resume interrupted batches
5. **Schema Validation**: Validate URN format before fetching

### Code Quality
1. **Type Hints**: Add comprehensive type annotations
2. ~~**Unit Tests**: Test individual components~~ ✅ Done — `test_legal_document_fetcher.py`
3. ~~**Integration Tests**: Test full workflow~~ ✅ Done — `pytest -m integration`
4. **Logging Levels**: Configurable logging verbosity
5. ~~**Requirements File**: Create requirements.txt for dependencies~~ ✅ Done

---

## Development Quick Start

### Dependencies

**Required Python packages** (inferred from imports):
```bash
pip install selenium beautifulsoup4 python-docx requests webdriver-manager tqdm pandas
```

### Running the Module

**As a CLI script** (pass a URL file as a positional argument):
```bash
# Fetch all URLs in a file (one URL per line, blank lines and # comments ignored)
python legal_document_fetcher.py recent_laws_urls.txt

# Custom output dir and rate limit
python legal_document_fetcher.py my_urls.txt --output-dir ./output --delay 3.0 --retries 5

# Built-in help
python legal_document_fetcher.py --help
```

**In a Python script**:
```python
from legal_document_fetcher import LegalDocumentFetcher, FetcherConfig

config = FetcherConfig(output_dir='./output')
fetcher = LegalDocumentFetcher(config)
results = fetcher.process_url_list([url1, url2, ...])
```

**In Jupyter Notebook**:
See `explore_legal_documents_fetcher.ipynb` for examples.

### Running the Tests

```bash
# Unit tests — no browser or network required (fast)
pytest test_legal_document_fetcher.py -m "not integration"

# Integration tests — require Chrome and network access
pytest test_legal_document_fetcher.py -m integration

# All tests
pytest test_legal_document_fetcher.py
```

Test coverage:
- `FetcherConfig` and `FetchResult` dataclasses
- `LegalDocumentFetcher.extract_law_number_from_url()` — parametrized with every URL in `recent_laws_urls.txt`
- `LegalDocumentFetcher.generate_filename()` — including duplicate-counter logic
- `HTMLContentExtractor` — Shadow DOM path, regular DOM path, fallback selectors, `clean_content`, `get_law_title`
- `WordDocumentBuilder` — heading conversion, bold formatting, title skip rules, file save
- `get_summary()` statistics
- CLI entry-point (`--help`, missing arg, empty file, comment-only file, indented comments)

### Debugging

**Enable verbose logging**:
```python
import logging
logging.getLogger('legal_document_fetcher').setLevel(logging.DEBUG)
```

**Check Selenium browser** (non-headless mode):
```python
# In legal_document_fetcher.py, line 490:
# Comment out: chrome_options.add_argument('--headless=new')
```

---

## Key Methods Reference

### LegalDocumentFetcher

| Method | Purpose | Returns |
|--------|---------|---------|
| `process_single_url(url)` | Fetch and convert one document | `FetchResult` |
| `process_url_list(urls)` | Batch process multiple URLs | `List[FetchResult]` |
| `get_summary()` | Get statistics | `Dict` with stats |
| `export_results_to_csv(path)` | Save results to CSV | None |
| `extract_law_number_from_url(url)` | Parse URN | Law identifier string |
| `generate_filename(law_number, url)` | Create output filename | File path string |
| `cleanup()` | Close Selenium driver | None |

### HTMLContentExtractor

| Method | Purpose | Returns |
|--------|---------|---------|
| `extract_main_content(html)` | Get main content div | `BeautifulSoup` object |
| `clean_content(soup)` | Remove unwanted elements | Cleaned `BeautifulSoup` |
| `get_law_title(soup)` | Extract document title | Title string |

### WordDocumentBuilder

| Method | Purpose | Returns |
|--------|---------|---------|
| `create_document(content, title)` | Build Word doc | `Document` object |
| `add_html_content(doc, soup)` | Add HTML to doc | None (modifies doc) |
| `save_document(doc, filepath)` | Write to disk | None |

---

## Common Workflows

### 1. Adding New Law Sources

To add laws from a different jurisdiction or type:

1. **Generate URNs**: Modify the URN format in the notebook
   ```python
   # Example: State law instead of federal
   URN_FORMAT = "https://normas.leg.br/?urn=urn:lex:br:{state}:lei:..."
   ```

2. **Test Single URL**: Verify the selector works
   ```python
   result = fetcher.process_single_url(test_url)
   ```

3. **Adjust Selectors**: If content extraction fails, update `content_selector`
   ```python
   config = FetcherConfig(content_selector='div.new-selector')
   ```

4. **Batch Process**: Run on full list

### 2. Handling Site Changes

If normas.leg.br introduces a new format or structure:

1. **Test with Debug Script**: Use Selenium to inspect the page
   ```python
   from selenium import webdriver
   from bs4 import BeautifulSoup

   driver = webdriver.Chrome()
   driver.get(url)

   # Check for Shadow DOM
   element = driver.find_element(By.TAG_NAME, "sf-unstructured-legislation-viewer")
   shadow_root = driver.execute_script('return arguments[0].shadowRoot', element)

   # Check regular DOM
   soup = BeautifulSoup(driver.page_source, 'html.parser')
   print(soup.select("sf-legislation-articulation-text"))
   ```

2. **Identify Content Container**: Look for the main content wrapper
   - Shadow DOM: Usually a `<div>` inside shadow root
   - Regular DOM: Look for Angular components or content divs

3. **Update Selectors**: Add new selector to `fallback_selectors` list (line 104-115)
   - Place new selectors at the TOP of the list for priority
   - Keep old selectors for backward compatibility

4. **Test Both Formats**: Verify old URLs still work
   - Test with shadow DOM URL: `lei:2000-12-19;10101`
   - Test with regular DOM URL: `constituicao:1988-10-05;1988`

5. **Update Wait Conditions**: If using Shadow DOM, modify line 547 in `_get_html_with_shadow_dom()`

### 3. Converting to Different Formats

To export to PDF instead of Word:

1. **Add PDF Library**: `pip install python-docx2pdf`
2. **Extend Builder**: Add `save_as_pdf()` method
3. **Modify Workflow**: Call PDF export after Word generation

---

## Success Metrics (from Last Run)

**Sample Batch Results** (106 URLs):
- **Success Rate**: 90.57%
- **Average Fetch Time**: 3.24s per document
- **Total Documents**: 96 successful, 10 failed
- **Common Failures**: Shadow DOM timeout, insufficient content

**Performance**: ~3-4 minutes for 100 documents (with 2s delays)

---

## Contact & Contribution

This is a research tool for RAG evaluation and legal document analysis.

**Potential Improvements Welcome**:
- Better error handling
- More robust title extraction
- Support for other legal document types
- Performance optimizations
- Test coverage

**Git Repository**: /work/doutorado/artigos/RAG_evaluation/br_legal_parser

---

## License

MIT License (see LICENSE file)

---

## Recent Updates

### December 7, 2024 - Dual Format Support Fix

**Issue**: Constitution and some newer documents were being extracted as single unformatted paragraphs (545K characters)

**Root Cause**: Website migrated from Shadow DOM to Regular DOM for certain document types, but selectors only matched old format

**Solution**: Added new selectors to handle both formats
- `sf-legislation-articulation-text` - New Angular component for structured legislation
- `div.content-text` - Content wrapper in new format

**Test Results**:
| Document Type | Before Fix | After Fix | Status |
|---------------|------------|-----------|--------|
| Constitution 1988 | 29 paragraphs<br/>First: 545,804 chars | 2,911 paragraphs<br/>First: 46 chars | ✅ Fixed |
| Lei 10.101/2000 | 71 paragraphs (working) | 71 paragraphs | ✅ Compatible |

**Impact**: Parser now correctly handles both rendering formats with 100% backward compatibility

---

**Last Updated**: December 7, 2024
**Python Version**: 3.x
**Primary Maintainer**: Research Project
