from typing import Optional
import streamlit as st
from data.sec_parser import smart_chunk, clean_text_for_llm
from ai.gemini_core import (
    get_gemini_model, _generate_with_retry, _is_rate_limit_error,
    _split_into_chunks, _gemini_summarize_segment, _gemini_synthesize_report, _gemini_forensic_audit,
)


def get_mda_chunked_insights(
    api_key: str, sections: dict, ticker: str, sector: str, industry: str, progress_callback=None
) -> str:
    """Full-text analysis: chunk 1A+7, summarize each segment, synthesize report; then append forensic (Item 3, 9A). progress_callback(step: str) optional."""
    def _progress(msg):
        if progress_callback:
            progress_callback(msg)
    combined = (sections.get("item1a") or "") + "\n\n---\n\n" + (sections.get("item7") or "")
    combined = combined.strip()
    if not combined:
        return "No 10-K text available to analyse."
    chunks = _split_into_chunks(combined, max_chars=22000)
    if not chunks:
        return "No content extracted."
    summaries = []
    n = len(chunks)
    for i, ch in enumerate(chunks):
        _progress(f"Analyzing Segment {i+1}/{n}...")
        summary = _gemini_summarize_segment(api_key, ch, ticker, f"Segment {i+1}/{n}")
        if summary:
            summaries.append(summary)
    if not summaries:
        return "Segment analysis produced no summaries."
    _progress("Synthesizing final report...")
    report = _gemini_synthesize_report(api_key, summaries, ticker, sector or "N/A", industry or "N/A")
    _progress("Running forensic audit (Item 3 & 9A)...")
    forensic = _gemini_forensic_audit(api_key, sections.get("item3") or "", sections.get("item9a") or "", ticker)
    return (report or "") + "\n\n---\n\n**Forensic (Item 3 & 9A)**\n\n" + (forensic or "")


def get_mda_insights(api_key: str, item1a_text: str, item7_text: str, ticker: str) -> str:
    """Send Item 1A + Item 7 to Gemini. Analyse: 1) Management's Tone (Sentiment), 2) Key Strategic Shifts, 3) Major Hidden Risks."""
    model = get_gemini_model(api_key)
    combined = []
    if item1a_text:
        combined.append(clean_text_for_llm(item1a_text))
    if item7_text:
        combined.append(clean_text_for_llm(item7_text))
    combined_text = "\n\n---\n\n".join(combined)
    combined_text = smart_chunk(combined_text, max_chars=22000)

    user_prompt = f"""You are a senior equity analyst. Use British English.

The text below is from the 10-K for {ticker}: **Item 1A (Risk Factors)** and **Item 7 (Management's Discussion and Analysis)**. HTML has been stripped; analyse only the substance.

Provide a concise report with three sections:

1. **Management's Tone (Sentiment)**: Is the overall tone positive, cautious, or negative? Quote 1–2 short phrases that support your view.

2. **Key Strategic Shifts**: What strategic priorities or shifts does management emphasise (e.g. capital allocation, growth drivers, new segments)? Be specific.

3. **Major Hidden Risks**: From both Risk Factors and MD&A, what are the 3–4 most material risks that an investor might overlook? Cite the document.

Use clear headings. Do not invent figures. Keep the response focused and under 800 words."""

    full_content = f"""--- 10-K Excerpt (Item 1A + Item 7) ---\n\n{combined_text}\n\n---\n\n{user_prompt}"""

    try:
        response = _generate_with_retry(
            model, full_content, {"temperature": 0.3, "max_output_tokens": 4096}
        )
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
    """Comparative analysis: if item7_3y_ago provided, compare MD&As over 3 years; else single-year. Sector-aware: extract industry-specific Non-GAAP KPIs."""
    model = get_gemini_model(api_key)
    sector_label = (sector or "N/A").strip()
    industry_label = (industry or "N/A").strip()
    kpi_instruction = (
        f" Given that this company is in the **{sector_label}** sector"
        + (f" (industry: {industry_label})" if industry_label != "N/A" else "")
        + ", meticulously scan the MD&A to find and extract **industry-specific Non-GAAP KPIs** "
        "(e.g. Same-Store Sales Growth for Retail, ARR/NDR for Software, DAU/MAU for Tech). Present these hidden KPIs in a **clean markdown table** with columns such as KPI name, value, and period if stated."
    )
    if not item7_3y_ago or not item7_3y_ago.strip():
        combined = []
        if item1a_text:
            combined.append(clean_text_for_llm(item1a_text))
        if item7_latest:
            combined.append(clean_text_for_llm(item7_latest))
        combined_text = "\n\n---\n\n".join(combined)
        combined_text = smart_chunk(combined_text, max_chars=22000)
        user_prompt = f"""You are a senior equity analyst. Use British English.
The text below is from the **latest 10-K only** for {ticker}: **Item 1A (Risk Factors)** and **Item 7 (MD&A)**. Provide a focused deep-dive report:

1. **Management's Tone (Sentiment)**: Overall tone and 1–2 supporting phrases.
2. **Current Strategy & Priorities**: Key strategic focus, capital allocation, growth drivers from this filing only.
3. **Major Hidden Risks**: From Item 1A and MD&A, the 3–4 most material risks investors might overlook.
4. **Forensic / Quality of Earnings**: Any red flags in MD&A (accounting caveats, one-offs, cash flow vs earnings, segment disclosure). If none material, say so briefly.{kpi_instruction}
**Token-saving (Item 3 / 9A):** If no material weaknesses, major lawsuits, or off-balance-sheet red flags, output exactly: "\u2705 No material red flags or special issues detected in Item 3 and 9A."
Use clear headings. Under 800 words."""
        full_content = f"""--- 10-K Excerpt (Latest Year) ---\n\n{combined_text}\n\n---\n\n{user_prompt}"""
    else:
        latest_clean = smart_chunk(clean_text_for_llm(item7_latest), max_chars=12000)
        past_clean = smart_chunk(clean_text_for_llm(item7_3y_ago), max_chars=12000)
        user_prompt = f"""You are a senior equity analyst. Use British English.
Below are **Item 7 (Management's Discussion and Analysis)** from the 10-K for {ticker}: **LATEST YEAR** and **THREE YEARS AGO**. Perform a **Comparative Analysis**.

1. **Core strategy**: What has changed in the company's stated strategy, priorities, or capital allocation between then and now?
2. **Emerging risks**: What new risks appear in the latest MD&A that were absent or less prominent 3 years ago?
3. **Management's tone**: How has the overall tone (confidence, caution, optimism) shifted? Quote 1–2 phrases from each period if relevant.
4. **Industry-specific KPIs**:{kpi_instruction}
5. **Item 3 (Legal) & Item 9A (Internal Controls):** You must save output tokens. If there are no material weaknesses, no massive lawsuits, and no major off-balance sheet red flags, DO NOT generate a long explanation. Simply output exactly: "\u2705 No material red flags or special issues detected in Item 3 and 9A." and move on.

Use clear headings. Do not invent figures. Keep the response focused and under 900 words."""
        full_content = f"""--- MD&A LATEST YEAR ---\n\n{latest_clean}\n\n--- MD&A THREE YEARS AGO ---\n\n{past_clean}\n\n---\n\n{user_prompt}"""
    try:
        response = _generate_with_retry(
            model, full_content, {"temperature": 0.3, "max_output_tokens": 4096}
        )
    except Exception as api_err:
        if _is_rate_limit_error(api_err):
            raise RuntimeError("Rate limit exceeded. Please try again in a few minutes.") from api_err
        raise
    if not response or not response.text:
        return "No analysis generated."
    return response.text.strip()


def _run_mda_analysis_background(ticker: str, api_key: str, sec_email: str) -> None:
    """Run download + Gemini in background (latest 10-K only for speed). Store result or error in st.session_state."""
    try:
        from data.sec_downloader import download_and_extract_item7_and_1a
        from data.fundamentals import get_sector_industry
        _, item1a, item7_latest = download_and_extract_item7_and_1a(ticker, sec_email)
        si = get_sector_industry(ticker)
        analysis = get_mda_comparative_insights(
            api_key, item1a or "", item7_latest or "", None, ticker,
            sector=si.get("sector"), industry=si.get("industry"),
        )
        st.session_state["mda_analysis_result"] = analysis
        st.session_state["mda_analysis_excerpt"] = ((item1a or "") + "\n\n---\n\n" + (item7_latest or ""))[:12000]
        st.session_state["mda_analysis_error"] = None
    except Exception as e:
        st.session_state["mda_analysis_error"] = str(e)
        st.session_state["mda_analysis_result"] = None
        st.session_state["mda_analysis_excerpt"] = None
    finally:
        st.session_state["mda_analysis_running"] = False
        st.session_state["mda_analysis_done"] = True
        st.session_state["mda_analysis_ticker"] = ticker


def get_industry_outlook(api_key: str, industry_name: str, tickers: list) -> str:
    """Gemini: Wall Street macro analyst-style Industry Outlook for the selected sector (12\u201318 months)."""
    model = get_gemini_model(api_key)
    ticker_list_str = ", ".join(str(t).upper() for t in tickers if t)
    user_prompt = f"""Act as an elite Wall Street macro analyst. Provide a concise **Industry Outlook** report for the **{industry_name}** sector, which includes leading companies like {ticker_list_str}.

Focus on:
1. **Macro trends** affecting this industry over the next 12\u201318 months.
2. **Major growth drivers** (e.g., AI, interest rates, consumer spending, regulation).
3. **Key headwinds or regulatory risks** that could impact valuations or growth.

Use clear headings. Be specific but concise. Keep the response under 600 words."""
    full_content = user_prompt
    try:
        response = _generate_with_retry(
            model, full_content, {"temperature": 0.4, "max_output_tokens": 2048}
        )
    except Exception as api_err:
        if _is_rate_limit_error(api_err):
            raise RuntimeError("Rate limit exceeded. Please try again in a few minutes.") from api_err
        raise
    if not response or not response.text:
        return "No industry outlook generated."
    return response.text.strip()
