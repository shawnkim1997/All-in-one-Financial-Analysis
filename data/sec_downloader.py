"""
SEC 10-K download + section extraction: download via sec-edgar-downloader, extract items, cache.
"""
import tempfile
from pathlib import Path

from config.constants import (
    ITEM1A_PATTERNS, ITEM3_PATTERNS, ITEM7_PATTERNS, ITEM8_PATTERNS, ITEM9A_PATTERNS,
)
from data.sec_parser import (
    find_item_section_generic, _find_section_start,
    _extract_item_from_full, clean_text_for_llm, smart_chunk,
)
from data.sec_fetcher import (
    get_edgar_downloader, find_downloaded_10k_path, find_all_10k_filing_dirs,
    get_main_10k_text, _load_10k_html_from_cache, _get_main_10k_html_file,
    _save_10k_html_to_cache, _load_10k_from_cache, _save_10k_to_cache,
)


def download_and_extract_all_items(ticker: str, email: str) -> dict:
    """Download latest 10-K, extract Item 1A, 3, 7, 9A; clean and return (and optionally cache).
    Also saves the raw HTML file to data/TICKER_latest_raw.html for the native viewer."""
    Downloader = get_edgar_downloader()
    with tempfile.TemporaryDirectory() as tmpdir:
        download_root = Path(tmpdir)
        dl = Downloader("FQDC-10K-Analyzer", email, str(download_root))
        dl.get("10-K", ticker.upper(), limit=1, download_details=True)
        filing_dir = find_downloaded_10k_path(download_root, ticker)
        if not filing_dir:
            raise FileNotFoundError(f"Could not find 10-K for ticker '{ticker}'.")
        full_text = get_main_10k_text(filing_dir)
        if not full_text:
            raise ValueError("Could not extract text from the 10-K.")
        # Save raw HTML to persistent cache while temp dir is still open
        if not _load_10k_html_from_cache(ticker):
            main_html_path = _get_main_10k_html_file(filing_dir)
            if main_html_path:
                try:
                    with open(main_html_path, "r", encoding="utf-8", errors="replace") as _f:
                        _save_10k_html_to_cache(ticker, _f.read())
                except Exception:
                    pass
    item1a = find_item_section_generic(full_text, ITEM1A_PATTERNS, 1, ["Risk", "Factors"], max_chars=80000)
    item3 = _extract_item_from_full(full_text, ITEM3_PATTERNS, 3, ["Legal", "Proceedings"], max_chars=40000)
    item9a = _extract_item_from_full(full_text, ITEM9A_PATTERNS, 9, ["Controls", "Procedures", "Internal"], max_chars=40000)
    start7 = _find_section_start(full_text, ITEM7_PATTERNS, 7)
    text_after_7 = full_text[start7:] if start7 >= 0 else full_text
    item7 = find_item_section_generic(text_after_7, ITEM7_PATTERNS, 7, ["Management's Discussion", "MD&A", "Analysis"], max_chars=100000)
    if not item7 and text_after_7:
        item7 = text_after_7[:120000]
    item8 = _extract_item_from_full(full_text, ITEM8_PATTERNS, 8, ["Financial Statements", "Supplementary Data"], max_chars=200000)
    data = {
        "item1a": clean_text_for_llm(item1a or ""),
        "item3": clean_text_for_llm(item3 or ""),
        "item9a": clean_text_for_llm(item9a or ""),
        "item7": clean_text_for_llm(item7 or ""),
        "item8": clean_text_for_llm(item8 or ""),
    }
    _save_10k_to_cache(ticker, data)
    return data


def get_10k_sections(ticker: str, email: str) -> tuple:
    """Return (sections dict, status). status = 'cache' if loaded from file else 'downloaded'."""
    cached = _load_10k_from_cache(ticker)
    if cached is not None:
        return cached, "cache"
    return download_and_extract_all_items(ticker, email), "downloaded"


def download_and_extract_item7_and_1a(ticker: str, email: str) -> tuple:
    """Fetch 10-K and return full_text, Item 1A (Risk Factors), Item 7 (MD&A). Uses cache when available."""
    sections, _ = get_10k_sections(ticker, email)
    return "", sections.get("item1a", "") or "", sections.get("item7", "") or ""


def download_item7_latest_and_3y_ago(ticker: str, email: str) -> tuple:
    """Download up to 5 10-Ks; extract Item 1A (latest only) and Item 7 from latest and from 3 years ago."""
    Downloader = get_edgar_downloader()
    with tempfile.TemporaryDirectory() as tmpdir:
        download_root = Path(tmpdir)
        dl = Downloader("FQDC-10K-Analyzer", email, str(download_root))
        dl.get("10-K", ticker.upper(), limit=5, download_details=True)
        filing_dirs = find_all_10k_filing_dirs(download_root, ticker)
        if not filing_dirs:
            raise FileNotFoundError(f"Could not find 10-K for ticker '{ticker}'.")
        full_latest = get_main_10k_text(filing_dirs[0])
        if not full_latest:
            raise ValueError("Could not extract text from the latest 10-K.")
        item1a = find_item_section_generic(
            full_latest, ITEM1A_PATTERNS, 1, ["Risk", "Factors"], max_chars=80000
        )
        text_after_7 = full_latest[_find_section_start(full_latest, ITEM7_PATTERNS, 7):] if _find_section_start(full_latest, ITEM7_PATTERNS, 7) >= 0 else full_latest
        item7_latest = find_item_section_generic(
            text_after_7, ITEM7_PATTERNS, 7, ["Management's Discussion", "MD&A", "Analysis"], max_chars=100000
        )
        if not item7_latest and text_after_7:
            item7_latest = smart_chunk(text_after_7[:120000], max_chars=20000)
        item7_3y_ago = None
        has_comparison = False
        if len(filing_dirs) >= 4:
            full_3y = get_main_10k_text(filing_dirs[3])
            if full_3y:
                text_3y = full_3y[_find_section_start(full_3y, ITEM7_PATTERNS, 7):] if _find_section_start(full_3y, ITEM7_PATTERNS, 7) >= 0 else full_3y
                item7_3y_ago = find_item_section_generic(
                    text_3y, ITEM7_PATTERNS, 7, ["Management's Discussion", "MD&A", "Analysis"], max_chars=100000
                )
                if not item7_3y_ago and text_3y:
                    item7_3y_ago = smart_chunk(text_3y[:120000], max_chars=20000)
                has_comparison = bool(item7_3y_ago)
    return item1a or "", item7_latest or "", item7_3y_ago, has_comparison
