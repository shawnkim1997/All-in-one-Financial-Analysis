"""Earnings router -- earnings history, upcoming dates, and transcripts."""

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


@router.get("/{ticker}/history", summary="Earnings history (EPS actual vs estimate)")
async def earnings_history(ticker: str) -> Dict[str, Any]:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        earnings = t.earnings_history
        if earnings is None or (hasattr(earnings, 'empty') and earnings.empty):
            return {"ticker": ticker.upper(), "history": []}

        history: List[Dict[str, Any]] = []
        if hasattr(earnings, 'iterrows'):
            for idx, row in earnings.iterrows():
                history.append({
                    "date": str(idx)[:10],
                    "eps_actual": _safe_float(row.get("epsActual", row.get("Reported EPS"))),
                    "eps_estimate": _safe_float(row.get("epsEstimate", row.get("EPS Estimate"))),
                    "surprise": round(_safe_float(row.get("surprisePercent", row.get("Surprise(%)")), 0) * 100, 2),
                })
        return {"ticker": ticker.upper(), "history": history[-12:]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Earnings history failed: {exc}") from exc


@router.get("/{ticker}/calendar", summary="Upcoming earnings date")
async def earnings_calendar(ticker: str) -> Dict[str, Any]:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        cal = t.calendar
        if cal is None:
            return {"ticker": ticker.upper(), "next_earnings": None}

        if isinstance(cal, dict):
            earnings_date = cal.get("Earnings Date")
            if isinstance(earnings_date, list) and earnings_date:
                earnings_date = str(earnings_date[0])[:10]
            elif earnings_date:
                earnings_date = str(earnings_date)[:10]
            return {
                "ticker": ticker.upper(),
                "next_earnings": earnings_date,
                "revenue_estimate": _safe_float(cal.get("Revenue Average")),
                "eps_estimate": _safe_float(cal.get("Earnings Average")),
            }
        return {"ticker": ticker.upper(), "next_earnings": None}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Earnings calendar failed: {exc}") from exc


@router.get("/{ticker}/quarterly", summary="Quarterly earnings data")
async def quarterly_earnings(ticker: str) -> Dict[str, Any]:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())

        quarterly = t.quarterly_earnings
        data: List[Dict[str, Any]] = []
        if quarterly is not None and hasattr(quarterly, 'iterrows'):
            for idx, row in quarterly.iterrows():
                data.append({
                    "period": str(idx),
                    "revenue": _safe_float(row.get("Revenue")),
                    "earnings": _safe_float(row.get("Earnings")),
                })

        return {"ticker": ticker.upper(), "quarterly": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Quarterly earnings failed: {exc}") from exc
