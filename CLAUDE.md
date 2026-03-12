# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A web scraping tool that fetches Brazilian federal legal documents from **normas.leg.br** (a JavaScript/Angular SPA with Shadow DOM) and converts them to Microsoft Word (.docx) format. Primary use case: building document corpora for RAG evaluation.

## Setup & Running

Install dependencies:
```bash
pip install -r requirements.txt
```

Run from the CLI with a URL file (one URL per line):
```bash
python legal_document_fetcher.py recent_laws_urls.txt
python legal_document_fetcher.py legal_documents/law_rules_URNs.txt --output-dir ./out --delay 3.0
python legal_document_fetcher.py --help
```

Run the test suite (no browser or network required):
```bash
pytest test_legal_document_fetcher.py -m "not integration"
```

Run integration tests (requires Chrome and network):
```bash
pytest test_legal_document_fetcher.py -m integration
```

Use the Jupyter notebook for exploratory work and URN generation:
```bash
jupyter notebook explore_legal_documents_fetcher.ipynb
```

Enable debug logging:
```python
import logging
logging.getLogger('legal_document_fetcher').setLevel(logging.DEBUG)
```

Disable headless mode for debugging (comment out line ~499 in `legal_document_fetcher.py`):
```python
# chrome_options.add_argument('--headless=new')
```

## Architecture

All logic lives in a single file: `legal_document_fetcher.py` (~880 lines). Four classes with clear separation:

- **`FetcherConfig`** (dataclass) — All configuration in one place: output dir, timeouts, retry counts, rate limiting, CSS selectors, Selenium settings.
- **`HTMLContentExtractor`** — Handles the two rendering formats of normas.leg.br (see below). Parses, extracts, and cleans HTML content.
- **`WordDocumentBuilder`** — Converts HTML elements (headings, paragraphs, lists, tables, base64 images) into a `python-docx` Document object.
- **`LegalDocumentFetcher`** — Orchestrator. Manages Selenium driver lifecycle (lazy init, shared across batch), retry logic, URN parsing, filename generation, batch processing with tqdm, and CSV export.

## Critical: Two Website Rendering Formats

normas.leg.br uses two different formats; the extractor handles both automatically:

1. **Shadow DOM format** (most individual laws): Content is inside `<sf-unstructured-legislation-viewer>`'s shadow root. Selenium accesses it via JavaScript (`arguments[0].shadowRoot`), then appends it to the base HTML with `<!-- SHADOW DOM CONTENT -->` markers for post-processing.

2. **Regular DOM format** (constitution, newer documents): Content is in `<sf-legislation-articulation-text>` directly in the DOM. Matched via fallback CSS selectors.

The `fallback_selectors` list in `HTMLContentExtractor` (line 104) controls priority — new selectors go at the **top** for priority while keeping old ones for backward compatibility.

## URL/URN Format

Target URL pattern:
```
https://normas.leg.br/?urn=urn:lex:br:federal:lei:YYYY-MM-DD;NUMBER
```

Generated filename pattern: `lei_{NUMBER}_{YYYYMMDD}.docx`

Output files go to `./legal_documents/` (gitignored). A list of 106 law URNs is at `legal_documents/law_rules_URNs.txt`.

## Key Behaviors to Be Aware Of

- **Selenium driver is shared** across a batch — initialized lazily on first use, cleaned up after `process_url_list()` completes.
- **Content validation**: Documents with fewer than 100 characters of text are rejected as failed fetches (Shadow DOM may not have loaded).
- **Titles longer than 200 chars** are skipped to avoid incorrectly extracted titles.
- The `requests`-based fallback path in `fetch_webpage()` will **not work** for normas.leg.br (no JS rendering), but is retained for potential future use with static pages.
