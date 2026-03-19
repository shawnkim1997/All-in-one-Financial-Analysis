"""
Soft Navy Professional Financial Terminal Theme — CSS + header HTML.
"""

SOFT_NAVY_CSS = """
<style>
/* ═══════ Soft Navy — Professional Financial Terminal Theme ═══════ */

/* Base */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #0F1923 0%, #131D2A 100%);
    color: #D1D5DB;
    font-family: 'Inter', -apple-system, sans-serif;
}
[data-testid="stSidebar"] {
    background: #0D1520;
    border-right: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stHeader"] {
    background: rgba(15, 25, 35, 0.95);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(255,255,255,0.06);
}

/* Typography */
h1, h2, h3, h4, h5, h6 { color: #F3F4F6 !important; font-family: 'Inter', sans-serif !important; font-weight: 700 !important; }
p, span, label, .stMarkdown, div[data-testid="stText"] { color: #D1D5DB !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: #6B7280 !important; }

/* Metrics — monospace numbers */
div[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    color: #F9FAFB !important;
}
[data-testid="stMetricDelta"] > div { font-family: 'JetBrains Mono', monospace !important; font-size: 0.85rem !important; }
[data-testid="stMetricDelta"][style*="color: rgb(9, 171, 59)"] { color: #34D399 !important; }
[data-testid="stMetricDelta"][style*="color: rgb(255, 43, 43)"] { color: #F87171 !important; }

/* Tabs — pill style */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(255,255,255,0.03);
    border-radius: 10px;
    padding: 4px 6px;
    border: 1px solid rgba(255,255,255,0.06);
}
.stTabs [data-baseweb="tab"] {
    padding: 8px 18px;
    font-weight: 600;
    font-size: 0.82rem;
    color: #6B7280;
    border-radius: 8px;
    background: transparent;
    border: none;
    transition: all 0.2s ease;
}
.stTabs [aria-selected="true"] {
    background: rgba(59, 130, 246, 0.15) !important;
    color: #60A5FA !important;
    box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.3);
}

/* Inputs */
input, textarea, [data-baseweb="input"] > div, [data-baseweb="select"] > div {
    background: rgba(255,255,255,0.04) !important;
    color: #E5E7EB !important;
    border-color: rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
}
input:focus, textarea:focus { border-color: rgba(59, 130, 246, 0.5) !important; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15) !important; }

/* Buttons */
.stButton > button {
    background: rgba(59, 130, 246, 0.12);
    color: #60A5FA;
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 8px 20px;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    background: rgba(59, 130, 246, 0.25);
    border-color: #60A5FA;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    overflow: hidden;
}
[data-testid="stDataFrame"] th {
    background: rgba(255,255,255,0.04) !important;
    color: #9CA3AF !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    font-size: 0.7rem !important;
    letter-spacing: 0.5px;
}
[data-testid="stDataFrame"] td {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
}

/* Expanders */
div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
}

/* Sliders */
.stSlider [data-baseweb="slider"] [role="slider"] { background: #3B82F6 !important; }
.stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] { color: #60A5FA !important; font-family: 'JetBrains Mono', monospace !important; }

/* Alerts */
[data-testid="stAlert"] { border-radius: 8px; border: none; }
div[data-baseweb="notification"][kind="positive"] { background: rgba(52, 211, 153, 0.08) !important; border-left: 3px solid #34D399 !important; }
div[data-baseweb="notification"][kind="warning"] { background: rgba(251, 191, 36, 0.08) !important; border-left: 3px solid #FBBF24 !important; }
div[data-baseweb="notification"][kind="negative"] { background: rgba(248, 113, 113, 0.08) !important; border-left: 3px solid #F87171 !important; }

/* Plotly */
.js-plotly-plot .plotly .main-svg { background: transparent !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }

/* Container */
.block-container { padding-top: 1rem; max-width: 1400px; }

/* Selectbox dropdown */
[data-baseweb="popover"] { background: #1A2332 !important; border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 8px !important; }
[data-baseweb="menu"] li { color: #D1D5DB !important; }
[data-baseweb="menu"] li:hover { background: rgba(59, 130, 246, 0.12) !important; }

/* Sidebar specific */
[data-testid="stSidebar"] .stButton > button { width: 100%; }
[data-testid="stSidebar"] [data-baseweb="select"] > div { background: rgba(255,255,255,0.06) !important; }

/* Custom utility classes */
.rating-badge { display: inline-block; padding: 4px 14px; border-radius: 6px; font-weight: 700; font-size: 0.85rem; font-family: 'JetBrains Mono', monospace; }
.rating-buy { background: rgba(52, 211, 153, 0.15); color: #34D399; border: 1px solid rgba(52, 211, 153, 0.3); }
.rating-sell { background: rgba(248, 113, 113, 0.15); color: #F87171; border: 1px solid rgba(248, 113, 113, 0.3); }
.rating-hold { background: rgba(251, 191, 36, 0.15); color: #FBBF24; border: 1px solid rgba(251, 191, 36, 0.3); }
.stat-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px; text-align: center; }
.stat-label { color: #6B7280; font-size: 0.7rem; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; }
.stat-value { color: #F9FAFB; font-size: 1.2rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; margin: 4px 0; }
.stat-delta { font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; }
.delta-up { color: #34D399; }
.delta-down { color: #F87171; }
.section-label { color: #6B7280; font-size: 0.7rem; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; margin: 20px 0 8px; }
</style>
"""

HEADER_HTML = """
<div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 4px;">
    <span style="font-size: 1.8rem; font-weight: 800; color: #60A5FA; font-family: 'JetBrains Mono', monospace; letter-spacing: -1px;">ATLAS</span>
    <span style="font-size: 1.8rem; font-weight: 300; color: #4B5563; letter-spacing: 2px;">TERMINAL</span>
    <span style="font-size: 0.65rem; color: #374151; font-weight: 600; padding: 2px 8px; background: rgba(59,130,246,0.1); border-radius: 4px; margin-left: 4px;">v2.0</span>
</div>
<p style="color: #4B5563; font-size: 0.78rem; margin-top: 0;">
    Hybrid: Gemini AI qualitative &middot; yfinance quantitative &middot; Single unified terminal
</p>
"""
