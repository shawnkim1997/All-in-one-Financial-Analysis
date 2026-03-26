# ATLAS Terminal — Web Application

> Next.js 14 + FastAPI full-stack financial analysis terminal.
>
> See the [main README](../README.md) for full documentation.

## Quick Start

```bash
# Backend (from atlas-terminal/)
pip install -r requirements.txt
PYTHONPATH="." uvicorn server.main:app --port 8000

# Frontend (from atlas-terminal/apps/web/)
npm install
npm run dev
```

- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Stack

- **Frontend:** Next.js 14, TypeScript, Tailwind CSS, TradingView Lightweight Charts
- **Backend:** FastAPI, Python 3.12+, yfinance, yahooquery, Google Gemini
- **Database:** SQLite (local) / PostgreSQL (production)

## Recent Updates

**2026-03-24**

- **Macro:** Global Macro & Smart Money dashboard (`/macro`), Recharts widgets, FastAPI `/api/macro/quadrant`, `/yield-fx`, `/smart-money` (FRED + yfinance + OECD/DBnomics).
- **Stability:** Sidebar `dynamic(..., ssr: false)`; `useTicker` hydration-safe init; `app/error.tsx`; macro/research layouts use Tailwind grid (removed `react-grid-layout`).
- **News / Filings:** Iframe fallback for blocked publishers (e.g. Yahoo); SEC filings show plain text when HTML snapshot cache is absent.

**Earlier**

- Multi-asset analysis branching across Overview/Research/Valuation/Earnings for equity, ETF, and commodity futures.
- Commodity and ETF market widgets; index-level stock heatmap with interactive index switching.
- Portfolio OCR upgrades, exchange selection (e.g. SMSN → `SMSN.L`), inline edit/delete; exchange-aware recalculation and FX matrix for multi-currency display.
