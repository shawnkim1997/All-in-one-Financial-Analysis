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

    from server.services.korean_market import get_naver_stock_snapshot, is_korean_equity_ticker

    normalized = ticker.upper()
    t = yf.Ticker(normalized)
    info = t.info or {}

    # Fallback: derive 52W low/high from history when yfinance returns 0 or None
    # (common for some Asian tickers like 005930.KS where info.fiftyTwoWeekLow == 0)
    hi52 = _safe_num(info.get("fiftyTwoWeekHigh"))
    lo52 = _safe_num(info.get("fiftyTwoWeekLow"))
    if not hi52 or not lo52 or lo52 == 0:
        try:
            hist = t.history(period="1y")
            if hist is not None and len(hist) > 0:
                h_max = float(hist["High"].max())
                l_min = float(hist["Low"].min())
                if not hi52:
                    hi52 = h_max
                if not lo52 or lo52 == 0:
                    lo52 = l_min
        except Exception:
            pass

    city = (info.get("city") or "").strip()
    state = (info.get("state") or "").strip()
    country = (info.get("country") or "").strip()
    hq_parts = [part for part in [city, state, country] if part]
    hq = ", ".join(hq_parts) if hq_parts else None

    naver = await get_naver_stock_snapshot(normalized) if is_korean_equity_ticker(normalized) else None

    price = _safe_num(info.get("currentPrice") or info.get("regularMarketPrice"))
    market_cap = _safe_num(info.get("marketCap"))
    currency = info.get("currency") or info.get("financialCurrency") or "USD"
    exchange = info.get("exchange")
    country_name = info.get("country")
    description = info.get("longBusinessSummary")

    if naver:
        price = _safe_num(naver.get("current_price")) or price
        market_cap = _safe_num(naver.get("market_cap")) or market_cap
        hi52 = _safe_num(naver.get("fifty_two_week_high")) or hi52
        lo52 = _safe_num(naver.get("fifty_two_week_low")) or lo52
        currency = str(naver.get("currency") or currency or "KRW")
        exchange = str(naver.get("exchange") or exchange or "")
        country_name = str(naver.get("country") or country_name or "KR")
        description = str(naver.get("description") or description or "")

    return {
        "name": naver.get("name") if naver else info.get("longName") or info.get("shortName", normalized),
        "name_ko": naver.get("name_ko") if naver else None,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": market_cap,
        "pe_ratio": _safe_num(info.get("trailingPE")) or _safe_num(info.get("forwardPE")),
        "dividend_yield": _safe_num(info.get("dividendYield")) or _safe_num(naver.get("dividend_yield") / 100.0 if naver and naver.get("dividend_yield") is not None else None),
        "beta": _safe_num(info.get("beta")),
        "high_52w": hi52,
        "low_52w": lo52,
        "price": price,
        "description": description,
        "currency": currency,
        "exchange": exchange,
        "country": country_name,
        "market": naver.get("market") if naver else None,
        "stock_code": naver.get("stock_code") if naver else None,
        "full_time_employees": info.get("fullTimeEmployees"),
        "average_volume": _safe_num(info.get("averageVolume")),
        "trailing_pe": _safe_num(info.get("trailingPE")),
        "forward_pe": _safe_num(naver.get("forward_pe") if naver else None) or _safe_num(info.get("forwardPE")),
        "enterprise_to_ebitda": _safe_num(info.get("enterpriseToEbitda")),
        "debt_to_equity": _safe_num(info.get("debtToEquity")),
        "return_on_equity": _safe_num(info.get("returnOnEquity")),
        "return_on_assets": _safe_num(info.get("returnOnAssets")),
        "free_cashflow": _safe_num(info.get("freeCashflow")),
        "revenue_growth": _safe_num(info.get("revenueGrowth")),
        "profit_margins": _safe_num(info.get("profitMargins")),
        "target_mean_price": _safe_num(naver.get("target_mean_price") if naver else None) or _safe_num(info.get("targetMeanPrice")),
        "target_high_price": _safe_num(info.get("targetHighPrice")),
        "target_low_price": _safe_num(info.get("targetLowPrice")),
        "recommendation": naver.get("recommendation") if naver else info.get("recommendationKey"),
        "num_analysts": info.get("numberOfAnalystOpinions"),
        "change": _safe_num(naver.get("change") if naver else None),
        "change_pct": _safe_num(naver.get("change_pct") if naver else None),
        "forward_eps": _safe_num(naver.get("forward_eps") if naver else None) or _safe_num(info.get("forwardEps")),
        "trailing_eps": _safe_num(naver.get("trailing_eps") if naver else None) or _safe_num(info.get("trailingEps")),
        "peg_ratio": _safe_num(info.get("pegRatio")),
        "ceo": info.get("companyOfficers", [{}])[0].get("name") if isinstance(info.get("companyOfficers"), list) and info.get("companyOfficers") else None,
        "founded": info.get("founded"),
        "hq": hq,
        "website": info.get("website"),
        "ipo_date": info.get("ipoExpectedDate") or info.get("firstTradeDateEpochUtc"),
        "source": naver.get("source") if naver else "yfinance",
    }
