"""Tab 1 — Deep-Dive AI Analysis: Management Strategy & Risk Factors buttons,
display of saved results."""

import streamlit as st
from data.sec_downloader import get_10k_sections
from data.fundamentals import get_sector_industry
from ai.gemini_core import _gemini_forensic_audit
from ai.gemini_sec import get_gemini_item7_strategy_stream, get_gemini_item1a_risks_stream


def render_tab1_ai_analysis(ticker, quant_ticker, market):
    """Render the Deep-Dive Analysis (AI) section of Tab 1."""
    st.markdown("---")
    st.markdown("#### 🔍 Deep-Dive Analysis (AI)")
    st.caption("10-K sections are cached in **data/**; repeat runs use cache for instant AI analysis. First run may take 20–60 s to fetch 10-K; Gemini then streams in ~5–10 s.")
    if not ticker:
        st.caption("Enter a ticker in the sidebar to enable analysis.")
    else:
        api_ok = bool(st.session_state.get("google_api_key"))
        email_ok = bool(st.session_state.get("sec_email"))
        err_msg = []
        if not api_ok:
            err_msg.append("Google API Key")
        if not email_ok:
            err_msg.append("SEC EDGAR Email")
        if err_msg:
            st.caption(f"Set **{' and '.join(err_msg)}** in the sidebar to run analysis.")
        col_a, col_b = st.columns(2)
        is_us = market and "US" in market
        is_korea = market and ("Korea" in market or "KOSPI" in market or "KOSDAQ" in market)
        is_japan_uk = market and ("Japan" in market or "Nikkei" in market or "UK" in market or "LSE" in market)
        # --- Button A: Management Strategy ---
        with col_a:
            if st.button("Analyze Management Strategy (MD&A)", key="run_mda_strategy"):
                if is_korea:
                    st.warning("DART API integration for Korean MD&A is currently under construction. Please check back in Phase 2.")
                elif is_japan_uk:
                    st.warning("EDINET/LSE document parsing is currently under development.")
                elif not api_ok or not email_ok:
                    st.error("Set API Key and SEC Email in the sidebar.")
                else:
                    try:
                        with st.status("Loading 10-K (cache or download)...", expanded=True) as status:
                            sections, _ = get_10k_sections(ticker, st.session_state["sec_email"])
                            si = get_sector_industry(quant_ticker)
                            status.update(label="10-K loaded. Calling Gemini…", state="running")

                        # Stream OUTSIDE the status box so user sees text as it arrives
                        st.markdown("### Management Strategy (Item 7)")
                        st.caption("Streaming from Gemini (first words in ~5–10 sec, then flows in real time).")
                        stream_gen = get_gemini_item7_strategy_stream(
                            st.session_state["google_api_key"],
                            sections.get("item7") or "",
                            ticker,
                            si.get("sector") or "N/A",
                            si.get("industry") or "N/A",
                        )
                        # write_stream returns the full concatenated string after it finishes streaming
                        full_response = st.write_stream(stream_gen)

                        st.session_state["mda_strategy_result"] = full_response
                        st.session_state["mda_strategy_ticker"] = ticker
                        st.session_state["mda_strategy_error"] = None
                    except Exception as e:
                        st.session_state["mda_strategy_error"] = str(e)
                        st.error(f"Strategy analysis failed: {str(e)}")
        # --- Button B: Risk Factors & Forensic ---
        with col_b:
            if st.button("Analyze Risk Factors (Item 1A)", key="run_mda_risk"):
                if is_korea:
                    st.warning("DART API integration for Korean MD&A is currently under construction. Please check back in Phase 2.")
                elif is_japan_uk:
                    st.warning("EDINET/LSE document parsing is currently under development.")
                elif not api_ok or not email_ok:
                    st.error("Set API Key and SEC Email in the sidebar.")
                else:
                    try:
                        with st.status("Loading 10-K (cache or download)...", expanded=True) as status:
                            sections, _ = get_10k_sections(ticker, st.session_state["sec_email"])
                            status.update(label="10-K loaded. Running forensic audit…", state="running")

                            # Run forensic silently IN THE BACKGROUND first
                            forensic = _gemini_forensic_audit(
                                st.session_state["google_api_key"],
                                sections.get("item3") or "",
                                sections.get("item9a") or "",
                                ticker,
                            )
                            status.update(label="Done.", state="complete")
                        # Stream the risk factors OUTSIDE the status box
                        st.markdown("### Risk Factors (Item 1A)")
                        st.caption("Streaming from Gemini (first words in ~5–10 sec, then flows in real time).")
                        stream_gen = get_gemini_item1a_risks_stream(
                            st.session_state["google_api_key"],
                            sections.get("item1a") or "",
                            ticker,
                        )
                        risk_response = st.write_stream(stream_gen)

                        # Combine both for the final result
                        final_out = risk_response
                        if forensic and forensic.strip():
                            st.markdown("### Forensic Audit (Item 3 & 9A)")
                            st.markdown(forensic.strip())
                            final_out += f"\n\n---\n\n### Forensic Audit (Item 3 & 9A)\n\n{forensic.strip()}"

                        st.session_state["mda_risk_result"] = final_out
                        st.session_state["mda_risk_ticker"] = ticker
                        st.session_state["mda_risk_error"] = None
                    except Exception as e:
                        st.session_state["mda_risk_error"] = str(e)
                        st.error(f"Risk analysis failed: {str(e)}")
        # --- Display Saved Results if User Switches Tabs ---
        st.markdown("---")
        if st.session_state.get("mda_strategy_ticker") == ticker:
            if st.session_state.get("mda_strategy_error"):
                st.error("Strategy Error: " + st.session_state["mda_strategy_error"])
            elif st.session_state.get("mda_strategy_result"):
                with st.expander("View Previous Strategy Analysis", expanded=True):
                    st.markdown(st.session_state["mda_strategy_result"])
        if st.session_state.get("mda_risk_ticker") == ticker:
            if st.session_state.get("mda_risk_error"):
                st.error("Risk Error: " + st.session_state["mda_risk_error"])
            elif st.session_state.get("mda_risk_result"):
                with st.expander("View Previous Risk & Forensic Analysis", expanded=True):
                    st.markdown(st.session_state["mda_risk_result"])
