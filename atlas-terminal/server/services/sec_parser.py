"""SEC EDGAR annual filing download, parsing, section extraction, and caching.

Handles the full pipeline from downloading an annual filing (10-K / 20-F / 40-F) via
``sec_edgar_downloader`` through HTML stripping to isolating individual
Item sections (risk, legal/other, MD&A/OFR, financials, controls) and persisting the cleaned text to a
local JSON cache under ``data/``.
"""

import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from bs4 import BeautifulSoup
from bs4.element import Comment, Tag

from server.services.text_chunker import clean_text_for_llm, smart_chunk

logger = logging.getLogger(__name__)

ANNUAL_SEC_FORMS: List[str] = ["10-K", "20-F", "40-F"]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR: Path = Path(__file__).resolve().parents[3] / "data"

# ---------------------------------------------------------------------------
# SEC EDGAR Filing URL Resolver
# ---------------------------------------------------------------------------

_CIK_CACHE: Dict[str, int] = {}
_SEC_HEADERS = {"User-Agent": "ATLAS-Terminal admin@atlas.local"}


def _resolve_cik(ticker: str) -> Optional[int]:
    """Resolve ticker → CIK via SEC's company_tickers.json."""
    t = ticker.upper().strip()
    if t in _CIK_CACHE:
        return _CIK_CACHE[t]
    try:
        resp = httpx.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=_SEC_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        for entry in data.values():
            tk = entry.get("ticker", "")
            cik = entry.get("cik_str")
            if tk:
                _CIK_CACHE[tk.upper()] = int(cik)
        return _CIK_CACHE.get(t)
    except Exception:
        logger.warning("Failed to resolve CIK for %s", t)
        return None


def get_sec_filing_url(ticker: str, preferred_forms: Optional[List[str]] = None) -> Optional[str]:
    """Return the URL of the latest annual filing document on SEC EDGAR."""
    cik = _resolve_cik(ticker)
    if cik is None:
        return None
    cik_padded = str(cik).zfill(10)
    forms_to_match = preferred_forms or ANNUAL_SEC_FORMS
    try:
        resp = httpx.get(
            f"https://data.sec.gov/submissions/CIK{cik_padded}.json",
            headers=_SEC_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        docs = recent.get("primaryDocument", [])
        for i, form in enumerate(forms):
            if form in forms_to_match or form.replace("/A", "") in forms_to_match:
                acc_no_dash = accessions[i].replace("-", "")
                return (
                    f"https://www.sec.gov/Archives/edgar/data"
                    f"/{cik_padded}/{acc_no_dash}/{docs[i]}"
                )
    except Exception:
        logger.warning("Failed to get filing URL for %s", ticker)
    return None

# ---------------------------------------------------------------------------
# Section-header regex patterns
# ---------------------------------------------------------------------------

ITEM1A_PATTERNS: List[str] = [
    r"Item\s+1A\s*[.:]\s*Risk\s+Factors",
    r"ITEM\s+1A\s*[.:]\s*Risk\s+Factors",
]

ITEM7_PATTERNS: List[str] = [
    r"Item\s+7\s*[.:]\s*Management['\u2019]s\s+Discussion\s+and\s+Analysis",
    r"ITEM\s+7\s*[.:]\s*Management['\u2019]s\s+Discussion",
    r"Item\s+7\s*[.:]\s*[\w\s]+MD&A",
]

ITEM8_PATTERNS: List[str] = [
    r"Item\s+8\s*[.:]\s*Financial\s+Statements",
    r"ITEM\s+8\s*[.:]\s*Financial\s+Statements",
]

ITEM3_PATTERNS: List[str] = [
    r"Item\s+3\s*[.:]\s*Legal\s+Proceedings",
    r"ITEM\s+3\s*[.:]\s*Legal\s+Proceedings",
]

ITEM9A_PATTERNS: List[str] = [
    r"Item\s+9A\s*[.:]\s*Controls\s+and\s+Procedures",
    r"Item\s+9A\s*[.:]\s*Internal\s+Control",
    r"ITEM\s+9A\s*[.:]\s*Controls",
]

ITEM20F_RISK_PATTERNS: List[str] = [
    r"Item\s+3\.?\s*D\s*[.:]\s*Risk\s+Factors",
    r"ITEM\s+3\.?\s*D\s*[.:]\s*Risk\s+Factors",
    r"Item\s+3\s*[.:][^\n]*Risk\s+Factors",
]

ITEM20F_MDA_PATTERNS: List[str] = [
    r"Item\s+5\s*[.:]\s*Operating\s+and\s+Financial\s+Review\s+and\s+Prospects",
    r"ITEM\s+5\s*[.:]\s*Operating\s+and\s+Financial\s+Review",
]

ITEM20F_FIN_PATTERNS: List[str] = [
    r"Item\s+18\s*[.:]\s*Financial\s+Statements",
    r"ITEM\s+18\s*[.:]\s*Financial\s+Statements",
    r"Item\s+17\s*[.:]\s*Financial\s+Statements",
    r"Item\s+8\s*[.:]\s*Financial\s+Information",
]

ITEM20F_CONTROLS_PATTERNS: List[str] = [
    r"Item\s+15\s*[.:]\s*Controls\s+and\s+Procedures",
    r"ITEM\s+15\s*[.:]\s*Controls\s+and\s+Procedures",
    r"Item\s+15\s*[.:]\s*Disclosure\s+Controls",
]

ITEM20F_LEGAL_PATTERNS: List[str] = [
    r"Legal\s+Proceedings",
    r"Litigation",
    r"Arbitration",
]


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _slice_html_items_1a_to_9a(raw_html: str) -> str:
    """Fast string-level slice: keep only Item 1A through end of Item 9A."""
    if not raw_html or len(raw_html) < 5000:
        return raw_html
    start = -1
    for needle in ("Item 1A", "ITEM 1A", "Item 1a"):
        i = raw_html.find(needle)
        if i != -1 and (start == -1 or i < start):
            start = i
    if start == -1:
        m = re.search(r"Item\s+1A\s", raw_html, re.IGNORECASE)
        start = m.start() if m else 0
    else:
        start = max(0, start - 200)
    search_region = raw_html[start:]
    end_match = re.search(
        r"Item\s+10\s|Item\s+12\s|Part\s+III\b|PART\s+III\b",
        search_region,
        re.IGNORECASE,
    )
    end = start + end_match.start() if end_match else len(raw_html)
    end = min(end, start + 8_000_000)
    return raw_html[start:end]


def _extract_text_from_html_string(html_str: str) -> str:
    """Parse an HTML string and return plain text (tables/scripts removed)."""
    if not html_str or not html_str.strip():
        return ""
    try:
        soup = BeautifulSoup(html_str, "lxml")
    except Exception:
        soup = BeautifulSoup(html_str, "html.parser")
    for tag in soup.find_all(["table", "img", "svg", "style", "script"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def extract_text_from_html(html_path: Path) -> str:
    """Read an HTML file, slice to Items 1A-9A, and return plain text."""
    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except Exception:
        with open(html_path, "r", encoding="latin-1", errors="replace") as f:
            raw = f.read()
    chunk = _slice_html_items_1a_to_9a(raw)
    return _extract_text_from_html_string(chunk)


def extract_text_from_file(file_path: Path) -> str:
    """Extract plain text from an HTML or TXT file."""
    suf = file_path.suffix.lower()
    if suf in (".htm", ".html"):
        return extract_text_from_html(file_path)
    if suf == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text
    return ""


# ---------------------------------------------------------------------------
# Section finders
# ---------------------------------------------------------------------------

def _find_section_start(text: str, patterns: List[str], item_num: int) -> int:
    """Return character offset where *item_num* section begins, or -1."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.start()
    m = re.search(r"\bItem\s+" + str(item_num) + r"\b", text, re.IGNORECASE)
    return m.start() if m else -1


def find_item_section_generic(
    text: str,
    patterns: List[str],
    item_num: int,
    title_keywords: List[str],
    max_chars: int = 120_000,
) -> str:
    """Extract a single Item section from full 10-K text."""
    start = _find_section_start(text, patterns, item_num)
    if start == -1:
        pattern = re.compile(
            r"\bItem\s+" + str(item_num)
            + r"\b[.\s]*[^\n]*("
            + "|".join(re.escape(k) for k in title_keywords)
            + r")?",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if not match:
            return ""
        start = match.start()
    next_item = re.search(r"\n\s*Item\s+\d+[A-Z]?\s+", text[start + 100:], re.IGNORECASE)
    end = start + 100 + next_item.start() if next_item else min(start + max_chars, len(text))
    return text[start:end].strip()


def _extract_item_from_full(
    text: str,
    patterns: List[str],
    item_num: int,
    keywords: List[str],
    max_chars: int = 60_000,
) -> str:
    """Extract one item section from full 10-K text."""
    start = _find_section_start(text, patterns, item_num)
    if start < 0:
        pat = re.compile(
            r"\bItem\s+" + str(item_num) + r"[A-Z]?\b[.\s]*[^\n]*",
            re.IGNORECASE,
        )
        match = pat.search(text)
        start = match.start() if match else -1
    if start < 0:
        return ""
    next_item = re.search(r"\n\s*Item\s+\d+[A-Z]?\s+", text[start + 100:], re.IGNORECASE)
    end = start + 100 + next_item.start() if next_item else min(start + max_chars, len(text))
    return text[start:end].strip()


# ---------------------------------------------------------------------------
# Filing directory helpers
# ---------------------------------------------------------------------------

def _get_edgar_downloader() -> type:
    """Lazy import of ``sec_edgar_downloader.Downloader``."""
    from sec_edgar_downloader import Downloader
    return Downloader


def find_downloaded_filing_path(download_root: Path, ticker: str, form_type: str) -> Optional[Path]:
    """Locate the most recent filing directory for *form_type* on disk."""
    ticker_upper = ticker.upper()
    for base in (download_root / "sec-edgar-filings", download_root):
        filing_path = base / ticker_upper / form_type
        if filing_path.exists():
            subdirs = sorted(
                [d for d in filing_path.iterdir() if d.is_dir()],
                key=lambda x: x.name,
                reverse=True,
            )
            if subdirs:
                return subdirs[0]
    for base in (download_root / "sec-edgar-filings", download_root):
        if not base.exists():
            continue
        for company_dir in base.iterdir():
            if not company_dir.is_dir():
                continue
            filing_path = company_dir / form_type
            if filing_path.exists():
                subdirs = sorted(
                    [d for d in filing_path.iterdir() if d.is_dir()],
                    key=lambda x: x.name,
                    reverse=True,
                )
                if subdirs:
                    return subdirs[0]
    return None


def find_downloaded_10k_path(download_root: Path, ticker: str) -> Optional[Path]:
    """Backwards-compatible alias for 10-K directory lookup."""
    return find_downloaded_filing_path(download_root, ticker, "10-K")


def find_all_filing_dirs(download_root: Path, ticker: str, form_type: str) -> List[Path]:
    """Return all filing directories for *form_type* sorted newest-first."""
    ticker_upper = ticker.upper()
    for base in (download_root / "sec-edgar-filings", download_root):
        filing_path = base / ticker_upper / form_type
        if filing_path.exists():
            return sorted(
                [d for d in filing_path.iterdir() if d.is_dir()],
                key=lambda x: x.name,
                reverse=True,
            )
    return []


def find_all_10k_filing_dirs(download_root: Path, ticker: str) -> List[Path]:
    """Backwards-compatible alias for 10-K directory lookup."""
    return find_all_filing_dirs(download_root, ticker, "10-K")


def get_main_10k_text(filing_dir: Path) -> str:
    """Return the longest extracted text from all files in *filing_dir*."""
    all_text: List[tuple] = []
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


def get_main_10k_html_path(filing_dir: Path) -> Optional[Path]:
    """Pick the largest ``.htm`` / ``.html`` file (primary 10-K document)."""
    best: Optional[Path] = None
    best_size = 0
    for path in filing_dir.rglob("*.htm*"):
        try:
            sz = path.stat().st_size
            if sz > best_size:
                best_size = sz
                best = path
        except OSError:
            continue
    return best


def read_main_10k_html_raw(filing_dir: Path) -> str:
    """Read raw HTML from the main filing document."""
    path = get_main_10k_html_path(filing_dir)
    if not path:
        return ""
    for enc in ("utf-8", "latin-1"):
        try:
            return path.read_text(encoding=enc, errors="replace")
        except Exception:
            continue
    return ""


def _strip_scripts_keep_html(html: str) -> str:
    """Remove ``<script>`` tags; keep layout/styles for readability."""
    if not html or not html.strip():
        return ""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("script"):
        tag.decompose()
    return str(soup)


# Regex bundles for DOM anchor injection (first match in document order wins).
_SEC_ITEM_INJECT_SPECS: List[tuple[str, List[re.Pattern]]] = [
    (
        "sec-item-1a",
        [re.compile(p, re.I) for p in ITEM1A_PATTERNS + ITEM20F_RISK_PATTERNS]
        + [re.compile(r"Item\s+1A\s*[.:]", re.I), re.compile(r"Item\s+3\.?\s*D\s*[.:]", re.I)],
    ),
    (
        "sec-item-3",
        [re.compile(p, re.I) for p in ITEM3_PATTERNS + ITEM20F_LEGAL_PATTERNS]
        + [re.compile(r"Legal\s+Proceedings", re.I)],
    ),
    (
        "sec-item-7",
        [re.compile(p, re.I) for p in ITEM7_PATTERNS + ITEM20F_MDA_PATTERNS]
        + [re.compile(r"Item\s+7\s*[.:]", re.I), re.compile(r"Item\s+5\s*[.:]", re.I)],
    ),
    (
        "sec-item-8",
        [re.compile(p, re.I) for p in ITEM8_PATTERNS + ITEM20F_FIN_PATTERNS]
        + [re.compile(r"Item\s+8\s*[.:]", re.I), re.compile(r"Item\s+18\s*[.:]", re.I)],
    ),
    (
        "sec-item-9a",
        [re.compile(p, re.I) for p in ITEM9A_PATTERNS + ITEM20F_CONTROLS_PATTERNS]
        + [re.compile(r"Item\s+9A\s*[.:]", re.I), re.compile(r"Item\s+15\s*[.:]", re.I)],
    ),
]


def _sanitize_sec_html_soup(soup: BeautifulSoup) -> None:
    """Remove scripts and dangerous attributes; keep tables and inline formatting."""
    for tag in soup.find_all(["script", "style", "noscript", "iframe", "object", "embed", "link"]):
        tag.decompose()
    for tag in soup.find_all(True):
        if not isinstance(tag, Tag) or not tag.attrs:
            continue
        for attr in list(tag.attrs.keys()):
            al = attr.lower()
            if al.startswith("on"):
                del tag[attr]
                continue
            if al == "href" and isinstance(tag.get("href"), str) and tag["href"].lower().strip().startswith(
                "javascript:",
            ):
                del tag[attr]


def _best_anchor_parent_for_text_node(text_node) -> Optional[Tag]:
    """Pick a block-level (or heading) ancestor to host ``id`` for an Item header."""
    p = getattr(text_node, "parent", None)
    depth = 0
    fallback: Optional[Tag] = None
    while p is not None and depth < 18:
        if not isinstance(p, Tag):
            break
        name = (p.name or "").lower()
        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            return p
        if name in ("p", "div", "td", "th", "li", "table", "tr"):
            fallback = p
        elif name in ("font",) and fallback is None:
            fallback = p
        elif name in ("b", "strong", "span", "a", "i", "u", "em") and fallback is None:
            fallback = p
        if name in ("body", "html", "[document]"):
            break
        p = p.parent
        depth += 1
    return fallback


def inject_sec_item_anchor_ids(soup: BeautifulSoup) -> None:
    """Set ``id=\"sec-item-*\"`` on heading-like nodes for Item 1A, 3, 7, 8, 9A.

    Strategy: collect *all* candidate matches per Item, then prefer a match
    that lives outside the first table-of-contents table — specifically one
    whose host element is an ``<h*>``, ``<p>``, or ``<div>`` (not a ``<td>``
    in the TOC).  Falls back to the last candidate if no heading match exists.
    """
    # Collect all candidates per el_id: list of (text_node, host_tag)
    candidates: dict[str, list[tuple]] = {spec[0]: [] for spec in _SEC_ITEM_INJECT_SPECS}
    for text in soup.find_all(string=True):
        if isinstance(text, Comment):
            continue
        text_val = str(text)
        if not text_val.strip():
            continue
        for el_id, regexes in _SEC_ITEM_INJECT_SPECS:
            if not any(rx.search(text_val) for rx in regexes):
                continue
            host = _best_anchor_parent_for_text_node(text)
            if host is not None:
                candidates[el_id].append((text, host))
            break  # only match first spec for this text node

    assigned: set[str] = set()
    for el_id, _ in _SEC_ITEM_INJECT_SPECS:
        cands = candidates.get(el_id, [])
        if not cands:
            continue
        # Prefer a heading-like host (h1-h6, p, div) that is NOT inside the TOC table
        best = None
        for _text, host in cands:
            host_name = (host.name or "").lower()
            if host_name in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "div"):
                best = host
                # Don't break — prefer later (actual section header) over earlier (TOC)
        if best is None and len(cands) > 1:
            # If no heading host, use the last match (skip the first/TOC one)
            best = cands[-1][1]
        elif best is None:
            best = cands[0][1]
        best["id"] = el_id
        assigned.add(el_id)


def prepare_native_html_fragment_from_10k_raw(raw_html: str) -> str:
    """Sanitize full 10-K HTML, inject ``sec-item-*`` anchors, return body HTML fragment.

    The entire document is preserved (table of contents, all Items, tables, etc.)
    so the user sees the original formatted filing inside the app.
    """
    if not raw_html or len(raw_html) < 100:
        return ""
    try:
        soup = BeautifulSoup(raw_html, "lxml")
    except Exception:
        soup = BeautifulSoup(raw_html, "html.parser")
    _sanitize_sec_html_soup(soup)
    inject_sec_item_anchor_ids(soup)
    if soup.body:
        return soup.body.decode_contents()
    return str(soup)


def inject_section_anchors(html: str) -> str:
    """Sanitize HTML and inject ``sec-item-*`` ids (DOM-preserving)."""
    if not html or not html.strip():
        return ""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    _sanitize_sec_html_soup(soup)
    inject_sec_item_anchor_ids(soup)
    if soup.body:
        return soup.body.decode_contents()
    return str(soup)


def normalize_cached_html_for_native_viewer(stored: str) -> str:
    """If cache holds a legacy full document, return body inner HTML only."""
    s = (stored or "").strip()
    if not s:
        return ""
    low = s[:32].lower()
    if "<!doctype" in low or (s.lower().startswith("<html") and "<body" in s.lower()):
        try:
            soup = BeautifulSoup(s, "lxml")
            if soup.body:
                return soup.body.decode_contents()
        except Exception:
            pass
    return s


def _html_slice_cache_path(ticker: str) -> Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR / f"{ticker.upper()}_10k_slice.html"


def load_10k_html_slice(ticker: str) -> Optional[str]:
    """Load cached HTML fragment for native viewer (legacy full-document cache supported)."""
    p = _html_slice_cache_path(ticker)
    if not p.exists():
        return None
    try:
        raw = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    norm = normalize_cached_html_for_native_viewer(raw)
    return norm if norm else None


def save_10k_html_slice(ticker: str, html: str) -> None:
    """Persist wrapped HTML next to JSON section cache."""
    p = _html_slice_cache_path(ticker)
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)


# ---------------------------------------------------------------------------
# Cache layer
# ---------------------------------------------------------------------------

def _get_10k_cache_path(ticker: str) -> Path:
    """Path for cached 10-K sections: ``data/TICKER_latest.json``."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR / f"{ticker.upper()}_latest.json"


def _get_filing_meta_cache_path(ticker: str) -> Path:
    """Path for cached filing metadata alongside the section cache."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR / f"{ticker.upper()}_latest_meta.json"


def _load_10k_from_cache(ticker: str) -> Optional[Dict[str, str]]:
    """Load cached sections or return ``None`` if absent."""
    path = _get_10k_cache_path(ticker)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_10k_to_cache(ticker: str, data: Dict[str, str]) -> None:
    """Persist cleaned 10-K sections to the JSON cache."""
    path = _get_10k_cache_path(ticker)
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)


def _load_filing_meta_from_cache(ticker: str) -> Dict[str, str]:
    """Load cached filing metadata, defaulting legacy caches to 10-K."""
    path = _get_filing_meta_cache_path(ticker)
    if not path.exists():
        return {"filing_form": "10-K", "filing_label": "10-K Annual Report (SEC)"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            filing_form = str(raw.get("filing_form") or "10-K")
            filing_label = str(raw.get("filing_label") or f"{filing_form} Annual Report (SEC)")
            return {"filing_form": filing_form, "filing_label": filing_label}
    except Exception:
        pass
    return {"filing_form": "10-K", "filing_label": "10-K Annual Report (SEC)"}


def _save_filing_meta_to_cache(ticker: str, filing_form: str) -> None:
    """Persist latest filing metadata."""
    path = _get_filing_meta_cache_path(ticker)
    payload = {
        "filing_form": filing_form,
        "filing_label": f"{filing_form} Annual Report (SEC)",
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=0)


# ---------------------------------------------------------------------------
# High-level download + extract
# ---------------------------------------------------------------------------

def _extract_sections_for_form(full_text: str, filing_form: str) -> Dict[str, str]:
    """Extract normalised section buckets for a specific SEC annual form."""
    if filing_form == "20-F":
        item1a = find_item_section_generic(full_text, ITEM20F_RISK_PATTERNS, 3, ["Risk", "Factors"], max_chars=80_000)
        item3 = find_item_section_generic(full_text, ITEM20F_LEGAL_PATTERNS, 8, ["Legal", "Proceedings", "Arbitration"], max_chars=40_000)
        start7 = _find_section_start(full_text, ITEM20F_MDA_PATTERNS, 5)
        text_after_7 = full_text[start7:] if start7 >= 0 else full_text
        item7 = find_item_section_generic(
            text_after_7,
            ITEM20F_MDA_PATTERNS,
            5,
            ["Operating", "Financial", "Review", "Prospects"],
            max_chars=100_000,
        )
        if not item7 and text_after_7:
            item7 = text_after_7[:120_000]
        item8 = find_item_section_generic(
            full_text,
            ITEM20F_FIN_PATTERNS,
            18,
            ["Financial Statements", "Financial Information"],
            max_chars=200_000,
        )
        item9a = find_item_section_generic(
            full_text,
            ITEM20F_CONTROLS_PATTERNS,
            15,
            ["Controls", "Procedures", "Internal"],
            max_chars=50_000,
        )
    else:
        item1a = find_item_section_generic(full_text, ITEM1A_PATTERNS, 1, ["Risk", "Factors"], max_chars=80_000)
        item3 = _extract_item_from_full(full_text, ITEM3_PATTERNS, 3, ["Legal", "Proceedings"], max_chars=40_000)
        item9a = _extract_item_from_full(full_text, ITEM9A_PATTERNS, 9, ["Controls", "Procedures", "Internal"], max_chars=40_000)
        start7 = _find_section_start(full_text, ITEM7_PATTERNS, 7)
        text_after_7 = full_text[start7:] if start7 >= 0 else full_text
        item7 = find_item_section_generic(text_after_7, ITEM7_PATTERNS, 7, ["Management's Discussion", "MD&A", "Analysis"], max_chars=100_000)
        if not item7 and text_after_7:
            item7 = text_after_7[:120_000]
        item8 = _extract_item_from_full(full_text, ITEM8_PATTERNS, 8, ["Financial Statements", "Supplementary Data"], max_chars=200_000)

    return {
        "item1a": clean_text_for_llm(item1a or ""),
        "item3": clean_text_for_llm(item3 or ""),
        "item9a": clean_text_for_llm(item9a or ""),
        "item7": clean_text_for_llm(item7 or ""),
        "item8": clean_text_for_llm(item8 or ""),
    }


def _download_latest_annual_filing_dir(download_root: Path, ticker: str, email: str, limit: int = 1) -> tuple[str, Path]:
    """Download the latest available annual SEC filing directory for a ticker."""
    Downloader = _get_edgar_downloader()
    dl = Downloader("FQDC-10K-Analyzer", email, str(download_root))
    for filing_form in ANNUAL_SEC_FORMS:
        dl.get(filing_form, ticker.upper(), limit=limit, download_details=True)
        filing_dir = find_downloaded_filing_path(download_root, ticker, filing_form)
        if filing_dir:
            return filing_form, filing_dir
    raise FileNotFoundError(
        f"Could not find annual SEC filing (10-K / 20-F / 40-F) for ticker '{ticker}'."
    )


def download_and_extract_all_items_with_form(ticker: str, email: str) -> tuple[Dict[str, str], str]:
    """Download latest annual filing, extract sections, and return filing form."""
    Downloader = _get_edgar_downloader()
    raw_html: Optional[str] = None
    with tempfile.TemporaryDirectory() as tmpdir:
        download_root = Path(tmpdir)
        _ = Downloader
        filing_form, filing_dir = _download_latest_annual_filing_dir(download_root, ticker, email, limit=1)
        full_text = get_main_10k_text(filing_dir)
        if not full_text:
            raise ValueError(f"Could not extract text from the {filing_form}.")
        # Read raw HTML while tempdir still exists
        raw_html = read_main_10k_html_raw(filing_dir)

    data = _extract_sections_for_form(full_text, filing_form)
    _save_10k_to_cache(ticker, data)
    _save_filing_meta_to_cache(ticker, filing_form)

    if raw_html:
        fragment = prepare_native_html_fragment_from_10k_raw(raw_html)
        if fragment:
            save_10k_html_slice(ticker, fragment)
    return data, filing_form


def download_and_extract_all_items(ticker: str, email: str) -> Dict[str, str]:
    """Backwards-compatible wrapper returning only the section payload."""
    data, _ = download_and_extract_all_items_with_form(ticker, email)
    return data


def get_10k_sections(ticker: str, email: str) -> tuple[Dict[str, str], str]:
    """Return ``(sections, status)``; *status* is ``'cache'`` or ``'downloaded'``."""
    cached = _load_10k_from_cache(ticker)
    if cached is not None:
        return cached, "cache"
    return download_and_extract_all_items(ticker, email), "downloaded"


def get_annual_sections_with_form(ticker: str, email: str) -> tuple[Dict[str, str], str, str]:
    """Return sections, cache status, and detected annual SEC filing form."""
    cached = _load_10k_from_cache(ticker)
    if cached is not None:
        meta = _load_filing_meta_from_cache(ticker)
        return cached, "cache", meta.get("filing_form", "10-K")
    data, filing_form = download_and_extract_all_items_with_form(ticker, email)
    return data, "downloaded", filing_form


def download_and_extract_item7_and_1a(ticker: str, email: str) -> tuple[str, str, str]:
    """Fetch annual filing and return ``(full_text, item1a, item7)``."""
    sections, _, _ = get_annual_sections_with_form(ticker, email)
    return "", sections.get("item1a", "") or "", sections.get("item7", "") or ""


def download_item7_latest_and_3y_ago(
    ticker: str,
    email: str,
) -> tuple[Optional[str], Optional[str], Optional[str], bool]:
    """Download up to 5 annual filings and compare latest vs 3-years-ago MD&A/OFR."""
    with tempfile.TemporaryDirectory() as tmpdir:
        download_root = Path(tmpdir)
        filing_form, _ = _download_latest_annual_filing_dir(download_root, ticker, email, limit=5)
        filing_dirs = find_all_filing_dirs(download_root, ticker, filing_form)
        if not filing_dirs:
            raise FileNotFoundError(
                f"Could not find annual SEC filing (10-K / 20-F / 40-F) for ticker '{ticker}'."
            )

        full_latest = get_main_10k_text(filing_dirs[0])
        if not full_latest:
            raise ValueError(f"Could not extract text from the latest {filing_form}.")

        latest_sections = _extract_sections_for_form(full_latest, filing_form)
        item1a = latest_sections.get("item1a", "")
        item7_latest = latest_sections.get("item7", "")
        if not item7_latest and full_latest:
            item7_latest = smart_chunk(full_latest[:120_000], max_chars=20_000)

        item7_3y_ago: Optional[str] = None
        has_comparison = False
        if len(filing_dirs) >= 4:
            full_3y = get_main_10k_text(filing_dirs[3])
            if full_3y:
                item7_3y_ago = _extract_sections_for_form(full_3y, filing_form).get("item7", "")
                if not item7_3y_ago:
                    item7_3y_ago = smart_chunk(full_3y[:120_000], max_chars=20_000)
                has_comparison = bool(item7_3y_ago)

    return item1a or "", item7_latest or "", item7_3y_ago, has_comparison
