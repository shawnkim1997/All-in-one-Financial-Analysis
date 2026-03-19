import pandas as pd
import streamlit as st
from config.constants import SECTORS
from data.ratios import get_comps_data
from ai.gemini_insights import get_industry_outlook


def render_tab3(ticker):
    st.subheader("Top-Down Sector Analysis")
    st.markdown("Select an **industry** to load peer multiples (Forward P/E, EV/EBITDA, P/B). Green = lowest (undervalued), Red = highest. Optionally generate an **AI Industry Outlook**.")
    sector_options = list(SECTORS.keys())
    selected_industry = st.selectbox("Select industry", sector_options, key="sector_select")
    tickers_list = list(SECTORS.get(selected_industry, []))
    if not tickers_list:
        st.warning("No tickers defined for this industry.")
    else:
        with st.spinner("Fetching market data..."):
            df_comps = get_comps_data(tuple(tickers_list))
        if df_comps.empty:
            st.warning("Could not fetch comps from yfinance. One or more tickers may have failed; try again later.")
        else:
            df_display = df_comps.copy()
            for col in ["Forward P/E", "EV/EBITDA", "P/B"]:
                if col not in df_display.columns:
                    continue
                df_display[col] = df_display[col].apply(
                    lambda x: "N/A" if (x is None or (isinstance(x, float) and pd.isna(x))) else x
                )
            try:
                styled = df_comps.style
                for col in ["Forward P/E", "EV/EBITDA", "P/B"]:
                    if col not in df_comps.columns:
                        continue
                    s = pd.to_numeric(df_comps[col], errors="coerce")
                    valid = s.dropna()
                    if len(valid) < 2:
                        continue
                    lo, hi = valid.min(), valid.max()
                    if lo == hi:
                        continue
                    def color_fn(v, lo_val=lo, hi_val=hi):
                        if pd.isna(v):
                            return ""
                        try:
                            x = float(v)
                        except (TypeError, ValueError):
                            return ""
                        if x <= lo_val:
                            return "background-color: rgba(0, 200, 83, 0.35); color: #0d5c2e"
                        if x >= hi_val:
                            return "background-color: rgba(255, 82, 82, 0.35); color: #b71c1c"
                        return ""
                    styled = styled.map(color_fn, subset=[col])
                styled = styled.format(subset=["Forward P/E", "EV/EBITDA", "P/B"], formatter=lambda x: "N/A" if (pd.isna(x) or x is None) else f"{x:.2f}")
                st.dataframe(styled, use_container_width=True, hide_index=True)
            except Exception:
                st.dataframe(df_display, use_container_width=True, hide_index=True)
        st.caption("Lowest multiple in each column = green (relatively undervalued); highest = red.")

    st.markdown("---")
    st.markdown("#### AI Industry Outlook")
    if st.button("Generate Industry Outlook", key="industry_outlook_btn"):
        if not tickers_list:
            st.error("Select an industry above first.")
        elif not st.session_state.get("google_api_key"):
            st.error("Enter your Google API Key in the sidebar.")
        else:
            try:
                with st.spinner("Generating industry outlook with Gemini..."):
                    report = get_industry_outlook(
                        st.session_state["google_api_key"],
                        selected_industry,
                        tickers_list,
                    )
                st.success("Done.")
                st.markdown(report)
            except RuntimeError as e:
                st.error(str(e))
            except Exception as e:
                st.error("Failed to generate outlook. See details below.")
                with st.expander("Error details"):
                    st.code(repr(e), language="text")
