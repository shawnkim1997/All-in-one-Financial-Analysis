"""Tax simulation endpoints.

These endpoints are educational calculators for personal planning.  They are
not tax advice and intentionally keep assumptions explicit in the payload.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from server.routers.portfolio import _get_current_quote, _load_positions

router = APIRouter()

UK_CGT_ALLOWANCE_2026 = 3000.0
UK_CGT_BASIC_RATE = 0.10
UK_CGT_HIGHER_RATE = 0.20

_FX_TO_GBP = {
    "GBP": 1.0,
    "GBX": 0.01,
    "USD": 0.80,
    "EUR": 0.86,
    "DKK": 0.115,
    "JPY": 0.0053,
    "KRW": 0.00058,
    "CHF": 0.90,
    "CAD": 0.58,
    "AUD": 0.52,
}


def _fx_to_gbp(currency: str) -> float:
    return _FX_TO_GBP.get((currency or "USD").upper(), _FX_TO_GBP["USD"])


def _position_gain(position: dict) -> dict:
    ticker = str(position.get("ticker", "")).upper()
    quantity = float(position.get("quantity") or 0)
    avg_price = float(position.get("avg_price") or 0)
    exchange = str(position.get("exchange") or "")
    quote = _get_current_quote(ticker, exchange)
    current_price = float(quote.get("price") or avg_price)
    cost_currency = str(position.get("currency") or position.get("avg_price_currency") or quote.get("currency") or "USD").upper()
    current_currency = str(quote.get("currency") or cost_currency).upper()
    cost_gbp = quantity * avg_price * _fx_to_gbp(cost_currency)
    value_gbp = quantity * current_price * _fx_to_gbp(current_currency)
    gain_gbp = value_gbp - cost_gbp
    return {
        "ticker": ticker,
        "quantity": quantity,
        "avg_price": avg_price,
        "current_price": current_price,
        "cost_currency": cost_currency,
        "current_currency": current_currency,
        "cost_gbp": round(cost_gbp, 2),
        "value_gbp": round(value_gbp, 2),
        "gain_gbp": round(gain_gbp, 2),
        "gain_per_share_gbp": round(gain_gbp / quantity, 4) if quantity else 0,
    }


def _optimal_realization(gains: list[dict], allowance: float) -> list[dict]:
    remaining = allowance
    suggestions = []
    positive = [item for item in gains if item["gain_gbp"] > 0 and item["quantity"] > 0]
    for item in sorted(positive, key=lambda row: row["gain_gbp"]):
        if remaining <= 0:
            break
        gain_per_share = item["gain_gbp"] / item["quantity"]
        if gain_per_share <= 0:
            continue
        shares = min(item["quantity"], remaining / gain_per_share)
        realized_gain = min(item["gain_gbp"], shares * gain_per_share)
        suggestions.append(
            {
                "ticker": item["ticker"],
                "shares_to_sell": round(shares, 6),
                "estimated_gain_gbp": round(realized_gain, 2),
            }
        )
        remaining -= realized_gain
    return suggestions


@router.get("/uk/cgt/{user_id}", summary="UK CGT allowance simulator")
async def simulate_uk_cgt(
    user_id: str,
    income_band: Literal["basic", "higher"] = Query("higher"),
):
    positions = _load_positions()
    gains = [_position_gain(position) for position in positions if position.get("ticker")]
    total_gain = round(sum(item["gain_gbp"] for item in gains if item["gain_gbp"] > 0), 2)
    taxable = round(max(0.0, total_gain - UK_CGT_ALLOWANCE_2026), 2)
    rate = UK_CGT_HIGHER_RATE if income_band == "higher" else UK_CGT_BASIC_RATE
    tax = round(taxable * rate, 2)
    return {
        "user_id": user_id,
        "income_band": income_band,
        "total_unrealized_gain_gbp": total_gain,
        "allowance": UK_CGT_ALLOWANCE_2026,
        "allowance_remaining": round(max(0.0, UK_CGT_ALLOWANCE_2026 - total_gain), 2),
        "taxable_if_sold_all": taxable,
        "tax_if_sold_all": tax,
        "rate": rate,
        "optimal_realization": _optimal_realization(gains, UK_CGT_ALLOWANCE_2026),
        "positions": gains,
        "tax_year_end": "2026-04-05",
        "fx_source": "static_estimate",
        "disclaimer": "Educational estimate only. Not tax advice. Consult HMRC guidance or a qualified adviser.",
    }
