"""
SEC 10-K text extraction: HTML parsing, item section extraction, text cleaning.
"""
import re
from pathlib import Path

from bs4 import BeautifulSoup

from config.constants import (
    ITEM1A_PATTERNS, ITEM3_PATTERNS, ITEM7_PATTERNS, ITEM8_PATTERNS, ITEM9A_PATTERNS,
)


def _slice_html_items_1a_to_9a(raw_html: str) -> str:
    """Fast string slice: keep only Item 1A through end of Item 9A to avoid parsing 50MB+ full file. Uses .find()/regex on raw string only."""
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
    end_match = re.search(r"Item\s+10\s|Item\s+12\s|Part\s+III\b|PART\s+III\b", search_region, re.IGNORECASE)
    end = start + end_match.start() if end_match else len(raw_html)
    end = min(end, start + 8_000_000)
    return raw_html[start:end]


def _extract_text_from_html_string(html_str: str) -> str:
    """Parse HTML string with lxml; drop table/img/svg/style/script immediately to reduce memory and speed."""
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
    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except Exception:
        with open(html_path, "r", encoding="latin-1", errors="replace") as f:
            raw = f.read()
    chunk = _slice_html_items_1a_to_9a(raw)
    return _extract_text_from_html_string(chunk)


def extract_text_from_file(file_path: Path) -> str:
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


def _find_section_start(text: str, patterns: list, item_num: int) -> int:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.start()
    m = re.search(r"\bItem\s+" + str(item_num) + r"\b", text, re.IGNORECASE)
    return m.start() if m else -1


def find_item_section_generic(text: str, patterns: list, item_num: int, title_keywords: list, max_chars: int = 120000) -> str:
    start = _find_section_start(text, patterns, item_num)
    if start == -1:
        pattern = re.compile(
            r"\bItem\s+" + str(item_num) + r"\b[.\s]*[^\n]*(" + "|".join(re.escape(k) for k in title_keywords) + r")?",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if not match:
            return ""
        start = match.start()
    next_item = re.search(r"\n\s*Item\s+\d+[A-Z]?\s+", text[start + 100:], re.IGNORECASE)
    if next_item:
        end = start + 100 + next_item.start()
    else:
        end = min(start + max_chars, len(text))
    return text[start:end].strip()


def clean_text_for_llm(html_content: str) -> str:
    """Aggressive cleaning for LLM: strip tables/code, collapse whitespace, drop non-ASCII. Uses lxml for speed; drops table/img/svg/style/script."""
    if not html_content or not html_content.strip():
        return ""
    try:
        soup = BeautifulSoup(html_content, "lxml")
        for tag in soup.find_all(["table", "img", "style", "script", "svg", "math"]):
            tag.decompose()
        text = soup.get_text(separator=" ")
    except Exception:
        text = re.sub(r"<[^>]+>", " ", html_content)
    text = re.sub(r"\s+", " ", text)
    text = " ".join(text.split())
    text = re.sub(r"[^\x20-\x7E\n]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if re.fullmatch(r"\d+", line) or re.fullmatch(r"[\.\-\s\-]+", line):
            continue
        if re.match(r"^(page\s+\d+|\d+)\s*$", line, re.IGNORECASE) and len(line) < 20:
            continue
        lines.append(line)
    result = " ".join(lines)
    result = re.sub(r"\s+", " ", result).strip()
    return result


def smart_chunk(section: str, max_chars: int = 10000, head_ratio: float = 0.5) -> str:
    """Limit payload for Gemini; 10k chars ~ 2.5k tokens for fast response."""
    if not section or len(section) <= max_chars:
        return section
    head_size = int(max_chars * head_ratio)
    tail_size = max_chars - head_size - 100
    return section[:head_size] + " [ ... middle omitted ... ] " + section[-tail_size:]


def _extract_item_from_full(text: str, patterns: list, item_num: int, keywords: list, max_chars: int = 60000) -> str:
    """Extract one item section from full 10-K text."""
    start = _find_section_start(text, patterns, item_num)
    if start < 0:
        pattern = re.compile(r"\bItem\s+" + str(item_num) + r"[A-Z]?\b[.\s]*[^\n]*", re.IGNORECASE)
        match = pattern.search(text)
        start = match.start() if match else -1
    if start < 0:
        return ""
    next_item = re.search(r"\n\s*Item\s+\d+[A-Z]?\s+", text[start + 100:], re.IGNORECASE)
    end = start + 100 + next_item.start() if next_item else min(start + max_chars, len(text))
    return text[start:end].strip()
