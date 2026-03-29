"""Institutional Report — gather all quantitative data for Wall Street 10 analysis.

Collects DuPont, Altman Z, F-Score, DCF, anomalies, and yfinance info
into a single rich context string that can be fed to Gemini for
institutional-grade multi-perspective analysis.

All numbers are pre-computed in Python (ATLAS hybrid principle: LLM never computes).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from server.utils.safe_float import _safe_float

logger = logging.getLogger(__name__)


def _fmt(v: Any, suffix: str = "", prefix: str = "") -> str:
    """Format a value for human-readable context."""
    if v is None:
        return "N/A"
    if isinstance(v, float):
        if abs(v) >= 1e9:
            return f"{prefix}{v / 1e9:.1f}B{suffix}"
        if abs(v) >= 1e6:
            return f"{prefix}{v / 1e6:.1f}M{suffix}"
        return f"{prefix}{v:.2f}{suffix}"
    return str(v)


def gather_quantitative_context(ticker: str) -> str:
    """Build a comprehensive quantitative context string (~2500-3500 words).

    This is the core data payload that gets injected into the institutional
    analysis prompt.  The LLM interprets these pre-computed numbers — it does
    NOT compute anything itself.
    """
    parts: List[str] = []
    ticker = ticker.upper()

    # ── 1. Basic Company Info (yfinance) ──────────────────────────────
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception:
        info = {}

    parts.append(f"""=== COMPANY PROFILE ===
Company: {info.get('longName', ticker)} ({ticker})
Sector: {info.get('sector', 'N/A')} | Industry: {info.get('industry', 'N/A')}
Market Cap: {_fmt(info.get('marketCap'), prefix='$')}
Enterprise Value: {_fmt(info.get('enterpriseValue'), prefix='$')}
Current Price: ${info.get('currentPrice', 'N/A')}
52W High: ${info.get('fiftyTwoWeekHigh', 'N/A')} | 52W Low: ${info.get('fiftyTwoWeekLow', 'N/A')}
Beta: {info.get('beta', 'N/A')}
Employees: {info.get('fullTimeEmployees', 'N/A')}""")

    # ── 2. Key Financial Metrics ──────────────────────────────────────
    rev = info.get('totalRevenue')
    ni = info.get('netIncomeToCommon')
    gm = info.get('grossMargins')
    om = info.get('operatingMargins')
    pm = info.get('profitMargins')
    roe = info.get('returnOnEquity')
    roa = info.get('returnOnAssets')
    de = info.get('debtToEquity')
    cr = info.get('currentRatio')
    fcf = info.get('freeCashflow')
    ocf = info.get('operatingCashflow')
    rev_growth = info.get('revenueGrowth')
    earn_growth = info.get('earningsGrowth')

    parts.append(f"""
=== KEY FINANCIALS (TTM) ===
Revenue: {_fmt(rev, prefix='$')} | Revenue Growth: {f'{rev_growth*100:.1f}%' if rev_growth else 'N/A'}
Net Income: {_fmt(ni, prefix='$')} | Earnings Growth: {f'{earn_growth*100:.1f}%' if earn_growth else 'N/A'}
Gross Margin: {f'{gm*100:.1f}%' if gm else 'N/A'} | Operating Margin: {f'{om*100:.1f}%' if om else 'N/A'} | Net Margin: {f'{pm*100:.1f}%' if pm else 'N/A'}
ROE: {f'{roe*100:.1f}%' if roe else 'N/A'} | ROA: {f'{roa*100:.1f}%' if roa else 'N/A'}
D/E: {de if de else 'N/A'} | Current Ratio: {cr if cr else 'N/A'}
Free Cash Flow: {_fmt(fcf, prefix='$')} | Operating Cash Flow: {_fmt(ocf, prefix='$')}
FCF Yield: {f'{fcf/info.get("marketCap")*100:.1f}%' if fcf and info.get("marketCap") else 'N/A'}""")

    # ── 3. Valuation Multiples ────────────────────────────────────────
    pe = info.get('trailingPE')
    fpe = info.get('forwardPE')
    ps = info.get('priceToSalesTrailing12Months')
    pb = info.get('priceToBook')
    ev_ebitda = info.get('enterpriseToEbitda')
    ev_rev = info.get('enterpriseToRevenue')
    peg = info.get('pegRatio')
    div_yield = info.get('dividendYield')
    payout = info.get('payoutRatio')

    parts.append(f"""
=== VALUATION MULTIPLES ===
P/E (TTM): {f'{pe:.1f}x' if pe else 'N/A'} | Forward P/E: {f'{fpe:.1f}x' if fpe else 'N/A'}
P/S: {f'{ps:.1f}x' if ps else 'N/A'} | P/B: {f'{pb:.1f}x' if pb else 'N/A'}
EV/EBITDA: {f'{ev_ebitda:.1f}x' if ev_ebitda else 'N/A'} | EV/Revenue: {f'{ev_rev:.1f}x' if ev_rev else 'N/A'}
PEG Ratio: {f'{peg:.2f}' if peg else 'N/A'}
Dividend Yield: {f'{div_yield*100:.2f}%' if div_yield else 'N/A'} | Payout Ratio: {f'{payout*100:.0f}%' if payout else 'N/A'}""")

    # ── 4. Analyst Consensus ──────────────────────────────────────────
    target_mean = info.get('targetMeanPrice')
    target_high = info.get('targetHighPrice')
    target_low = info.get('targetLowPrice')
    rec = info.get('recommendationKey')
    num_analysts = info.get('numberOfAnalystOpinions')

    cur_price = info.get('currentPrice') or info.get('regularMarketPrice')
    upside = None
    if target_mean and cur_price and cur_price > 0:
        upside = (target_mean - cur_price) / cur_price * 100

    parts.append(f"""
=== ANALYST CONSENSUS ===
Target Mean: ${target_mean or 'N/A'} | High: ${target_high or 'N/A'} | Low: ${target_low or 'N/A'}
Implied Upside: {f'{upside:+.1f}%' if upside is not None else 'N/A'}
Recommendation: {rec or 'N/A'} | # Analysts: {num_analysts or 'N/A'}""")

    # ── 5. Shareholder Returns ────────────────────────────────────────
    buyback = info.get('sharesOutstanding')
    shares_float = info.get('floatShares')
    parts.append(f"""
=== SHAREHOLDER RETURNS ===
Shares Outstanding: {_fmt(buyback)} | Float: {_fmt(shares_float)}
Dividend Yield: {f'{div_yield*100:.2f}%' if div_yield else 'None'}
Payout Ratio: {f'{payout*100:.0f}%' if payout else 'N/A'}
Free Cash Flow: {_fmt(fcf, prefix='$')} (available for buybacks/dividends)""")

    # ── 6. DuPont Decomposition + Altman Z + Red Flags ────────────────
    try:
        from server.services.financial_metrics import get_dupont_altman_redflags_yoy
        health = get_dupont_altman_redflags_yoy(ticker)
        if health:
            dupont_df = health.get("dupont")
            if dupont_df is not None and not dupont_df.empty:
                rows_str = dupont_df.to_string(index=False)
                parts.append(f"""
=== DUPONT ROE DECOMPOSITION (3-Year) ===
ROE = Net Profit Margin × Asset Turnover × Equity Multiplier
{rows_str}""")

            altman = health.get("altman_z")
            if altman is not None:
                zone = "Safe (>2.99)" if altman > 2.99 else ("Gray Zone (1.81-2.99)" if altman > 1.81 else "Distress (<1.81)")
                parts.append(f"""
=== ALTMAN Z-SCORE ===
Z-Score: {altman:.2f} — {zone}""")

            red_flags = health.get("red_flags", [])
            if red_flags:
                flags_str = "\n".join(f"  ⚠ {rf.get('flag', rf) if isinstance(rf, dict) else rf}" for rf in red_flags[:10])
                parts.append(f"""
=== RED FLAGS ===
{flags_str}""")

            yoy_data = health.get("yoy", [])
            if yoy_data:
                yoy_str = "\n".join(f"  {y.get('Ratio', '')}: {y.get('Comment', '')}" for y in yoy_data)
                parts.append(f"""
=== YOY RATIO CHANGES ===
{yoy_str}""")
    except Exception as e:
        logger.warning("DuPont/Altman failed for %s: %s", ticker, e)

    # ── 7. Piotroski F-Score ──────────────────────────────────────────
    try:
        from server.services.research_dashboard import build_research_dashboard
        dash = build_research_dashboard(ticker)
        if dash and dash.fscore_total is not None:
            score = dash.fscore_total
            criteria_str = ""
            for c in dash.fscore_criteria:
                latest = c.history[0] if c.history else None
                status = "✓" if (latest and latest.pass_flag) else "✗"
                criteria_str += f"  {status} {c.label}\n"
            parts.append(f"""
=== PIOTROSKI F-SCORE: {score}/9 ===
{criteria_str.rstrip()}""")

            # Anomalies
            if dash.anomalies:
                anom_str = "\n".join(
                    f"  {'▲' if a.direction == 'up' else '▼'} {a.display_name}: "
                    f"{f'{a.change_pct:+.1f}%' if a.change_pct else 'N/A'} YoY"
                    for a in dash.anomalies[:8]
                )
                parts.append(f"""
=== YOY ANOMALIES (>30% change) ===
{anom_str}""")
    except Exception as e:
        logger.warning("F-Score/anomalies failed for %s: %s", ticker, e)

    # ── 8. DCF Valuation (Smart Defaults) ─────────────────────────────
    try:
        from server.services.dcf_engine import dcf_10y_2stage, reverse_dcf

        base_fcf = _safe_float(info.get("freeCashflow"))
        total_debt = _safe_float(info.get("totalDebt")) or 0
        cash = _safe_float(info.get("totalCash")) or 0
        shares = _safe_float(info.get("sharesOutstanding")) or 1

        if base_fcf and base_fcf > 0 and shares and shares > 0:
            beta_val = info.get("beta", 1.0) or 1.0
            wacc = 0.04 + beta_val * 0.05  # CAPM approximation
            wacc = max(0.06, min(0.15, wacc))
            tg = 0.025
            growth = min(0.25, max(-0.05, (rev_growth or 0.08)))

            # 3 scenarios
            scenarios = {}
            for label, g_mult, w_adj in [("Bear", 0.5, 0.02), ("Base", 1.0, 0), ("Bull", 1.5, -0.01)]:
                g = growth * g_mult
                w = wacc + w_adj
                ev = dcf_10y_2stage(base_fcf, w, tg, g)
                eq = ev - total_debt + cash
                vps = eq / shares if shares > 0 else 0
                scenarios[label] = round(vps, 2)

            # Reverse DCF
            try:
                implied_g = reverse_dcf(
                    current_price=cur_price or 0,
                    shares=shares,
                    total_debt=total_debt,
                    cash=cash,
                    wacc=wacc,
                    term_growth=tg,
                    fcf_base=base_fcf,
                )
            except Exception:
                implied_g = None

            parts.append(f"""
=== DCF VALUATION (ATLAS Engine) ===
Base FCF: {_fmt(base_fcf, prefix='$')} | WACC: {wacc*100:.1f}% | Terminal Growth: {tg*100:.1f}%
FCF Growth (Base): {growth*100:.1f}%
Bear Case: ${scenarios.get('Bear', 'N/A')}/share
Base Case: ${scenarios.get('Base', 'N/A')}/share
Bull Case: ${scenarios.get('Bull', 'N/A')}/share
Current Price: ${cur_price or 'N/A'}
Reverse DCF Implied Growth: {f'{implied_g*100:.1f}%' if implied_g is not None else 'N/A'}""")
    except Exception as e:
        logger.warning("DCF failed for %s: %s", ticker, e)

    # ── 9. Peer Comparison ────────────────────────────────────────────
    try:
        from server.services.peer_comparison_service import build_peer_comparison
        peer_data = build_peer_comparison(ticker)
        peers = peer_data.get("peers", []) if peer_data else []
        if peers:
            peer_lines = []
            for p in peers[:6]:
                name = p.get("ticker", p.get("symbol", "?"))
                p_pe = p.get("pe", p.get("trailingPE"))
                p_ps = p.get("ps", p.get("priceToSales"))
                p_pb = p.get("pb", p.get("priceToBook"))
                peer_lines.append(
                    f"  {name}: P/E={f'{p_pe:.1f}' if p_pe else 'N/A'} "
                    f"P/S={f'{p_ps:.1f}' if p_ps else 'N/A'} "
                    f"P/B={f'{p_pb:.1f}' if p_pb else 'N/A'}"
                )
            if peer_lines:
                parts.append(f"""
=== PEER VALUATION ===
{chr(10).join(peer_lines)}""")
    except Exception as e:
        logger.warning("Peer comparison failed for %s: %s", ticker, e)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Wall Street 10 Prompt Builder
# ---------------------------------------------------------------------------

WALL_STREET_10_PROMPT = """You are a team of 10 elite Wall Street analysts, each representing a different institutional perspective. Analyze {ticker} using the comprehensive quantitative data below.

ALL numbers are pre-computed by our quantitative engine. DO NOT recalculate or invent new numbers. Your job is to INTERPRET these numbers from each firm's unique analytical lens.

{context}

═══════════════════════════════════════════════════════════════
Produce a JSON object with exactly these 10 keys. Each value is a markdown string (2-4 paragraphs with bullet points). Be specific — cite the actual numbers from the data above.

{{
  "executive_summary": "2-3 sentence overall verdict with a conviction rating (Strong Buy / Buy / Hold / Sell / Strong Sell) and 12-month outlook",

  "goldman_sachs": "**Goldman Sachs — Investment Conviction Framework**\\nConviction rating, key thesis, catalysts, and price target rationale. Reference DCF valuation, analyst consensus, and current multiples.",

  "morgan_stanley": "**Morgan Stanley — Scenario Analysis**\\nBull/Base/Bear cases with specific price targets from DCF. Probability-weight each scenario. Key swing factors.",

  "jp_morgan": "**JP Morgan — Sector Relative Value**\\nHow does {ticker} compare to sector peers on P/E, P/S, EV/EBITDA? Premium/discount justified? Sector rotation implications.",

  "blackrock": "**BlackRock — Risk Factor Decomposition**\\nSystematic vs. idiosyncratic risk. Altman Z interpretation, leverage analysis, red flags assessment. Downside protection.",

  "bridgewater": "**Bridgewater — Macro Overlay**\\nRate sensitivity (via beta, D/E), currency exposure, inflation hedge characteristics. Where in the economic cycle does this company perform best?",

  "berkshire": "**Berkshire Hathaway — Intrinsic Value & Moat**\\nDurable competitive advantage? Pricing power (gross margin trend)? Management quality (capital allocation via FCF, buybacks, ROE). Would Buffett buy this?",

  "citadel": "**Citadel — Alpha Signal Identification**\\nYoY anomalies, earnings quality (OCF vs NI via F-Score), accounting signals. Where is the market mispricing this stock?",

  "two_sigma": "**Two Sigma — Quantitative Quality Score**\\nF-Score {fscore}/9 assessment. DuPont decomposition quality. Trend stability. Statistical edge in current valuation.",

  "elliott": "**Elliott Management — Shareholder Value & Activism**\\nCapital return efficiency (FCF yield, dividend, buybacks). Is management maximizing shareholder value? What would an activist push for?"
}}

CRITICAL RULES:
- Output ONLY the JSON object. No markdown fences, no commentary before/after.
- Each section must reference specific numbers from the data.
- Be analytical and actionable, not generic.
- Answer in English.
"""


def build_institutional_prompt(ticker: str, context: str, fscore: int = 0) -> str:
    """Build the Wall Street 10 mega-prompt with pre-computed data injected."""
    return WALL_STREET_10_PROMPT.format(
        ticker=ticker.upper(),
        context=context,
        fscore=fscore,
    )
