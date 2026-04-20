# Plan: resolve human-readable law references to normas.leg.br URNs

## Context

`legal_document_fetcher.py` takes URN URLs (e.g. `https://normas.leg.br/?urn=urn:lex:br:federal:lei:2011-11-18;12527`) and converts each document to `.docx`. Building that input list by hand is painful — the user curates laws as human-friendly strings (see `lista_de_leis.txt`: `Lei 12527/2011`, `Decreto-lei 4657/1942`, `Constituição`, …). This feature closes the gap: given a text file of such strings, query `https://normas.leg.br/busca`, find the exact match (by type + number + date), capture the URN, and write a CSV mapping each input line to its URN. The CSV is then the input for the existing fetcher.

## Scope (from user clarifications)

- **Supported types:** `Lei`, `Lei Complementar`, `Decreto`, `Decreto-Lei`, `Constituição`. Anything else in the input (e.g. `Res. Anatel 612/2015`, `Portaria MJSP 502/2021`, `Res. ANPD 2/2022`) → recorded as `status=unsupported_type`, not an error.
- **Date matching:** if the input line has only a year (`Lei 12527/2011`), match on year only. If a full date is present, match on the full date. `Constituição` has no number/date — hard-match the single federal constitution URN.
- **Output:** a CSV.

## Files

Files to create:
- `law_urn_resolver.py` — new module (do not extend `legal_document_fetcher.py`; it is already ~930 lines and mixes concerns).
- `test_law_urn_resolver.py` — unit + integration tests, following the convention of the existing `test_legal_document_fetcher.py`.

Files to read/reuse (no edits required):
- `legal_document_fetcher.py:53` — reuse `FetcherConfig` verbatim (output_dir, delay_between_requests, selenium_wait_time, user_agent).
- `legal_document_fetcher.py:492-511` — `_init_selenium_driver`. Duplicate the ~15 lines into the new module rather than forcing a shared helper; keep the refactor out of scope.
- `legal_document_fetcher.py:540-588` — `_get_html_with_shadow_dom` pattern (`driver.execute_script('return arguments[0].shadowRoot', el)`). Reuse the idiom.
- `legal_document_fetcher.py:634-668` — URN-parsing regex (`urn:lex:br:federal:<type>:YYYY-MM-DD;NUMBER`). Adapt to parse URNs pulled out of `href` attributes in search results.
- `legal_document_fetcher.py:849-877` — CSV export style (`csv.writer`, header row).
- `conftest.py:2` — `@pytest.mark.integration` marker (no edit).
- `explore_legal_documents_fetcher.ipynb` — Portuguese month-name → int dict (for the optional full-date regex).

## Module design (`law_urn_resolver.py`)

Small, focused classes:

1. `InputEntry` dataclass: `raw_line, doc_type (canonical), number (normalized or None), year (int or None), full_date (date or None), supported (bool), parse_error (str or None)`.
2. `ResolverResult` dataclass: `input, urn_url, matched_type, matched_date, status, error_message` (6 columns; CSV header matches).
3. `InputParser` — pure Python. `parse_line(str) -> InputEntry`. Regex set, tried **in order** (most-specific first so `Lei Complementar` beats plain `Lei`):
   - `^constitui[cç][aã]o$` → `constituicao` (case-insensitive, accent-insensitive).
   - `^lei\s+complementar\s+(?P<num>[\d.]+)/(?P<year>\d{4})$` → `lei_complementar`.
   - `^decreto[\s-]*lei\s+(?P<num>[\d.]+)/(?P<year>\d{4})$` → `decreto_lei` (handles `Decreto-lei`, `Decreto-Lei`, `Decreto lei`).
   - `^decreto\s+(?P<num>[\d.]+)/(?P<year>\d{4})$` → `decreto`.
   - `^lei\s+(?P<num>[\d.]+)/(?P<year>\d{4})$` → `lei`.
   - Optional full-date variant using month-name dict from the notebook.
   - Number normalization: `re.sub(r"[.\s]", "", num).lstrip("0") or "0"`.
   - Type canonicalization: NFD-normalize, strip combining marks, lowercase, underscore-join.
4. `SearchResultMatcher` — pure Python. `match(entry, candidates) -> (status, best_candidate_or_list)`. Matching rules:
   - URN type segment → canonical type via map `{"lei.complementar": "lei_complementar", "decreto.lei": "decreto_lei", "lei": "lei", "decreto": "decreto", "constituicao": "constituicao"}`; other segments rejected.
   - Number: normalize both sides, require equality.
   - Date: full-date equality if `entry.full_date` set, else year equality.
   - 0 matches → `not_found`; 1 → `found`; >1 → `ambiguous` (join URNs with `;`).
   - `Constituição`: if no candidate parses, fall back to hard-coded `urn:lex:br:federal:constituicao:1988-10-05;1988`.
5. `_SearchPageClient` — Selenium interaction. Methods: `search(type, number, year) -> list[SearchCandidate]`, `close()`. Candidates parse the URN itself (authoritative), with the display text used only as a sanity check.
6. `LawURNResolver` — orchestrator. Owns a `FetcherConfig` and a lazy driver. `resolve(entry) -> ResolverResult`, `resolve_file(in_path, out_path)`, `close()`, context-manager protocol. Applies `config.delay_between_requests` between searches. Wraps each resolve in try/except so one failure doesn't kill the batch → `status=error`, `error_message` populated.

## Search-page interaction — probe first

The current shadow host `sf-unstructured-legislation-viewer` is for individual document pages, **not** `/busca`. The busca-page structure is unknown. **First implementation task** is a throwaway Selenium probe (runnable from a notebook cell or a one-off script under `tests/manual/` — do NOT commit as a test):

1. Selenium-load `https://normas.leg.br/busca`, try both a plain visit and `?q=12527` / `?termo=12527` / `?busca=12527`.
2. Enumerate shadow roots via `document.querySelectorAll('*')` filtered by `.shadowRoot !== null`; log tag names. Likely candidates: `sf-search-results`, `sf-search-viewer`, `app-busca`, `app-root`.
3. Enable `goog:loggingPrefs.performance=ALL` and capture `Network.responseReceived` events to find a JSON endpoint (likely `/api/busca` or the LexML SRU endpoint).
4. Cross-check by opening DevTools in a real browser; confirm the exact query-parameter name.

Two valid strategies — pick one after probing:
- **Preferred:** hit the JSON API with `requests` if one exists. Deterministic, no Selenium for the search step, much faster.
- **Fallback:** Selenium + shadow-DOM recursion. For each result element, read `href`/`data-urn`, then apply `re.search(r"urn=(urn:lex:[^&\"'\s]+)", href)` (adapted from `legal_document_fetcher.py:634`).

The probe result goes into a short docstring comment block at the top of `_SearchPageClient` so the reasoning is recorded.

## CLI

Standalone script, mirrors `legal_document_fetcher.py:880-931`:
```
python law_urn_resolver.py lista_de_leis.txt \
    --output-csv ./out/resolved_urns.csv \
    --delay 2.0 \
    --selenium-wait 20
```
Flags: `input_file` (positional), `--output-csv` (default `./out/resolved_urns.csv`), `--delay` (2.0), `--selenium-wait` (20), `--headless/--no-headless` (default headless), `--log-level` (INFO).

## CSV output

Header: `input,urn_url,matched_type,matched_date,status,error_message`. One row per input line, in input order. Status values: `found`, `not_found`, `ambiguous`, `unsupported_type`, `parse_error`, `error`.

## Tests (`test_law_urn_resolver.py`)

Unit (no marker, run by default — pure Python, zero Selenium):
- `test_parse_lei_simple` — `"Lei 12527/2011"` → `(lei, "12527", year=2011)`.
- `test_parse_with_dots` — `"Lei 12.527/2011"` → number `"12527"`.
- `test_parse_lei_complementar_precedence` — `"Lei Complementar 123/2006"` classified as `lei_complementar`, not `lei`.
- `test_parse_decreto_lei_variants` — `"Decreto-lei 4657/1942"`, `"Decreto-Lei 4657/1942"`, `"Decreto lei 4657/1942"` all → `decreto_lei`.
- `test_parse_decreto_not_decreto_lei` — `"Decreto 7724/2012"` must NOT match the `decreto_lei` regex.
- `test_parse_constituicao` — `"Constituição"` and `"constituicao"` both canonicalize to `constituicao`.
- `test_parse_unsupported` — `"Res. Anatel 612/2015"`, `"Portaria MJSP 502/2021"`, `"Res. ANPD 2/2022"`, `"Emenda Constitucional 45/2004"` → `supported=False`.
- `test_match_year_only` — entry year=2011, candidate date=2011-11-18 → matches.
- `test_match_full_date_mismatch` — entry full_date=2011-01-01, candidate=2011-11-18 → no match.
- `test_match_number_leading_zeros` — `"00012527"` vs `"12527"` → match.
- `test_match_ambiguous` — two matching candidates → `ambiguous`, both URNs joined with `;`.
- `test_urn_type_mapping` — URN segment `lei.complementar` → `lei_complementar`.
- `test_csv_header_and_row_ordering` — feed mocked resolver results, check CSV.

Integration (`@pytest.mark.integration`, requires Chrome + network):
- `test_resolve_lei_12527_2011` — end-to-end: `"Lei 12527/2011"` → URN contains `lei:2011-11-18;12527`, status `found`.
- `test_resolve_constituicao` — `"Constituição"` → URN contains `constituicao:1988-10-05;1988`.
- `test_resolve_unsupported_skipped` — `"Res. Anatel 612/2015"` → status `unsupported_type`; assert `_SearchPageClient.search` was never called (monkeypatch/spy).

## Verification (end-to-end)

1. `pytest test_law_urn_resolver.py -m "not integration"` — all unit tests pass.
2. `pytest test_law_urn_resolver.py -m integration` — live tests pass (Chrome + network).
3. Manual: `python law_urn_resolver.py lista_de_leis.txt --output-csv ./out/resolved_urns.csv`; inspect CSV. Spot-check:
   - `Lei 12527/2011` → `urn:lex:br:federal:lei:2011-11-18;12527`, `found`.
   - `Constituição` → `urn:lex:br:federal:constituicao:1988-10-05;1988`, `found`.
   - `Res. Anatel 612/2015` → `unsupported_type`.
4. Pipeline check: feed the URN column into `legal_document_fetcher.py` and confirm one `.docx` is produced.

## Risks / open questions

- **Busca-page DOM & query param are unverified.** Must be resolved by the probe step before writing `_SearchPageClient`. If probing reveals a stable JSON API, strongly prefer it.
- **Pagination.** Exact matches normally appear on page 1; if the probe shows otherwise, add a page loop capped at 3 pages.
- **Rate limiting.** If the site throttles, log and raise the delay; no aggressive retries.
- **Search timeouts.** Catch `TimeoutException` from `WebDriverWait`, record `status=error`, continue the batch.
- **Emenda Constitucional** is outside the supported set and must flag `unsupported_type` — explicit negative test covers this.
