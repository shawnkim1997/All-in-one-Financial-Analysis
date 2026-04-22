"""Earnings-call transcript delta analysis.

Deterministic phrase deltas are computed locally so the feature remains useful
without an LLM key.  A best-effort Claude/Gemini narrative is layered on top
when a server-side key is configured.
"""

from __future__ import annotations

import json
import math
import os
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

_TOPIC_LEXICON: dict[str, set[str]] = {
    "AI / Data Centre": {"ai", "artificial intelligence", "data center", "data centre", "accelerated computing", "inference", "training"},
    "Capex / Supply": {"capex", "capital expenditure", "supply", "capacity", "manufacturing", "inventory", "lead time"},
    "Margins / Pricing": {"margin", "gross margin", "pricing", "cost", "mix", "profitability", "operating leverage"},
    "Demand / Customers": {"demand", "customer", "enterprise", "cloud", "hyperscaler", "consumer", "orders"},
    "Risk / Regulation": {"risk", "regulation", "export", "competition", "uncertain", "headwind", "restriction"},
    "Product Mix": {"gaming", "automotive", "software", "services", "networking", "platform", "segment"},
}


@dataclass(frozen=True)
class Transcript:
    ticker: str
    year: int
    quarter: int
    content: str
    source: str = "fmp"


@dataclass(frozen=True)
class Token:
    text: str
    lemma: str
    position: int


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


def _lemma(word: str) -> str:
    irregular = {
        "centres": "centre",
        "centers": "center",
        "margins": "margin",
        "revenues": "revenue",
        "customers": "customer",
        "orders": "order",
        "risks": "risk",
        "costs": "cost",
        "services": "service",
    }
    if word in irregular:
        return irregular[word]
    if word in {"ai", "data", "capex", "cloud"}:
        return word
    if len(word) > 5 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 6 and word.endswith("ing"):
        base = word[:-3]
        return base[:-1] if len(base) > 3 and base[-1] == base[-2] else base
    if len(word) > 5 and word.endswith("ed"):
        return word[:-2]
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def tokenize_and_normalize(text: str) -> list[Token]:
    words = re.findall(r"[a-zA-Z][a-zA-Z\-']{1,}", text.lower())
    normalized = [word.strip("-'") for word in words]
    tokens: list[Token] = []
    for position, word in enumerate(normalized):
        if (len(word) <= 2 and word != "ai") or word in _STOPWORDS:
            continue
        tokens.append(Token(text=word, lemma=_lemma(word), position=position))
    return tokens


def _phrase_counts(text: str) -> Counter[str]:
    tokens = tokenize_and_normalize(text)
    lemmas = [token.lemma for token in tokens]
    phrases: Counter[str] = Counter(lemmas)
    for size in (2, 3):
        for idx in range(0, max(0, len(lemmas) - size + 1)):
            phrase = " ".join(lemmas[idx : idx + size])
            phrases[phrase] += 1
    return phrases


def _tfidf_score(phrase: str, count: int, curr: Counter[str], prev: Counter[str]) -> float:
    doc_freq = int(curr.get(phrase, 0) > 0) + int(prev.get(phrase, 0) > 0)
    idf = math.log((1 + 2) / (1 + doc_freq)) + 1
    return round(count * idf, 3)


def _sentiment_score(counts: Counter[str]) -> float:
    total = sum(counts.values()) or 1
    pos = sum(counts[word] for word in _POSITIVE)
    neg = sum(counts[word] for word in _NEGATIVE)
    return round((pos - neg) / total * 100, 2)


def _tone_label(score: float) -> str:
    if score >= 0.12:
        return "bullish"
    if score <= -0.12:
        return "bearish"
    return "neutral"


def _top_new(curr: Counter[str], prev: Counter[str], limit: int = 10) -> list[dict[str, Any]]:
    rows = [
        {"phrase": phrase, "count": count, "score": _tfidf_score(phrase, count, curr, prev)}
        for phrase, count in curr.items()
        if count >= 2 and prev.get(phrase, 0) == 0 and " " in phrase
    ]
    return sorted(rows, key=lambda row: row["score"], reverse=True)[:limit]


def _top_removed(curr: Counter[str], prev: Counter[str], limit: int = 10) -> list[dict[str, Any]]:
    rows = [
        {"phrase": phrase, "previous_count": count, "score": _tfidf_score(phrase, count, curr, prev)}
        for phrase, count in prev.items()
        if count >= 2 and curr.get(phrase, 0) == 0 and " " in phrase
    ]
    return sorted(rows, key=lambda row: row["score"], reverse=True)[:limit]


def _emphasis_shift(curr: Counter[str], prev: Counter[str], limit: int = 12) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    curr_total = sum(curr.values()) or 1
    prev_total = sum(prev.values()) or 1
    for phrase in set(curr) | set(prev):
        if " " not in phrase:
            continue
        curr_count = curr.get(phrase, 0)
        prev_count = prev.get(phrase, 0)
        delta = curr_count - prev_count
        if abs(delta) < 2:
            continue
        curr_rate = curr_count / curr_total
        prev_rate = prev_count / prev_total
        score = abs(curr_rate - prev_rate) * math.log(curr_count + prev_count + 2)
        rows.append({
            "phrase": phrase,
            "current_count": curr_count,
            "previous_count": prev_count,
            "delta": delta,
            "score": round(score, 5),
        })
    return sorted(rows, key=lambda row: row["score"], reverse=True)[:limit]


def _topic_shift(curr: Counter[str], prev: Counter[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for topic, keywords in _TOPIC_LEXICON.items():
        curr_count = sum(curr.get(keyword, 0) for keyword in keywords)
        prev_count = sum(prev.get(keyword, 0) for keyword in keywords)
        delta = curr_count - prev_count
        if curr_count == 0 and prev_count == 0:
            continue
        rows.append({
            "topic": topic,
            "current_count": curr_count,
            "previous_count": prev_count,
            "delta": delta,
        })
    return sorted(rows, key=lambda row: abs(row["delta"]), reverse=True)


def compute_delta(curr: Transcript, prev: Transcript) -> dict[str, Any]:
    curr_counts = _phrase_counts(curr.content)
    prev_counts = _phrase_counts(prev.content)
    current_tone = _sentiment_score(curr_counts)
    previous_tone = _sentiment_score(prev_counts)
    return {
        "ticker": curr.ticker,
        "available": True,
        "current": {"year": curr.year, "quarter": curr.quarter},
        "previous": {"year": prev.year, "quarter": prev.quarter},
        "new_phrases": _top_new(curr_counts, prev_counts),
        "removed_phrases": _top_removed(curr_counts, prev_counts),
        "emphasis_shift": _emphasis_shift(curr_counts, prev_counts, limit=20),
        "tone_shift": {
            "current_score": current_tone,
            "previous_score": previous_tone,
            "delta": round(current_tone - previous_tone, 2),
            "current_label": _tone_label(current_tone),
            "previous_label": _tone_label(previous_tone),
        },
        "topic_shift": _topic_shift(curr_counts, prev_counts),
    }


async def generate_delta_narrative(delta: dict[str, Any], ticker: str) -> dict[str, Any]:
    fallback = {
        "key_shifts": [row["phrase"] for row in delta.get("emphasis_shift", [])[:3]],
        "what_it_means": "Transcript language changed, but AI narrative is unavailable. Review the phrase deltas for direction.",
        "questions_to_ask": ["Which new phrases are one-off comments versus strategy?", "Are margin or capex terms increasing?"],
        "variant_view": "Use phrase shifts as a prompt for deeper research, not as standalone evidence.",
    }
    prompt = (
        "You are a skeptical institutional equity analyst reviewing earnings-call language drift.\n"
        "Return ONLY valid JSON with this exact shape:\n"
        '{"key_shifts":["..."],"what_it_means":"...","questions_to_ask":["..."],"variant_view":"..."}\n'
        "Keep what_it_means to five concise analyst-style lines or fewer. Do not invent numbers.\n\n"
        f"TICKER: {ticker.upper()}\n"
        f"DELTA_DATA: {json.dumps(delta, ensure_ascii=False)[:12000]}"
    )

    anthropic_key = (os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY") or "").strip()
    if anthropic_key:
        try:
            from server.ai.llm_router import LLMConfig, LLMProvider, llm_router

            text = await llm_router.generate(
                prompt,
                config=LLMConfig(
                    provider=LLMProvider.CLAUDE,
                    model="claude-sonnet-4-20250514",
                    api_key=anthropic_key,
                    temperature=0.2,
                    max_tokens=900,
                ),
                system_prompt="You return strict JSON for equity research workflows.",
            )
            parsed = _parse_json_object(text)
            if parsed:
                return {**fallback, **parsed}
        except Exception:
            pass

    try:
        from server.services.gemini_service import generate_text

        text = await generate_text(prompt)
        parsed = _parse_json_object(text)
        if parsed:
            return {**fallback, **parsed}
    except Exception:
        return fallback
    return fallback


def _parse_json_object(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.S)
    if match:
        cleaned = match.group(0)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
