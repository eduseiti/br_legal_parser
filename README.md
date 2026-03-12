# br_legal_parser

A web scraping tool that fetches Brazilian federal legal documents from [normas.leg.br](https://normas.leg.br) and converts them to Microsoft Word (.docx) format, intended for use in RAG (Retrieval-Augmented Generation) pipelines and legal document analysis.

## Quick Start

Install dependencies:
```bash
pip install -r requirements.txt
```

Fetch documents from a URL file (one URL per line):
```bash
python legal_document_fetcher.py recent_laws_urls.txt
python legal_document_fetcher.py legal_documents/law_rules_URNs.txt --output-dir ./out --delay 3.0
python legal_document_fetcher.py --help
```

Or use the API directly:
```python
from legal_document_fetcher import LegalDocumentFetcher, FetcherConfig

fetcher = LegalDocumentFetcher(FetcherConfig(output_dir='./legal_documents'))
result = fetcher.process_single_url("https://normas.leg.br/?urn=urn:lex:br:federal:lei:2003-10-01;10741")
print(result)  # ✓ lei_10741_20031001 -> lei_10741_20031001.docx (1.49s)
```

See `explore_legal_documents_fetcher.ipynb` for batch processing examples and URN generation from law titles.

## Testing

Run the unit tests (no browser or network required):
```bash
pytest test_legal_document_fetcher.py -m "not integration"
```

Run integration tests (requires Chrome and network):
```bash
pytest test_legal_document_fetcher.py -m integration
```

## How It Works

The site renders legal content via JavaScript/Angular with Shadow DOM elements, so the tool uses Selenium (headless Chrome) to render pages and extract content. Extracted HTML is then converted to `.docx` using `python-docx`.

Documents are saved as `lei_{NUMBER}_{YYYYMMDD}.docx` in the configured output directory.

## Documentation

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation covering class design, the dual Shadow DOM / Regular DOM rendering formats, configuration options, output formats, known limitations, and development workflows.

## License

MIT License
