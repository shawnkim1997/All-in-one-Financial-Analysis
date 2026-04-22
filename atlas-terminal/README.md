# ATLAS Terminal

[![CI](https://github.com/shawnkim1997/All-in-one-Financial-Analysis/actions/workflows/ci.yml/badge.svg)](https://github.com/shawnkim1997/All-in-one-Financial-Analysis/actions/workflows/ci.yml)

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
- Frontend state: Zustand persistent terminal store, shared API hook, Playwright smoke tests
- Backend: FastAPI, Python 3.12+, Pydantic, yfinance, yahooquery, FMP gateway scaffold, pandas, scipy
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

### Verification

```bash
pytest tests -q
cd apps/web
npm run typecheck
npm run build
npm run e2e
```

### Local URLs

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Secure Credential Storage

Server-side broker/API credentials are stored with envelope encryption. The master key must live in the environment and is never written to SQLite/PostgreSQL.

Generate a local master key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then set it in `.env`:

```bash
ATLAS_MASTER_KEY=your-generated-value
```

Credential tables:

- `user_credentials`: encrypted provider blobs keyed by `user_id` and `provider`
- `credential_access_log`: audit trail for store/status/delete/decrypt attempts

Credential API:

- `PUT /api/credentials/{provider}` stores a secret after envelope encryption
- `GET /api/credentials/{provider}/status` returns only metadata, never the secret
- `DELETE /api/credentials/{provider}` removes the encrypted credential

## Recent Work

- Phase 5 earnings-call delta MVP: FMP transcript pair lookup, deterministic new/faded/emphasis phrase analysis, tone shift scoring, and best-effort AI narrative on the Earnings page
- Phase 4 peer comparison: gateway-backed peer discovery, parallel fundamentals matrix, percentile-colored valuation/quality cells, and backward-compatible `/api/market/peers/{ticker}` responses for overview/report flows
- Phase 3 security hardening: AES-GCM envelope encryption, credential tables, credential access audit logs, and `ATLAS_MASTER_KEY` documentation for future KIS/IBKR key storage
- v2 refactor foundation: baseline measurements in `docs/baseline-2026-04.md`, CI workflow, pytest smoke tests, and Playwright route smoke tests
- Data Gateway scaffold: typed `DataGateway` contract, chained providers, TTL cache wrapper, provider metrics, and a flag-gated `/api/market/quote/{ticker}` migration path via `ATLAS_FLAG_GATEWAY=true`
- Central terminal state: Zustand-backed `useTerminal` store for active symbol, page context, recent symbols, watchlist, currency, theme, layouts, and Copilot context
- Copilot context injection: right rail chat now sends terminal context to `/api/copilot/chat` on every turn
- Keyboard workflow: `Cmd/Ctrl+K` and `G` focus ticker search, `/` focuses Copilot, `W` adds the active symbol to watchlist, and `P/M/N` navigate Portfolio/Macro/News
- Smarter ticker search: company-name and Korean aliases now resolve suggestions such as Berkshire Hathaway, SK hynix, Samsung Electronics, Toyota, Novo Nordisk, and common ETFs/commodities
- Portfolio and FX reliability: exchange-aware Novo Nordisk EUR handling, faster FX/portfolio repeat loads, and cleaner local artifact ignore rules
- Morgan Stanley-inspired redesign across the shell, overview, research, valuation, technical, macro, settings, and report flows
- Shared chart palette and UI primitives for a more consistent desktop terminal experience
- Research dashboard performance fixes for faster repeat loads and less blocking on page open
- Improved macro failure states, report messaging, tooltip formatting, and chart legibility

## Refactor Roadmap

- Phase 0: Foundation safety net, baseline docs, CI, backend smoke tests, frontend e2e smoke tests
- Phase 1: Data Gateway migration behind `ATLAS_FLAG_GATEWAY`, starting with low-risk quote data before wider overview/profile routes
- Phase 2: Global terminal state through Zustand, Copilot context, and keyboard-first terminal navigation
- Next phases: encrypted credential vault, peer comparison, earnings-call delta analysis, and smaller institutional feature gaps

## Why This Project

ATLAS Terminal started as an attempt to build a personal Bloomberg-lite for retail investing workflows: high information density, clean narrative structure, and a hard separation between AI-generated language and deterministic financial computation.

It is currently optimized as a desktop-first personal research environment rather than a SaaS product.
