"""Market Data router -- sector info, financial trends, comps, health metrics."""

from typing import Any, Dict, List

from fastapi import APIRouter, Query

router = APIRouter()


def _safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        import math
        f = float(val)
        return default if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return default


@router.get("/indices", summary="Major market indices")
async def market_indices():
    try:
        import yfinance as yf
        symbols = [
            {"label": "S&P 500", "symbol": "^GSPC"},
            {"label": "NASDAQ", "symbol": "^IXIC"},
            {"label": "KOSPI", "symbol": "^KS11"},
            {"label": "BTC", "symbol": "BTC-USD"},
        ]
        results = []
        for s in symbols:
            try:
                t = yf.Ticker(s["symbol"])
                info = t.info or {}
                price = _safe_float(info.get("regularMarketPrice") or info.get("previousClose"))
                prev = _safe_float(info.get("regularMarketPreviousClose") or info.get("previousClose"))
                change = price - prev if prev else 0
                pct = (change / prev * 100) if prev else 0
                results.append({
                    "label": s["label"],
                    "symbol": s["symbol"],
                    "price": f"{price:,.2f}" if price else "—",
                    "change": f"{pct:+.2f}%",
                    "positive": pct >= 0,
                })
            except Exception:
                results.append({"label": s["label"], "symbol": s["symbol"], "price": "—", "change": "—", "positive": True})
        return results
    except Exception:
        return []


@router.get("/sector/{ticker}", summary="Sector and industry classification")
async def sector_industry(ticker: str):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        return {
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": _safe_float(info.get("marketCap")),
            "pe_ratio": _safe_float(info.get("trailingPE")) or _safe_float(info.get("forwardPE")),
            "dividend_yield": _safe_float(info.get("dividendYield")),
            "beta": _safe_float(info.get("beta")),
            "fifty_two_week_high": _safe_float(info.get("fiftyTwoWeekHigh")),
            "fifty_two_week_low": _safe_float(info.get("fiftyTwoWeekLow")),
            "current_price": _safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
        }
    except Exception:
        return {"sector": "N/A", "industry": "N/A"}


@router.get("/trend/{ticker}", summary="5-year financial trend")
async def financial_trend(ticker: str):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        fin = t.financials
        cf = t.cashflow
        if fin is None or fin.empty:
            return {"years": [], "revenue": [], "net_income": [], "operating_margin": [], "fcf": []}

        years = [str(c.year) for c in fin.columns[:5]]
        revenue = [_safe_float(fin.loc["Total Revenue"][c]) if "Total Revenue" in fin.index else 0 for c in fin.columns[:5]]
        net_income = [_safe_float(fin.loc["Net Income"][c]) if "Net Income" in fin.index else 0 for c in fin.columns[:5]]

        op_margin = []
        for i, c in enumerate(fin.columns[:5]):
            oi = _safe_float(fin.loc["Operating Income"][c]) if "Operating Income" in fin.index else 0
            rev = revenue[i] if i < len(revenue) else 1
            op_margin.append(round(oi / rev * 100, 2) if rev else 0)

        fcf_list = []
        if cf is not None and not cf.empty:
            for c in fin.columns[:5]:
                if c in cf.columns:
                    ocf = _safe_float(cf.loc["Operating Cash Flow"][c]) if "Operating Cash Flow" in cf.index else 0
                    capex = _safe_float(cf.loc["Capital Expenditure"][c]) if "Capital Expenditure" in cf.index else 0
                    fcf_list.append(ocf + capex)  # capex is negative
                else:
                    fcf_list.append(0)

        return {"years": years, "revenue": revenue, "net_income": net_income, "operating_margin": op_margin, "fcf": fcf_list}
    except Exception:
        return {"years": [], "revenue": [], "net_income": [], "operating_margin": [], "fcf": []}


@router.get("/comps", summary="Industry comparable companies")
async def industry_comps(tickers: str = Query(..., description="Comma-separated tickers")):
    try:
        import yfinance as yf
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        if not ticker_list:
            return {"tickers": [], "data": []}

        results = []
        for sym in ticker_list:
            t = yf.Ticker(sym)
            info = t.info or {}
            results.append({
                "ticker": sym,
                "forward_pe": _safe_float(info.get("forwardPE"), None),
                "trailing_pe": _safe_float(info.get("trailingPE"), None),
                "pb": _safe_float(info.get("priceToBook"), None),
                "ev_ebitda": _safe_float(info.get("enterpriseToEbitda"), None),
                "market_cap": _safe_float(info.get("marketCap"), None),
            })
        return {"tickers": ticker_list, "data": results}
    except Exception:
        return {"tickers": [], "data": []}


@router.get("/health/{ticker}", summary="DuPont, Altman Z-Score, Red Flags")
async def financial_health(ticker: str):
    fallback = {"ticker": ticker.upper(), "dupont": {}, "altman_z": None, "red_flags": []}
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        bs = t.balance_sheet
        fin = t.financials

        # DuPont Analysis
        npm = _safe_float(info.get("profitMargins"))
        roe = _safe_float(info.get("returnOnEquity"))
        roa = _safe_float(info.get("returnOnAssets"))

        total_assets = 0
        total_equity = 0
        total_revenue = 0
        net_income = 0

        if bs is not None and not bs.empty:
            col = bs.columns[0]
            total_assets = _safe_float(bs.loc["Total Assets"][col]) if "Total Assets" in bs.index else 0
            se_keys = ["Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity"]
            for k in se_keys:
                if k in bs.index:
                    total_equity = _safe_float(bs.loc[k][col])
                    break

        if fin is not None and not fin.empty:
            col = fin.columns[0]
            total_revenue = _safe_float(fin.loc["Total Revenue"][col]) if "Total Revenue" in fin.index else 0
            net_income = _safe_float(fin.loc["Net Income"][col]) if "Net Income" in fin.index else 0

        asset_turnover = round(total_revenue / total_assets, 3) if total_assets else 0
        equity_multiplier = round(total_assets / total_equity, 3) if total_equity else 0

        dupont = {
            "npm": round(npm, 4) if npm else round(net_income / total_revenue, 4) if total_revenue else 0,
            "asset_turnover": asset_turnover,
            "equity_multiplier": equity_multiplier,
            "roe": round(roe, 4) if roe else round(npm * asset_turnover * equity_multiplier, 4) if npm else 0,
        }

        # Altman Z-Score (simplified)
        altman_z = None
        if bs is not None and not bs.empty and fin is not None and not fin.empty:
            col_bs = bs.columns[0]
            col_fin = fin.columns[0]

            ca = _safe_float(bs.loc["Current Assets"][col_bs]) if "Current Assets" in bs.index else 0
            cl = _safe_float(bs.loc["Current Liabilities"][col_bs]) if "Current Liabilities" in bs.index else 0
            ta = total_assets
            re_val = _safe_float(bs.loc["Retained Earnings"][col_bs]) if "Retained Earnings" in bs.index else 0
            ebit = _safe_float(fin.loc["EBIT"][col_fin]) if "EBIT" in fin.index else _safe_float(fin.loc.get("Operating Income", {}).get(col_fin, 0))
            mc = _safe_float(info.get("marketCap"))
            tl_val = _safe_float(bs.loc["Total Liabilities Net Minority Interest"][col_bs]) if "Total Liabilities Net Minority Interest" in bs.index else (ta - total_equity)
            rev = total_revenue

            if ta > 0 and tl_val > 0:
                wc_ta = (ca - cl) / ta
                re_ta = re_val / ta
                ebit_ta = ebit / ta
                mc_tl = mc / tl_val if tl_val else 0
                rev_ta = rev / ta
                altman_z = round(1.2 * wc_ta + 1.4 * re_ta + 3.3 * ebit_ta + 0.6 * mc_tl + 1.0 * rev_ta, 2)

        # Red Flags
        red_flags = []
        cr = _safe_float(info.get("currentRatio"))
        de = _safe_float(info.get("debtToEquity"))
        if cr and cr < 1.0:
            red_flags.append(f"Low current ratio: {cr:.2f}")
        if de and de > 200:
            red_flags.append(f"High debt-to-equity: {de:.1f}%")
        if npm and npm < 0:
            red_flags.append("Negative profit margin")
        if roe and roe < 0:
            red_flags.append("Negative ROE")

        return {"ticker": ticker.upper(), "dupont": dupont, "altman_z": altman_z, "red_flags": red_flags}
    except Exception as e:
        return fallback


@router.get("/piotroski/{ticker}", summary="Piotroski F-Score")
async def piotroski_score(ticker: str):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        fin = t.financials
        bs = t.balance_sheet
        cf = t.cashflow

        score = 0
        details = {}

        if fin is None or fin.empty or bs is None or bs.empty:
            return {"total": 0, "details": {}, "score": 0}

        col = fin.columns[0]
        prev_col = fin.columns[1] if len(fin.columns) > 1 else None

        # 1. Positive ROA
        ni = _safe_float(fin.loc["Net Income"][col]) if "Net Income" in fin.index else 0
        ta = _safe_float(bs.loc["Total Assets"][col]) if "Total Assets" in bs.index else 1
        roa = ni / ta if ta else 0
        details["positive_roa"] = roa > 0
        score += 1 if roa > 0 else 0

        # 2. Positive Operating Cash Flow
        ocf = 0
        if cf is not None and not cf.empty and "Operating Cash Flow" in cf.index:
            ocf = _safe_float(cf.loc["Operating Cash Flow"][cf.columns[0]])
        details["positive_ocf"] = ocf > 0
        score += 1 if ocf > 0 else 0

        # 3. ROA improving
        if prev_col is not None:
            prev_ni = _safe_float(fin.loc["Net Income"][prev_col]) if "Net Income" in fin.index else 0
            prev_ta = _safe_float(bs.loc["Total Assets"][prev_col]) if prev_col in bs.columns and "Total Assets" in bs.index else 1
            prev_roa = prev_ni / prev_ta if prev_ta else 0
            details["roa_improving"] = roa > prev_roa
            score += 1 if roa > prev_roa else 0
        else:
            details["roa_improving"] = False

        # 4. Cash flow > Net Income (accrual)
        details["accrual"] = ocf > ni
        score += 1 if ocf > ni else 0

        # 5. Decreasing leverage
        dle = _safe_float(info.get("debtToEquity", 0))
        details["lower_leverage"] = dle < 100
        score += 1 if dle < 100 else 0

        # 6. Higher current ratio
        cr = _safe_float(info.get("currentRatio", 0))
        details["higher_liquidity"] = cr > 1.0
        score += 1 if cr > 1.0 else 0

        # 7. No dilution
        shares = _safe_float(info.get("sharesOutstanding", 0))
        details["no_dilution"] = True  # simplified
        score += 1

        # 8. Higher gross margin
        gm = _safe_float(info.get("grossMargins", 0))
        details["higher_gross_margin"] = gm > 0.3
        score += 1 if gm > 0.3 else 0

        # 9. Higher asset turnover
        rev = _safe_float(fin.loc["Total Revenue"][col]) if "Total Revenue" in fin.index else 0
        at = rev / ta if ta else 0
        details["higher_asset_turnover"] = at > 0.5
        score += 1 if at > 0.5 else 0

        return {"total": score, "details": details, "score": score}
    except Exception:
        return {"total": 0, "details": {}, "score": 0}


@router.get("/sankey/{ticker}", summary="Income statement Sankey data")
async def sankey_data(ticker: str):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        fin = t.financials
        if fin is None or fin.empty:
            return {"nodes": [], "links": []}

        col = fin.columns[0]
        rev = _safe_float(fin.loc["Total Revenue"][col]) if "Total Revenue" in fin.index else 0
        cogs = _safe_float(fin.loc["Cost Of Revenue"][col]) if "Cost Of Revenue" in fin.index else 0
        gp = rev - cogs
        opex = _safe_float(fin.loc["Operating Expense"][col]) if "Operating Expense" in fin.index else 0
        oi = _safe_float(fin.loc["Operating Income"][col]) if "Operating Income" in fin.index else gp - opex
        ni = _safe_float(fin.loc["Net Income"][col]) if "Net Income" in fin.index else 0
        tax_other = oi - ni

        nodes = [
            {"name": "Revenue", "value": rev},
            {"name": "COGS", "value": cogs},
            {"name": "Gross Profit", "value": gp},
            {"name": "Operating Expenses", "value": opex},
            {"name": "Operating Income", "value": oi},
            {"name": "Tax & Other", "value": abs(tax_other)},
            {"name": "Net Income", "value": ni},
        ]
        return {"nodes": nodes}
    except Exception:
        return {"nodes": []}


@router.get("/radar/{ticker}", summary="Radar chart metrics")
async def radar_metrics(ticker: str):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        info = t.info or {}

        return {
            "roe": _safe_float(info.get("returnOnEquity", 0)) * 100,
            "roa": _safe_float(info.get("returnOnAssets", 0)) * 100,
            "gross_margin": _safe_float(info.get("grossMargins", 0)) * 100,
            "current_ratio": _safe_float(info.get("currentRatio", 0)),
            "revenue_growth": _safe_float(info.get("revenueGrowth", 0)) * 100,
        }
    except Exception:
        return {}
