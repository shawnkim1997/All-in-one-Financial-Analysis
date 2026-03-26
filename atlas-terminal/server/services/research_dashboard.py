"""Research deep-dive dashboard: F-Score history, DuPont tree, Sankey, waterfall, anomalies.

All quantitative; no LLM. See claude.md hybrid separation principle.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from server.utils.safe_float import _safe_float
from server.services.market_fetcher import _get_annual_financials_balance_cashflow, _get_row_series
from server.services.financial_metrics import get_dupont_altman_redflags_yoy
from server.services.financial_metrics_ext import get_income_statement_sankey_data
from server.models.schemas import (
    DuPontTreeNode,
    DuPontTreePayload,
    FScoreCriterionSeries,
    FScoreYearPoint,
    FinancialAnomalyItem,
    ResearchDashboardResponse,
    SankeyGraphPayload,
    SankeyNivoLink,
    SankeyNivoNode,
    WaterfallStep,
)

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore[assignment]

_FSCORE_KEYS = [
    ("profitable", "Net income > 0"),
    ("ocf_pos", "Operating cash flow > 0"),
    ("roa_up", "ROA vs prior year"),
    ("ocf_gt_ni", "OCF > net income"),
    ("leverage_down", "Lower LT debt / assets"),
    ("cr_up", "Current ratio improved"),
    ("no_dilution", "Shares flat or down"),
    ("gm_up", "Gross margin improved"),
    ("at_up", "Asset turnover improved"),
]


def _col_year(fin: pd.DataFrame, idx: int) -> int:
    if fin is None or fin.empty or idx >= len(fin.columns):
        return 0
    c = fin.columns[idx]
    s = str(c)[:4]
    return int(s) if s.isdigit() else 2024 - idx


def _vx(s: Optional[pd.Series], i: int) -> Optional[float]:
    if s is None or len(s) <= i:
        return None
    x = _safe_float(s.iloc[i])
    return x if x is not None and x == x and not pd.isna(x) else None


def _fscore_passes_for_pair(
    fin: pd.DataFrame,
    bal: pd.DataFrame,
    cf: pd.DataFrame,
    ticker: str,
    i: int,
) -> Tuple[bool, ...]:
    """Piotroski 9 booleans comparing fiscal column i vs i+1 (i is more recent)."""
    ncol = len(fin.columns)
    if i + 1 >= ncol:
        return tuple([False] * 9)

    rev = _get_row_series(fin, "Total Revenue", "Revenue")
    ni = _get_row_series(fin, "Net Income", "Net Income Common Stockholders")
    gross = _get_row_series(fin, "Gross Profit")
    ta = _get_row_series(bal, "Total Assets")
    lt_debt = _get_row_series(bal, "Long Term Debt")
    ca = _get_row_series(bal, "Current Assets")
    cl = _get_row_series(bal, "Current Liabilities")
    ocf = _get_row_series(cf, "Operating Cash Flow", "Cash From Operating Activities") if not cf.empty else None
    shares = _get_row_series(bal, "Share Issued")
    if shares is None or (hasattr(shares, "empty") and shares.empty):
        shares = _get_row_series(bal, "Ordinary Shares Number")

    ni0, ni1 = _vx(ni, i), _vx(ni, i + 1)
    ocf0 = _vx(ocf, i) if ocf is not None else None
    ta0, ta1 = _vx(ta, i), _vx(ta, i + 1)
    roa0 = (ni0 / ta0 * 100) if (ni0 is not None and ta0 and ta0 != 0) else None
    roa1 = (ni1 / ta1 * 100) if (ni1 is not None and ta1 and ta1 != 0) else None
    lt0 = _vx(lt_debt, i) or 0
    lt1 = _vx(lt_debt, i + 1) or 0
    cl0, cl1 = _vx(cl, i), _vx(cl, i + 1)
    ca0, ca1 = _vx(ca, i), _vx(ca, i + 1)
    cr0 = (ca0 / cl0) if (ca0 is not None and cl0 and cl0 != 0) else None
    cr1 = (ca1 / cl1) if (ca1 is not None and cl1 and cl1 != 0) else None
    sh0, sh1 = _vx(shares, i), _vx(shares, i + 1)
    rev0, rev1 = _vx(rev, i), _vx(rev, i + 1)
    gm0 = (_vx(gross, i) / rev0 * 100) if (gross is not None and rev0 and rev0 != 0) else None
    gm1 = (_vx(gross, i + 1) / rev1 * 100) if (gross is not None and rev1 and rev1 != 0) else None
    at0 = (rev0 / ta0) if (rev0 and ta0 and ta0 != 0) else None
    at1 = (rev1 / ta1) if (rev1 and ta1 and ta1 != 0) else None

    if shares is None or (sh0 is None and sh1 is None) and yf:
        try:
            info = (yf.Ticker(ticker.upper()).info) or {}
            sh_out = info.get("sharesOutstanding")
            if sh_out is not None:
                sh0 = sh0 or _safe_float(sh_out)
        except Exception:
            pass

    p1 = ni0 is not None and ni0 > 0
    p2 = ocf0 is not None and ocf0 > 0
    p3 = roa0 is not None and roa1 is not None and roa0 > roa1
    p4 = ocf0 is not None and ni0 is not None and ocf0 > ni0
    p5 = bool(ta0 and ta0 != 0 and ta1 and ta1 != 0 and (lt0 / ta0) < (lt1 / ta1))
    p6 = cr0 is not None and cr1 is not None and cr0 > cr1
    p7 = (sh0 is not None and sh1 is not None and sh0 <= sh1) if (sh0 is not None and sh1 is not None) else True
    p8 = gm0 is not None and gm1 is not None and gm0 > gm1
    p9 = at0 is not None and at1 is not None and at0 > at1
    return (p1, p2, p3, p4, p5, p6, p7, p8, p9)


def _build_fscore_series(ticker: str, fin: pd.DataFrame, bal: pd.DataFrame, cf: pd.DataFrame) -> Tuple[int, List[FScoreCriterionSeries]]:
    criteria_out: List[FScoreCriterionSeries] = []
    ncol = len(fin.columns)
    if ncol < 2:
        return 0, []

    max_pairs = min(3, ncol - 1)
    latest_passes = _fscore_passes_for_pair(fin, bal, cf, ticker, 0)
    total = sum(1 for p in latest_passes if p)

    for ci, (key, label) in enumerate(_FSCORE_KEYS):
        hist: List[FScoreYearPoint] = []
        for k in range(max_pairs):
            passes = _fscore_passes_for_pair(fin, bal, cf, ticker, k)
            yr = _col_year(fin, k)
            hist.append(FScoreYearPoint(year=yr, pass_flag=bool(passes[ci])))
        criteria_out.append(FScoreCriterionSeries(key=key, label=label, history=list(reversed(hist))))

    return total, criteria_out


def _dupont_tree_from_df(dupont_df: pd.DataFrame) -> Optional[DuPontTreePayload]:
    if dupont_df is None or dupont_df.empty:
        return None
    row0 = dupont_df.iloc[0]
    npm = float(row0.get("NPM %") or 0)
    at = float(row0.get("Asset Turnover") or 0)
    em = float(row0.get("Equity Mult.") or 0)
    roe = float(row0.get("ROE %") or 0)

    tail = dupont_df.iloc[1:6]
    def avg(col: str) -> Optional[float]:
        if col not in tail.columns:
            return None
        s = tail[col].dropna()
        if s.empty:
            return None
        return float(s.mean())

    def node(
        nid: str,
        lbl: str,
        val: float,
        unit: str,
        col: str,
    ) -> DuPontTreeNode:
        a = avg(col)
        vs = ((val - a) / abs(a) * 100) if (a is not None and a != 0) else None
        if vs is None:
            tr = "flat"
        elif vs > 2:
            tr = "up"
        elif vs < -2:
            tr = "down"
        else:
            tr = "flat"
        return DuPontTreeNode(
            id=nid,
            label=lbl,
            value=round(val, 4),
            unit=unit,
            avg_5y=round(a, 4) if a is not None else None,
            vs_5y_avg_pct=round(vs, 2) if vs is not None else None,
            trend=tr,
        )

    root = node("roe", "ROE", roe, "pct", "ROE %")
    return DuPontTreePayload(
        root=root,
        npm=node("npm", "Net margin", npm, "pct", "NPM %"),
        asset_turnover=node("at", "Asset turnover", at, "x", "Asset Turnover"),
        equity_mult=node("em", "Equity multiplier", em, "x", "Equity Mult."),
    )


def _build_sankey_nivo(ticker: str) -> SankeyGraphPayload:
    d = get_income_statement_sankey_data(ticker)
    rev = max(d.get("revenue") or 0, 1)
    cogs = min(abs(d.get("cogs") or 0), rev * 0.999)
    gp = max(d.get("gross_profit") or 0, 0)
    opex = max(d.get("opex") or 0, 0)
    oi = d.get("operating_income") or 0
    tax = max(d.get("tax_interest_other") or 0, 0)
    ni = d.get("net_income") or 0

    nodes = [
        SankeyNivoNode(id="revenue", label="Revenue"),
        SankeyNivoNode(id="cogs", label="COGS"),
        SankeyNivoNode(id="gross_profit", label="Gross profit"),
        SankeyNivoNode(id="opex", label="Operating expenses"),
        SankeyNivoNode(id="operating_income", label="Operating income"),
        SankeyNivoNode(id="tax_other", label="Tax & other"),
        SankeyNivoNode(id="net_income", label="Net income"),
    ]
    links: List[SankeyNivoLink] = [
        SankeyNivoLink(source="revenue", target="cogs", value=float(cogs)),
        SankeyNivoLink(source="revenue", target="gross_profit", value=float(max(gp, rev - cogs))),
    ]
    gp_v = links[-1].value
    links.append(SankeyNivoLink(source="gross_profit", target="opex", value=float(min(opex, gp_v))))
    links.append(SankeyNivoLink(source="gross_profit", target="operating_income", value=float(max(oi, gp_v - opex))))
    oi_v = links[-1].value
    tax_v = min(tax, max(oi_v, 0))
    links.append(SankeyNivoLink(source="operating_income", target="tax_other", value=float(tax_v)))
    links.append(SankeyNivoLink(source="operating_income", target="net_income", value=float(max(abs(ni), 0))))
    return SankeyGraphPayload(nodes=nodes, links=links)


def _build_waterfall(fin: pd.DataFrame) -> List[WaterfallStep]:
    if fin is None or fin.empty or len(fin.columns) < 2:
        return []
    c0, c1 = fin.columns[0], fin.columns[1]

    def cell(row_names: Tuple[str, ...]) -> Tuple[float, float]:
        v0 = v1 = 0.0
        for name in row_names:
            if name in fin.index:
                v0 += float(_safe_float(fin.loc[name, c0]) or 0)
                v1 += float(_safe_float(fin.loc[name, c1]) or 0)
        return v0, v1

    gp0, gp1 = cell(("Gross Profit",))
    if gp0 == 0 and gp1 == 0:
        r0, r1 = cell(("Total Revenue", "Revenue"))
        cg0, cg1 = cell(("Cost Of Revenue", "Cost of Revenue"))
        gp0, gp1 = r0 - cg0, r1 - cg1

    oi0, oi1 = cell(("Operating Income", "EBIT"))
    opex0 = max(gp0 - oi0, 0)
    opex1 = max(gp1 - oi1, 0)

    d_gp = gp0 - gp1
    d_opex = opex0 - opex1

    y0 = _col_year(fin, 0)
    y1 = _col_year(fin, 1)
    cum = oi1
    steps: List[WaterfallStep] = [
        WaterfallStep(id="prior_oi", label=f"Operating income {y1}", value=oi1, cumulative=cum, step_type="total"),
        WaterfallStep(id="d_gp", label="Gross profit change", value=d_gp, cumulative=cum + d_gp, step_type="relative"),
        WaterfallStep(id="d_opex", label="Operating expense change", value=-d_opex, cumulative=cum + d_gp - d_opex, step_type="relative"),
    ]
    final = cum + d_gp - d_opex
    diff = oi0 - final
    if abs(diff) > max(abs(oi0), 1) * 0.02:
        steps.append(WaterfallStep(id="other", label="Other / rounding", value=diff, cumulative=oi0, step_type="relative"))
    steps.append(WaterfallStep(id="current_oi", label=f"Operating income {y0}", value=oi0, cumulative=oi0, step_type="total"))
    return steps


_ANOMALY_ROWS = [
    ("Total Revenue", "Revenue"),
    ("Cost Of Revenue", "COGS"),
    ("Research And Development", "R&D"),
    ("Selling General And Administration", "SG&A"),
    ("Operating Expense", "Operating expenses"),
    ("Operating Income", "Operating income"),
    ("Net Income", "Net income"),
    ("Total Debt", "Total debt"),
    ("Long Term Debt", "Long-term debt"),
    ("Current Debt", "Short-term debt"),
]


def _detect_anomalies(fin: pd.DataFrame, bal: pd.DataFrame, threshold: float = 0.30) -> List[FinancialAnomalyItem]:
    out: List[FinancialAnomalyItem] = []
    if fin is None or fin.empty or len(fin.columns) < 2:
        return out
    c0, c1 = fin.columns[0], fin.columns[1]

    def check_row(idx_name: str, display: str) -> None:
        if idx_name not in fin.index:
            return
        cur = _safe_float(fin.loc[idx_name, c0])
        prev = _safe_float(fin.loc[idx_name, c1])
        if cur is None or prev is None or abs(prev) < 1e-6:
            return
        chg = (cur - prev) / abs(prev)
        if abs(chg) < threshold:
            return
        out.append(
            FinancialAnomalyItem(
                account_key=idx_name,
                display_name=display,
                prior_value=prev,
                current_value=cur,
                change_pct=round(chg * 100, 2),
                direction="up" if chg > 0 else "down",
            )
        )

    for key, disp in _ANOMALY_ROWS:
        check_row(key, disp)

    if bal is not None and not bal.empty and len(bal.columns) >= 2:
        b0, b1 = bal.columns[0], bal.columns[1]
        for idx_name, display in [
            ("Current Debt", "Short-term borrowings"),
            ("Long Term Debt", "Long-term debt"),
            ("Total Debt", "Total debt"),
        ]:
            if idx_name not in bal.index:
                continue
            cur = _safe_float(bal.loc[idx_name, b0])
            prev = _safe_float(bal.loc[idx_name, b1])
            if cur is None or prev is None or abs(prev) < 1e-6:
                continue
            chg = (cur - prev) / abs(prev)
            if abs(chg) < threshold:
                continue
            out.append(
                FinancialAnomalyItem(
                    account_key=f"BS:{idx_name}",
                    display_name=display,
                    prior_value=prev,
                    current_value=cur,
                    change_pct=round(chg * 100, 2),
                    direction="up" if chg > 0 else "down",
                )
            )

    out.sort(key=lambda x: abs(x.change_pct or 0), reverse=True)
    return out[:12]


def sankey_nivo_for_ticker(ticker: str) -> Dict[str, Any]:
    """Public helper for /api/market/sankey extended payload."""
    return _build_sankey_nivo(ticker).model_dump()


def build_research_dashboard(ticker: str) -> ResearchDashboardResponse:
    sym = ticker.upper().strip()
    fin, bal, cf = _get_annual_financials_balance_cashflow(sym)
    if fin is None or fin.empty or bal is None or bal.empty:
        return ResearchDashboardResponse(ticker=sym, error="Insufficient financial statements")

    if cf is None or cf.empty:
        cf = pd.DataFrame()

    total, fseries = _build_fscore_series(sym, fin, bal, cf)
    dq = get_dupont_altman_redflags_yoy(sym)
    dupont_df = dq.get("dupont") if dq else None
    tree = _dupont_tree_from_df(dupont_df) if isinstance(dupont_df, pd.DataFrame) else None

    sankey = _build_sankey_nivo(sym)
    waterfall = _build_waterfall(fin)
    anomalies = _detect_anomalies(fin, bal)

    return ResearchDashboardResponse(
        ticker=sym,
        fscore_total=total,
        fscore_criteria=fseries,
        dupont_tree=tree,
        sankey=sankey,
        waterfall=waterfall,
        anomalies=anomalies,
    )
