"""
AI Financial Summary — Gemini-powered analyst report.
Split from tab8 to keep files under 300 lines.
"""
import streamlit as st


def _df_to_summary_text(df, label: str, max_cols: int = 5) -> str:
    if df is None or df.empty:
        return f"[{label}: No data available]\n"
    cols = df.columns[:max_cols]
    sliced = df[cols]
    lines = [f"=== {label} ===", "Period: " + " | ".join(str(c) for c in cols)]
    for idx in sliced.index:
        vals = " | ".join(
            f"{v:,.0f}" if isinstance(v, (int, float)) and v == v else "N/A"
            for v in sliced.loc[idx]
        )
        lines.append(f"  {idx}: {vals}")
    return "\n".join(lines) + "\n"


def _build_prompt(ticker, inc, bal, cf):
    return f"""You are a **Senior Equity Analyst at Franklin Templeton** with 15+ years of experience. Write a comprehensive financial summary for **{ticker}**.

{inc}
{bal}
{cf}

Produce a professional report with: 1. Executive Summary, 2. Revenue & Profitability Analysis,
3. Balance Sheet Health, 4. Cash Flow Quality, 5. Key Ratios & Red Flags,
6. Investment Thesis (Bull vs Bear), 7. Analyst's Bottom Line.
Use actual numbers. Under 1,200 words. Markdown formatting."""


def render_ai_summary(ticker, fin_df, bal_df, cf_df):
    """Render the AI Financial Summary section."""
    st.markdown("---")
    st.markdown("### AI Financial Summary (Powered by Gemini)")
    google_api_key = (st.session_state.get("google_api_key") or "").strip()
    if not google_api_key:
        st.info("Enter your Google API Key in the sidebar to enable AI summaries.")
        return
    report_key = f"ai_summary_report_{ticker}"
    if st.button("Generate Senior Analyst Report", key=f"btn_ai_{ticker}", type="primary"):
        with st.spinner("Generating analyst report..."):
            try:
                if fin_df is None or fin_df.empty:
                    st.error("No financial data available.")
                    return
                inc = _df_to_summary_text(fin_df, "Income Statement")
                bal = _df_to_summary_text(bal_df, "Balance Sheet")
                cf = _df_to_summary_text(cf_df, "Cash Flow Statement")
                import google.generativeai as genai
                from config.constants import GEMINI_MODEL
                genai.configure(api_key=google_api_key)
                model = genai.GenerativeModel(GEMINI_MODEL)
                r = model.generate_content(
                    _build_prompt(ticker, inc, bal, cf),
                    generation_config={"temperature": 0.3, "max_output_tokens": 4096},
                )
                text = (r.text or "").strip()
                if text:
                    st.session_state[report_key] = text
                else:
                    st.error("Empty response from Gemini.")
            except Exception as e:
                err = str(e).lower()
                if "429" in err or "resource" in err:
                    st.error("Rate limit reached. Wait and retry.")
                else:
                    st.error(f"Error: {e}")
    if st.session_state.get(report_key):
        st.markdown(st.session_state[report_key])
        st.caption("AI-generated. Verify independently before making investment decisions.")
