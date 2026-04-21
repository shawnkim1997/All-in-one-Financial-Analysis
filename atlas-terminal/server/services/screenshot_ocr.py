"""Portfolio OCR with smart reverse-engineering against live market prices."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Optional

import yfinance as yf
from server.services.exchange_resolver import resolve_exchange_option, resolve_ticker_with_exchange

SCREENSHOT_OCR_PROMPT = """
Analyze this screenshot of a stock trading app portfolio (Trading 212, IBKR, Webull, etc).

CRITICAL INSTRUCTIONS:
- Extract ALL positions visible in the image. There are likely 5-15 positions.
- Do NOT stop after the first position. Keep going until every position is captured.
- You MUST extract ALL positions visible in the screenshot.
- If you see 8 positions in the image, you MUST return exactly 8 objects in the positions array.
- The account currency shown at the top (£, $, €) may differ from individual stock currencies.

For EACH position, extract:
1. ticker: Stock ticker symbol exactly as shown (e.g., "IREN", "NVDA", "SMSN")
2. name: Company name
3. displayed_value: The monetary value shown (number only, no currency symbol)
4. displayed_currency: Currency symbol next to the value (£, $, €, ₩, ¥)
5. weight_pct: Portfolio weight % if shown (e.g., 28.66)
6. gain_loss_pct: P&L percentage if shown (e.g., -16.27 or +8.80)
7. gain_loss_amount: P&L monetary amount (number only)
8. shares: Number of shares if visible (preserve ALL decimals)
9. avg_price: Average purchase price if visible (number only)
10. avg_price_currency: Currency of avg price

ALSO extract portfolio summary from the top of the screen:
- total_value: Total portfolio value (number only)
- total_currency: Currency symbol (£, $, €)
- cost_basis: Cost basis if shown (number only)
- unrealised_pnl: Unrealised P&L (number only)
- unrealised_pnl_pct: P&L percentage

Return ONLY valid JSON, no other text.
"""

def _norm_currency(sym: str | None, default: str = "USD") -> str:
    s = (sym or "").strip().upper()
    mapping = {"£": "GBP", "$": "USD", "€": "EUR", "₩": "KRW", "¥": "JPY"}
    return mapping.get(s, s or default)


def _resolve_ticker(t212_ticker: str) -> str:
    return resolve_ticker_with_exchange(t212_ticker, None)


def _get_realtime_price(ticker: str) -> Optional[dict]:
    try:
        yf_ticker = _resolve_ticker(ticker)
        t = yf.Ticker(yf_ticker)
        info = t.info or {}
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        currency = (info.get("currency") or "USD").upper()
        if price is None:
            fast = getattr(t, "fast_info", None)
            if fast:
                price = getattr(fast, "last_price", None)
        if price is None:
            hist = t.history(period="1d")
            if hist is not None and not hist.empty:
                price = float(hist["Close"].iloc[-1])
        if price is None:
            return None
        return {"price": float(price), "currency": currency, "yf_ticker": yf_ticker}
    except Exception:
        return None


def _get_fx_rate(from_currency: str, to_currency: str) -> float:
    f = _norm_currency(from_currency)
    t = _norm_currency(to_currency)
    if f == t:
        return 1.0
    try:
        pair = f"{f}{t}=X"
        hist = yf.Ticker(pair).history(period="1d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
        rev = f"{t}{f}=X"
        hist2 = yf.Ticker(rev).history(period="1d")
        if hist2 is not None and not hist2.empty:
            return 1.0 / float(hist2["Close"].iloc[-1])
    except Exception:
        pass
    fallback = {
        ("GBP", "USD"): 1.27, ("USD", "GBP"): 0.79,
        ("EUR", "USD"): 1.08, ("USD", "EUR"): 0.93,
        ("USD", "KRW"): 1370.0, ("KRW", "USD"): 0.00073,
        ("USD", "JPY"): 149.5, ("JPY", "USD"): 0.0067,
    }
    return fallback.get((f, t), 1.0)


def _preferred_stock_currency(pos: dict) -> str | None:
    """Use stock-level currency hints only; account/display value currency can differ."""
    avg_currency = _norm_currency(pos.get("avg_price_currency"), "")
    return avg_currency or None


def reverse_engineer_positions(ocr_result: dict, exchange_overrides: dict[str, str] | None = None) -> list[dict]:
    account_currency = _norm_currency(ocr_result.get("account_currency"), "USD")
    out: list[dict] = []
    for pos in ocr_result.get("positions", []) or []:
        ticker = (pos.get("ticker") or "").upper().strip()
        if not ticker:
            continue
        selected_exchange = (exchange_overrides or {}).get(ticker)
        exchange_option = resolve_exchange_option(
            ticker,
            selected_exchange,
            preferred_currency=_preferred_stock_currency(pos) if not selected_exchange else None,
        )
        resolved_exchange = (exchange_option or {}).get("exchange") or selected_exchange or ""
        yf_ticker = resolve_ticker_with_exchange(
            ticker,
            selected_exchange,
            preferred_currency=_preferred_stock_currency(pos) if not selected_exchange else None,
        )
        mkt = _get_realtime_price(yf_ticker)
        if not mkt:
            out.append({
                "ticker": ticker,
                "name": pos.get("name") or ticker,
                "quantity": pos.get("shares"),
                "avg_price": pos.get("avg_price"),
                "avg_price_currency": _norm_currency(pos.get("avg_price_currency"), "USD"),
                "current_price": None,
                "stock_currency": "USD",
                "account_currency": account_currency,
                "current_value_account": pos.get("displayed_value"),
                "pnl_pct": pos.get("gain_loss_pct"),
                "confidence": "low",
                "method": "ocr_only",
                "yf_ticker": yf_ticker,
                "exchange": resolved_exchange,
            })
            continue

        stock_price = float(mkt["price"])
        stock_currency = _norm_currency(mkt["currency"], "USD")
        shares = pos.get("shares")
        confidence = "high"
        method = "ocr_shares"

        if not shares:
            displayed_value = pos.get("displayed_value")
            displayed_currency = _norm_currency(pos.get("displayed_currency"), account_currency)
            if displayed_value and float(displayed_value) > 0:
                v_stock = float(displayed_value) * _get_fx_rate(displayed_currency, stock_currency)
                shares = v_stock / stock_price if stock_price > 0 else None
                confidence = "medium"
                method = "reverse_from_value"
            else:
                shares = None
                confidence = "low"
                method = "unknown"

        avg_price = pos.get("avg_price")
        avg_currency = _norm_currency(pos.get("avg_price_currency"), stock_currency)
        avg_price_stock = None
        avg_method = "ocr_avg"
        if avg_price:
            avg_price_stock = float(avg_price) * _get_fx_rate(avg_currency, stock_currency)
        else:
            gain_loss_pct = pos.get("gain_loss_pct")
            gain_loss_amount = pos.get("gain_loss_amount")
            displayed_value = pos.get("displayed_value")
            displayed_currency = _norm_currency(pos.get("displayed_currency"), account_currency)

            # Method 1: reverse from PnL %
            try:
                if gain_loss_pct is not None and stock_price is not None:
                    gl_pct = float(gain_loss_pct)
                    denom = 1 + (gl_pct / 100.0)
                    if abs(denom) > 1e-9:
                        avg_price_stock = stock_price / denom
                        avg_method = "reverse_from_pnl_pct"
            except Exception:
                avg_price_stock = None

            # Method 2: reverse from displayed value and pnl amount
            if avg_price_stock is None:
                try:
                    if gain_loss_amount is not None and displayed_value is not None and shares and float(shares) > 0:
                        cost_basis_display = float(displayed_value) - float(gain_loss_amount)
                        fx = _get_fx_rate(displayed_currency, stock_currency)
                        cost_basis_stock = cost_basis_display * fx
                        avg_price_stock = cost_basis_stock / float(shares)
                        avg_method = "reverse_from_pnl_amount"
                except Exception:
                    avg_price_stock = None

            # Method 3: fallback to current price
            if avg_price_stock is None:
                avg_price_stock = stock_price
                avg_method = "fallback_current_price"

        if shares and pos.get("displayed_value"):
            displayed = float(pos["displayed_value"])
            displayed_currency = _norm_currency(pos.get("displayed_currency"), account_currency)
            calc_value = float(shares) * stock_price * _get_fx_rate(stock_currency, displayed_currency)
            err = abs(calc_value - displayed) / displayed * 100 if displayed > 0 else 999
            if err > 10 and stock_price > 0:
                shares = displayed * _get_fx_rate(displayed_currency, stock_currency) / stock_price
                confidence = "medium"
                method = "reverse_recalculated"

        total_pnl = None
        pnl_pct = pos.get("gain_loss_pct")
        if shares and avg_price_stock and stock_price:
            pnl_per_share = stock_price - avg_price_stock
            total_pnl = pnl_per_share * float(shares)
            pnl_pct = (pnl_per_share / avg_price_stock) * 100 if avg_price_stock > 0 else None

        cur_val = None
        if shares:
            cur_val = float(shares) * stock_price * _get_fx_rate(stock_currency, account_currency)

        # If avg is reconstructed and shares are available, promote confidence.
        if confidence == "medium" and avg_method in {"reverse_from_pnl_pct", "reverse_from_pnl_amount"} and shares:
            confidence = "high"

        out.append({
            "ticker": ticker,
            "name": pos.get("name") or ticker,
            "quantity": round(float(shares), 6) if shares else None,
            "avg_price": round(float(avg_price_stock), 4) if avg_price_stock is not None else avg_price,
            "avg_price_currency": stock_currency,
            "current_price": round(stock_price, 2),
            "stock_currency": stock_currency,
            "account_currency": account_currency,
            "current_value_account": round(cur_val, 2) if cur_val is not None else None,
            "total_pnl": round(float(total_pnl), 2) if total_pnl is not None else None,
            "pnl_pct": round(float(pnl_pct), 2) if pnl_pct is not None else None,
            "weight_pct": pos.get("weight_pct"),
            "confidence": confidence,
            "method": method,
            "avg_method": avg_method,
            "yf_ticker": yf_ticker,
            "exchange": resolved_exchange,
        })
    return out


def _detect_mime(image_bytes: bytes) -> str:
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_bytes[:4] == b"RIFF":
        return "image/webp"
    return "image/png"


def _parse_llm_json(text: str) -> dict:
    raw = (text or "").strip()
    raw = re.sub(r"^```json\s*", "", raw, flags=re.I)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw.strip())


async def process_portfolio_screenshot(api_key: str, image_bytes: bytes) -> dict:
    if not api_key or not api_key.strip():
        return {"error": "API key is required."}
    if not image_bytes:
        return {"error": "No image data provided."}

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        image_part = {"mime_type": _detect_mime(image_bytes), "data": image_bytes}
        response = await asyncio.to_thread(
            model.generate_content,
            [image_part, SCREENSHOT_OCR_PROMPT],
            generation_config={"temperature": 0.0, "max_output_tokens": 8192},
        )
        parsed = _parse_llm_json(response.text or "")
    except json.JSONDecodeError:
        return {"error": "Failed to parse OCR result."}
    except Exception as e:
        return {"error": f"OCR model call failed: {e}"}

    enriched = reverse_engineer_positions(parsed)
    warnings = []
    for p in enriched:
        if p.get("confidence") == "low":
            warnings.append(f"{p.get('ticker')}: Low confidence (market verify failed)")
        if p.get("method") == "reverse_recalculated":
            warnings.append(f"{p.get('ticker')}: Quantity recalculated due to >10% mismatch")

    return {
        "account_currency": _norm_currency(parsed.get("account_currency"), "USD"),
        "total_value": {
            "amount": parsed.get("total_value"),
            "currency": _norm_currency(parsed.get("account_currency"), "USD"),
        },
        "positions": enriched,
        "warnings": warnings,
        "raw_ocr": parsed,
    }
