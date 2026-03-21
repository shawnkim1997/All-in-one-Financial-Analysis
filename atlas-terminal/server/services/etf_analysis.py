"""ETF and equity-like overview helpers."""

from __future__ import annotations

import math
from typing import Any


def _safe_num(v: Any) -> float | None:
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


def _compute_sharpe(returns) -> float | None:
    if returns is None or len(returns) < 2:
        return None
    std = returns.std()
    if not std:
        return None
    return round(float((returns.mean() / std) * (252**0.5)), 2)


def _compute_sortino(returns) -> float | None:
    if returns is None or len(returns) < 2:
        return None
    downside = returns[returns < 0]
    if downside is None or len(downside) < 2:
        return None
    std = downside.std()
    if not std:
        return None
    return round(float((returns.mean() / std) * (252**0.5)), 2)


def _max_drawdown(returns) -> float | None:
    if returns is None or len(returns) < 2:
        return None
    curve = (1 + returns).cumprod()
    dd = (curve / curve.cummax()) - 1
    return round(float(dd.min()) * 100, 2)


async def get_benchmark_comparison(ticker: str, benchmark: str = "SPY", period: str = "1y") -> dict:
    import yfinance as yf

    data = yf.download([ticker.upper(), benchmark.upper()], period=period, auto_adjust=True, progress=False)
    if data is None or data.empty:
        return {}
    close = data["Close"] if "Close" in data else data
    if close is None or close.empty:
        return {}
    t_col = ticker.upper()
    b_col = benchmark.upper()
    if t_col not in close.columns or b_col not in close.columns:
        return {}
    close = close[[t_col, b_col]].dropna()
    if close.empty:
        return {}
    normalized = close / close.iloc[0] * 100
    return {
        "dates": normalized.index.strftime("%Y-%m-%d").tolist(),
        "ticker_values": [float(x) for x in normalized[t_col].tolist()],
        "benchmark_values": [float(x) for x in normalized[b_col].tolist()],
        "benchmark": benchmark.upper(),
    }


async def get_etf_holdings(ticker: str, top_n: int = 10) -> list[dict]:
    import yfinance as yf

    t = yf.Ticker(ticker.upper())
    out = []
    try:
        holdings = getattr(t, "fund_top_holdings", None)
        if holdings is not None and not holdings.empty:
            for _, row in holdings.head(top_n).iterrows():
                out.append(
                    {
                        "symbol": row.get("symbol") or row.get("holdingName") or "",
                        "name": row.get("holdingName") or row.get("symbol") or "",
                        "weight_pct": _safe_num(row.get("holdingPercent")),
                    }
                )
    except Exception:
        pass
    return out


async def get_etf_overview(ticker: str) -> dict:
    import yfinance as yf

    t = yf.Ticker(ticker.upper())
    info = t.info or {}
    hist = t.history(period="5y", auto_adjust=True)

    def period_return(days: int) -> float | None:
        if hist is None or hist.empty or len(hist) <= days:
            return None
        cur = _safe_num(hist["Close"].iloc[-1])
        prev = _safe_num(hist["Close"].iloc[-days])
        if cur is None or prev is None or prev == 0:
            return None
        return round((cur / prev - 1) * 100, 2)

    ytd_days = 0
    if hist is not None and not hist.empty:
        ytd_days = int((hist.index.year == hist.index[-1].year).sum())
    returns = hist["Close"].pct_change().dropna() if hist is not None and not hist.empty else None

    return {
        "name": info.get("longName") or info.get("shortName", ticker.upper()),
        "category": info.get("category") or info.get("fundFamily") or "N/A",
        "aum": _safe_num(info.get("totalAssets")),
        "expense_ratio": _safe_num(info.get("annualReportExpenseRatio")),
        "nav": _safe_num(info.get("navPrice")),
        "inception": info.get("fundInceptionDate"),
        "price": _safe_num(info.get("currentPrice") or info.get("regularMarketPrice")),
        "high_52w": _safe_num(info.get("fiftyTwoWeekHigh")),
        "low_52w": _safe_num(info.get("fiftyTwoWeekLow")),
        "returns": {
            "1m": period_return(21),
            "3m": period_return(63),
            "6m": period_return(126),
            "ytd": period_return(ytd_days) if ytd_days else None,
            "1y": period_return(252),
            "3y": period_return(756),
            "5y": period_return(1260),
        },
        "holdings": await get_etf_holdings(ticker, top_n=10),
        "risk": {
            "sharpe": _compute_sharpe(returns),
            "sortino": _compute_sortino(returns),
            "max_drawdown": _max_drawdown(returns),
            "volatility": round(float(returns.std()) * (252**0.5) * 100, 2) if returns is not None and len(returns) > 1 else None,
        },
        "benchmark_comparison": await get_benchmark_comparison(ticker, "SPY", "1y"),
    }


async def get_equity_overview(ticker: str) -> dict:
    import yfinance as yf

    t = yf.Ticker(ticker.upper())
    info = t.info or {}
    return {
        "name": info.get("longName") or info.get("shortName", ticker.upper()),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": _safe_num(info.get("marketCap")),
        "pe_ratio": _safe_num(info.get("trailingPE")) or _safe_num(info.get("forwardPE")),
        "dividend_yield": _safe_num(info.get("dividendYield")),
        "beta": _safe_num(info.get("beta")),
        "high_52w": _safe_num(info.get("fiftyTwoWeekHigh")),
        "low_52w": _safe_num(info.get("fiftyTwoWeekLow")),
        "price": _safe_num(info.get("currentPrice") or info.get("regularMarketPrice")),
        "description": info.get("longBusinessSummary"),
    }
