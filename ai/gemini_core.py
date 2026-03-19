"""
Gemini model initialization, retry logic, streaming, text chunking, summarize/synthesize/forensic.
"""
import re
import time
from config.constants import GEMINI_MODEL, RATE_LIMIT_WAIT_SEC


def get_gemini_model(api_key: str):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)


def _is_rate_limit_error(e: Exception) -> bool:
    err_msg = str(e).lower()
    return "429" in err_msg or "resourcelimited" in err_msg or "resource exhausted" in err_msg or getattr(e, "code", None) == 429


def _generate_with_retry(model, content, config, max_retries: int = 3):
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            return model.generate_content(content, generation_config=config)
        except Exception as e:
            last_err = e
            if attempt < max_retries and _is_rate_limit_error(e):
                time.sleep(RATE_LIMIT_WAIT_SEC)
                continue
            raise
    raise last_err


def _generate_stream(model, content, config):
    """Yield text chunks from Gemini with stream=True. For use with st.write_stream()."""
    try:
        response = model.generate_content(content, generation_config=config, stream=True)
        for chunk in response:
            if hasattr(chunk, "text") and chunk.text:
                yield chunk.text
    except Exception:
        raise


def _split_into_chunks(text: str, max_chars: int = 22000, min_chunk: int = 5000) -> list:
    """Split text into sequential chunks without cutting mid-sentence when possible."""
    if not text or len(text) <= max_chars:
        return [text] if text and text.strip() else []
    chunks = []
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


def _gemini_summarize_segment(api_key: str, segment_text: str, ticker: str, segment_label: str) -> str:
    """Extract strategic shifts and hidden risks from one segment. No trimming."""
    model = get_gemini_model(api_key)
    prompt = f"""You are a senior equity analyst. The following is one segment of the 10-K for {ticker} (Item 1A Risk Factors and/or Item 7 MD&A).
Extract and list all significant: (1) strategic shifts or priorities, (2) hidden or material risks, (3) management tone cues. Use concise bullet points. Do not omit important details. Segment: {segment_label}."""
    full = f"""--- 10-K Segment ---\n\n{segment_text[:50000]}\n\n---\n\n{prompt}"""
    try:
        r = _generate_with_retry(model, full, {"temperature": 0.2, "max_output_tokens": 2048})
        return (r.text or "").strip()
    except Exception:
        return ""


def _gemini_synthesize_report(api_key: str, segment_summaries: list, ticker: str, sector: str, industry: str) -> str:
    """Synthesis call: turn segment summaries into Executive Insight Report."""
    model = get_gemini_model(api_key)
    combined = "\n\n---\n\n".join(segment_summaries)
    kpi_note = f" Sector: {sector}; Industry: {industry}. Include industry-specific KPIs if mentioned." if sector and sector != "N/A" else ""
    prompt = f"""You are a senior equity analyst. Use British English. Below are summarized insights from the full 10-K for {ticker} (Item 1A and Item 7). Create the final **Executive Insight Report** with these sections:

1. **Management's Tone (Sentiment)**: Overall tone and supporting evidence.
2. **Current Strategy & Priorities**: Key strategic focus, capital allocation, growth drivers.
3. **Major Hidden Risks**: The 3-4 most material risks investors might overlook.
4. **Forensic / Quality of Earnings**: Accounting caveats, one-offs, cash flow vs earnings. If none material, say so briefly.{kpi_note}

Use clear headings. Do not invent figures. Keep under 900 words."""
    full = f"""--- Segment Summaries ---\n\n{combined}\n\n---\n\n{prompt}"""
    try:
        r = _generate_with_retry(model, full, {"temperature": 0.3, "max_output_tokens": 4096})
        return (r.text or "").strip()
    except Exception:
        return ""


def _gemini_forensic_audit(api_key: str, item3: str, item9a: str, ticker: str) -> str:
    """Dedicated high-priority check: Material Weaknesses, lawsuits, off-balance-sheet from Item 3 and 9A."""
    model = get_gemini_model(api_key)
    combined = (item3 or "") + "\n\n---\n\n" + (item9a or "")
    if not combined.strip():
        return "No Item 3 / 9A text provided; skip forensic."
    prompt = f"""From the following 10-K excerpts for {ticker} (Item 3 Legal Proceedings and Item 9A Controls/Internal Control), list any:
- Material weaknesses in internal control
- Significant legal proceedings or litigation
- Off-balance-sheet or governance red flags
If none of the above, output exactly: "No material red flags or special issues detected in Item 3 and 9A."
Be concise (under 150 words)."""
    full = f"""--- Item 3 & 9A ---\n\n{combined[:30000]}\n\n---\n\n{prompt}"""
    try:
        r = _generate_with_retry(model, full, {"temperature": 0.1, "max_output_tokens": 512})
        return (r.text or "").strip()
    except Exception:
        return ""
