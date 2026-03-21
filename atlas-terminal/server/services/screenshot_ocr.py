"""Portfolio screenshot OCR using Gemini Vision.

Analyses screenshots from Trading 212 or Interactive Brokers (IBKR) portfolio
views and extracts structured position data (ticker, quantity, market value,
gain/loss) via the Gemini multimodal API.
"""

import json
import re
from typing import Any, Dict, List, Optional


def _get_vision_model(api_key: str) -> Any:
    """Configure Gemini and return a multimodal model."""
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def _build_prompt() -> str:
    """Return the extraction prompt for portfolio screenshots."""
    return """You are a financial data extraction assistant.

Analyse this portfolio screenshot from a brokerage app (Trading 212,
Interactive Brokers, or similar).

Extract every visible position and return ONLY a valid JSON object with
this structure:

{
  "broker": "Trading 212" | "IBKR" | "Unknown",
  "currency": "USD" | "GBP" | "EUR" | ...,
  "positions": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "quantity": 10.5,
      "avg_price": 150.00,
      "current_price": 175.00,
      "market_value": 1837.50,
      "gain_loss": 262.50,
      "gain_loss_pct": 16.67
    }
  ],
  "total_value": 50000.00,
  "total_gain_loss": 5000.00
}

Rules:
- Use null for any field you cannot read.
- quantity may be fractional (e.g. 0.125 shares).
- Monetary values should be plain numbers, no currency symbols.
- If the screenshot is not a portfolio view, return {"error": "Not a portfolio screenshot"}.
- Output ONLY the JSON object, nothing else.
"""


def analyze_portfolio_screenshot(
    api_key: str,
    image_bytes: bytes,
) -> Dict[str, Any]:
    """Extract portfolio positions from a brokerage screenshot.

    Uses Gemini Vision (multimodal) to read the image and return
    structured position data.

    Parameters
    ----------
    api_key:
        Google Gemini API key.
    image_bytes:
        Raw bytes of the screenshot image (PNG, JPEG, etc.).

    Returns
    -------
    dict
        Parsed portfolio data with ``broker``, ``currency``,
        ``positions`` (list), ``total_value``, and ``total_gain_loss``.
        On error, returns ``{"error": "<description>"}``.
    """
    if not api_key or not api_key.strip():
        return {"error": "API key is required."}
    if not image_bytes:
        return {"error": "No image data provided."}

    try:
        model = _get_vision_model(api_key)
    except Exception as e:
        return {"error": f"Failed to initialise Gemini Vision: {e}"}

    prompt = _build_prompt()

    # Build multimodal content: image + text prompt
    try:
        import google.generativeai as genai

        # Detect MIME type from magic bytes
        mime_type = "image/png"
        if image_bytes[:3] == b"\xff\xd8\xff":
            mime_type = "image/jpeg"
        elif image_bytes[:4] == b"\x89PNG":
            mime_type = "image/png"
        elif image_bytes[:4] == b"RIFF":
            mime_type = "image/webp"

        image_part = {"mime_type": mime_type, "data": image_bytes}
        response = model.generate_content(
            [image_part, prompt],
            generation_config={"temperature": 0.0, "max_output_tokens": 4096},
        )

        raw = (response.text or "").strip()
        if not raw:
            return {"error": "Gemini returned an empty response."}

        # Strip markdown code fences if present
        raw = re.sub(r"^```\s*json\s*", "", raw)
        raw = re.sub(r"^```\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
        raw = raw.strip()

        result: Dict[str, Any] = json.loads(raw)

        # Validate structure
        if "error" in result:
            return result
        if "positions" not in result:
            return {"error": "Response missing 'positions' key.", "raw": raw}

        # Coerce numeric fields
        for pos in result.get("positions", []):
            for key in ("quantity", "avg_price", "current_price", "market_value", "gain_loss", "gain_loss_pct"):
                val = pos.get(key)
                if val is not None:
                    try:
                        pos[key] = float(val)
                    except (TypeError, ValueError):
                        pos[key] = None

        return result

    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON from Gemini response.", "raw": raw}
    except Exception as e:
        return {"error": f"Screenshot analysis failed: {e}"}
