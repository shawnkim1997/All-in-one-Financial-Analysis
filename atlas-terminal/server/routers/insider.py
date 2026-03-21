"""Insider trading router -- recent insider transactions from yfinance."""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

router = APIRouter()


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        import math
        f = float(val)
        return default if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return default


@router.get("/{ticker}", summary="Recent insider transactions")
async def insider_transactions(ticker: str) -> Dict[str, Any]:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        insiders = t.insider_transactions
        if insiders is None or (hasattr(insiders, 'empty') and insiders.empty):
            return {"ticker": ticker.upper(), "transactions": []}

        transactions: List[Dict[str, Any]] = []
        if hasattr(insiders, 'iterrows'):
            for _, row in insiders.iterrows():
                transactions.append({
                    "date": str(row.get("Start Date", ""))[:10] if "Start Date" in row.index else "",
                    "insider": str(row.get("Insider", "")),
                    "relation": str(row.get("Position", row.get("Relationship", ""))),
                    "transaction": str(row.get("Transaction", "")),
                    "shares": _safe_float(row.get("Shares")),
                    "value": _safe_float(row.get("Value")),
                })

        return {"ticker": ticker.upper(), "transactions": transactions[:30]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Insider transactions failed: {exc}") from exc


@router.get("/{ticker}/holders", summary="Institutional and mutual fund holders")
async def holders(ticker: str) -> Dict[str, Any]:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())

        institutional = []
        inst = t.institutional_holders
        if inst is not None and hasattr(inst, 'iterrows'):
            for _, row in inst.iterrows():
                institutional.append({
                    "holder": str(row.get("Holder", "")),
                    "shares": _safe_float(row.get("Shares")),
                    "value": _safe_float(row.get("Value")),
                    "pct_held": _safe_float(row.get("% Out")),
                })

        return {
            "ticker": ticker.upper(),
            "institutional": institutional[:15],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Holders failed: {exc}") from exc
