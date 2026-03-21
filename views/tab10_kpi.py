"""
KPI section — AI-powered company-specific KPI analysis via Gemini.
Generates key performance indicators relevant to the company's industry.
"""
import streamlit as st


def render_kpi_section(ticker: str, sector: str, industry: str):
    """Render AI-generated KPI analysis for a company."""
    st.markdown("---")
    st.markdown("#### Company KPI Analysis (AI-Powered)")
    st.caption(
        "AI identifies and analyzes the most important KPIs for this company's "
        "business model and industry."
    )

    google_api_key = (st.session_state.get("google_api_key") or "").strip()
    if not google_api_key:
        st.info("Enter your Google API Key in the sidebar to enable KPI analysis.")
        return

    kpi_key = f"kpi_analysis_{ticker}"

    if st.button("Generate KPI Analysis", key=f"btn_kpi_{ticker}"):
        with st.spinner("Analyzing company KPIs with Gemini..."):
            try:
                import google.generativeai as genai
                from config.constants import GEMINI_MODEL

                genai.configure(api_key=google_api_key)
                model = genai.GenerativeModel(GEMINI_MODEL)

                prompt = f"""You are a senior equity research analyst. For **{ticker}** (Sector: {sector}, Industry: {industry}), identify and analyze the **top 5 most critical KPIs** that investors should track.

For each KPI:
1. **KPI Name** — what it measures and why it matters for this specific company
2. **Current Context** — what investors should know about this metric's recent trajectory
3. **Industry Benchmark** — how to interpret good vs bad values

Format as a clean markdown list. Focus on KPIs that are:
- Specific to this company's business model (not generic financial ratios)
- Forward-looking indicators of growth or risk
- Examples: For NVIDIA → CUDA developer adoption, data center revenue mix, AI training chip market share
- Examples: For Starbucks → same-store sales growth, store count, average ticket size

Also include a brief section: "**Key Risks to Watch**" with 2-3 forward-looking risk indicators.
Keep under 500 words. Be specific and actionable."""

                r = model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.3, "max_output_tokens": 2048},
                )
                text = (r.text or "").strip()
                if text:
                    st.session_state[kpi_key] = text
                else:
                    st.error("Empty response from Gemini.")
            except Exception as e:
                err = str(e).lower()
                if "429" in err or "resource" in err:
                    st.error("Rate limit. Please wait and retry.")
                else:
                    st.error(f"Error: {e}")

    if st.session_state.get(kpi_key):
        st.markdown(st.session_state[kpi_key])
