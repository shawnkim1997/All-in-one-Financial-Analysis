"""
SEC EDGAR download, fetch, cache: 10-K download via sec-edgar-downloader, EDGAR API HTML fetch, disk cache.
"""
import json
import re
import tempfile
import requests
from pathlib import Path
from typing import Optional

from utils.prefs import _DATA_DIR
from config.constants import (
    ITEM1A_PATTERNS, ITEM3_PATTERNS, ITEM7_PATTERNS, ITEM8_PATTERNS, ITEM9A_PATTERNS,
)
from data.sec_parser import (
    extract_text_from_file, find_item_section_generic, _find_section_start,
    _extract_item_from_full, clean_text_for_llm,
)


def get_edgar_downloader():
    from sec_edgar_downloader import Downloader
    return Downloader


def find_downloaded_10k_path(download_root: Path, ticker: str) -> Optional[Path]:
    ticker_upper = ticker.upper()
    for base in (download_root / "sec-edgar-filings", download_root):
        path_10k = base / ticker_upper / "10-K"
        if path_10k.exists():
            subdirs = sorted([d for d in path_10k.iterdir() if d.is_dir()], key=lambda x: x.name, reverse=True)
            if subdirs:
                return subdirs[0]
    for base in (download_root / "sec-edgar-filings", download_root):
        if not base.exists():
            continue
        for company_dir in base.iterdir():
            if not company_dir.is_dir():
                continue
            path_10k = company_dir / "10-K"
            if path_10k.exists():
                subdirs = sorted([d for d in path_10k.iterdir() if d.is_dir()], key=lambda x: x.name, reverse=True)
                if subdirs:
                    return subdirs[0]
    return None


def find_all_10k_filing_dirs(download_root: Path, ticker: str) -> list:
    """Return list of 10-K filing dirs sorted newest first (for multi-year comparison)."""
    ticker_upper = ticker.upper()
    for base in (download_root / "sec-edgar-filings", download_root):
        path_10k = base / ticker_upper / "10-K"
        if path_10k.exists():
            subdirs = sorted([d for d in path_10k.iterdir() if d.is_dir()], key=lambda x: x.name, reverse=True)
            return subdirs
    return []


def get_main_10k_text(filing_dir: Path) -> str:
    all_text = []
    for ext in ("*.htm", "*.html", "*.txt"):
        for path in filing_dir.rglob(ext):
            try:
                t = extract_text_from_file(path)
                if len(t) > 1000:
                    all_text.append((path, t))
            except Exception:
                continue
    if not all_text:
        return ""
    _, main_text = max(all_text, key=lambda x: len(x[1]))
    return main_text


def _get_10k_cache_path(ticker: str) -> Path:
    """Path for cached 10-K sections: data/TICKER_latest.json."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR / f"{ticker.upper()}_latest.json"


def _get_10k_html_cache_path(ticker: str) -> Path:
    """Path for cached raw 10-K HTML: data/TICKER_latest_raw.html."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR / f"{ticker.upper()}_latest_raw.html"


def _load_10k_html_from_cache(ticker: str) -> Optional[str]:
    """Load raw 10-K HTML from data/TICKER_latest_raw.html. Returns None if missing."""
    path = _get_10k_html_cache_path(ticker)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return None


def _save_10k_html_to_cache(ticker: str, html: str) -> None:
    """Save raw 10-K HTML to data/TICKER_latest_raw.html."""
    path = _get_10k_html_cache_path(ticker)
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", errors="replace") as f:
        f.write(html)


def fetch_sec_filing_html(ticker: str, filing_type: str = "10-K") -> dict:
    """Fetch raw SEC filing HTML from EDGAR public API.

    Returns dict with keys:
      - html: str | None  (the raw HTML content)
      - error: str | None (human-readable error for st.error())
      - doc_url: str | None (final document URL for reference)
      - source: 'cache' | 'edgar_api' | None
    """
    # Check disk cache (only for 10-K for backward compat)
    if filing_type == "10-K":
        cached = _load_10k_html_from_cache(ticker)
        if cached:
            return {"html": cached, "error": None, "doc_url": None, "source": "cache"}

    # SEC requires: "Company Name (contact@email.com)" format
    headers = {
        "User-Agent": "FQDC-Terminal (atlas-terminal@fqdc.io)",
        "Accept-Encoding": "gzip, deflate",
    }

    # Step 1: ticker -> CIK
    url_tickers = "https://www.sec.gov/files/company_tickers.json"
    r = requests.get(url_tickers, headers={**headers, "Accept": "application/json"}, timeout=15)
    if not r.ok:
        return {"html": None, "error": f"SEC tickers lookup failed: HTTP {r.status_code}", "doc_url": url_tickers, "source": None}
    cik = None
    for entry in r.json().values():
        if entry.get("ticker", "").upper() == ticker.upper():
            cik = str(entry["cik_str"]).zfill(10)
            break
    if not cik:
        return {"html": None, "error": f"Ticker '{ticker}' not found in SEC company_tickers.json", "doc_url": None, "source": None}

    # Step 2: find latest filing of requested type + primaryDocument
    url_submissions = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = requests.get(url_submissions, headers={**headers, "Accept": "application/json"}, timeout=15)
    if not r.ok:
        return {"html": None, "error": f"SEC submissions API failed: HTTP {r.status_code} for CIK {cik}", "doc_url": url_submissions, "source": None}
    filings = r.json().get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accessions = filings.get("accessionNumber", [])
    primary_docs = filings.get("primaryDocument", [])
    filing_dates = filings.get("filingDate", [])

    accession = None
    main_doc = None
    filing_date = None
    for form, acc, pdoc, fdate in zip(forms, accessions, primary_docs, filing_dates):
        if form == filing_type:
            accession = acc.replace("-", "")
            main_doc = pdoc
            filing_date = fdate
            break
    if not accession or not main_doc:
        return {"html": None, "error": f"No '{filing_type}' filing found for {ticker} (CIK {cik})", "doc_url": None, "source": None}

    # Step 3: download the primary .htm document
    doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{main_doc}"
    r = requests.get(doc_url, headers={**headers, "Accept": "text/html,application/xhtml+xml"}, timeout=90)
    if not r.ok:
        return {"html": None, "error": f"SEC document download failed: HTTP {r.status_code} for {doc_url}", "doc_url": doc_url, "source": None}

    html_content = r.text
    if not html_content or len(html_content) < 500:
        return {"html": None, "error": f"SEC returned empty/tiny document ({len(html_content)} bytes) from {doc_url}", "doc_url": doc_url, "source": None}

    # Cache to disk (10-K only)
    if filing_type == "10-K":
        _save_10k_html_to_cache(ticker, html_content)

    return {"html": html_content, "error": None, "doc_url": doc_url, "source": "edgar_api", "filing_date": filing_date}


def _wrap_edgar_html_for_iframe(raw_html: str, ticker: str) -> str:
    """Inject a minimal CSS reset so EDGAR HTML renders cleanly inside components.html()."""
    inject_css = """
<style>
  /* Soft readability reset for EDGAR documents */
  body {
    font-family: 'Times New Roman', Times, serif;
    font-size: 14px;
    line-height: 1.6;
    color: #1a1a1a;
    background: #ffffff;
    margin: 16px 24px;
    max-width: 1100px;
  }
  table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 13px; }
  td, th { border: 1px solid #ccc; padding: 4px 8px; vertical-align: top; }
  th { background: #f0f0f0; font-weight: bold; }
  p { margin: 6px 0; }
  h1, h2, h3, h4 { color: #111; margin: 12px 0 6px; }
  a { color: #1155cc; }
  hr { border: none; border-top: 1px solid #ddd; margin: 12px 0; }
</style>
"""
    # If the HTML has a <head>, inject after it. Otherwise prepend.
    if "<head>" in raw_html.lower():
        raw_html = raw_html.replace("<head>", f"<head>{inject_css}", 1)
    elif "<html" in raw_html.lower():
        raw_html = raw_html.replace("<html", f"<html", 1)
        raw_html = inject_css + raw_html
    else:
        raw_html = f"<html><head>{inject_css}</head><body>{raw_html}</body></html>"
    return raw_html


def _load_10k_from_cache(ticker: str) -> Optional[dict]:
    """Load Item 1A, 3, 7, 8, 9A (plain text) from data/ticker_latest.json. Returns None if missing."""
    path = _get_10k_cache_path(ticker)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_10k_to_cache(ticker: str, data: dict) -> None:
    """Save cleaned 10-K sections to data/ticker_latest.json."""
    path = _get_10k_cache_path(ticker)
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)


def _get_main_10k_html_file(filing_dir: Path) -> Optional[Path]:
    """Return the Path of the largest .htm/.html file in the filing dir (the main document)."""
    candidates = []
    for ext in ("*.htm", "*.html"):
        for p in filing_dir.rglob(ext):
            try:
                candidates.append((p.stat().st_size, p))
            except Exception:
                pass
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


# Download & extraction functions moved to data/sec_downloader.py:
# download_and_extract_all_items, get_10k_sections,
# download_and_extract_item7_and_1a, download_item7_latest_and_3y_ago
