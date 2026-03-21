# ATLAS Terminal

> Personal Bloomberg-style financial terminal -- real-time market data,
> AI-powered analysis, DCF valuation, and portfolio management.

## Features

- **SEC EDGAR** -- 10-K filing download and section extraction
- **AI Analysis** -- Gemini-powered financial statement analysis
- **DCF Valuation** -- Single-stage, two-stage, and Excel-style DCF models with Damodaran WACC
- **Market Data** -- Live stock quotes, indices, and sector data
- **News** -- Financial news aggregation via RSS feeds
- **Crypto** -- Top 20 cryptocurrency prices (Bithumb KRW + Binance USD)
- **FX** -- Foreign exchange rates and 1-year history via yfinance
- **Portfolio** -- Position tracking with P&L and multi-currency support
- **Financial Health** -- DuPont analysis, Altman Z-Score, Piotroski F-Score, radar charts

## Tech Stack

**Backend:** Python 3.12+, FastAPI, Pydantic v2, yfinance, yahooquery, Google Generative AI, Supabase

**Frontend:** Next.js 14, TypeScript, Tailwind CSS

## Quick Start

```bash
# Backend
cd atlas-terminal
pip install -r requirements.txt
cp .env.example .env  # configure API keys
uvicorn server.main:app --reload --port 8000

# Frontend
cd apps/web
npm install
npm run dev
```

The API will be available at `http://localhost:8000` and the web UI at `http://localhost:3000`.

## Project Structure

```
atlas-terminal/
  server/
    main.py              # FastAPI entry point
    models/              # Pydantic schemas, Supabase client
    routers/             # API route handlers
    services/            # Business logic, data fetchers
    utils/               # safe_float, ticker utilities
  apps/web/              # Next.js frontend
  supabase/migrations/   # Database schema
  tests/                 # pytest test suite
  scripts/               # Automation scripts
```

## API Endpoints

| Prefix           | Description                        |
|------------------|------------------------------------|
| `/api/edgar`     | SEC EDGAR 10-K filings             |
| `/api/analysis`  | AI-powered financial analysis      |
| `/api/valuation` | DCF valuation and smart defaults   |
| `/api/market`    | Stock quotes and market overview    |
| `/api/news`      | Financial news feeds               |
| `/api/crypto`    | Cryptocurrency prices              |
| `/api/fx`        | Foreign exchange rates and history  |
| `/api/portfolio` | Portfolio position management      |
| `/health`        | Liveness probe                     |

## License

Private project.
