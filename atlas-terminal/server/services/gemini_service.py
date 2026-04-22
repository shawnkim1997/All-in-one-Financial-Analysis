"""Gemini LLM integration for qualitative financial analysis.

All functions in this module talk to Google Gemini (via the
``google.generativeai`` SDK) and return plain strings or dicts.
No Streamlit dependencies.
"""

import json
import os
import re
import time
import asyncio
from typing import Any, Dict, Generator, List, Optional

from server.utils.safe_float import _safe_float
from server.services.text_chunker import clean_text_for_llm, smart_chunk, _split_into_chunks

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GEMINI_MODEL: str = "gemini-2.0-flash"
RATE_LIMIT_WAIT_SEC: int = 60

_REQUIRED_FINANCIAL_KEYS: List[str] = [
    "Revenue", "CostOfRevenue", "OperatingExpenses", "NetIncome",
    "TotalAssets", "CurrentAssets", "CurrentLiabilities", "LongTermDebt",
    "OperatingCashFlow", "SharesOutstanding",
]


# ---------------------------------------------------------------------------
# Model initialisation
# ---------------------------------------------------------------------------

def get_gemini_model(api_key: str) -> Any:
    """Configure and return a ``GenerativeModel`` for :data:`GEMINI_MODEL`."""
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)


async def generate_text(prompt: str, temperature: float = 0.3, max_tokens: int = 1200) -> str:
    """Async convenience wrapper used by lightweight best-effort AI features.

    It reads a server-side Gemini key from the environment.  Browser-local keys
    are intentionally not pulled in here because routers should not receive API
    secrets implicitly from localStorage.
    """

    api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY is not configured")

    def _run() -> str:
        model = get_gemini_model(api_key)
        response = _generate_with_retry(
            model,
            prompt,
            {"temperature": temperature, "max_output_tokens": max_tokens},
        )
        return (response.text or "").strip()

    return await asyncio.to_thread(_run)


# ---------------------------------------------------------------------------
# Retry / streaming helpers
# ---------------------------------------------------------------------------

def _is_rate_limit_error(e: Exception) -> bool:
    """Return ``True`` if *e* looks like a 429 / resource-exhausted error."""
    err_msg = str(e).lower()
    return (
        "429" in err_msg
        or "resourcelimited" in err_msg
        or "resource exhausted" in err_msg
        or getattr(e, "code", None) == 429
    )


def _generate_with_retry(
    model: Any,
    content: str,
    config: Dict[str, Any],
    max_retries: int = 3,
) -> Any:
    """Call ``model.generate_content`` with automatic rate-limit back-off."""
    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return model.generate_content(content, generation_config=config)
        except Exception as e:
            last_err = e
            if attempt < max_retries and _is_rate_limit_error(e):
                time.sleep(RATE_LIMIT_WAIT_SEC)
                continue
            raise
    raise last_err  # type: ignore[misc]


def _generate_stream(
    model: Any,
    content: str,
    config: Dict[str, Any],
) -> Generator[str, None, None]:
    """Yield text chunks from Gemini with ``stream=True``."""
    response = model.generate_content(content, generation_config=config, stream=True)
    for chunk in response:
        if hasattr(chunk, "text") and chunk.text:
            yield chunk.text


# ---------------------------------------------------------------------------
# Segment-level helpers (chunked analysis)
# ---------------------------------------------------------------------------

def _gemini_summarize_segment(
    api_key: str,
    segment_text: str,
    ticker: str,
    segment_label: str,
) -> str:
    """Summarise one segment of Item 1A / Item 7 text."""
    model = get_gemini_model(api_key)
    prompt = (
        f"You are a senior equity analyst. The following is one segment of "
        f"the 10-K for {ticker} (Item 1A Risk Factors and/or Item 7 MD&A).\n"
        "Extract and list all significant: (1) strategic shifts or priorities, "
        "(2) hidden or material risks, (3) management tone cues. Use concise "
        f"bullet points. Do not omit important details. Segment: {segment_label}."
    )
    full = f"--- 10-K Segment ---\n\n{segment_text[:50000]}\n\n---\n\n{prompt}"
    try:
        r = _generate_with_retry(model, full, {"temperature": 0.2, "max_output_tokens": 2048})
        return (r.text or "").strip()
    except Exception:
        return ""


def _gemini_synthesize_report(
    api_key: str,
    segment_summaries: List[str],
    ticker: str,
    sector: str,
    industry: str,
) -> str:
    """Synthesise segment summaries into an Executive Insight Report."""
    model = get_gemini_model(api_key)
    combined = "\n\n---\n\n".join(segment_summaries)
    kpi_note = (
        f" Sector: {sector}; Industry: {industry}. Include industry-specific KPIs if mentioned."
        if sector and sector != "N/A"
        else ""
    )
    prompt = (
        f"You are a senior equity analyst. Use British English. Below are "
        f"summarized insights from the full 10-K for {ticker} (Item 1A and "
        "Item 7). Create the final **Executive Insight Report** with these sections:\n\n"
        "1. **Management's Tone (Sentiment)**: Overall tone and supporting evidence.\n"
        "2. **Current Strategy & Priorities**: Key strategic focus, capital allocation, growth drivers.\n"
        "3. **Major Hidden Risks**: The 3-4 most material risks investors might overlook.\n"
        "4. **Forensic / Quality of Earnings**: Accounting caveats, one-offs, cash flow vs earnings."
        f"{kpi_note}\n\n"
        "Use clear headings. Do not invent figures. Keep under 900 words."
    )
    full = f"--- Segment Summaries ---\n\n{combined}\n\n---\n\n{prompt}"
    try:
        r = _generate_with_retry(model, full, {"temperature": 0.3, "max_output_tokens": 4096})
        return (r.text or "").strip()
    except Exception:
        return ""


def _gemini_forensic_audit(
    api_key: str,
    item3: str,
    item9a: str,
    ticker: str,
) -> str:
    """Check Item 3 & 9A for material weaknesses, lawsuits, red flags."""
    model = get_gemini_model(api_key)
    combined = (item3 or "") + "\n\n---\n\n" + (item9a or "")
    if not combined.strip():
        return "No Item 3 / 9A text provided; skip forensic."
    prompt = (
        f"From the following 10-K excerpts for {ticker} (Item 3 Legal Proceedings "
        "and Item 9A Controls/Internal Control), list any:\n"
        "- Material weaknesses in internal control\n"
        "- Significant legal proceedings or litigation\n"
        "- Off-balance-sheet or governance red flags\n"
        'If none, output: "No material red flags or special issues detected '
        'in Item 3 and 9A."\nBe concise (under 150 words).'
    )
    full = f"--- Item 3 & 9A ---\n\n{combined[:30000]}\n\n---\n\n{prompt}"
    try:
        r = _generate_with_retry(model, full, {"temperature": 0.1, "max_output_tokens": 512})
        return (r.text or "").strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Public analysis functions
# ---------------------------------------------------------------------------

def get_sec_financials_llm(api_key: str, item8_text: str, ticker: str) -> Dict[str, Any]:
    """Extract current/previous year financials from Item 8 via Gemini."""
    if not (api_key or "").strip() or not (item8_text or "").strip():
        return {}
    payload = smart_chunk((item8_text or "").strip(), max_chars=35_000)
    model = get_gemini_model(api_key)
    prompt = (
        f"You are a financial analyst. Below is Item 8 (Financial Statements "
        f"and Supplementary Data) from the latest 10-K for {ticker}.\n\n"
        "Extract figures for **Current Year** and **Previous Year**. "
        "Monetary values in millions. Shares in millions.\n\n"
        "Return ONLY valid JSON:\n"
        '{"current_yr": {...}, "previous_yr": {...}}\n'
        "Keys: Revenue, CostOfRevenue, OperatingExpenses, NetIncome, "
        "TotalAssets, CurrentAssets, CurrentLiabilities, LongTermDebt, "
        "OperatingCashFlow, SharesOutstanding.\n"
        "If not found use 0. Output nothing except JSON."
    )
    full = f"--- Item 8 ---\n\n{payload}\n\n---\n\n{prompt}"
    try:
        r = _generate_with_retry(model, full, {"temperature": 0.0, "max_output_tokens": 2048})
        raw = (r.text or "").strip()
        if not raw:
            return {}
        raw = re.sub(r"^```\s*json\s*", "", raw)
        raw = re.sub(r"^```\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
        raw = raw.strip()
        out = json.loads(raw)
        cur = out.get("current_yr") or {}
        prev = out.get("previous_yr") or {}
        for key in _REQUIRED_FINANCIAL_KEYS:
            cur[key] = _safe_float(cur.get(key)) or 0
            prev[key] = _safe_float(prev.get(key)) or 0
        return {"current_yr": cur, "previous_yr": prev}
    except (json.JSONDecodeError, Exception):
        return {}


def get_gemini_item7_strategy(
    api_key: str,
    item7_text: str,
    ticker: str,
    sector: str,
    industry: str,
) -> str:
    """Analyse Item 7 for business performance and strategic shifts."""
    if not (item7_text or "").strip():
        return "No Item 7 (MD&A) text available."
    model = get_gemini_model(api_key)
    text = smart_chunk(clean_text_for_llm(item7_text), max_chars=10_000)
    sector_note = f" Sector: {sector}; Industry: {industry}." if sector and sector != "N/A" else ""
    prompt = (
        f"You are a senior equity analyst. Use British English. The text below is "
        f"**Item 7 (Management's Discussion and Analysis)** from the latest 10-K for {ticker}.{sector_note}\n\n"
        "Provide a concise **Management Strategy** report:\n"
        "1. **Business performance**\n2. **Strategic shifts**\n3. **Capital allocation**\n"
        "Use clear headings. Under 600 words. Output in British English even if source is another language."
    )
    full = f"--- Item 7 (MD&A) ---\n\n{text}\n\n---\n\n{prompt}"
    try:
        r = _generate_with_retry(model, full, {"temperature": 0.3, "max_output_tokens": 2048})
        return (r.text or "").strip()
    except Exception:
        return ""


def get_gemini_item7_strategy_stream(
    api_key: str,
    item7_text: str,
    ticker: str,
    sector: str,
    industry: str,
) -> Generator[str, None, None]:
    """Yield MD&A strategy report chunks for real-time streaming."""
    if not (item7_text or "").strip():
        yield "No Item 7 (MD&A) text available."
        return
    model = get_gemini_model(api_key)
    text = smart_chunk(clean_text_for_llm(item7_text), max_chars=10_000)
    sector_note = f" Sector: {sector}; Industry: {industry}." if sector and sector != "N/A" else ""
    prompt = (
        f"You are a senior equity analyst. Use British English. The text below is "
        f"**Item 7 (MD&A)** from the latest 10-K for {ticker}.{sector_note}\n\n"
        "Provide a concise **Management Strategy** report:\n"
        "1. **Business performance**\n2. **Strategic shifts**\n3. **Capital allocation**\n"
        "Under 600 words. British English."
    )
    full = f"--- Item 7 (MD&A) ---\n\n{text}\n\n---\n\n{prompt}"
    yield from _generate_stream(model, full, {"temperature": 0.3, "max_output_tokens": 2048})


def get_gemini_item1a_risks(
    api_key: str,
    item1a_text: str,
    item3: str,
    item9a: str,
    ticker: str,
) -> str:
    """Analyse Item 1A risks and append forensic audit of Items 3 & 9A."""
    if not (item1a_text or "").strip():
        return "No Item 1A (Risk Factors) text available."
    model = get_gemini_model(api_key)
    text = smart_chunk(clean_text_for_llm(item1a_text), max_chars=10_000)
    prompt = (
        f"You are a senior equity analyst. Use British English. The text below is "
        f"**Item 1A (Risk Factors)** from the latest 10-K for {ticker}.\n\n"
        "Provide a concise **Risk Factors** report:\n"
        "1. **Legal & regulatory risks**\n2. **Operational risks**\n3. **Market & competitive risks**\n"
        "Under 500 words. British English."
    )
    full = f"--- Item 1A ---\n\n{text}\n\n---\n\n{prompt}"
    try:
        report = _generate_with_retry(model, full, {"temperature": 0.3, "max_output_tokens": 2048})
        risks = (report.text or "").strip()
    except Exception:
        risks = ""
    forensic = _gemini_forensic_audit(api_key, item3 or "", item9a or "", ticker)
    return (risks or "") + "\n\n---\n\n**Forensic Audit (Item 3 & 9A)**\n\n" + (forensic or "")


def get_gemini_item1a_risks_stream(
    api_key: str,
    item1a_text: str,
    ticker: str,
) -> Generator[str, None, None]:
    """Yield Risk Factors report chunks; caller appends forensic separately."""
    if not (item1a_text or "").strip():
        yield "No Item 1A (Risk Factors) text available."
        return
    model = get_gemini_model(api_key)
    text = smart_chunk(clean_text_for_llm(item1a_text), max_chars=10_000)
    prompt = (
        f"You are a senior equity analyst. Use British English. The text below is "
        f"**Item 1A (Risk Factors)** from the latest 10-K for {ticker}.\n\n"
        "Provide a concise **Risk Factors** report:\n"
        "1. **Legal & regulatory risks**\n2. **Operational risks**\n3. **Market & competitive risks**\n"
        "Under 500 words. British English."
    )
    full = f"--- Item 1A ---\n\n{text}\n\n---\n\n{prompt}"
    yield from _generate_stream(model, full, {"temperature": 0.3, "max_output_tokens": 2048})
