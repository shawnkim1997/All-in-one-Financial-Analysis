"""SEC EDGAR 10-K download, parsing, section extraction, and caching.

Handles the full pipeline from downloading a 10-K filing via
``sec_edgar_downloader`` through HTML stripping to isolating individual
Item sections (1A, 3, 7, 8, 9A) and persisting the cleaned text to a
local JSON cache under ``data/``.
"""

import json
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from bs4.element import Comment, Tag

from server.services.text_chunker import clean_text_for_llm, smart_chunk

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR: Path = Path(__file__).resolve().parents[3] / "data"

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


def find_downloaded_10k_path(download_root: Path, ticker: str) -> Optional[Path]:
    """Locate the most recent 10-K filing directory on disk."""
    ticker_upper = ticker.upper()
    for base in (download_root / "sec-edgar-filings", download_root):
        path_10k = base / ticker_upper / "10-K"
        if path_10k.exists():
            subdirs = sorted(
                [d for d in path_10k.iterdir() if d.is_dir()],
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
            path_10k = company_dir / "10-K"
            if path_10k.exists():
                subdirs = sorted(
                    [d for d in path_10k.iterdir() if d.is_dir()],
                    key=lambda x: x.name,
                    reverse=True,
                )
                if subdirs:
                    return subdirs[0]
    return None


def find_all_10k_filing_dirs(download_root: Path, ticker: str) -> List[Path]:
    """Return all 10-K filing directories sorted newest-first."""
    ticker_upper = ticker.upper()
    for base in (download_root / "sec-edgar-filings", download_root):
        path_10k = base / ticker_upper / "10-K"
        if path_10k.exists():
            return sorted(
                [d for d in path_10k.iterdir() if d.is_dir()],
                key=lambda x: x.name,
                reverse=True,
            )
    return []


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
    ("sec-item-1a", [re.compile(p, re.I) for p in ITEM1A_PATTERNS] + [re.compile(r"Item\s+1A\s*[.:]", re.I)]),
    ("sec-item-3", [re.compile(p, re.I) for p in ITEM3_PATTERNS] + [re.compile(r"Item\s+3\s*[.:]", re.I)]),
    ("sec-item-7", [re.compile(p, re.I) for p in ITEM7_PATTERNS] + [re.compile(r"Item\s+7\s*[.:]", re.I)]),
    ("sec-item-8", [re.compile(p, re.I) for p in ITEM8_PATTERNS] + [re.compile(r"Item\s+8\s*[.:]", re.I)]),
    ("sec-item-9a", [re.compile(p, re.I) for p in ITEM9A_PATTERNS] + [re.compile(r"Item\s+9A\s*[.:]", re.I)]),
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
    """Set ``id=\"sec-item-*\"`` on heading-like nodes for Item 1A, 3, 7, 8, 9A."""
    assigned: set[str] = set()
    for text in soup.find_all(string=True):
        if isinstance(text, Comment):
            continue
        text_val = str(text)
        if not text_val.strip():
            continue
        for el_id, regexes in _SEC_ITEM_INJECT_SPECS:
            if el_id in assigned:
                continue
            if not any(rx.search(text_val) for rx in regexes):
                continue
            host = _best_anchor_parent_for_text_node(text)
            if host is None:
                continue
            host["id"] = el_id
            assigned.add(el_id)
            break


def prepare_native_html_fragment_from_10k_raw(raw_html: str) -> str:
    """Slice Items 1A–9A, sanitize, inject ``sec-item-*`` anchors, return body HTML fragment."""
    if not raw_html or len(raw_html) < 100:
        return ""
    sliced = _slice_html_items_1a_to_9a(raw_html)
    try:
        soup = BeautifulSoup(sliced, "lxml")
    except Exception:
        soup = BeautifulSoup(sliced, "html.parser")
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


# ---------------------------------------------------------------------------
# High-level download + extract
# ---------------------------------------------------------------------------

def download_and_extract_all_items(ticker: str, email: str) -> Dict[str, str]:
    """Download latest 10-K, extract Items 1A/3/7/8/9A, clean and cache."""
    Downloader = _get_edgar_downloader()
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

    item1a = find_item_section_generic(full_text, ITEM1A_PATTERNS, 1, ["Risk", "Factors"], max_chars=80_000)
    item3 = _extract_item_from_full(full_text, ITEM3_PATTERNS, 3, ["Legal", "Proceedings"], max_chars=40_000)
    item9a = _extract_item_from_full(full_text, ITEM9A_PATTERNS, 9, ["Controls", "Procedures", "Internal"], max_chars=40_000)

    start7 = _find_section_start(full_text, ITEM7_PATTERNS, 7)
    text_after_7 = full_text[start7:] if start7 >= 0 else full_text
    item7 = find_item_section_generic(text_after_7, ITEM7_PATTERNS, 7, ["Management's Discussion", "MD&A", "Analysis"], max_chars=100_000)
    if not item7 and text_after_7:
        item7 = text_after_7[:120_000]
    item8 = _extract_item_from_full(full_text, ITEM8_PATTERNS, 8, ["Financial Statements", "Supplementary Data"], max_chars=200_000)

    data: Dict[str, str] = {
        "item1a": clean_text_for_llm(item1a or ""),
        "item3": clean_text_for_llm(item3 or ""),
        "item9a": clean_text_for_llm(item9a or ""),
        "item7": clean_text_for_llm(item7 or ""),
        "item8": clean_text_for_llm(item8 or ""),
    }
    _save_10k_to_cache(ticker, data)

    raw_html = read_main_10k_html_raw(filing_dir)
    if raw_html:
        fragment = prepare_native_html_fragment_from_10k_raw(raw_html)
        if fragment:
            save_10k_html_slice(ticker, fragment)
    return data


def get_10k_sections(ticker: str, email: str) -> tuple[Dict[str, str], str]:
    """Return ``(sections, status)``; *status* is ``'cache'`` or ``'downloaded'``."""
    cached = _load_10k_from_cache(ticker)
    if cached is not None:
        return cached, "cache"
    return download_and_extract_all_items(ticker, email), "downloaded"


def download_and_extract_item7_and_1a(ticker: str, email: str) -> tuple[str, str, str]:
    """Fetch 10-K and return ``(full_text, item1a, item7)``."""
    sections, _ = get_10k_sections(ticker, email)
    return "", sections.get("item1a", "") or "", sections.get("item7", "") or ""


def download_item7_latest_and_3y_ago(
    ticker: str,
    email: str,
) -> tuple[Optional[str], Optional[str], Optional[str], bool]:
    """Download up to 5 10-Ks; return item1a (latest), item7 latest, item7 3y ago, has_comparison."""
    Downloader = _get_edgar_downloader()
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

        item1a = find_item_section_generic(full_latest, ITEM1A_PATTERNS, 1, ["Risk", "Factors"], max_chars=80_000)

        s7 = _find_section_start(full_latest, ITEM7_PATTERNS, 7)
        text_after_7 = full_latest[s7:] if s7 >= 0 else full_latest
        item7_latest = find_item_section_generic(text_after_7, ITEM7_PATTERNS, 7, ["Management's Discussion", "MD&A", "Analysis"], max_chars=100_000)
        if not item7_latest and text_after_7:
            item7_latest = smart_chunk(text_after_7[:120_000], max_chars=20_000)

        item7_3y_ago: Optional[str] = None
        has_comparison = False
        if len(filing_dirs) >= 4:
            full_3y = get_main_10k_text(filing_dirs[3])
            if full_3y:
                s7_3y = _find_section_start(full_3y, ITEM7_PATTERNS, 7)
                text_3y = full_3y[s7_3y:] if s7_3y >= 0 else full_3y
                item7_3y_ago = find_item_section_generic(text_3y, ITEM7_PATTERNS, 7, ["Management's Discussion", "MD&A", "Analysis"], max_chars=100_000)
                if not item7_3y_ago and text_3y:
                    item7_3y_ago = smart_chunk(text_3y[:120_000], max_chars=20_000)
                has_comparison = bool(item7_3y_ago)

    return item1a or "", item7_latest or "", item7_3y_ago, has_comparison
