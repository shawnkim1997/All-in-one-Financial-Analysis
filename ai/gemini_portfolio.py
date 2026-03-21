"""
Gemini Vision — extract portfolio holdings from Trading 212 / IBKR screenshots.
Uses multimodal Gemini to OCR brokerage screenshots and return structured data.
"""
import json
import streamlit as st


def extract_portfolio_from_image(api_key: str, image_bytes: bytes, broker: str = "auto") -> list:
    """
    Send a brokerage screenshot to Gemini Vision and extract holdings.
    Returns list of dicts: [{"ticker": "AAPL", "name": "Apple Inc", "shares": 10, "avg_cost": 150.0}, ...]
    """
    import google.generativeai as genai
    from config.constants import GEMINI_MODEL

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = f"""You are a financial data extraction expert. The user has uploaded a screenshot from their **{broker}** brokerage account (Trading 212, IBKR, or similar).

Extract ALL stock/ETF holdings visible in the screenshot. For each holding, extract:
1. **ticker** — the stock ticker symbol (e.g., "AAPL", "MSFT"). If only the company name is visible, infer the most likely US ticker.
2. **name** — the full company/ETF name as shown
3. **shares** — number of shares held (decimal OK)
4. **avg_cost** — average purchase price per share (if visible, otherwise null)
5. **current_price** — current market price per share (if visible, otherwise null)

Return ONLY a valid JSON array. No explanation, no markdown. Example:
[
  {{"ticker": "AAPL", "name": "Apple Inc", "shares": 10.5, "avg_cost": 150.25, "current_price": 178.50}},
  {{"ticker": "MSFT", "name": "Microsoft Corp", "shares": 5, "avg_cost": 380.00, "current_price": 415.20}}
]

If you cannot extract any holdings, return an empty array: []
Important: Extract ALL visible rows, do not skip any."""

    import PIL.Image
    import io
    img = PIL.Image.open(io.BytesIO(image_bytes))

    try:
        response = model.generate_content(
            [prompt, img],
            generation_config={"temperature": 0.1, "max_output_tokens": 4096},
        )
        text = (response.text or "").strip()
        # Clean markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        holdings = json.loads(text)
        if not isinstance(holdings, list):
            return []
        # Normalize each holding
        cleaned = []
        for h in holdings:
            cleaned.append({
                "ticker": str(h.get("ticker", "")).upper().strip(),
                "name": str(h.get("name", "")),
                "shares": _safe_num(h.get("shares")),
                "avg_cost": _safe_num(h.get("avg_cost")),
                "current_price": _safe_num(h.get("current_price")),
            })
        return [c for c in cleaned if c["ticker"]]
    except json.JSONDecodeError:
        st.error("AI could not parse the screenshot. Please try a clearer image.")
        return []
    except Exception as e:
        err = str(e).lower()
        if "429" in err or "resource" in err:
            st.error("Gemini API rate limit. Please wait and retry.")
        else:
            st.error(f"Error extracting portfolio: {e}")
        return []


def _safe_num(val):
    """Convert to float safely, return None on failure."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
