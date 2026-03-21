<p align="center">
  <strong style="font-size: 2em;">ATLAS TERMINAL</strong>
</p>

<p align="center">
  <em>Personal Bloomberg Terminal — Institutional-Grade Financial Analysis for Everyone</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" alt="Next.js 14" />
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/TypeScript-5.0+-3178C6?logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/TailwindCSS-3.4-06B6D4?logo=tailwindcss&logoColor=white" alt="Tailwind" />
</p>

---

## What is ATLAS Terminal?

ATLAS Terminal is a **full-stack financial analysis platform** that brings institutional-grade equity research tools to a single, unified interface. It combines **AI-driven qualitative analysis** of SEC 10-K filings with **quantitative valuation models**, real-time market data, and portfolio management — all wrapped in a sleek, dark-themed terminal UI.

**Design philosophy:** LLM for text interpretation, Python for numbers. This eliminates hallucination risk on financial figures while delivering nuanced qualitative insights from SEC filings.

---

## Pages & Features

### 📊 Overview
Company snapshot at a glance — current price, sector, industry, market cap, P/E ratio, beta, dividend yield, 52-week range, **Altman Z-Score** (safe/grey/distress zones), and **DuPont decomposition** (ROE → NPM × Asset Turnover × Equity Multiplier).

### 🔬 Research
AI-powered deep-dive analysis using Google Gemini. Ask natural-language questions about any company and receive structured financial insights with context from SEC filings, financial statements, and market data.

### 💰 Valuation — 5 Analytical Models

| Tab | Description |
|-----|-------------|
| **DCF Model** | 2-stage discounted cash flow with smart defaults from CAPM/Beta. Adjustable WACC, terminal growth, and FCF growth sliders. Analyst consensus (target price, recommendation) displayed alongside. |
| **Sensitivity** | WACC × Terminal Growth Rate matrix table. Center cell highlighted to show base-case intrinsic value. Instantly see how assumptions shift fair value. |
| **Monte Carlo** | 5,000-simulation DCF with randomized inputs. Histogram visualization (red below / green above current price). Statistics: mean, median, P10/P90, probability of upside. |
| **Tornado** | Variable impact ranking chart. Shows which input assumption (WACC, growth rate, terminal growth, margins) has the largest effect on valuation — sorted by sensitivity range. |
| **Reverse DCF** | Solves for the implied growth rate the market is pricing in. Compares market-implied growth vs. your assumption and analyst consensus. Uses scipy's Brent root-finding method. |

### 📈 Technical Analysis
- **Candlestick chart** with volume histogram (TradingView Lightweight Charts)
- Period selector: 1MO, 3MO, 6MO, 1Y, 2Y
- **RSI(14)** with overbought/oversold classification
- **MACD** with signal line and histogram
- **Bollinger Bands** — %B, bandwidth, current position
- **Moving Averages** table — SMA/EMA 20/50/100/200 with ABOVE/BELOW signals
- **Fibonacci retracement** levels with "near current price" highlighting
- **ATR** (Average True Range) for volatility measurement
- **ADX** for trend strength detection

### 🌍 Financial Statements
Institutional-style financial data table with:
- **Income Statement**, **Balance Sheet**, **Cash Flow** tabs
- Up to 5 annual periods with proper date headers
- **YoY Growth** badges (green for positive, red for negative)
- **Margin %** rows (Gross Margin, Operating Margin, Net Margin)
- Row groups: Revenue, COGS, Gross Profit, SG&A, R&D, Operating Income, EBITDA, Net Income, EPS
- Pipe-separated multi-key lookup to handle both yfinance and yahooquery column naming conventions

### 📅 Earnings
- **Next earnings date** card with countdown
- **EPS Beat/Miss** visual history — green bars for beats, red for misses, with surprise percentage
- **Revenue & Earnings estimates** vs. actuals
- **Quarterly breakdown** cards

### 📰 News Feed
Split-view news aggregator:
- **Left panel**: Scrollable article list (40+ articles from Finviz & Google News) with source badges and timestamps
- **Right panel**: Article header bar + iframe embedding of original content
- "Open Original ↗" button for sites that block iframe embedding
- Ticker-specific filtering

### 💼 Portfolio
Position tracking with multi-currency support (USD, KRW, GBP, EUR, JPY, CNY). P&L calculation, FX-adjusted returns, and risk metrics including:
- **VaR** (Value at Risk)
- **Sharpe Ratio** & **Sortino Ratio**
- **Maximum Drawdown**
- **Beta** & **Correlation** to benchmark

### 📑 SEC Filings (EDGAR)
Inline 10-K filing viewer:
- Downloads and parses latest 10-K from SEC EDGAR
- **5 section tabs**: Risk Factors (1A), MD&A (7), Financial Statements (8), Legal Proceedings (3), Controls & Procedures (9A)
- Intelligent content formatting — headers detected and styled, bullets indented, paragraphs separated
- **Word count** per section
- **AI Summary** button — sends section text to Gemini for key risk/trend extraction
- Section caching to avoid repeat downloads

### ⚙️ Settings
- Google Gemini API key configuration
- SEC EDGAR email for fair-access compliance
- Persistent storage via localStorage

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ATLAS TERMINAL                           │
├────────────────────────────┬────────────────────────────────────┤
│   Next.js 14 Frontend      │     FastAPI Backend                │
│   (Port 3000)              │     (Port 8000)                    │
│                            │                                    │
│   ┌──────────────────┐     │     ┌──────────────────────┐       │
│   │ App Router Pages │     │     │   13 API Routers     │       │
│   │ • Overview       │────────▶  │   • /api/market      │       │
│   │ • Research       │  proxy    │   • /api/financials   │       │
│   │ • Valuation      │ /api/*   │   • /api/valuation    │       │
│   │ • Technical      │     │     │   • /api/technical    │       │
│   │ • Markets        │     │     │   • /api/earnings     │       │
│   │ • Earnings       │     │     │   • /api/edgar        │       │
│   │ • News           │     │     │   • /api/news         │       │
│   │ • Portfolio      │     │     │   • /api/portfolio    │       │
│   │ • Filings        │     │     │   • /api/insider      │       │
│   │ • Settings       │     │     │   • /api/analysis     │       │
│   └──────────────────┘     │     │   • /api/crypto       │       │
│                            │     │   • /api/fx           │       │
│   ┌──────────────────┐     │     │   • /api/estimates    │       │
│   │ Components       │     │     └──────────┬───────────┘       │
│   │ • Sidebar        │     │                │                   │
│   │ • Ticker Bar     │     │     ┌──────────▼───────────┐       │
│   │ • Chat Panel     │     │     │   15 Service Modules  │       │
│   │ • useTicker()    │     │     │   • dcf_engine        │       │
│   └──────────────────┘     │     │   • monte_carlo       │       │
│                            │     │   • sensitivity       │       │
│   ┌──────────────────┐     │     │   • risk_metrics      │       │
│   │ Design System    │     │     │   • technical_analysis│       │
│   │ Terminal Noir    │     │     │   • sec_parser        │       │
│   │ #0A0A0F bg       │     │     │   • news_aggregator   │       │
│   │ #00D4AA accent   │     │     │   • gemini_service    │       │
│   │ #FF4757 red      │     │     │   • market_data       │       │
│   └──────────────────┘     │     └──────────┬───────────┘       │
│                            │                │                   │
│                            │     ┌──────────▼───────────┐       │
│                            │     │   Data Sources        │       │
│                            │     │   • yfinance          │       │
│                            │     │   • yahooquery         │       │
│                            │     │   • SEC EDGAR API      │       │
│                            │     │   • Google Gemini      │       │
│                            │     │   • Finviz / RSS       │       │
│                            │     └──────────────────────┘       │
└────────────────────────────┴────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| **Charts** | TradingView Lightweight Charts (candlestick, volume) |
| **Backend** | Python 3.12+, FastAPI, Pydantic v2, Uvicorn |
| **AI / LLM** | Google Gemini 2.0 Flash (`google-generativeai`) |
| **Financial Data** | yfinance (primary), yahooquery (fallback) |
| **Technical Indicators** | `ta` library (RSI, MACD, Bollinger, Ichimoku, ADX) |
| **Valuation Engine** | NumPy (Monte Carlo), SciPy (Brent root-finding for Reverse DCF) |
| **SEC Data** | `sec-edgar-downloader`, EDGAR REST API, BeautifulSoup4 + lxml |
| **Database** | SQLite (local) / PostgreSQL (production) via asyncpg |
| **News** | Finviz scraping + Google News RSS via feedparser |
| **Design System** | Terminal Noir — custom dark theme (#0A0A0F, #00D4AA, #FF4757) |

---

## Project Structure

```
atlas-terminal/
│
├── apps/web/                          # Next.js 14 Frontend
│   ├── src/app/
│   │   ├── page.tsx                   # Overview (home)
│   │   ├── research/page.tsx          # AI Research
│   │   ├── valuation/page.tsx         # DCF + Sensitivity + Monte Carlo + Tornado + Reverse DCF
│   │   ├── technical/page.tsx         # Technical Analysis (TradingView charts)
│   │   ├── markets/page.tsx           # Financial Statements table
│   │   ├── earnings/page.tsx          # Earnings history & calendar
│   │   ├── news/page.tsx              # News feed (split-view)
│   │   ├── portfolio/page.tsx         # Portfolio tracker
│   │   ├── filings/page.tsx           # SEC EDGAR filing viewer
│   │   ├── settings/page.tsx          # API keys configuration
│   │   ├── components/
│   │   │   ├── sidebar.tsx            # Navigation sidebar
│   │   │   ├── ticker-bar.tsx         # Live market indices bar
│   │   │   └── chat-panel.tsx         # AI Copilot chat interface
│   │   └── lib/
│   │       ├── use-ticker.ts          # Ticker state hook (localStorage + CustomEvent)
│   │       └── api.ts                 # API helper functions
│   ├── next.config.mjs                # API proxy: /api/* → localhost:8000
│   ├── tailwind.config.ts             # Terminal Noir color system
│   └── package.json
│
├── server/                            # FastAPI Backend
│   ├── main.py                        # App entry + CORS + router mounting
│   ├── routers/                       # 13 API route handlers
│   │   ├── market_data.py             # Stock quotes, indices, overview
│   │   ├── financials.py              # Income statement, balance sheet, cash flow
│   │   ├── valuation.py               # DCF, sensitivity, Monte Carlo, tornado, reverse DCF
│   │   ├── technical.py               # RSI, MACD, Bollinger, moving averages, Fibonacci
│   │   ├── earnings.py                # EPS history, calendar, quarterly data
│   │   ├── insider.py                 # Insider transactions, institutional holders
│   │   ├── edgar.py                   # SEC 10-K section extraction
│   │   ├── analysis.py                # Gemini AI analysis endpoints
│   │   ├── news.py                    # News aggregation
│   │   ├── portfolio.py               # Position CRUD + risk metrics
│   │   ├── estimates.py               # Analyst estimates
│   │   ├── crypto.py                  # Cryptocurrency prices
│   │   └── fx.py                      # FX rates and history
│   ├── services/                      # 15 business logic modules
│   │   ├── dcf_engine.py              # Excel-style DCF, 2-stage DCF, reverse DCF (scipy brentq)
│   │   ├── monte_carlo.py             # Monte Carlo simulation (5000 runs, numpy)
│   │   ├── sensitivity.py             # WACC × TG matrix, tornado data
│   │   ├── risk_metrics.py            # VaR, Sharpe, Sortino, MDD, Beta, Correlation
│   │   ├── technical_analysis.py      # All indicators via `ta` library
│   │   ├── sec_parser.py              # SEC EDGAR download, HTML parse, section cache
│   │   ├── news_aggregator.py         # Finviz + Google News RSS
│   │   ├── gemini_service.py          # Gemini API wrapper
│   │   ├── gemini_analysis.py         # Structured AI analysis prompts
│   │   ├── market_data.py             # Market overview, sector data
│   │   ├── financial_metrics.py       # DuPont, Altman Z, ratio calculations
│   │   └── ...                        # crypto, fx, screenshot OCR, text chunker
│   ├── models/                        # Pydantic schemas
│   ├── db/                            # SQLite + PostgreSQL repositories
│   ├── ai/                            # LLM router, context builder
│   └── utils/                         # safe_float, ticker utilities
│
├── tests/                             # pytest test suite
├── supabase/migrations/               # Database schema
└── requirements.txt                   # Python dependencies
```

---

## API Endpoints

| Prefix | Methods | Description |
|--------|---------|-------------|
| `/api/market` | GET | Stock quotes, company info, market overview, sector data |
| `/api/financials` | GET | Income statement, balance sheet, cash flow, highlights, ratios |
| `/api/valuation` | GET, POST | DCF defaults, sensitivity matrix, Monte Carlo, tornado, reverse DCF |
| `/api/technical` | GET | RSI, MACD, Bollinger, moving averages, Fibonacci, ATR, ADX |
| `/api/earnings` | GET | EPS history, earnings calendar, quarterly data |
| `/api/insider` | GET | Insider transactions, institutional holders |
| `/api/edgar` | GET | SEC 10-K section extraction, Item 7 MD&A, filing comparison |
| `/api/analysis` | POST | Gemini AI analysis (MD&A, risk factors, financial health) |
| `/api/estimates` | GET | Analyst consensus estimates |
| `/api/news` | GET | Financial news aggregation (Finviz + Google News) |
| `/api/portfolio` | GET, POST, DELETE | Position management, risk metrics |
| `/api/crypto` | GET | Cryptocurrency prices (BTC, ETH, SOL, etc.) |
| `/api/fx` | GET | FX rates and historical data |
| `/health` | GET | Liveness probe with DB status |

Full interactive API documentation available at `http://localhost:8000/docs` (Swagger UI).

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- [Google Gemini API Key](https://aistudio.google.com/apikey) (for AI features)
- Email address for SEC EDGAR fair-access compliance

### Installation & Launch

```bash
# Clone the repository
git clone https://github.com/shawnkim1997/All-in-one-Financial-Analysis.git
cd "All-in-one-Financial-Analysis/atlas-terminal"

# ── Backend ──
pip install -r requirements.txt
PYTHONPATH="." uvicorn server.main:app --port 8000

# ── Frontend (new terminal) ──
cd apps/web
npm install
npm run dev
```

Open **http://localhost:3000** in your browser.

Configure your **Gemini API Key** and **SEC EDGAR email** in the Settings page, then search for any ticker (e.g., MSFT, AAPL, GOOGL) to explore.

---

## Design System — Terminal Noir

ATLAS Terminal uses a custom dark theme inspired by professional trading terminals:

| Token | Value | Usage |
|-------|-------|-------|
| `bg-primary` | `#0A0A0F` | Main background |
| `bg-card` | `#12121A` | Card surfaces |
| `bg-elevated` | `#1A1A2E` | Hover states, elevated panels |
| `border` | `#2A2A3E` | Borders and dividers |
| `accent-green` | `#00D4AA` | Positive values, CTAs, active states |
| `accent-red` | `#FF4757` | Negative values, warnings |
| `accent-blue` | `#4A9EFF` | Informational badges, links |
| `accent-yellow` | `#FFD93D` | Caution, highlights |
| `text-primary` | `#E8E8ED` | Primary text |
| `text-secondary` | `#A0A0B0` | Secondary text |
| `text-muted` | `#6B6B80` | Muted labels |

---

## Evolution: Streamlit → Next.js + FastAPI

This project began as a **Streamlit prototype** (`app.py`, 3,909 lines) and has been fully migrated to a modern full-stack architecture:

| Aspect | Streamlit (v1-v3) | Next.js + FastAPI (v4) |
|--------|-------------------|----------------------|
| Frontend | Streamlit widgets | Next.js 14 App Router + Tailwind |
| Backend | Embedded in Streamlit | Dedicated FastAPI with 13 routers |
| Charts | Plotly (Sankey, Radar) | TradingView Lightweight Charts |
| State | `st.session_state` | React hooks + localStorage |
| Routing | Tab-based (7 tabs) | File-based (10 pages) |
| API | Monolithic | RESTful with OpenAPI docs |
| Caching | `@st.cache_data` | SQLite/PostgreSQL persistence |
| Deployment | Single process | Frontend + Backend independently scalable |

The original Streamlit version remains functional at the project root (`app.py`) for reference.

---

## Technical Highlights

### Hybrid AI Architecture
Gemini handles **text interpretation only** (MD&A analysis, risk factor extraction, industry outlook). All financial figures come from yfinance/yahooquery — zero hallucination risk on numbers.

### Multi-Source Data Resilience
Primary source (yfinance) with automatic yahooquery fallback. Pipe-separated multi-key column lookups handle naming differences between providers (`"TotalRevenue|Total Revenue|Revenue"`).

### Quantitative Valuation Suite
Five interconnected valuation models — DCF serves as the base, Sensitivity shows assumption impact, Monte Carlo quantifies uncertainty, Tornado ranks variable importance, and Reverse DCF reveals market-implied expectations.

### SEC EDGAR Integration
Full pipeline: `sec-edgar-downloader` → HTML parsing with BeautifulSoup → section extraction (Items 1A, 3, 7, 8, 9A) → local caching → AI summarization via Gemini.

---

## Requirements

See [`atlas-terminal/requirements.txt`](atlas-terminal/requirements.txt) for the full Python dependency list. Key packages:

- `fastapi`, `uvicorn` — Web framework
- `yfinance`, `yahooquery` — Financial data
- `google-generativeai` — Gemini AI
- `sec-edgar-downloader`, `beautifulsoup4`, `lxml` — SEC filing parsing
- `ta` — Technical analysis indicators
- `numpy`, `scipy` — Monte Carlo simulation, optimization
- `pandas` — Data manipulation

Frontend: `next`, `react`, `tailwindcss`, `lightweight-charts`

---

## Update History (Changelog)

| Date | Update |
|------|--------|
| **2026-03-21** | **Full-stack migration (v4.0) — Next.js 14 + FastAPI:** Complete rewrite from Streamlit to Next.js 14 App Router + FastAPI backend. 10 dedicated pages (Overview, Research, Valuation, Technical, Markets, Earnings, News, Portfolio, Filings, Settings). 13 REST API routers with Swagger docs. 5 valuation models (DCF, Sensitivity Matrix, Monte Carlo 5000-sim, Tornado, Reverse DCF with scipy brentq). TradingView Lightweight Charts for candlestick/volume. Technical Analysis page with RSI, MACD, Bollinger, Fibonacci, Moving Averages, ADX. Earnings beat/miss visualization. News split-view with iframe article embedding. SEC EDGAR inline filing viewer with 5 section tabs + AI Summary. Financial Statements table with YoY growth badges and margin rows. Terminal Noir dark theme design system. AI Copilot chat panel with Gemini. |
| **2026-03-19** | **Modular refactoring (v3.0) + SEC filing viewer fix:** (1) **Architecture:** 3,909-line `app.py` refactored into 28 focused modules across `config/`, `utils/`, `data/`, `ai/`, `views/`. Each file under 300 lines. Strict unidirectional dependency graph (no circular imports). All `@st.cache_data` TTLs and `st.session_state` keys preserved identically. (2) **SEC Filing Viewer fixed:** Rebuilt EDGAR fetch chain using `submissions/CIK{cik}.json` → `filings.recent.primaryDocument[]` (replaces deprecated `directory.item` lookup). Added filing type `st.selectbox` (10-K, 10-Q, 8-K, 20-F, 6-K) connected to backend dynamically. Native HTML rendered via `streamlit.components.v1.html()` with injected CSS reset. Errors surfaced explicitly with `st.error()`. (3) **DART links** restored for Korean-listed companies. |
| **2026-02-18** | **Market Heatmap & FX charts:** Sector heatmap with 5d/1mo data and per-ticker fallback (weekend/holiday robust). FX Momentum normalized 1Y line chart (GBP/USD, EUR/USD, USD/JPY, KRW). 10-K language toggle (한글/영문) via Gemini translation. plotly/yfinance added to requirements. |
| **2026-02-17** | **DART, prefs, run script:** DART fetch timeout 90s; DART report titles in English (cached). SEC & DART per-category iframe viewer. Last selected company persisted in `.app_prefs.json` (survives page refresh). Single run script `run.sh` at port 8501. |
| **2025-02-15** | **Multi-currency portfolio & FX:** Per-position currency (USD/GBP/EUR/KRW/JPY/CNY), fractional quantity, FX-adjusted returns. Gemini Vision AI screenshot import (extracts ticker, price, currency, quantity). App-wide `get_currency_for_ticker`, `get_fx_rate`, `format_price_with_usd`. |
| **2025-02-14** | **Global company search:** yahooquery `search()` replaces static dropdown. Search by name in any language; filters INDEX/MUTUALFUND; auto-infers .KS/.KQ/.T/.L suffix. |
| **2025-02-13** | **Design Rationale & 10Y DCF:** Design rationale section (undergrad automation mindset, 10Y 2-stage DCF, Damodaran integration). Wall Street Assumptions panel (analyst consensus + Damodaran baselines). Smart DCF defaults from Beta/CAPM. |
| **2025-02-13** | **Robust data & comps redesign:** Multi-step shares/debt/cash fallback (fast_info → info → balance). Top-down sector analysis with `SECTORS` dict and AI Industry Outlook (Gemini). |
| **2025-02-12** | **Hybrid architecture:** Item 7 only to Gemini; yfinance for all numbers. HTML cleansing pipeline (BeautifulSoup + regex). |
| **2025-02-12** | **DuPont, Altman Z, Piotroski, sector KPIs, TTM fallback:** Full quantitative financial health suite. Sector-specific metrics (Tech: Rule of 40; Retail: Inventory Turnover; Financials: ROE/ROA). |
| **2025-02-12** | **Preference persistence:** "Remember API key & email" checkbox; `.app_prefs.json` (gitignored). |
| **2025-01-XX** | **Initial release:** SEC EDGAR 10-K download, Item 7/8 extraction, Gemini analysis, Streamlit UI. |

---

## License & Disclaimer

This project is built for learning, research, and portfolio demonstration purposes. Nothing in this application constitutes investment advice. Comply with [SEC EDGAR policy](https://www.sec.gov/os/webmaster-faq#code-support) when accessing SEC data, and with Google's terms of service for the Gemini API.

---

<p align="center">
  <sub>Built with ☕ and late nights — <a href="https://github.com/shawnkim1997">@shawnkim1997</a></sub>
</p>
