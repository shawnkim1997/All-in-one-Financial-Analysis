"""High-level Gemini analysis orchestrators.

Contains the composite analysis functions that combine multiple Gemini
calls (chunked insights, comparative MD&A, industry outlook). These build
on the primitives in :mod:`server.services.gemini_service`.
"""

from typing import Any, Callable, Dict, Optional

from server.services.gemini_service import (
    _gemini_forensic_audit,
    _gemini_summarize_segment,
    _gemini_synthesize_report,
    _generate_with_retry,
    _is_rate_limit_error,
    get_gemini_model,
)
from server.services.text_chunker import clean_text_for_llm, smart_chunk, _split_into_chunks


def get_mda_chunked_insights(
    api_key: str,
    sections: Dict[str, str],
    ticker: str,
    sector: str,
    industry: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> str:
    """Full-text analysis: chunk 1A+7, summarise each, synthesise, then append forensic.

    Parameters
    ----------
    api_key:
        Google Gemini API key.
    sections:
        Dict with keys ``item1a``, ``item7``, ``item3``, ``item9a``.
    ticker:
        Stock ticker symbol.
    sector / industry:
        Used for sector-aware KPI extraction.
    progress_callback:
        Optional ``fn(msg: str)`` called with status updates.

    Returns
    -------
    str
        Markdown-formatted Executive Insight Report.
    """
    def _progress(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    combined = (sections.get("item1a") or "") + "\n\n---\n\n" + (sections.get("item7") or "")
    combined = combined.strip()
    if not combined:
        return "No 10-K text available to analyse."

    chunks = _split_into_chunks(combined, max_chars=22_000)
    if not chunks:
        return "No content extracted."

    summaries = []
    n = len(chunks)
    for i, ch in enumerate(chunks):
        _progress(f"Analyzing Segment {i + 1}/{n}...")
        summary = _gemini_summarize_segment(api_key, ch, ticker, f"Segment {i + 1}/{n}")
        if summary:
            summaries.append(summary)

    if not summaries:
        return "Segment analysis produced no summaries."

    _progress("Synthesizing final report...")
    report = _gemini_synthesize_report(api_key, summaries, ticker, sector or "N/A", industry or "N/A")

    _progress("Running forensic audit (Item 3 & 9A)...")
    forensic = _gemini_forensic_audit(api_key, sections.get("item3") or "", sections.get("item9a") or "", ticker)

    return (report or "") + "\n\n---\n\n**Forensic (Item 3 & 9A)**\n\n" + (forensic or "")


def get_mda_insights(
    api_key: str,
    item1a_text: str,
    item7_text: str,
    ticker: str,
) -> str:
    """Single-shot analysis of Item 1A + Item 7 (tone, strategy, risks)."""
    model = get_gemini_model(api_key)
    combined = []
    if item1a_text:
        combined.append(clean_text_for_llm(item1a_text))
    if item7_text:
        combined.append(clean_text_for_llm(item7_text))
    combined_text = smart_chunk("\n\n---\n\n".join(combined), max_chars=22_000)

    prompt = (
        f"You are a senior equity analyst. Use British English.\n\n"
        f"The text below is from the 10-K for {ticker}: **Item 1A** and **Item 7**.\n\n"
        "Provide a concise report:\n"
        "1. **Management's Tone (Sentiment)**\n"
        "2. **Key Strategic Shifts**\n"
        "3. **Major Hidden Risks**\n\n"
        "Use clear headings. Under 800 words."
    )
    full = f"--- 10-K Excerpt ---\n\n{combined_text}\n\n---\n\n{prompt}"
    try:
        response = _generate_with_retry(model, full, {"temperature": 0.3, "max_output_tokens": 4096})
    except Exception as api_err:
        if _is_rate_limit_error(api_err):
            raise RuntimeError("Rate limit exceeded. Please try again in a few minutes.") from api_err
        raise
    if not response or not response.text:
        return "No analysis generated."
    return response.text.strip()


def get_mda_comparative_insights(
    api_key: str,
    item1a_text: str,
    item7_latest: str,
    item7_3y_ago: Optional[str],
    ticker: str,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
) -> str:
    """Comparative or single-year MD&A deep-dive with sector-aware KPIs."""
    model = get_gemini_model(api_key)
    sector_label = (sector or "N/A").strip()
    industry_label = (industry or "N/A").strip()
    kpi_instruction = (
        f" Given that this company is in the **{sector_label}** sector"
        + (f" (industry: {industry_label})" if industry_label != "N/A" else "")
        + ", extract **industry-specific Non-GAAP KPIs** in a markdown table."
    )

    if not item7_3y_ago or not item7_3y_ago.strip():
        combined = []
        if item1a_text:
            combined.append(clean_text_for_llm(item1a_text))
        if item7_latest:
            combined.append(clean_text_for_llm(item7_latest))
        combined_text = smart_chunk("\n\n---\n\n".join(combined), max_chars=22_000)
        prompt = (
            f"You are a senior equity analyst. Use British English.\n"
            f"Latest 10-K only for {ticker} (Item 1A + Item 7). Provide:\n"
            "1. **Management's Tone**\n2. **Current Strategy & Priorities**\n"
            "3. **Major Hidden Risks**\n4. **Forensic / Quality of Earnings**\n"
            f"{kpi_instruction}\nUnder 800 words."
        )
        full = f"--- 10-K Excerpt (Latest Year) ---\n\n{combined_text}\n\n---\n\n{prompt}"
    else:
        latest_clean = smart_chunk(clean_text_for_llm(item7_latest), max_chars=12_000)
        past_clean = smart_chunk(clean_text_for_llm(item7_3y_ago), max_chars=12_000)
        prompt = (
            f"You are a senior equity analyst. Use British English.\n"
            f"Below are Item 7 from the 10-K for {ticker}: LATEST and THREE YEARS AGO.\n"
            "1. **Core strategy** changes\n2. **Emerging risks**\n"
            "3. **Management's tone** shift\n4. **Industry-specific KPIs**\n"
            f"{kpi_instruction}\nUnder 900 words."
        )
        full = (
            f"--- MD&A LATEST YEAR ---\n\n{latest_clean}\n\n"
            f"--- MD&A THREE YEARS AGO ---\n\n{past_clean}\n\n---\n\n{prompt}"
        )

    try:
        response = _generate_with_retry(model, full, {"temperature": 0.3, "max_output_tokens": 4096})
    except Exception as api_err:
        if _is_rate_limit_error(api_err):
            raise RuntimeError("Rate limit exceeded. Please try again in a few minutes.") from api_err
        raise
    if not response or not response.text:
        return "No analysis generated."
    return response.text.strip()


def get_industry_outlook(
    api_key: str,
    industry_name: str,
    tickers: list,
) -> str:
    """Generate a Wall Street macro-analyst-style Industry Outlook (12-18 months)."""
    model = get_gemini_model(api_key)
    ticker_list_str = ", ".join(str(t).upper() for t in tickers if t)
    prompt = (
        f"Act as an elite Wall Street macro analyst. Provide a concise "
        f"**Industry Outlook** for the **{industry_name}** sector, "
        f"which includes companies like {ticker_list_str}.\n\n"
        "Focus on:\n"
        "1. **Macro trends** (next 12-18 months)\n"
        "2. **Major growth drivers**\n"
        "3. **Key headwinds or regulatory risks**\n\n"
        "Use clear headings. Under 600 words."
    )
    try:
        response = _generate_with_retry(model, prompt, {"temperature": 0.4, "max_output_tokens": 2048})
    except Exception as api_err:
        if _is_rate_limit_error(api_err):
            raise RuntimeError("Rate limit exceeded. Please try again in a few minutes.") from api_err
        raise
    if not response or not response.text:
        return "No industry outlook generated."
    return response.text.strip()
