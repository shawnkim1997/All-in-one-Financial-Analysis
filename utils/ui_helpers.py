"""
UI helper functions for rendering analyst consensus, sensitivity tables, etc.
"""
import pandas as pd
import streamlit as st

from utils.dcf import excel_style_dcf


def _render_analyst_consensus(ticker: str):
    """Render analyst consensus rating with visual badge and target prices."""
    from data.valuation import get_analyst_consensus
    consensus = get_analyst_consensus(ticker)
    if not consensus:
        st.caption("Analyst consensus data not available.")
        return

    rec = (consensus.get("recommendationKey") or "N/A").upper()
    target_mean = consensus.get("targetMeanPrice")
    target_high = consensus.get("targetHighPrice")
    target_low = consensus.get("targetLowPrice")
    num_analysts = consensus.get("numberOfAnalystOpinions", "N/A")
    current = consensus.get("currentPrice")

    # Rating badge colors
    if rec in ("BUY", "STRONG_BUY", "STRONG BUY"):
        badge_bg = "rgba(52, 211, 153, 0.15)"
        badge_border = "rgba(52, 211, 153, 0.4)"
        badge_color = "#34D399"
    elif rec in ("SELL", "STRONG_SELL", "STRONG SELL"):
        badge_bg = "rgba(248, 113, 113, 0.15)"
        badge_border = "rgba(248, 113, 113, 0.4)"
        badge_color = "#F87171"
    else:
        badge_bg = "rgba(251, 191, 36, 0.15)"
        badge_border = "rgba(251, 191, 36, 0.4)"
        badge_color = "#FBBF24"
    rec_display = rec.replace("_", " ")

    upside = ""
    if target_mean and current and current > 0:
        upside_pct = (target_mean - current) / current * 100
        upside_color = "#34D399" if upside_pct > 0 else "#F87171"
        upside = f'<span style="color: {upside_color}; font-family: JetBrains Mono, monospace; font-weight: 600; margin-left: 12px;">{upside_pct:+.1f}% implied</span>'

    if target_mean:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 16px; padding: 16px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; margin-bottom: 12px;">
            <div>
                <div style="color: #6B7280; font-size: 0.65rem; font-weight: 600; letter-spacing: 1px; text-transform: uppercase;">ANALYST RATING</div>
                <span style="display: inline-block; padding: 4px 14px; border-radius: 6px; font-weight: 700; font-family: JetBrains Mono, monospace; background: {badge_bg}; border: 1px solid {badge_border}; color: {badge_color}; font-size: 1.1rem; margin-top: 4px;">{rec_display}</span>
                {upside}
            </div>
            <div style="margin-left: auto; display: flex; gap: 24px;">
                <div style="text-align: center;">
                    <div style="color: #6B7280; font-size: 0.6rem; letter-spacing: 1px;">TARGET (MEAN)</div>
                    <div style="color: #F3F4F6; font-size: 1.1rem; font-family: JetBrains Mono, monospace; font-weight: 700;">${target_mean:,.2f}</div>
                </div>
                <div style="text-align: center;">
                    <div style="color: #6B7280; font-size: 0.6rem; letter-spacing: 1px;">HIGH</div>
                    <div style="color: #34D399; font-size: 0.95rem; font-family: JetBrains Mono, monospace;">${target_high:,.2f}</div>
                </div>
                <div style="text-align: center;">
                    <div style="color: #6B7280; font-size: 0.6rem; letter-spacing: 1px;">LOW</div>
                    <div style="color: #F87171; font-size: 0.95rem; font-family: JetBrains Mono, monospace;">${target_low:,.2f}</div>
                </div>
                <div style="text-align: center;">
                    <div style="color: #6B7280; font-size: 0.6rem; letter-spacing: 1px;">ANALYSTS</div>
                    <div style="color: #D1D5DB; font-size: 0.95rem; font-family: JetBrains Mono, monospace;">{num_analysts}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption("Analyst targets not available.")


def _render_sensitivity_table(fcf: float, total_debt: float, cash: float, shares: float):
    """Render DCF sensitivity table: WACC vs Terminal Growth Rate."""
    wacc_range = [0.065, 0.070, 0.075, 0.080, 0.085, 0.090, 0.095, 0.100]
    tgr_range = [0.020, 0.025, 0.030, 0.035, 0.040]
    rows = []
    for tgr in tgr_range:
        row = {"TGR": f"{tgr*100:.1f}%"}
        for w in wacc_range:
            res = excel_style_dcf(fcf, w, tgr, 0.10, total_debt, cash, shares)
            val = res.get("value_per_share", 0)
            row[f"{w*100:.1f}%"] = f"${val:,.0f}" if val and val > 0 else "N/A"
        rows.append(row)
    return pd.DataFrame(rows).set_index("TGR")
