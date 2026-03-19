import json
import re
import streamlit as st
from utils.formatting import _safe_float
from data.sec_parser import smart_chunk, clean_text_for_llm
from ai.gemini_core import get_gemini_model, _generate_with_retry, _generate_stream, _gemini_forensic_audit
from config.constants import REQUIRED_FINANCIAL_KEYS


@st.cache_data(ttl=3600)
def get_sec_financials_llm(api_key: str, item8_text: str, ticker: str) -> dict:
    """Extract Current Year and Previous Year financial figures from 10-K Item 8 via Gemini. Returns dict with current_yr and previous_yr (each with 10 numeric fields). Cached by (api_key, item8_text, ticker)."""
    if not (api_key or "").strip() or not (item8_text or "").strip():
        return {}
    payload = smart_chunk((item8_text or "").strip(), max_chars=35000)
    model = get_gemini_model(api_key)
    prompt = f"""You are a financial analyst. Below is Item 8 (Financial Statements and Supplementary Data) from the latest 10-K for {ticker}.

Extract the following figures for the **Current Year** (most recent fiscal year) and **Previous Year** (prior fiscal year). Use the exact numbers from the financial statements. All monetary values in millions (e.g. 50000 for $50 billion). Shares in millions.

Return ONLY a valid JSON object, no other text. Use this exact structure:
{{
  "current_yr": {{
    "Revenue": <number>,
    "CostOfRevenue": <number>,
    "OperatingExpenses": <number>,
    "NetIncome": <number>,
    "TotalAssets": <number>,
    "CurrentAssets": <number>,
    "CurrentLiabilities": <number>,
    "LongTermDebt": <number>,
    "OperatingCashFlow": <number>,
    "SharesOutstanding": <number>
  }},
  "previous_yr": {{
    "Revenue": <number>,
    "CostOfRevenue": <number>,
    "OperatingExpenses": <number>,
    "NetIncome": <number>,
    "TotalAssets": <number>,
    "CurrentAssets": <number>,
    "CurrentLiabilities": <number>,
    "LongTermDebt": <number>,
    "OperatingCashFlow": <number>,
    "SharesOutstanding": <number>
  }}
}}

If a value is not found in the document, use 0 or a reasonable estimate and still include the key. Output nothing except this JSON."""

    full = f"""--- Item 8 (Financial Statements) ---\n\n{payload}\n\n---\n\n{prompt}"""
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
        for key in REQUIRED_FINANCIAL_KEYS:
            cur[key] = _safe_float(cur.get(key)) or 0
            prev[key] = _safe_float(prev.get(key)) or 0
        return {"current_yr": cur, "previous_yr": prev}
    except (json.JSONDecodeError, Exception):
        return {}


def get_gemini_item7_strategy(api_key: str, item7_text: str, ticker: str, sector: str, industry: str) -> str:
    """Item 7 only: business performance, strategic shifts, capital allocation."""
    if not (item7_text or "").strip():
        return "No Item 7 (MD&A) text available."
    model = get_gemini_model(api_key)
    text = smart_chunk(clean_text_for_llm(item7_text), max_chars=10000)
    sector_note = f" Sector: {sector}; Industry: {industry}." if sector and sector != "N/A" else ""
    prompt = f"""You are a senior equity analyst. Use British English. The text below is **Item 7 (Management's Discussion and Analysis)** from the latest 10-K for {ticker}.{sector_note}

Provide a concise **Management Strategy** report with these sections:

1. **Business performance**: Key revenue, margin, or segment highlights management emphasises.
2. **Strategic shifts**: Changes in priorities, growth drivers, or capital allocation (e.g. capex, M&A, buybacks).
3. **Capital allocation**: How management describes use of cash (dividends, debt paydown, R&D, acquisitions).

Use clear headings. Do not invent figures. Keep under 600 words. Focus only on narrative insights; ignore missing quantitative data.
Even if the source text is in another language (e.g. Korean or Japanese), analyse it and output your final report strictly in British English."""
    full = f"""--- Item 7 (MD&A) ---\n\n{text}\n\n---\n\n{prompt}"""
    try:
        r = _generate_with_retry(model, full, {"temperature": 0.3, "max_output_tokens": 2048})
        return (r.text or "").strip()
    except Exception:
        return ""


def get_gemini_item7_strategy_stream(api_key: str, item7_text: str, ticker: str, sector: str, industry: str):
    """Generator that yields MD&A strategy report chunks for real-time streaming (e.g. st.write_stream)."""
    if not (item7_text or "").strip():
        yield "No Item 7 (MD&A) text available."
        return
    model = get_gemini_model(api_key)
    text = smart_chunk(clean_text_for_llm(item7_text), max_chars=10000)
    sector_note = f" Sector: {sector}; Industry: {industry}." if sector and sector != "N/A" else ""
    prompt = f"""You are a senior equity analyst. Use British English. The text below is **Item 7 (Management's Discussion and Analysis)** from the latest 10-K for {ticker}.{sector_note}

Provide a concise **Management Strategy** report with these sections:

1. **Business performance**: Key revenue, margin, or segment highlights management emphasises.
2. **Strategic shifts**: Changes in priorities, growth drivers, or capital allocation (e.g. capex, M&A, buybacks).
3. **Capital allocation**: How management describes use of cash (dividends, debt paydown, R&D, acquisitions).

Use clear headings. Do not invent figures. Keep under 600 words. Focus only on narrative insights; ignore missing quantitative data.
Even if the source text is in another language (e.g. Korean or Japanese), analyse it and output your final report strictly in British English."""
    full = f"""--- Item 7 (MD&A) ---\n\n{text}\n\n---\n\n{prompt}"""
    config = {"temperature": 0.3, "max_output_tokens": 2048}
    yield from _generate_stream(model, full, config)


def get_gemini_item1a_risks(api_key: str, item1a_text: str, item3: str, item9a: str, ticker: str) -> str:
    """Item 1A only: legal, operational, market-related threats. Includes Forensic Audit (Item 3 & 9A) as safety check."""
    if not (item1a_text or "").strip():
        return "No Item 1A (Risk Factors) text available."
    model = get_gemini_model(api_key)
    text = smart_chunk(clean_text_for_llm(item1a_text), max_chars=10000)
    prompt = f"""You are a senior equity analyst. Use British English. The text below is **Item 1A (Risk Factors)** from the latest 10-K for {ticker}.

Provide a concise **Risk Factors** report with these sections:

1. **Legal & regulatory risks**: Litigation, regulatory changes, compliance.
2. **Operational risks**: Supply chain, key person, technology, execution.
3. **Market & competitive risks**: Demand, competition, macro, currency.

Use clear headings. Do not invent figures. Keep under 500 words. Focus only on narrative insights; ignore missing quantitative data.
Even if the source text is in another language (e.g. Korean or Japanese), analyse it and output your final report strictly in British English."""
    full = f"""--- Item 1A (Risk Factors) ---\n\n{text}\n\n---\n\n{prompt}"""
    try:
        report = _generate_with_retry(model, full, {"temperature": 0.3, "max_output_tokens": 2048})
        risks = (report.text or "").strip()
    except Exception:
        risks = ""
    forensic = _gemini_forensic_audit(api_key, item3 or "", item9a or "", ticker)
    return (risks or "") + "\n\n---\n\n**Forensic Audit (Item 3 & 9A)**\n\n" + (forensic or "")


def get_gemini_item1a_risks_stream(api_key: str, item1a_text: str, ticker: str):
    """Generator that yields Risk Factors report chunks for real-time streaming. Caller appends Forensic (Item 3 & 9A) after stream."""
    if not (item1a_text or "").strip():
        yield "No Item 1A (Risk Factors) text available."
        return
    model = get_gemini_model(api_key)
    text = smart_chunk(clean_text_for_llm(item1a_text), max_chars=10000)
    prompt = f"""You are a senior equity analyst. Use British English. The text below is **Item 1A (Risk Factors)** from the latest 10-K for {ticker}.

Provide a concise **Risk Factors** report with these sections:

1. **Legal & regulatory risks**: Litigation, regulatory changes, compliance.
2. **Operational risks**: Supply chain, key person, technology, execution.
3. **Market & competitive risks**: Demand, competition, macro, currency.

Use clear headings. Do not invent figures. Keep under 500 words. Focus only on narrative insights; ignore missing quantitative data.
Even if the source text is in another language (e.g. Korean or Japanese), analyse it and output your final report strictly in British English."""
    full = f"""--- Item 1A (Risk Factors) ---\n\n{text}\n\n---\n\n{prompt}"""
    config = {"temperature": 0.3, "max_output_tokens": 2048}
    yield from _generate_stream(model, full, config)
