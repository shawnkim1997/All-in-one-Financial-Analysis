"""Text cleaning and chunking utilities for LLM payloads.

Provides aggressive HTML-stripping, whitespace normalisation, and
intelligent splitting of long text into sequential chunks that avoid
cutting mid-sentence when possible.
"""

import re
from typing import List

from bs4 import BeautifulSoup


def clean_text_for_llm(html_content: str) -> str:
    """Strip HTML, collapse whitespace, and remove non-ASCII for LLM input.

    Removes ``<table>``, ``<img>``, ``<style>``, ``<script>``, ``<svg>``,
    and ``<math>`` elements before extracting text.  Drops page-number-only
    lines and other layout artefacts.

    Parameters
    ----------
    html_content:
        Raw HTML (or already-plain text with residual tags).

    Returns
    -------
    str
        Clean, single-line-ish text suitable for an LLM prompt.
    """
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

    lines: List[str] = []
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


def smart_chunk(
    section: str,
    max_chars: int = 10_000,
    head_ratio: float = 0.5,
) -> str:
    """Truncate *section* to *max_chars* keeping head and tail portions.

    When the text exceeds the limit the middle is replaced with a brief
    ``[ ... middle omitted ... ]`` marker.  Approximately
    ``head_ratio * max_chars`` characters come from the start and the
    remainder from the end.

    Parameters
    ----------
    section:
        Full text to be trimmed.
    max_chars:
        Hard character budget (default 10 000 ~= 2.5k tokens).
    head_ratio:
        Fraction of the budget allocated to the leading portion.

    Returns
    -------
    str
        Text guaranteed to be at most *max_chars* characters long.
    """
    if not section or len(section) <= max_chars:
        return section
    head_size = int(max_chars * head_ratio)
    tail_size = max_chars - head_size - 100
    return section[:head_size] + " [ ... middle omitted ... ] " + section[-tail_size:]


def _split_into_chunks(
    text: str,
    max_chars: int = 22_000,
    min_chunk: int = 5_000,
) -> List[str]:
    """Split *text* into sequential chunks without cutting mid-sentence.

    Prefers breaking at paragraph boundaries (double newlines).  Each chunk
    is at most *max_chars* characters; the algorithm avoids creating a
    trailing fragment shorter than *min_chunk* unless it is the only chunk.

    Parameters
    ----------
    text:
        The document to split.
    max_chars:
        Maximum characters per chunk.
    min_chunk:
        Minimum look-back distance when searching for a break point.

    Returns
    -------
    List[str]
        Non-empty stripped chunks in document order.
    """
    if not text or len(text) <= max_chars:
        return [text] if text and text.strip() else []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            break_at = text.rfind("\n\n", start, end + 1)
            if break_at > start + min_chunk:
                end = break_at + 2
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]
