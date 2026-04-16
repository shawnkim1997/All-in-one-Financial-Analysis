# ATLAS Terminal

Institutional-style equity research terminal built with Next.js 14 and FastAPI.

ATLAS Terminal brings market overview, quant research, valuation, technical analysis, macro monitoring, filings workflows, and printable institutional reports into one desktop-first interface.

## What It Does

- Multi-asset overview for equities, ETFs, commodities, crypto, FX, and macro signals
- Quant research dashboards with F-Score, DuPont, anomalies, Sankey, and waterfall views
- Valuation tooling including DCF, sensitivity, Monte Carlo, tornado, and reverse DCF
- Technical analysis with candlesticks, moving averages, Bollinger Bands, RSI, MACD, and Fibonacci levels
- Cross-market monitoring through macro, smart-money, yield/FX, earnings, news, filings, and portfolio pages
- Institutional report generation with printable PDF-style layouts

## Core Product Principle

> LLMs handle text. Python handles numbers.

Qualitative analysis, summarization, and narrative framing can be AI-assisted, while valuation logic, financial metrics, and quantitative workflows are computed deterministically in code.

## Product Tour

### Overview

![ATLAS overview](./docs/media/atlas-overview.png)

### Valuation

![ATLAS valuation](./docs/media/atlas-valuation.png)

### Technical Analysis

![ATLAS technical analysis](./docs/media/atlas-technical.png)

### Institutional Report

![ATLAS institutional report](./docs/media/atlas-report.png)

## Demo Assets

- [Open recorded demo video](./docs/media/atlas-demo.mp4)
- [Open report preview PDF](./docs/media/atlas-report-preview.pdf)

You can also click the screenshot below to open the recorded walkthrough:

[![Watch the ATLAS demo](./docs/media/atlas-overview.png)](./docs/media/atlas-demo.mp4)

## Stack

- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS, Recharts, Lightweight Charts
- Backend: FastAPI, Python 3.12+, Pydantic, yfinance, pandas, scipy
- Data: SEC, DART, EDINET, FRED, OECD, DBnomics, Yahoo Finance
- AI: Gemini for qualitative analysis only
- Storage: SQLite by default

## Key Pages

- `/` overview dashboard
- `/research` quant research workbench
- `/valuation` DCF and scenario analysis
- `/technical` chart-driven technical analysis
- `/macro` macro and smart-money dashboard
- `/filings` SEC, DART, and EDINET workflows
- `/report` institutional report generator
- `/portfolio` portfolio tracking and OCR import

## Quick Start

### Backend

```bash
pip install -r requirements.txt
PYTHONPATH="." uvicorn server.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

### Local URLs

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Recent Work

- Morgan Stanley-inspired redesign across the shell, overview, research, valuation, technical, macro, settings, and report flows
- Shared chart palette and UI primitives for a more consistent desktop terminal experience
- Research dashboard performance fixes for faster repeat loads and less blocking on page open
- Improved macro failure states, report messaging, tooltip formatting, and chart legibility

## Why This Project

ATLAS Terminal started as an attempt to build a personal Bloomberg-lite for retail investing workflows: high information density, clean narrative structure, and a hard separation between AI-generated language and deterministic financial computation.

It is currently optimized as a desktop-first personal research environment rather than a SaaS product.
