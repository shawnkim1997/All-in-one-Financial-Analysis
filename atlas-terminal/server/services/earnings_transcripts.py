"""Earnings-call transcript delta analysis.

This intentionally starts lightweight: deterministic phrase deltas are computed
locally, and the LLM narrative is best-effort so the feature still works without
an AI key.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from server.services.fmp_client import fetch_earning_call_transcript, fmp_is_configured

_STOPWORDS = {
    "about", "after", "again", "also", "and", "are", "because", "been", "but", "can", "could",
    "did", "does", "for", "from", "have", "into", "just", "like", "more", "our", "out", "over",
    "said", "should", "that", "the", "their", "then", "there", "these", "they", "this", "those",
    "through", "was", "were", "what", "when", "where", "which", "while", "will", "with", "would",
    "you", "your", "we", "us", "quarter", "year", "thank", "thanks", "operator", "question",
}

_POSITIVE = {"growth", "accelerate", "strong", "record", "improve", "expansion", "demand", "margin", "profitable"}
_NEGATIVE = {"decline", "pressure", "risk", "weak", "slower", "headwind", "inventory", "cost", "uncertain"}


@dataclass(frozen=True)
class Transcript:
    ticker: str
    year: int
    quarter: int
    content: str
    source: str = "fmp"


def default_quarter_pair(today: date | None = None) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return a reasonable current/previous quarter pair for transcript lookup."""

    d = today or date.today()
    current_q = ((d.month - 1) // 3) + 1
    latest_q = current_q - 1
    latest_year = d.year
    if latest_q == 0:
        latest_q = 4
        latest_year -= 1
    prev_q = latest_q - 1
    prev_year = latest_year
    if prev_q == 0:
        prev_q = 4
        prev_year -= 1
    return (latest_year, latest_q), (prev_year, prev_q)


def _extract_content(row: Dict[str, Any]) -> str:
    for key in ("content", "transcript", "text"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


async def fetch_transcript(ticker: str, year: int, quarter: int) -> Optional[Transcript]:
    if not fmp_is_configured():
        return None
    rows = await fetch_earning_call_transcript(ticker, year, quarter)
    if not rows:
        return None
    content = _extract_content(rows[0])
    if not content:
        return None
    return Transcript(ticker=ticker.upper(), year=year, quarter=quarter, content=content)


def tokenize_and_normalize(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z\-']{1,}", text.lower())
    normalized = [word.strip("-'") for word in words]
    return [word for word in normalized if (len(word) > 2 or word == "ai") and word not in _STOPWORDS]


def _phrase_counts(text: str) -> Counter[str]:
    tokens = tokenize_and_normalize(text)
    phrases: Counter[str] = Counter(tokens)
    for size in (2, 3):
        for idx in range(0, max(0, len(tokens) - size + 1)):
            phrase = " ".join(tokens[idx : idx + size])
            phrases[phrase] += 1
    return phrases


def _sentiment_score(counts: Counter[str]) -> float:
    total = sum(counts.values()) or 1
    pos = sum(counts[word] for word in _POSITIVE)
    neg = sum(counts[word] for word in _NEGATIVE)
    return round((pos - neg) / total * 100, 2)


def _top_new(curr: Counter[str], prev: Counter[str], limit: int = 10) -> list[dict[str, Any]]:
    rows = [
        {"phrase": phrase, "count": count}
        for phrase, count in curr.items()
        if count >= 2 and prev.get(phrase, 0) == 0 and " " in phrase
    ]
    return sorted(rows, key=lambda row: row["count"], reverse=True)[:limit]


def _top_removed(curr: Counter[str], prev: Counter[str], limit: int = 10) -> list[dict[str, Any]]:
    rows = [
        {"phrase": phrase, "previous_count": count}
        for phrase, count in prev.items()
        if count >= 2 and curr.get(phrase, 0) == 0 and " " in phrase
    ]
    return sorted(rows, key=lambda row: row["previous_count"], reverse=True)[:limit]


def _emphasis_shift(curr: Counter[str], prev: Counter[str], limit: int = 12) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for phrase in set(curr) | set(prev):
        if " " not in phrase:
            continue
        curr_count = curr.get(phrase, 0)
        prev_count = prev.get(phrase, 0)
        delta = curr_count - prev_count
        if abs(delta) < 2:
            continue
        rows.append({"phrase": phrase, "current_count": curr_count, "previous_count": prev_count, "delta": delta})
    return sorted(rows, key=lambda row: abs(row["delta"]), reverse=True)[:limit]


def compute_delta(curr: Transcript, prev: Transcript) -> dict[str, Any]:
    curr_counts = _phrase_counts(curr.content)
    prev_counts = _phrase_counts(prev.content)
    return {
        "ticker": curr.ticker,
        "available": True,
        "current": {"year": curr.year, "quarter": curr.quarter},
        "previous": {"year": prev.year, "quarter": prev.quarter},
        "new_phrases": _top_new(curr_counts, prev_counts),
        "removed_phrases": _top_removed(curr_counts, prev_counts),
        "emphasis_shift": _emphasis_shift(curr_counts, prev_counts),
        "tone_shift": {
            "current_score": _sentiment_score(curr_counts),
            "previous_score": _sentiment_score(prev_counts),
        },
    }


async def generate_delta_narrative(delta: dict[str, Any], ticker: str) -> dict[str, Any]:
    fallback = {
        "key_shifts": [row["phrase"] for row in delta.get("emphasis_shift", [])[:3]],
        "what_it_means": "Transcript language changed, but AI narrative is unavailable. Review the phrase deltas for direction.",
        "questions_to_ask": ["Which new phrases are one-off comments versus strategy?", "Are margin or capex terms increasing?"],
        "variant_view": "Use phrase shifts as a prompt for deeper research, not as standalone evidence.",
    }
    try:
        from server.services.gemini_service import generate_text

        prompt = (
            f"Analyze {ticker.upper()} earnings call transcript delta. Return concise JSON with keys "
            "key_shifts, what_it_means, questions_to_ask, variant_view. Data:\n"
            f"{delta}"
        )
        text = await generate_text(prompt)
        import json

        parsed = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
        if isinstance(parsed, dict):
            return {**fallback, **parsed}
    except Exception:
        return fallback
    return fallback
