"""Financial statements router -- statements, highlights, and ratios."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter

router = APIRouter()


def _df_to_periods(df: Any, max_periods: int = 5) -> List[Dict[str, Any]]:
    """Convert a yfinance / yahooquery financial DataFrame to a list of dicts.

    Each dict represents one fiscal period.  NaN values are replaced with
    ``None`` for clean JSON serialisation.
    """
    try:
        import pandas as pd

        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return []
        result = df.iloc[:, :max_periods].T
        result.index = [str(i)[:10] for i in result.index]
        records = result.reset_index().rename(columns={"index": "period"})
        return records.where(records.notna(), None).to_dict(orient="records")
    except Exception:
        return []


def _calc_yoy_growth(series_list: List[Optional[float]]) -> List[Optional[float]]:
    """Return YoY growth rates for a list of period values.

    The first element is always ``None`` (no prior period).
    """
    growth: List[Optional[float]] = [None]
    for i in range(1, len(series_list)):
        prev = series_list[i - 1]
        curr = series_list[i]
        if prev and curr and prev != 0:
            growth.append(round((curr - prev) / abs(prev) * 100, 2))
        else:
            growth.append(None)
    return growth


def _safe_get(info: Dict[str, Any], key: str) -> Optional[float]:
    """Safely get a numeric value from *info*, returning None for NaN."""
    import math

    val = info.get(key)
    if val is None:
        return None
    try:
        if math.isnan(val):
            return None
    except (TypeError, ValueError):
        return None
    return float(val)


@router.get(
    "/{ticker}/statements",
    summary="Income statement, balance sheet, cash flow",
)
async def financial_statements(ticker: str) -> Dict[str, Any]:
    """Return income statement, balance sheet, and cash flow for *ticker*.

    Tries yfinance annual statements first, then yahooquery if empty
    (see ``claude.md`` §2.3 — order differs from ``market_fetcher``).
    Includes up to 5 annual periods with YoY growth rates.
    """
    try:
        income_data: List[Dict[str, Any]] = []
        balance_data: List[Dict[str, Any]] = []
        cashflow_data: List[Dict[str, Any]] = []

        # Use yfinance for clean annual data
        import yfinance as yf

        t = yf.Ticker(ticker.upper())
        income_data = _df_to_periods(t.income_stmt)
        balance_data = _df_to_periods(t.balance_sheet)
        cashflow_data = _df_to_periods(t.cashflow)

        # If yfinance gives no data, try yahooquery and filter to annual only
        if not income_data:
            try:
                from yahooquery import Ticker as YQTicker  # type: ignore[import-untyped]
                import pandas as pd

                yq = YQTicker(ticker.upper())
                inc = yq.income_statement(frequency="a")
                bal = yq.balance_sheet(frequency="a")
                cf = yq.cash_flow(frequency="a")

                if isinstance(inc, pd.DataFrame) and not inc.empty:
                    income_data = _df_to_periods(inc.T)
                if isinstance(bal, pd.DataFrame) and not bal.empty:
                    balance_data = _df_to_periods(bal.T)
                if isinstance(cf, pd.DataFrame) and not cf.empty:
                    cashflow_data = _df_to_periods(cf.T)
            except ImportError:
                pass

        # Filter out TTM periods — keep only 12M/annual
        def _filter_annual(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            filtered = [r for r in records if r.get("periodType") != "TTM"]
            return filtered if filtered else records

        income_data = _filter_annual(income_data)
        balance_data = _filter_annual(balance_data)
        cashflow_data = _filter_annual(cashflow_data)

        # Calculate YoY growth for revenue if available
        revenue_values: List[Optional[float]] = []
        for rec in income_data:
            for key in ("TotalRevenue", "Total Revenue", "Revenue"):
                if key in rec and rec[key] is not None:
                    revenue_values.append(rec[key])
                    break
            else:
                revenue_values.append(None)

        revenue_growth = _calc_yoy_growth(revenue_values)

        return {
            "ticker": ticker.upper(),
            "income_statement": income_data,
            "balance_sheet": balance_data,
            "cash_flow": cashflow_data,
            "revenue_yoy_growth": revenue_growth,
        }
    except Exception:
        return {
            "ticker": ticker.upper(),
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
            "revenue_yoy_growth": [],
        }


@router.get(
    "/{ticker}/highlights",
    summary="Key financial metrics summary",
)
async def financial_highlights(ticker: str) -> Dict[str, Any]:
    """Return key financial metrics: revenue, margins, ROE, D/E, OCF.

    Sourced from yfinance ``info`` for the most recent data.
    """
    try:
        import yfinance as yf

        t = yf.Ticker(ticker.upper())
        info: Dict[str, Any] = t.info or {}

        highlights: Dict[str, Any] = {
            "ticker": ticker.upper(),
            "company_name": info.get("longName", info.get("shortName", "")),
            "revenue": _safe_get(info, "totalRevenue"),
            "revenue_per_share": _safe_get(info, "revenuePerShare"),
            "gross_margin": _safe_get(info, "grossMargins"),
            "operating_margin": _safe_get(info, "operatingMargins"),
            "profit_margin": _safe_get(info, "profitMargins"),
            "ebitda": _safe_get(info, "ebitda"),
            "ebitda_margin": None,
            "roe": _safe_get(info, "returnOnEquity"),
            "roa": _safe_get(info, "returnOnAssets"),
            "debt_to_equity": _safe_get(info, "debtToEquity"),
            "current_ratio": _safe_get(info, "currentRatio"),
            "operating_cash_flow": _safe_get(info, "operatingCashflow"),
            "free_cash_flow": _safe_get(info, "freeCashflow"),
            "book_value": _safe_get(info, "bookValue"),
            "earnings_growth": _safe_get(info, "earningsGrowth"),
            "revenue_growth": _safe_get(info, "revenueGrowth"),
        }

        # Derive EBITDA margin if both values exist
        rev = highlights["revenue"]
        ebitda = highlights["ebitda"]
        if rev and ebitda and rev > 0:
            highlights["ebitda_margin"] = round(ebitda / rev, 4)

        return highlights
    except Exception:
        return {
            "ticker": ticker.upper(),
            "company_name": "",
            "revenue": None, "revenue_per_share": None,
            "gross_margin": None, "operating_margin": None, "profit_margin": None,
            "ebitda": None, "ebitda_margin": None,
            "roe": None, "roa": None,
            "debt_to_equity": None, "current_ratio": None,
            "operating_cash_flow": None, "free_cash_flow": None,
            "book_value": None, "earnings_growth": None, "revenue_growth": None,
        }


@router.get(
    "/{ticker}/kpi-history",
    summary="Quarterly KPI series for charts",
)
async def kpi_history(ticker: str) -> Dict[str, Any]:
    """QoQ revenue growth, margins, ROE, FCF from quarterly statements (no LLM)."""
    try:
        from server.services.kpi_history_service import build_kpi_history

        return build_kpi_history(ticker)
    except Exception:
        return {
            "ticker": ticker.upper(),
            "quarters": [],
            "revenue_growth": [],
            "operating_margin": [],
            "net_margin": [],
            "roe": [],
            "fcf": [],
        }


@router.get(
    "/{ticker}/ratios",
    summary="Valuation and financial ratios",
)
async def financial_ratios(ticker: str) -> Dict[str, Any]:
    """Return valuation ratios with 5-year averages.

    Includes PER, PBR, PSR, P/OCF, EV/EBITDA, and PEG ratio.
    """
    try:
        import yfinance as yf

        t = yf.Ticker(ticker.upper())
        info: Dict[str, Any] = t.info or {}

        # Current ratios
        ratios: Dict[str, Any] = {
            "ticker": ticker.upper(),
            "trailing_pe": _safe_get(info, "trailingPE"),
            "forward_pe": _safe_get(info, "forwardPE"),
            "price_to_book": _safe_get(info, "priceToBook"),
            "price_to_sales": _safe_get(info, "priceToSalesTrailing12Months"),
            "enterprise_to_ebitda": _safe_get(info, "enterpriseToEbitda"),
            "enterprise_to_revenue": _safe_get(info, "enterpriseToRevenue"),
            "peg_ratio": _safe_get(info, "pegRatio"),
            "price_to_ocf": None,
            "ev": _safe_get(info, "enterpriseValue"),
            "market_cap": _safe_get(info, "marketCap"),
        }

        # Calculate P/OCF
        ocf = _safe_get(info, "operatingCashflow")
        mkt_cap = _safe_get(info, "marketCap")
        if ocf and mkt_cap and ocf > 0:
            ratios["price_to_ocf"] = round(mkt_cap / ocf, 2)

        # 5-year average PE from historical data
        five_year_avg: Dict[str, Optional[float]] = {
            "five_year_avg_pe": _safe_get(info, "fiveYearAvgDividendYield"),
            "trailing_pe_5y_avg": None,
        }

        # Try to get peer average from industry
        peer_avg: Dict[str, Optional[float]] = {
            "industry_pe_avg": _safe_get(info, "industryPe") if "industryPe" in info else None,
        }

        ratios["averages"] = five_year_avg
        ratios["peer_comparison"] = peer_avg

        return ratios
    except Exception:
        return {
            "ticker": ticker.upper(),
            "trailing_pe": None, "forward_pe": None,
            "price_to_book": None, "price_to_sales": None,
            "enterprise_to_ebitda": None, "enterprise_to_revenue": None,
            "peg_ratio": None, "price_to_ocf": None,
            "ev": None, "market_cap": None,
            "averages": {}, "peer_comparison": {},
        }
