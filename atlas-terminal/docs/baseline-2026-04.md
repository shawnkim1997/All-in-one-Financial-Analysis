# ATLAS Terminal Baseline — April 2026

Captured on 2026-04-21 before the v2 Data Gateway migration.

## Environment

- Backend: FastAPI on `127.0.0.1:8000`
- Frontend: Next.js dev server on `localhost:3000`
- Database: SQLite
- Browser baseline: `agent-browser` Chromium session

## Frontend Timing

Local overview route `/` after network idle:

| Metric | Value |
| --- | ---: |
| DOM interactive | 171 ms |
| DOMContentLoaded | 172 ms |
| First paint | 284 ms |
| First contentful paint | 284 ms |
| Load event end | 394 ms |
| Resource count | 26 |

Lighthouse was not run in this pass because the repo does not currently include a Lighthouse dependency or script. The browser navigation timing above is the baseline until Lighthouse is added.

## API Latency Samples

Measured with `curl` against the live local backend. Values are seconds.

| Endpoint | Samples | Approx p50 | Approx p95 | Notes |
| --- | --- | ---: | ---: | --- |
| `/api/health` | 0.0014, 0.0024, 0.0010, 0.0010 | 0.0012 | 0.0024 | Stable local health check |
| `/api/market/indices` | 0.7092, 0.8025, 0.2898, 0.3265 | 0.518 | 0.8025 | yfinance-backed and still provider-bound |
| `/api/market/asset-type/AAPL` | 0.2486, 0.1845, 0.2014, 0.1920 | 0.2014 | 0.2486 | Lightweight ticker classification |
| `/api/portfolio/summary` | 0.2929, 0.0019, 0.0017, 0.0018 | 0.0019 | 0.2929 | Warm cache makes repeat calls near-instant |
| `/api/fx/rates` | 0.1722, 0.0012, 0.0010, 0.0012 | 0.0012 | 0.1722 | Warm cache makes repeat calls near-instant |

## Bundle Size Baseline

Latest `npm run build` route output:

| Route | Size | First Load JS |
| --- | ---: | ---: |
| `/` | 6.35 kB | 98.2 kB |
| `/earnings` | 4.31 kB | 92 kB |
| `/filings` | 8.24 kB | 96 kB |
| `/macro` | 16 kB | 207 kB |
| `/markets` | 7.03 kB | 94.8 kB |
| `/news` | 5.43 kB | 93.2 kB |
| `/portfolio` | 5.93 kB | 93.7 kB |
| `/report` | 21.7 kB | 213 kB |
| `/research` | 2.73 kB | 94.6 kB |
| `/screener` | 3.26 kB | 91 kB |
| `/settings` | 2.57 kB | 90.3 kB |
| `/technical` | 6.38 kB | 94.1 kB |
| `/valuation` | 5.1 kB | 97 kB |

Shared first-load JS: 87.7 kB.

## FMP Call Baseline

Runtime FMP call volume is not yet centrally instrumented. Static inspection shows FMP access still lives behind `server/services/fmp_client.py`, but daily call count cannot be measured reliably until Phase 1 routes provider traffic through the Data Gateway.

Baseline tracking target for Phase 1: add provider-level counters at the gateway seam and compare FMP calls before/after each migrated endpoint.
