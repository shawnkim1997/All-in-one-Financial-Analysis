"""Tab 1 — Financial Health (Tables & Charts): Sankey, Radar, F-Score,
Altman Z, red flags, sector metrics, YoY changes, quarterly momentum/ratios."""

import pandas as pd
import streamlit as st
from data.sec_downloader import get_10k_sections
from data.ratios import get_dupont_altman_redflags_yoy, get_quarterly_momentum, get_quarterly_ratio_changes
from data.scores import (
    get_income_statement_sankey_data, get_radar_metrics_normalized, _build_radar_figure,
    get_piotroski_fscore, get_sector_specific_metrics,
)
from data.scores_ai import sankey_data_from_ai, piotroski_from_ai, radar_metrics_from_ai
from ai.gemini_sec import get_sec_financials_llm
from utils.charts import (
    _build_sankey_figure, _build_radar_figure_from_metrics,
    _build_radar_from_manual, _apply_dark_theme,
)
try:
    from yahooquery import Ticker as YQTicker
except ImportError:
    YQTicker = None


def _style_change_column(df: pd.DataFrame):
    """Green for improvement (+), red for decline (-) in Change column."""
    change_col = "Change (%)" if "Change (%)" in df.columns else "Change"
    if change_col not in df.columns or df.empty:
        return df.style
    def _cell_style(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        s = str(v).strip()
        if s == "—":
            return ""
        if s.startswith("+") or "↑" in s:
            return "background-color: #d4edda; color: #155724"
        if s.startswith("-") or "↓" in s:
            return "background-color: #f8d7da; color: #721c24"
        return ""
    return df.style.apply(lambda col: [_cell_style(v) for v in col], subset=[change_col])


def render_tab1_quantitative(ticker, quant_ticker, market, sector, industry, google_api_key, sec_email):
    """Render the Financial Health section of Tab 1."""
    ai_data = {}
    if market and "US" in market and google_api_key and sec_email:
        with st.spinner("SEC 10-K 원본에서 재무제표 데이터를 해독하여 그래프를 생성 중입니다... (약 30~60초 소요)"):
            sections, _ = get_10k_sections(ticker, sec_email)
            item8 = (sections or {}).get("item8") or ""
            if item8.strip():
                ai_data = get_sec_financials_llm(google_api_key, item8, ticker)
    q = get_dupont_altman_redflags_yoy(quant_ticker)
    dupont_df = (q or {}).get("dupont") if q else None
    if q or ai_data:
        st.markdown("---")
        st.markdown("#### 📊 Financial Health (Tables & Charts)")
        c1, c2 = st.columns(2)
        with c1:
            if ai_data and ai_data.get("current_yr"):
                sankey_data = sankey_data_from_ai(ai_data)
            else:
                sankey_data = get_income_statement_sankey_data(quant_ticker)
            if sankey_data.get("revenue", 0) > 0:
                fig_sankey = _build_sankey_figure(sankey_data)
                if fig_sankey is not None:
                    _apply_dark_theme(fig_sankey)
                    st.plotly_chart(fig_sankey, use_container_width=True)
            else:
                st.caption("Income Statement flow: data not available.")
        with c2:
            if ai_data and ai_data.get("current_yr"):
                radar_metrics = radar_metrics_from_ai(ai_data)
                fig_radar = _build_radar_figure_from_metrics(radar_metrics) if radar_metrics else None
            else:
                fig_radar = _build_radar_figure(quant_ticker)
            if fig_radar is not None:
                _apply_dark_theme(fig_radar)
                st.plotly_chart(fig_radar, use_container_width=True)
            else:
                st.caption("Financial radar: need 2+ years of data.")
                with st.expander("Manual Data Entry (Radar Chart Fallback)", expanded=False):
                    st.caption("Enter 5 key ratios to plot a custom radar. ROE %, Current Ratio, Asset Turnover, Equity Mult., Revenue YoY %.")
                    roe_man = st.number_input("ROE %", value=15.0, min_value=-50.0, max_value=100.0, step=1.0, key="radar_roe")
                    cr_man = st.number_input("Current Ratio", value=1.5, min_value=0.0, max_value=10.0, step=0.1, key="radar_cr")
                    at_man = st.number_input("Asset Turnover", value=0.8, min_value=0.0, max_value=5.0, step=0.1, key="radar_at")
                    em_man = st.number_input("Equity Mult.", value=2.0, min_value=0.5, max_value=10.0, step=0.1, key="radar_em")
                    yoy_man = st.number_input("Revenue YoY %", value=10.0, min_value=-50.0, max_value=200.0, step=1.0, key="radar_yoy")
                    if st.button("Plot Radar", key="radar_plot_btn"):
                        fig_man = _build_radar_from_manual(roe_man, cr_man, at_man, em_man, yoy_man)
                        if fig_man is not None:
                            st.session_state["radar_manual_fig"] = fig_man
                    if st.session_state.get("radar_manual_fig") is not None:
                        _apply_dark_theme(st.session_state["radar_manual_fig"])
                        st.plotly_chart(st.session_state["radar_manual_fig"], use_container_width=True)
                with st.expander("Debug: Raw YahooQuery Data", expanded=False):
                    if YQTicker and quant_ticker:
                        try:
                            yq_ticker = YQTicker(quant_ticker.upper())
                            inc_raw = yq_ticker.income_statement(trailing=False)
                            bal_raw = yq_ticker.balance_sheet(trailing=False)
                            if inc_raw is not None and not inc_raw.empty:
                                st.caption("Income statement (last 2 periods) — check column names for mapping.")
                                st.dataframe(inc_raw.tail(2), use_container_width=True, hide_index=True)
                            else:
                                st.caption("Income statement: no data.")
                            if bal_raw is not None and not bal_raw.empty:
                                st.caption("Balance sheet (last 2 periods) — check column names for mapping.")
                                st.dataframe(bal_raw.tail(2), use_container_width=True, hide_index=True)
                            else:
                                st.caption("Balance sheet: no data.")
                        except Exception as e:
                            st.error(f"YahooQuery debug failed: {e}")
                    else:
                        st.caption("YahooQuery not available or no ticker selected.")
        if ai_data and ai_data.get("current_yr"):
            piot = piotroski_from_ai(ai_data)
        else:
            piot = get_piotroski_fscore(quant_ticker)
        st.markdown("**Piotroski F-Score (9-point checklist)**")
        score = piot.get("score", 0)
        legend = "**Score 8–9: Excellent** · 4–7: Average · 0–3: High Risk"
        st.metric("F-Score", f"{score} / 9", legend)
        if ai_data and ai_data.get("current_yr"):
            st.caption("*(from SEC 10-K Item 8)*")
        elif piot.get("used_ttm"):
            st.caption("*(Estimated via TTM Data)*")
        st.caption("✅ = Good (passes criterion). ❌ = Fails criterion.")
        criteria = piot.get("criteria", [])
        if criteria:
            cols = st.columns(3)
            for i, (label, passed) in enumerate(criteria):
                with cols[i % 3]:
                    st.caption(("✅ " if passed else "❌ ") + label)
        az = (q or {}).get("altman_z")
        if az is not None:
            st.caption(f"**Altman Z-Score:** {az} (Safe > 2.99 · Grey 1.81–2.99 · Distress < 1.81)")
        red_flags = (q or {}).get("red_flags") or []
        if red_flags:
            for rf in red_flags:
                val = rf.get("value")
                val_str = "N/A" if (val is None or (isinstance(val, float) and (pd.isna(val) or val != val))) else val
                st.warning(f"**{rf.get('metric')}:** {val_str} (threshold: {rf.get('threshold')})")
        elif dupont_df is not None and not dupont_df.empty:
            st.success("No red flags (Current Ratio ≥ 1.0, Interest Coverage ≥ 1.5).")
        sector_metrics = get_sector_specific_metrics(quant_ticker, sector) if quant_ticker else {}
        if sector_metrics:
            st.markdown("**Sector-specific metrics**")
            cols = st.columns(min(len(sector_metrics), 4))
            for i, (k, v) in enumerate(sector_metrics.items()):
                with cols[i % len(cols)]:
                    disp = f"{v}" if v is not None else "N/A"
                    st.metric(k, disp, None)
        yoy_list = (q or {}).get("yoy") or []
        if yoy_list:
            st.markdown("**YoY ratio changes**")
            rows_yoy = []
            for item in yoy_list:
                cur = item.get("Latest")
                if cur is not None and isinstance(cur, (int, float)):
                    cur = round(cur, 2)
                chg_pp = item.get("YoY (pp)")
                chg_pct = item.get("YoY %")
                if chg_pp is not None:
                    chg_str = f"{chg_pp:+.1f}%"
                elif chg_pct is not None:
                    chg_str = f"{chg_pct:+.1f}%"
                else:
                    chg_str = "—"
                status = "↑" if (chg_pp is not None and chg_pp > 0) or (chg_pct is not None and chg_pct > 0) else ("↓" if (chg_pp is not None and chg_pp < 0) or (chg_pct is not None and chg_pct < 0) else "—")
                cur_disp = f"{cur:.2f}" if isinstance(cur, (int, float)) else ("—" if cur is None else str(cur))
                rows_yoy.append({"Metric": item.get("Ratio"), "Current Value": cur_disp, "Change (%)": chg_str, "Status": status})
            if rows_yoy:
                df_yoy = pd.DataFrame(rows_yoy)
                st.dataframe(_style_change_column(df_yoy), use_container_width=True, hide_index=True)
        st.markdown("**Quarter ratio changes**")
        qmom = get_quarterly_momentum(quant_ticker)
        qoq_rows = get_quarterly_ratio_changes(quant_ticker)
        qoq_r, qoq_n = qmom.get("qoq_revenue_pct"), qmom.get("qoq_ni_pct")
        build = []
        if qoq_r is not None:
            build.append({"Metric": "Revenue", "Current Value": "—", "Change (%)": f"{qoq_r:+.1f}%", "Status": "↑" if qoq_r > 0 else "↓"})
        if qoq_n is not None:
            build.append({"Metric": "Net Income", "Current Value": "—", "Change (%)": f"{qoq_n:+.1f}%", "Status": "↑" if qoq_n > 0 else "↓"})
        for r in qoq_rows:
            r_copy = dict(r)
            if "Current Value" in r_copy:
                v = r_copy["Current Value"]
                if isinstance(v, (int, float)):
                    r_copy["Current Value"] = f"{round(v, 2):.2f}"
                elif v is None:
                    r_copy["Current Value"] = "—"
                else:
                    r_copy["Current Value"] = str(v)
            if "Change" in r_copy and "Change (%)" not in r_copy:
                r_copy["Change (%)"] = r_copy.pop("Change", "—")
            if "Trend" in r_copy:
                r_copy["Status"] = r_copy.pop("Trend", "—")
            build.append(r_copy)
        if build:
            df_q = pd.DataFrame(build)
            if "Change" in df_q.columns and "Change (%)" not in df_q.columns:
                df_q = df_q.rename(columns={"Change": "Change (%)"})
            if "Trend" in df_q.columns:
                df_q = df_q.rename(columns={"Trend": "Status"})
            st.dataframe(_style_change_column(df_q), use_container_width=True, hide_index=True)
        elif not qmom.get("df") or qmom["df"].empty:
            st.caption("Quarterly data not available for this ticker.")
    else:
        st.info("Quantitative data not available for this ticker.")
