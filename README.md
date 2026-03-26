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

## Pages & Features (12 Pages, 92 API Routes)

### 📊 Overview — Multi-Asset Intelligence
Auto-detects asset type and renders the appropriate dashboard:
- **Equity**: Sector/industry, market cap, P/E, beta, dividend, 52-week range, **Altman Z-Score**, **DuPont decomposition**, **KPI sparklines** (revenue growth, margins, ROE, FCF), **Peer valuation comparison** (PE/PB/PS/EV-EBITDA)
- **ETF**: Top holdings, sector breakdown, expense ratio
- **Commodity**: Monthly seasonal patterns, cross-commodity correlations

### 🔬 Research — Quantitative Dashboard
Grid-based research layout with five panels:
- **F-Score Panel**: Piotroski 9-criteria history with pass/fail indicators
- **DuPont Tree**: 3-factor ROE decomposition (NPM × Asset Turnover × Equity Multiplier)
- **Sankey**: Income statement flow visualization (Revenue → EBIT, @nivo/sankey)
- **Waterfall**: Operating income bridge chart (@nivo/bar)
- **Anomaly Chips**: YoY anomaly detection with Gemini AI explanations

### 💰 Valuation — 5 Analytical Models

| Tab | Description |
|-----|-------------|
| **DCF Model** | 3-scenario discounted cash flow with smart defaults from CAPM/Beta. Adjustable WACC, terminal growth, and FCF growth sliders. Analyst consensus displayed alongside. |
| **Sensitivity** | WACC × Terminal Growth Rate matrix table. Center cell highlighted to show base-case intrinsic value. |
| **Monte Carlo** | 5,000-simulation DCF with randomized inputs. Histogram (red below / green above current price). P10/P90, probability of upside. |
| **Tornado** | Variable impact ranking — which input assumption has the largest effect on valuation. |
| **Reverse DCF** | Market-implied growth rate via scipy Brent root-finding. Compares vs your assumption and analyst consensus. |

### 📈 Technical Analysis
- **Candlestick chart** with volume histogram (TradingView Lightweight Charts)
- Period selector: 1MO, 3MO, 6MO, 1Y, 2Y
- **RSI(14)**, **MACD**, **Bollinger Bands**, **ATR**, **ADX**
- **Moving Averages** table — SMA/EMA 20/50/100/200 with ABOVE/BELOW signals
- **Fibonacci retracement** levels
- **Ichimoku cloud** components

### 🌍 Financial Statements
- **Income Statement**, **Balance Sheet**, **Cash Flow** tabs
- Up to 5 annual periods with **YoY Growth** badges (green/red)
- **Margin %** rows (Gross, Operating, Net)
- **Sector heatmap** (S&P 500, NASDAQ 100, KOSPI, FTSE 100 constituents)

### 🌐 Macro & Cycle — Global Dashboard
Five collapsible tabs plus three always-visible sections:
- **Tabs**: FRED time series, Macro Cycle Heatmap (countries + assets), OECD CLI (DBnomics), Korea indicators (ECOS), Economic Calendar
- **Global Quadrant**: Growth vs inflation Z-score scatter (4 macro regimes)
- **Yield-FX**: US 10Y spread vs FX pairs (USD/JPY, EUR/USD, USD/KRW)
- **Smart Money**: Copper/Gold ratio + RORO (Risk-On/Risk-Off) composite gauge

### 📅 Earnings
- **Next earnings date** card with countdown
- **EPS Beat/Miss** visual history with surprise percentage
- **Quarterly breakdown** cards (revenue, net income)
- **Earnings transcript** (requires FMP API key)

### 📰 News Feed
Split-view news aggregator:
- **Left panel**: 40+ articles from Finviz, Google News, Yahoo RSS with source badges
- **Right panel**: Article header + iframe; domain-aware handling for sites blocking iframes (Yahoo, Bloomberg, WSJ) — shows summary + Open Original

### 🎯 Screener & Backtest
- **Stock Screener**: Filter by PE, sector, dividend yield
- **Strategy Backtest**: SMA Crossover, RSI Oversold, Buy & Hold — with candlestick chart visualization (lightweight-charts)

### 💼 Portfolio
Position tracking with multi-currency support (USD, KRW, GBP, EUR, JPY, CNY). P&L calculation, FX-adjusted returns, OCR screenshot import, and risk metrics:
- **VaR**, **Sharpe Ratio**, **Sortino Ratio**, **Maximum Drawdown**, **Beta**, **Correlation**

### 📑 Filings — Multi-Jurisdiction
Auto-detects filing jurisdiction from ticker suffix:
- **SEC EDGAR** (US stocks): 10-K section viewer (Items 1A, 3, 7, 8, 9A)
- **DART** (`.KS`/`.KQ` Korean stocks): 사업보고서 sections mapped to SEC equivalents
- **EDINET** (`.T` Japanese stocks): 有価証券報告書 sections (optional API key)

Each with 5 section tabs, word count, and **AI Summary** via Gemini.

### ⚙️ Settings
- Google Gemini API key configuration
- SEC EDGAR email for fair-access compliance
- Persistent storage via localStorage

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                         ATLAS TERMINAL                            │
├─────────────────────────────┬─────────────────────────────────────┤
│   Next.js 14 Frontend       │     FastAPI Backend                  │
│   (Port 3000)               │     (Port 8000)                     │
│                             │                                     │
│   ┌───────────────────┐     │     ┌───────────────────────┐       │
│   │ 12 App Router     │     │     │   21 API Routers      │       │
│   │ Pages + AppShell  │────────▶  │   92 endpoints        │       │
│   │ + Error Boundaries│  proxy    │   /api/market (17)     │       │
│   └───────────────────┘ /api/*    │   /api/macro (11)      │       │
│                             │     │   /api/portfolio (10)  │       │
│   ┌───────────────────┐     │     │   /api/valuation (8)   │       │
│   │ 5 Component Dirs  │     │     │   /api/analysis (6)    │       │
│   │ overview/ macro/  │     │     │   + 14 more routers    │       │
│   │ research/ markets/│     │     └───────────┬───────────┘       │
│   │ filings/          │     │                 │                   │
│   └───────────────────┘     │     ┌───────────▼───────────┐       │
│                             │     │   37 Service Modules   │       │
│   ┌───────────────────┐     │     │   dcf_engine, monte    │       │
│   │ Design System     │     │     │   carlo, risk_metrics  │       │
│   │ Terminal Noir     │     │     │   macro_fetcher, oecd  │       │
│   │ @nivo + recharts  │     │     │   research_dashboard   │       │
│   │ lightweight-charts│     │     │   dart/edinet/fmp...   │       │
│   └───────────────────┘     │     └───────────┬───────────┘       │
│                             │                 │                   │
│                             │     ┌───────────▼───────────┐       │
│                             │     │   Data Sources         │       │
│                             │     │   yfinance, yahooquery  │       │
│                             │     │   SEC EDGAR, DART, EDNT│       │
│                             │     │   FRED, OECD, ECOS     │       │
│                             │     │   FMP, Gemini, Finviz  │       │
│                             │     └───────────────────────┘       │
└─────────────────────────────┴─────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| **Charts** | TradingView Lightweight Charts, @nivo/sankey, @nivo/bar, Recharts |
| **Backend** | Python 3.12+, FastAPI, Pydantic v2, Uvicorn |
| **AI / LLM** | Google Gemini 2.0 Flash (`google-generativeai`) |
| **Financial Data** | yfinance (primary), yahooquery (fallback), FMP (optional) |
| **Technical Indicators** | `ta` library (RSI, MACD, Bollinger, Ichimoku, ADX) |
| **Valuation Engine** | NumPy (Monte Carlo), SciPy (Brent root-finding for Reverse DCF) |
| **Filings** | SEC EDGAR, Korea DART (`dart-fss`), Japan EDINET |
| **Macro Data** | FRED (public CSV), OECD (DBnomics), ECOS (한국은행) |
| **Database** | SQLite (local) / PostgreSQL (production) via asyncpg |
| **News** | Finviz scraping + Google News RSS + Yahoo RSS via feedparser |
| **Design System** | Terminal Noir — custom dark theme (#0A0A0F, #00D4AA, #FF4757) |

---

## Project Structure

```
atlas-terminal/
│
├── apps/web/                          # Next.js 14 Frontend
│   ├── src/app/
│   │   ├── page.tsx                   # Overview (Multi-Asset: Equity/ETF/Commodity)
│   │   ├── research/page.tsx          # Research Grid (F-Score, DuPont, Sankey, Waterfall)
│   │   ├── valuation/page.tsx         # DCF + Sensitivity + Monte Carlo + Tornado + Reverse
│   │   ├── technical/page.tsx         # Technical Analysis (TradingView + Indicators)
│   │   ├── markets/page.tsx           # Financial Statements + Sector Heatmap
│   │   ├── macro/page.tsx             # Global Macro (Quadrant, YieldFX, SmartMoney, FRED)
│   │   ├── earnings/page.tsx          # Earnings history & calendar
│   │   ├── news/page.tsx              # News feed (split-view, iframe-aware)
│   │   ├── screener/page.tsx          # Stock screener + Strategy backtest
│   │   ├── portfolio/page.tsx         # Portfolio tracker + OCR + Risk
│   │   ├── filings/page.tsx           # Multi-jurisdiction filing viewer (SEC/DART/EDINET)
│   │   ├── settings/page.tsx          # API keys configuration
│   │   ├── components/                # 5 component directories + 3 global components
│   │   │   ├── app-shell.tsx          # 3-panel layout (SSR-safe)
│   │   │   ├── sidebar.tsx            # Navigation (12 items)
│   │   │   ├── ticker-bar.tsx         # Live indices bar
│   │   │   ├── chat-panel.tsx         # AI Copilot
│   │   │   ├── overview/             # EquityOverview, ETFOverview, CommodityOverview, KPI, Peer
│   │   │   ├── research/             # FScorePanel, DuPontTree, SankeyWidget, WaterfallWidget
│   │   │   ├── macro/                # QuadrantChart, YieldFxChart, SmartMoneyPanel
│   │   │   ├── markets/              # HeatmapSection, EconomicCalendar, KoreaMonitor, OECD
│   │   │   └── filings/              # FilingsViewer (scroll-spy)
│   │   └── lib/
│   │       ├── use-ticker.ts          # Ticker state (localStorage + CustomEvent, hydration-safe)
│   │       ├── api.ts                 # API helper (apiFetch, apiPost)
│   │       ├── ticker-alias.ts        # Natural language → ticker ("gold" → GC=F)
│   │       └── filing-jurisdiction.ts # Ticker → SEC/DART/EDINET inference
│   └── next.config.mjs                # API proxy: /api/* → localhost:8000
│
├── server/                            # FastAPI Backend
│   ├── main.py                        # App entry + 21 routers
│   ├── routers/ (21)                  # API route handlers
│   ├── services/ (37)                 # Business logic modules
│   ├── db/                            # SQLite + PostgreSQL repositories
│   ├── models/                        # Pydantic schemas
│   ├── ai/                            # LLM router, context builder
│   └── utils/                         # safe_float, ticker utilities
│
└── requirements.txt                   # Python dependencies
```

---

## API Endpoints (92 routes across 21 routers)

| Prefix | Count | Description |
|--------|-------|-------------|
| `/api/market` | 17 | Stock quotes, overview (multi-asset), sectors, health, peers, F-Score, Sankey, radar, ETF holdings, commodity seasonal/correlations |
| `/api/macro` | 11 | FRED, OECD CLI, macro snapshot, **quadrant**, **yield-fx**, **smart-money**, Korea, calendar, ECOS |
| `/api/portfolio` | 10 | Position CRUD, risk metrics, OCR screenshot, exchange options |
| `/api/valuation` | 8 | DCF (3-scenario), sensitivity, Monte Carlo, tornado, reverse DCF, consensus, smart defaults |
| `/api/analysis` | 6 | Gemini AI analysis (strategy, risks, MD&A, forensic, financials) |
| `/api/financials` | 4 | Statements (IS+BS+CF), highlights, KPI history, ratios |
| `/api/technical` | 4 | Indicators, chart data, Fibonacci, Ichimoku |
| `/api/earnings` | 4 | EPS history, calendar, quarterly, transcript |
| `/api/chat` | 4 | AI Copilot (stream, complete, suggested, configure) |
| `/api/edgar` | 3 | 10-K sections, Item 7 MD&A, filing comparison |
| `/api/estimates` | 3 | Analyst consensus, history, growth |
| `/api/dart` | 2 | Korea DART company search + 사업보고서 sections |
| `/api/edinet` | 2 | Japan EDINET links + 有価証券報告書 sections |
| `/api/fmp` | 2 | Historical key metrics + ratios (FMP or Yahoo fallback) |
| `/api/screener` | 2 | Stock screener + strategy backtest |
| `/api/insider` | 2 | Insider transactions, institutional holders |
| `/api/news` | 2 | News aggregation + sentiment |
| `/api/crypto` | 2 | Cryptocurrency prices |
| `/api/fx` | 2 | FX rates and history |
| `/api/markets` | 1 | Index constituent heatmap |
| `/api/research` | 1 | Quant research dashboard (F-Score, DuPont, Sankey, Waterfall, Anomalies) |

Full interactive API documentation at `http://localhost:8000/docs` (Swagger UI).

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

### Optional API Keys

| Key | Purpose | Where to get |
|-----|---------|-------------|
| `GOOGLE_API_KEY` | Gemini AI analysis | [Google AI Studio](https://aistudio.google.com/apikey) |
| `SEC_EDGAR_EMAIL` | SEC fair-access compliance | Any valid email |
| `FMP_API_KEY` | Analyst estimates, transcripts, calendar | [Financial Modeling Prep](https://financialmodelingprep.com/) |
| `ECOS_API_KEY` | Korea Bank economic data | [ECOS](https://ecos.bok.or.kr/) |
| `DART_API_KEY` | Korea DART 사업보고서 | [Open DART](https://opendart.fss.or.kr/) |
| `EDINET_SUBSCRIPTION_KEY` | Japan EDINET 有価証券報告書 | [EDINET API](https://disclosure.edinet-fsa.go.jp/) |

---

## Design System — Terminal Noir

| Token | Value | Usage |
|-------|-------|-------|
| `bg-primary` | `#0A0A0F` | Main background |
| `bg-card` | `#1A1A26` | Card surfaces |
| `bg-hover` | `#252536` | Hover states |
| `border` | `#2A2A3A` | Borders and dividers |
| `accent-green` | `#00D4AA` | Positive values, CTAs, active states |
| `accent-red` | `#FF4757` | Negative values, warnings |
| `accent-blue` | `#4DA6FF` | Information, links |
| `accent-yellow` | `#FFD93D` | Caution, highlights |
| `text-primary` | `#F3F4F6` | Primary text |
| `text-secondary` | `#9CA3AF` | Secondary text |
| `text-muted` | `#6B7280` | Muted labels |

---

## Technical Highlights

### Hybrid AI Architecture
Gemini handles **text interpretation only** (MD&A analysis, risk factor extraction, anomaly explanation). All financial figures come from yfinance/yahooquery — zero hallucination risk on numbers.

### Multi-Source Data Resilience
Primary source (yfinance) with automatic yahooquery fallback. FMP as optional premium source. Pipe-separated multi-key column lookups handle naming differences between providers (`"TotalRevenue|Total Revenue|Revenue"`).

### Quantitative Valuation Suite
Five interconnected valuation models — DCF serves as the base, Sensitivity shows assumption impact, Monte Carlo quantifies uncertainty, Tornado ranks variable importance, and Reverse DCF reveals market-implied expectations.

### Multi-Jurisdiction Filing Support
SEC EDGAR (US), DART (Korea), EDINET (Japan) — automatically routed by ticker suffix. Each maps to a standardized 5-section view with AI summarization.

### Global Macro Analytics
Growth-vs-inflation quadrant (FRED/OECD Z-scores), yield spread vs FX pairs, copper/gold + RORO composite — institutional-grade macro regime detection.

---

## Update History (Changelog)

| Date | Update |
|------|--------|
| **2026-03-26** | **Codebase audit & documentation sync:** (1) Fixed `requirements.txt` — added missing `numpy`, `scipy`, `dbnomics` dependencies. (2) Full `claude.md` synchronization — updated §3 File Structure (removed 6 deleted services, added 37 current services + 21 routers), §5 API Endpoints (92 routes accurately documented), §6 Frontend Pages (12 pages with feature descriptions), §13 TODO (8 items marked complete). (3) Verified all 21 routers import cleanly, 92 API routes registered, 11/12 key endpoints tested OK (macro/quadrant timeout is external FRED latency, not code issue). |
| **2026-03-24** | **Macro dashboard, layout stability, News/Filings UX:** Global Macro & Smart Money page with quadrant, yield-FX, copper/gold + RORO gauge. Hydration/white-screen fix (SSR-safe useTicker + dynamic Sidebar). Research grid rebuilt with Tailwind CSS. News domain-aware iframe handling. Filings plain-text fallback. Error boundaries. |
| **2026-03-21** | **Full-stack migration (v4.0) — Next.js 14 + FastAPI:** Complete rewrite from Streamlit. 10 pages, 13 routers, 5 valuation models, TradingView charts, Technical Analysis suite, Earnings visualization, News split-view, SEC EDGAR viewer, Terminal Noir theme, AI Copilot. |
| **2026-03-19** | **Modular refactoring (v3.0):** 3,909-line `app.py` → 28 focused modules. SEC filing viewer rebuilt with EDGAR JSON API. DART links restored for Korean stocks. |
| **2026-02-18** | **Market Heatmap & FX charts:** Sector heatmap, FX momentum chart, 10-K language toggle. |
| **2026-02-17** | **DART, prefs, run script:** DART fetch timeout, English report titles, per-category iframe viewer. |
| **2025-02-15** | **Multi-currency portfolio & FX:** Per-position currency, Gemini Vision OCR screenshot import. |
| **2025-02-14** | **Global company search:** yahooquery search, auto-infers exchange suffix. |
| **2025-02-13** | **10Y DCF & comps redesign:** Wall Street Assumptions panel, Smart DCF defaults, sector analysis. |
| **2025-02-12** | **Hybrid architecture:** Item 7 only to Gemini; yfinance for all numbers. DuPont, Altman Z, Piotroski F-Score. |
| **2025-01-XX** | **Initial release:** SEC EDGAR 10-K download, Gemini analysis, Streamlit UI. |

---

## License & Disclaimer

This project is built for learning, research, and portfolio demonstration purposes. Nothing in this application constitutes investment advice. Comply with [SEC EDGAR policy](https://www.sec.gov/os/webmaster-faq#code-support) when accessing SEC data, and with Google's terms of service for the Gemini API.

---

<p align="center">
  <sub>Built with ☕ and late nights — <a href="https://github.com/shawnkim1997">@shawnkim1997</a></sub>
</p>
