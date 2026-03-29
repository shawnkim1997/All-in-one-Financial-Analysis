"""Earnings router -- earnings history, upcoming dates, and transcripts (FMP)."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

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


@router.get("/{ticker}/transcript", summary="Earnings call transcript (FMP)")
async def earnings_transcript(
    ticker: str,
    year: int = Query(..., ge=1990, le=2035),
    quarter: int = Query(..., ge=1, le=4),
) -> Dict[str, Any]:
    """Return one quarter of earnings call text from FMP when ``FMP_API_KEY`` is set."""
    from server.services.fmp_client import fetch_earning_call_transcript, fmp_is_configured

    if not fmp_is_configured():
        return {
            "ticker": ticker.upper(),
            "year": year,
            "quarter": quarter,
            "available": False,
            "message": "Set FMP_API_KEY for earnings call transcripts.",
            "content": None,
        }
    rows: Optional[List[Dict[str, Any]]] = await fetch_earning_call_transcript(
        ticker, year, quarter
    )
    if not rows:
        return {
            "ticker": ticker.upper(),
            "year": year,
            "quarter": quarter,
            "available": False,
            "message": "No transcript returned (symbol/quarter or API limit).",
            "content": None,
        }
    # FMP returns list of dicts with 'content' or similar
    return {
        "ticker": ticker.upper(),
        "year": year,
        "quarter": quarter,
        "available": True,
        "data": rows,
    }


@router.get("/{ticker}/delta", summary="What changed vs last quarter")
async def earnings_delta(ticker: str) -> Dict[str, Any]:
    """Compare the two most recent quarters: revenue/earnings delta + AI summary."""
    try:
        import yfinance as yf

        t = yf.Ticker(ticker.upper())
        quarterly = t.quarterly_earnings
        if quarterly is None or (hasattr(quarterly, "empty") and quarterly.empty) or len(quarterly) < 2:
            return {"ticker": ticker.upper(), "available": False, "message": "Not enough quarterly data"}

        rows = []
        for idx, row in quarterly.iterrows():
            rows.append({
                "period": str(idx),
                "revenue": _safe_float(row.get("Revenue")),
                "earnings": _safe_float(row.get("Earnings")),
            })
        if len(rows) < 2:
            return {"ticker": ticker.upper(), "available": False, "message": "Not enough quarterly data"}

        latest, prev = rows[0], rows[1]
        rev_delta = None
        earn_delta = None
        if latest["revenue"] and prev["revenue"] and prev["revenue"] != 0:
            rev_delta = round((latest["revenue"] - prev["revenue"]) / abs(prev["revenue"]) * 100, 2)
        if latest["earnings"] and prev["earnings"] and prev["earnings"] != 0:
            earn_delta = round((latest["earnings"] - prev["earnings"]) / abs(prev["earnings"]) * 100, 2)

        # EPS surprise trend from earnings_history
        eh = t.earnings_history
        eps_trend: List[Dict[str, Any]] = []
        if eh is not None and hasattr(eh, "iterrows"):
            for idx2, row2 in eh.iterrows():
                eps_trend.append({
                    "date": str(idx2)[:10],
                    "surprise_pct": round(_safe_float(row2.get("surprisePercent", 0), 0) * 100, 2),
                })
            eps_trend = eps_trend[-4:]

        # AI summary via Gemini (best-effort)
        ai_summary: Optional[str] = None
        try:
            from server.services.gemini_service import generate_text
            prompt = (
                f"Compare {ticker.upper()} most recent two quarters.\n"
                f"Latest quarter ({latest['period']}): Revenue ${latest['revenue']}, Earnings ${latest['earnings']}.\n"
                f"Previous quarter ({prev['period']}): Revenue ${prev['revenue']}, Earnings ${prev['earnings']}.\n"
                f"Revenue changed {rev_delta}%, Earnings changed {earn_delta}%.\n"
                "In 2-3 sentences, explain what changed and why. Be concise and specific."
            )
            ai_summary = await generate_text(prompt)
        except Exception:
            pass

        return {
            "ticker": ticker.upper(),
            "available": True,
            "latest_quarter": latest["period"],
            "prev_quarter": prev["period"],
            "latest_revenue": latest["revenue"],
            "prev_revenue": prev["revenue"],
            "latest_earnings": latest["earnings"],
            "prev_earnings": prev["earnings"],
            "revenue_delta_pct": rev_delta,
            "earnings_delta_pct": earn_delta,
            "eps_trend": eps_trend,
            "ai_summary": ai_summary,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Earnings delta failed: {exc}") from exc


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
