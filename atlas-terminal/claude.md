# claude.md — ATLAS Terminal Build Guide

> 이 문서는 Claude Code 에이전트가 프로젝트를 빌드할 때 참조하는 마스터 가이드입니다.
> 모든 에이전트는 작업 시작 전 이 문서를 반드시 읽어야 합니다.
> **마지막 수정: 2026-03-26**

---

## 1. Project Identity

| 항목 | 내용 |
|------|------|
| **이름** | ATLAS Terminal (Advanced Terminal for Liquid Asset Surveillance) |
| **목적** | 개인 투자자에게 기관급 투자 리서치를 단일 인터페이스로 제공 |
| **핵심 철학** | 금융 정보 비대칭 해소 — 기술로 리테일 투자자의 무기를 평등하게 |
| **디자인** | Bloomberg Terminal의 정보 밀도 + Notion의 깔끔함 + 다크 모드 |
| **스택** | Next.js 14 (App Router) + FastAPI + SQLite/PostgreSQL + Gemini API |
| **프로젝트 루트** | `/Users/seonpil/Library/Mobile Documents/com~apple~CloudDocs/Documents/FQDC Project/atlas-terminal/` |

---

## 2. Architecture Principles (절대 규칙)

### 2.1 하이브리드 분리 원칙
```
정성 데이터 (Qualitative) → LLM (Gemini) → 텍스트 분석만
정량 데이터 (Quantitative) → Pandas + yfinance/yahooquery → 숫자/계산만
```
- **절대 LLM에 숫자 계산을 맡기지 않는다** — LLM은 텍스트 분석, 번역, 요약만 담당
- 모든 재무 지표(DCF, DuPont, Altman Z, F-Score)는 Python 코드로 계산
- 이 원칙을 위반하면 비용 폭발 + 정확도 하락

### 2.2 토큰 최적화 (비용 통제)
- 10-K 원문을 LLM에 보내기 전 반드시 `sec_parser.py`로 Item 1A~9A만 추출
- `text_chunker.py`의 `smart_chunk()`로 10,000자 이내로 압축 (head+tail 보존)
- Gemini 호출은 탭당 최대 1~2회로 제한
- 429 에러 시 `_generate_with_retry()`로 60초 대기 후 재시도

### 2.3 다단계 폴백 체인 (기능별 — 코드와 일치)
“한 줄 체인”이 아니라 **엔드포인트/서비스마다** 소스 순서가 다르다. 아래가 실제 구현 기준이다.

| 영역 | 1순위 | 2순위 | 비고 |
|------|--------|--------|------|
| 가격·차트·`info`·배당 등 | yfinance | yahooquery | `market_data`, `technical`, 대부분 라우터 |
| 연간 재무제표 (`/api/financials/.../statements`) | yfinance | yahooquery | 연간만 필터 |
| DCF 입력·`market_fetcher` 연간 집계 | yahooquery (TTM 보강) | yfinance (분기 합산 등) | `server/services/market_fetcher.py` |
| 히스토리컬 밸류·재무 비율·어닝콜 (선택) | FMP (`FMP_API_KEY` 있을 때만) | yahooquery `summary_detail` / `financial_data` | yfinance `info` — `server/services/fmp_client.py` |
| 거시 (FRED/OECD/ECOS) | FRED 공개 CSV / ECOS 키 | — | `server/services/macro_fetcher.py` |

레거시 서술(참고): 티커 메타/추정 등 일부 경로는 `fast_info` → `info` → 재무표 순으로 보강한다.
- 모든 숫자 파싱에 `_safe_float()` 사용 (`server/utils/safe_float.py`)
- 실패 시 빈 DataFrame 또는 None 반환, 절대 에러를 UI에 노출하지 않음

### 2.4 모듈 분리 원칙
- **한 파일 = 한 책임** — 단일 파일 3000줄 금지
- 파일당 최대 300줄 목표
- 비즈니스 로직 → `server/services/`, API 엔드포인트 → `server/routers/`
- 프론트엔드 컴포넌트는 기능별로 분리

### 2.5 Multi-Key Column Lookup (중요!)
yfinance와 yahooquery는 같은 데이터의 컬럼명이 다르다:
- yfinance: `"Total Revenue"` (띄어쓰기)
- yahooquery: `"TotalRevenue"` (CamelCase)

프론트엔드에서 **파이프 구분자 패턴**으로 해결:
```tsx
function getValue(periodData: Record<string, any>, key: string) {
  const keys = key.split("|");
  for (const k of keys) {
    const v = periodData[k.trim()];
    if (v != null && typeof v === "number") return v;
  }
  return null;
}
// 사용 예: getValue(data, "TotalRevenue|Total Revenue|Revenue")
```

---

## 3. 현재 File Structure (실제 아키텍처)

```
atlas-terminal/
├── apps/web/                        # Next.js 14 프론트엔드
│   ├── src/app/
│   │   ├── layout.tsx               # 루트 레이아웃 (AppShell 래퍼)
│   │   ├── page.tsx                 # Overview — Multi-Asset (Equity/ETF/Commodity 자동분기)
│   │   ├── globals.css              # Tailwind + Terminal Noir 기본 스타일
│   │   ├── error.tsx                # 세그먼트 레벨 에러 바운더리
│   │   ├── global-error.tsx         # 루트 레벨 에러 바운더리
│   │   ├── not-found.tsx            # 404 페이지
│   │   ├── research/page.tsx        # 리서치 그리드 (F-Score, DuPont, Sankey, Waterfall, Anomaly)
│   │   ├── valuation/page.tsx       # 5-Tab: DCF, Sensitivity, Monte Carlo, Tornado, Reverse DCF
│   │   ├── technical/page.tsx       # TradingView 캔들차트 + RSI/MACD/Bollinger/Fibonacci/Ichimoku
│   │   ├── markets/page.tsx         # 재무제표 테이블 + 섹터 히트맵
│   │   ├── macro/page.tsx           # 거시 5탭(FRED/Cycle/OECD/Korea/Calendar) + Quadrant/YieldFX/SmartMoney
│   │   ├── earnings/page.tsx        # EPS Beat/Miss + Revenue + Next Earnings
│   │   ├── news/page.tsx            # Split-view: 기사 리스트 + iframe 원문
│   │   ├── transcripts/page.tsx     # 비디오/오디오 트랜스크립트 업로드 + 검색 + 분석
│   │   ├── screener/page.tsx        # 종목 스크리너 + 전략 백테스트
│   │   ├── portfolio/page.tsx       # 포지션 CRUD + Risk Metrics + OCR
│   │   ├── filings/page.tsx         # 공시 원문 — SEC/DART/EDINET 자동분기 (5탭 + AI 요약)
│   │   ├── settings/page.tsx        # API Key 관리
│   │   ├── components/
│   │   │   ├── app-shell.tsx        # 3-panel 레이아웃 래퍼 (SSR-safe dynamic import)
│   │   │   ├── sidebar.tsx          # 좌측 네비게이션 (13개 메뉴)
│   │   │   ├── ticker-bar.tsx       # 상단 실시간 지수 바 (S&P, NASDAQ, KOSPI, BTC)
│   │   │   ├── chat-panel.tsx       # 우측 AI Copilot 채팅
│   │   │   ├── filings/
│   │   │   │   └── FilingsViewer.tsx       # 공시 뷰어 (IntersectionObserver scroll-spy)
│   │   │   ├── transcripts/
│   │   │   │   ├── TranscriptUploadForm.tsx   # YouTube/URL/업로드 3-탭 입력
│   │   │   │   ├── TranscriptJobList.tsx      # 상태 배지 + 진행률 리스트
│   │   │   │   ├── TranscriptDetailPanel.tsx  # 요약/키워드/감성/원문 패널
│   │   │   │   └── TranscriptSearchBar.tsx    # 저장된 트랜스크립트 전문 검색
│   │   │   ├── macro/
│   │   │   │   ├── GlobalMacroQuadrantChart.tsx  # 성장 vs 인플레 Z-score 산점도
│   │   │   │   ├── YieldFxDualAxisChart.tsx       # US10Y 스프레드 vs FX 이중축
│   │   │   │   └── SmartMoneyPanel.tsx            # Copper/Gold + RORO 패널
│   │   │   ├── markets/
│   │   │   │   ├── HeatmapSection.tsx      # 섹터 히트맵 (S&P/NASDAQ/KOSPI/FTSE)
│   │   │   │   ├── EconomicCalendar.tsx    # 글로벌 경제 이벤트
│   │   │   │   ├── KoreaMonitor.tsx        # 한국 경제 지표 (ECOS)
│   │   │   │   ├── MacroCycleHeatmap.tsx   # 매크로 사이클 히트맵
│   │   │   │   └── OECDCycleChart.tsx      # OECD CLI 차트
│   │   │   ├── overview/
│   │   │   │   ├── EquityOverview.tsx      # 주식 오버뷰 (섹터, DuPont, Altman Z)
│   │   │   │   ├── ETFOverview.tsx         # ETF 오버뷰 (보유종목, 섹터비중)
│   │   │   │   ├── CommodityOverview.tsx   # 원자재 오버뷰 (계절성, 상관관계)
│   │   │   │   ├── KpiSection.tsx          # 분기 KPI 스파크라인
│   │   │   │   └── PeerComparison.tsx      # 동종업계 밸류에이션 비교
│   │   │   └── research/
│   │   │       ├── ResearchGridLayout.tsx  # 12-col CSS 그리드 레이아웃
│   │   │       ├── FScorePanel.tsx         # Piotroski F-Score 이력 (9항목)
│   │   │       ├── DuPontTree.tsx          # 3-Factor ROE 분해 트리
│   │   │       ├── SankeyWidget.tsx        # 손익 Sankey (@nivo/sankey)
│   │   │       ├── WaterfallWidget.tsx     # 영업이익 워터폴 (@nivo/bar)
│   │   │       ├── AnomalyChips.tsx        # YoY 이상치 + Gemini 설명
│   │   │       └── types.ts               # 리서치 대시보드 타입 정의
│   │   └── lib/
│   │       ├── use-ticker.ts        # 티커 상태 훅 (localStorage + CustomEvent, hydration-safe)
│   │       ├── api.ts               # API 클라이언트 유틸 (apiFetch, apiPost)
│   │       ├── use-video-transcript.ts  # 트랜스크립트 submit/list/get/search/poll 훅
│   │       ├── video-transcript-types.ts # 트랜스크립트 타입 정의
│   │       ├── ticker-alias.ts      # 자연어→티커 매핑 ("gold"→GC=F, "samsung"→005930.KS)
│   │       └── filing-jurisdiction.ts # 티커→관할권 추론 (SEC/DART/EDINET)
│   ├── next.config.mjs              # /api/* → localhost:8000 프록시
│   ├── tailwind.config.ts           # Terminal Noir 컬러 토큰
│   └── package.json
│
├── server/                          # FastAPI 백엔드
│   ├── main.py                      # FastAPI app + 22개 라우터 등록
│   ├── routers/                     # API 엔드포인트 (22개)
│   │   ├── analysis.py              # POST /api/analysis — Gemini LLM 분석 (strategy/risks/mda/forensic)
│   │   ├── chat.py                  # /api/chat — AI Copilot
│   │   ├── crypto.py                # /api/crypto — 암호화폐 가격
│   │   ├── dart.py                  # /api/dart — Korea DART 기업검색 + 사업보고서 섹션
│   │   ├── daily_news.py            # /api/daily-news — FT 헤드라인 + 번역
│   │   ├── earnings.py              # /api/earnings — history|calendar|quarterly|transcript
│   │   ├── edgar.py                 # /api/edgar — SEC 10-K 다운로드 + 파싱
│   │   ├── edinet.py                # /api/edinet — Japan EDINET 링크 + 섹션 (optional key)
│   │   ├── estimates.py             # /api/estimates — 애널리스트 추정치
│   │   ├── financials.py            # /api/financials — statements/highlights/kpi-history/ratios
│   │   ├── fmp.py                   # /api/fmp — Key metrics, ratios (optional FMP key)
│   │   ├── fx.py                    # /api/fx — 환율
│   │   ├── insider.py               # /api/insider — 내부자 거래 + 기관보유
│   │   ├── macro.py                 # /api/macro — FRED/OECD/ECOS/Quadrant/YieldFX/SmartMoney/Calendar
│   │   ├── market_data.py           # /api/market — 시세/섹터/헬스/트렌드/피어/Sankey/Radar/ETF/원자재
│   │   ├── markets.py               # /api/markets — 섹터 히트맵
│   │   ├── news.py                  # /api/news — Finviz + Google + Yahoo RSS
│   │   ├── portfolio.py             # /api/portfolio — CRUD + Risk + OCR
│   │   ├── research.py              # /api/research — 퀀트 대시보드 (F-Score/DuPont/Sankey/Waterfall/Anomaly)
│   │   ├── screener.py              # /api/screener — 종목 검색 + 백테스트
│   │   ├── technical.py             # /api/technical — indicators/chart-data/fibonacci/ichimoku
│   │   ├── valuation.py             # /api/valuation — DCF/Sensitivity/Monte Carlo/Tornado/Reverse DCF
│   │   └── video_transcript.py      # /api/video — submit/upload/jobs/search/delete
│   ├── services/                    # 비즈니스 로직 (37개)
│   │   ├── backtester.py            # 전략 백테스트 (SMA/RSI/Buy&Hold)
│   │   ├── cache.py                 # 인메모리 TTL 캐시 데코레이터
│   │   ├── commodity_analysis.py    # 원자재 계절성·상관관계
│   │   ├── dart_fetcher.py          # DART API 클라이언트 (기업검색)
│   │   ├── dart_filing_service.py   # DART 사업보고서 ZIP/XML → 섹션 매핑 + 캐시
│   │   ├── dcf_engine.py            # excel_style_dcf, dcf_10y_2stage, reverse_dcf (scipy brentq)
│   │   ├── economic_calendar.py     # 경제 캘린더 데이터
│   │   ├── ecos_fetcher.py          # 한국은행 ECOS 매크로 데이터
│   │   ├── edinet_filing_service.py # EDINET API v2 + 링크 폴백
│   │   ├── etf_analysis.py          # ETF 보유종목·섹터비중
│   │   ├── exchange_resolver.py     # 거래소 해석
│   │   ├── financial_metrics.py     # DuPont, Altman Z, Piotroski F-Score
│   │   ├── financial_metrics_ext.py # 확장 지표 (Sankey, Waterfall 데이터)
│   │   ├── fmp_client.py            # FMP API + Yahoo fallback snapshots
│   │   ├── gemini_service.py        # Gemini API 래퍼 (retry, streaming)
│   │   ├── global_macro_quadrant.py # 성장 vs 인플레 Z-score 사분면
│   │   ├── heatmap.py               # 섹터 히트맵 데이터
│   │   ├── kpi_history_service.py   # 분기 KPI 시계열 (매출성장/마진/ROE/FCF)
│   │   ├── macro_cycle.py           # 매크로 사이클 분석 (FRED + World Bank)
│   │   ├── macro_fetcher.py         # FRED CSV + OECD + ECOS 매크로 데이터
│   │   ├── market_fetcher.py        # yfinance/yahooquery 폴백 체인 (DCF 입력)
│   │   ├── market_overview.py       # 시장 개요 데이터
│   │   ├── monte_carlo.py           # run_monte_carlo_dcf (numpy, 5000 sims)
│   │   ├── news_aggregator.py       # Finviz scrape + Google/Yahoo RSS
│   │   ├── oecd_cycle.py            # OECD CLI via DBnomics
│   │   ├── peer_comparison_service.py # 동종업계 밸류에이션 비교
│   │   ├── research_dashboard.py    # 리서치 대시보드 (F-Score/DuPont/Sankey/Waterfall/Anomaly)
│   │   ├── risk_metrics.py          # VaR, Sharpe, Sortino, MDD, Beta, Correlation
│   │   ├── screener.py              # 종목 스크리너 로직
│   │   ├── screenshot_ocr.py        # Gemini Vision OCR (포트폴리오 스크린샷)
│   │   ├── sec_parser.py            # 10-K 다운로드 + HTML 파싱 + 섹션 추출 + 캐싱
│   │   ├── sector_heatmap.py        # 섹터 히트맵 계산
│   │   ├── sensitivity.py           # build_sensitivity_matrix, build_tornado_data
│   │   ├── smart_money_service.py   # Copper/Gold ratio + RORO 리스크 복합지수
│   │   ├── text_chunker.py          # smart_chunk, clean_text_for_llm
│   │   ├── video_transcript_service.py # yt-dlp + faster-whisper + Gemini 통합 파이프라인
│   │   └── yield_fx_service.py      # US10Y 스프레드 vs FX (USDJPY/EURUSD/USDKRW)
│   ├── db/                          # 데이터베이스 레이어
│   │   ├── unified_repo.py          # SQLite/PostgreSQL 통합 인터페이스
│   │   ├── cache.py                 # 캐시 저장소
│   │   ├── database.py              # SQLite 커넥션
│   │   ├── pg_database.py           # PostgreSQL 커넥션
│   │   ├── portfolio_repo.py        # 포트폴리오 SQLite CRUD
│   │   ├── pg_portfolio_repo.py     # 포트폴리오 PostgreSQL CRUD
│   │   ├── pg_cache_repo.py         # PostgreSQL 캐시
│   │   ├── video_repo.py            # 트랜스크립트 SQLite CRUD + FTS5
│   │   ├── pg_video_repo.py         # 트랜스크립트 PostgreSQL CRUD + tsvector
│   │   ├── dashboard_repo.py        # 대시보드 레이아웃 저장
│   │   └── settings_repo.py         # 설정 저장소
│   ├── models/
│   │   ├── schemas.py               # Pydantic 모델 (요청/응답)
│   │   └── db.py                    # DB 모델
│   ├── ai/
│   │   ├── llm_router.py            # LLM 프로바이더 라우팅
│   │   └── context_builder.py       # 컨텍스트 빌더
│   └── utils/
│       ├── safe_float.py            # 안전한 숫자 파싱
│       └── ticker_utils.py          # 티커/자산유형 유틸리티
│
├── claude.md                        # 이 파일 (AI 에이전트 매뉴얼)
├── requirements.txt                 # Python 의존성
└── README.md
```

---

## 4. Design System — "Terminal Noir"

### 4.1 Tailwind 컬러 토큰 (`tailwind.config.ts`)
```typescript
colors: {
  bg: {
    primary: "#0A0A0F",    // 메인 배경
    secondary: "#12121A",  // 서브 배경
    card: "#1A1A26",       // 카드 서피스
    hover: "#252536",      // 호버 상태
  },
  accent: {
    green: "#00D4AA",      // 상승, CTA, 활성 (민트 그린)
    red: "#FF4757",        // 하락, 경고
    yellow: "#FFD93D",     // 주의, 하이라이트
    blue: "#4DA6FF",       // 정보, 링크
  },
  text: {
    primary: "#F3F4F6",    // 주 텍스트
    secondary: "#9CA3AF",  // 보조 텍스트
    muted: "#6B7280",      // 약한 라벨
  },
  border: { DEFAULT: "#2A2A3A" },
}
fontFamily: {
  sans: ["Inter", "system-ui", "sans-serif"],
  mono: ["JetBrains Mono", "monospace"],
}
```

### 4.2 UI 규칙
- **숫자**: 양수 = `text-accent-green` + `+` 접두사, 음수 = `text-accent-red`, 폰트 = `font-mono`
- **카드**: `bg-bg-card border border-border rounded-lg p-5`
- **로딩**: `text-accent-green animate-pulse font-mono "Loading data..."`
- **AI 관련**: `text-accent-blue` 또는 인디고 계열
- **에러**: `border-accent-red/30` 배경 + `text-accent-red` 텍스트

### 4.3 3-Panel 레이아웃
```
┌──────────────────────────────────────────────────────────┐
│  [ATLAS TERMINAL]  S&P 500 -1.51%  NASDAQ +2.81%  ...   │  ← TickerBar (h-52px, fixed top)
├───────────┬──────────────────────────┬───────────────────┤
│           │                          │                   │
│ Sidebar   │    Main Content          │   AI Copilot      │
│ w-260px   │    flex-1                │   w-380px         │
│           │    p-7                   │                   │
│ Overview  │                          │  Ask me anything  │
│ Research  │    (각 페이지 콘텐츠)      │  about {ticker}   │
│ Valuation │                          │                   │
│ Technical │                          │  [Send]           │
│ Markets   │                          │                   │
│ Earnings  │                          │                   │
│ News      │                          │                   │
│ Portfolio │                          │                   │
│ Filings   │                          │                   │
│ Settings  │                          │                   │
│           │                          │                   │
└───────────┴──────────────────────────┴───────────────────┘
```

---

## 5. API Endpoints (전체 목록)

### 5.1 Market Data (`/api/market`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/market/indices` | S&P 500, NASDAQ, KOSPI, BTC |
| GET | `/api/market/overview` | 글로벌 시장 개요 |
| GET | `/api/market/overview/{ticker}` | 자산유형별 개요 (Equity/ETF/Commodity 자동분기) |
| GET | `/api/market/sectors` | 섹터 히트맵 데이터 |
| GET | `/api/market/sector/{ticker}` | 섹터, 산업, 시총, PE, 베타, 52주 |
| GET | `/api/market/health/{ticker}` | DuPont, Altman Z, Red Flags |
| GET | `/api/market/quote/{ticker}` | 현재가, 변동률 (빠른 시세) |
| GET | `/api/market/trend/{ticker}` | 5년 재무 트렌드 |
| GET | `/api/market/peers/{ticker}` | 동종업계 밸류에이션 멀티플 |
| GET | `/api/market/comps` | 비교기업 분석 |
| GET | `/api/market/piotroski/{ticker}` | Piotroski F-Score |
| GET | `/api/market/sankey/{ticker}` | 손익 Sankey 데이터 |
| GET | `/api/market/radar/{ticker}` | 레이더 차트 지표 |
| GET | `/api/market/etf/{ticker}/holdings` | ETF 보유종목 |
| GET | `/api/market/commodity/{ticker}/seasonal` | 원자재 월별 계절성 |
| GET | `/api/market/commodity/{ticker}/correlations` | 원자재 상관관계 |

### 5.2 Financials (`/api/financials`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/financials/{ticker}/statements` | IS + BS + CF 통합 (yfinance → yahooquery 폴백) |
| GET | `/api/financials/{ticker}/highlights` | 핵심 재무 요약 (매출, 마진, ROE, D/E, OCF) |
| GET | `/api/financials/{ticker}/kpi-history` | 분기 KPI 시계열 (매출성장, 마진, ROE, FCF) |
| GET | `/api/financials/{ticker}/ratios` | 밸류에이션·재무 비율 |

### 5.3 Valuation (`/api/valuation`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/valuation/dcf-inputs/{ticker}` | DCF 입력 자동채움 |
| GET | `/api/valuation/smart-defaults/{ticker}` | 스마트 DCF 기본값 |
| POST | `/api/valuation/dcf` | 3-시나리오 DCF |
| POST | `/api/valuation/sensitivity` | WACC × Terminal Growth 매트릭스 |
| POST | `/api/valuation/monte-carlo` | 5000회 시뮬레이션 + 히스토그램 |
| POST | `/api/valuation/tornado` | 변수별 민감도 순위 |
| POST | `/api/valuation/reverse-dcf` | 시장 내재 성장률 (scipy brentq) |
| GET | `/api/valuation/consensus/{ticker}` | 애널리스트 컨센서스 |

### 5.4 Technical (`/api/technical`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/technical/{ticker}/indicators` | RSI, SMA, EMA, MACD, BB, ATR |
| GET | `/api/technical/{ticker}/chart-data` | OHLCV 캔들 데이터 |
| GET | `/api/technical/{ticker}/fibonacci` | 피보나치 되돌림 레벨 |
| GET | `/api/technical/{ticker}/ichimoku` | 일목균형표 클라우드 |

### 5.5 Earnings (`/api/earnings`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/earnings/{ticker}/history` | EPS Beat/Miss 이력 |
| GET | `/api/earnings/{ticker}/calendar` | 다음 실적 발표일 |
| GET | `/api/earnings/{ticker}/quarterly` | 분기별 매출/순이익 |
| GET | `/api/earnings/{ticker}/transcript` | 어닝콜 트랜스크립트 (FMP 키 필요) |

### 5.6 Research (`/api/research`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/research/dashboard/{ticker}` | 퀀트 대시보드 (F-Score/DuPont/Sankey/Waterfall/Anomaly) |

### 5.7 FMP (`/api/fmp`, 선택)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/fmp/key-metrics/{ticker}` | 히스토리컬 key metrics (키 없으면 Yahoo 스냅샷) |
| GET | `/api/fmp/ratios/{ticker}` | 히스토리컬 ratios (키 없으면 Yahoo 스냅샷) |

### 5.8 Macro (`/api/macro`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/macro/quadrant` | 글로벌 성장 vs 인플레 Z-score 사분면 |
| GET | `/api/macro/yield-fx` | US10Y 스프레드 vs FX (usdjpy\|eurusd\|usdkrw) |
| GET | `/api/macro/smart-money` | Copper/Gold ratio + RORO 복합지수 |
| GET | `/api/macro/fred/{series_id}` | FRED 시계열 (공개 CSV) |
| GET | `/api/macro/oecd/mei` | OECD MEI (빈 배열 — API 변경 대비) |
| GET | `/api/macro/oecd/cli` | OECD CLI 스냅샷 (DBnomics) |
| GET | `/api/macro/snapshot` | 매크로 사이클 히트맵 (국가, 자산, 밸류에이션) |
| GET | `/api/macro/korea` | 한국 경제 지표 (ECOS or yfinance 폴백) |
| GET | `/api/macro/economic-calendar` | 경제 캘린더 (스크래핑) |
| GET | `/api/macro/ecos` | ECOS 직접 호출 (`ECOS_API_KEY`) |
| GET | `/api/macro/calendar` | 경제 캘린더 — FMP (`FMP_API_KEY`) |

### 5.9 DART (`/api/dart`, 선택)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/dart/search?q=` | 상장사 이름 검색 (`DART_API_KEY`) |
| GET | `/api/dart/sections/{ticker}` | 최신 사업보고서 → SEC 유사 5섹션 + HTML (`.KS` / `.KQ`) |

### 5.10 EDINET (`/api/edinet`, 선택)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/edinet/links/{ticker}` | EDINET 포털 링크 (키 없이 사용, `7203.T`) |
| GET | `/api/edinet/sections/{ticker}` | 有価証券報告書 섹션 (`EDINET_SUBSCRIPTION_KEY` 없으면 링크만) |

### 5.11 SEC EDGAR (`/api/edgar`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/edgar/sections/{ticker}` | 10-K 섹션별 텍스트 (1A, 3, 7, 8, 9A) |
| GET | `/api/edgar/item7/{ticker}` | Item 7 MD&A 텍스트만 |
| GET | `/api/edgar/compare/{ticker}` | 최신 vs 3년전 Item 7 비교 |

### 5.12 Insider (`/api/insider`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/insider/{ticker}` | 최근 내부자 거래 |
| GET | `/api/insider/{ticker}/holders` | 기관투자자 보유 현황 |

### 5.13 News (`/api/news`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/news/{ticker}` | Finviz(스크랩) + Google RSS + Yahoo Finance RSS |
| GET | `/api/news/{ticker}/sentiment` | 뉴스 감성 분석 |

### 5.14 Screener (`/api/screener`)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/screener/search` | 종목 스크리너 (PE, 섹터, 배당 필터) |
| POST | `/api/screener/backtest` | 전략 백테스트 (SMA/RSI/Buy&Hold) |

### 5.15 Markets (`/api/markets`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/markets/heatmap/{index_name}` | 지수 구성종목 히트맵 (S&P/NASDAQ/KOSPI/FTSE) |

### 5.16 Video Transcript (`/api/video`)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/video/submit` | YouTube/웹 URL/로컬 경로 제출 → 비동기 transcript job 생성 |
| POST | `/api/video/upload` | multipart 업로드 → 임시 저장 후 transcript job 생성 |
| GET | `/api/video/jobs` | 최근 트랜스크립트 작업 목록 |
| GET | `/api/video/jobs/{job_id}` | 단일 작업 상세 (상태 + 분석 + 원문) |
| GET | `/api/video/search?q=` | 저장된 트랜스크립트 전문 검색 |
| DELETE | `/api/video/jobs/{job_id}` | 작업 삭제 |

### 5.17 기타
| Prefix | 설명 |
|--------|------|
| `/api/analysis` | Gemini AI 분석 (strategy/risks/mda/forensic/financials) |
| `/api/chat` | AI Copilot (stream/complete/suggested/configure) |
| `/api/crypto` | 암호화폐 시세 |
| `/api/fx` | 환율 |
| `/api/estimates` | 애널리스트 추정치 (consensus/history/growth) |
| `/api/portfolio` | 포트폴리오 CRUD + Risk + OCR + Screenshot |

---

## 6. Frontend Pages (전체 13개)

| 경로 | 파일 | 핵심 기능 |
|------|------|----------|
| `/` | `page.tsx` | **Multi-Asset Overview** — 티커 자동감지 → Equity(섹터/DuPont/Altman Z/KPI/Peer)/ETF(보유종목/섹터비중)/Commodity(계절성/상관) |
| `/research` | `research/page.tsx` | **리서치 그리드** — F-Score 이력, DuPont Tree, Sankey(손익흐름), Waterfall(영업이익), YoY 이상치+Gemini 설명 |
| `/valuation` | `valuation/page.tsx` | **5-Tab**: DCF(3시나리오), Sensitivity Matrix(WACC×TG), Monte Carlo(히스토그램), Tornado, Reverse DCF |
| `/technical` | `technical/page.tsx` | TradingView 캔들(lightweight-charts), RSI/MACD/ATR 카드, 이동평균, Bollinger, Fibonacci, Ichimoku |
| `/markets` | `markets/page.tsx` | 재무제표 테이블(YoY Growth/Margin) + **섹터 히트맵**(S&P/NASDAQ/KOSPI/FTSE) |
| `/macro` | `macro/page.tsx` | **5탭**(FRED/Cycle Heatmap/OECD CLI/Korea/Calendar) + **Quadrant**(성장vs인플레) + **YieldFX** + **SmartMoney**(Copper/Gold+RORO) |
| `/earnings` | `earnings/page.tsx` | 다음 실적일, EPS Beat/Miss 바차트, 분기 매출/순이익 |
| `/news` | `news/page.tsx` | Split-view — 좌측 기사 리스트(340px) + 우측 iframe 원문 보기 |
| `/transcripts` | `transcripts/page.tsx` | 비디오/오디오 입력, 상태 폴링, 요약/키워드/감성, 전문검색 |
| `/screener` | `screener/page.tsx` | **종목 스크리너**(PE/섹터/배당 필터) + **전략 백테스트**(SMA/RSI/Buy&Hold, 캔들차트 시각화) |
| `/portfolio` | `portfolio/page.tsx` | 포지션 CRUD + Risk Metrics(VaR/Sharpe/MDD) + OCR 스크린샷 |
| `/filings` | `filings/page.tsx` | **관할권 자동분기** — 티커 접미사로 SEC/DART(`.KS`/`.KQ`)/EDINET(`.T`), 5탭 + AI Summary |
| `/settings` | `settings/page.tsx` | Gemini API Key, SEC Email 설정 |

---

## 7. Ticker State Management

**전역 티커 상태**는 React Context 없이 `localStorage` + `CustomEvent` 패턴으로 관리:

```tsx
// apps/web/src/app/lib/use-ticker.ts
export function useTicker() {
  const [ticker, setTicker] = useState(() =>
    localStorage.getItem("atlas-ticker") || "MSFT"
  );

  // 다른 컴포넌트의 변경도 감지
  useEffect(() => {
    const handler = () => setTicker(localStorage.getItem("atlas-ticker") || "MSFT");
    window.addEventListener("ticker-changed", handler);
    return () => window.removeEventListener("ticker-changed", handler);
  }, []);

  const updateTicker = (t: string) => {
    localStorage.setItem("atlas-ticker", t.toUpperCase());
    window.dispatchEvent(new CustomEvent("ticker-changed"));
  };

  return { ticker, setTicker: updateTicker };
}
```

**사용법**: 모든 페이지에서 `const { ticker } = useTicker();`로 현재 티커 접근.
TickerBar의 검색창에서 `setTicker()`로 전역 변경.

---

## 8. Key Algorithms

### DCF 10Y 2-Stage (`server/services/dcf_engine.py`)
- Stage 1 (Y1-5): `FCF × (1 + growth)^t`
- Stage 2 (Y6-10): growth linearly fades to terminal growth rate
- Terminal Value at Y10: `FCF₁₀ × (1 + TG) / (WACC - TG)`
- Enterprise Value = sum of discounted FCFs + discounted TV

### Reverse DCF (`server/services/dcf_engine.py`)
- scipy `brentq` root-finding: 현재 시가총액을 설명하는 성장률 역산
- `f(g) = DCF(g) - market_cap = 0` 풀기

### Monte Carlo (`server/services/monte_carlo.py`)
- numpy로 5000회 시뮬레이션
- growth, wacc, margin을 정규분포로 샘플링
- 히스토그램 빈 + P(> current price) 계산

### Sensitivity Matrix (`server/services/sensitivity.py`)
- WACC (행) × Terminal Growth (열) 조합별 DCF 결과 매트릭스
- Tornado: 각 변수를 ±20% 변동시켜 가격 영향 범위 계산, 영향력 순 정렬

### DuPont 3-Factor
`ROE = NPM × Asset Turnover × Equity Multiplier`

### Altman Z-Score
`Z = 1.2(WC/TA) + 1.4(RE/TA) + 3.3(EBIT/TA) + 0.6(MC/TL) + 1.0(Sales/TA)`

### Technical Indicators (`server/services/technical_analysis.py`)
- `ta` 라이브러리 사용: RSI, MACD, Bollinger Bands, Ichimoku Cloud, ADX
- `detect_signals()`: MA 크로스, RSI 과매수/과매도, MACD 시그널
- `compute_fibonacci_levels()`: 52주 고/저 기반 되돌림 레벨

---

## 9. Development Rules (가드레일)

### 코드
- TypeScript strict mode (프론트), Python type hints (백엔드)
- 모든 API 호출 try/except; UI에 기술적 에러 노출 금지
- 캐싱: 재무=TTL 300초, 10-K=영구, 환율=TTL 60초
- `"use client"` — 모든 페이지 최상단에 필수 (App Router + hooks)

### 프론트엔드 API 호출 패턴
```tsx
// Next.js rewrites가 /api/* → localhost:8000/api/* 프록시
// 따라서 상대경로로 호출:
fetch(`/api/market/sector/${ticker}`)
fetch(`/api/valuation/dcf`, { method: "POST", body: JSON.stringify(params) })
```

### Gemini API
- 요청당 최대 25,000자, temperature 0.2~0.4
- 429 → 60초 대기 × 3회 재시도
- 스트리밍: MD&A/Risk 분석은 `stream=True`

### yfinance 주의사항
- `earnings_history` 컬럼명: `epsActual`, `epsEstimate`, `surprisePercent` (camelCase)
- `surprisePercent`는 소수 (0.0759 = 7.59%) → 프론트에서 `× 100` 필요
- 날짜는 DataFrame index에 있음 (컬럼 아님) → `str(idx)[:10]`
- 연간 데이터에 TTM 행 혼재 가능 → `_filter_annual()` 적용

### 서버 실행
```bash
# 백엔드 (포트 8000)
cd atlas-terminal
PYTHONPATH="." python3 -m uvicorn server.main:app --port 8000 --host 0.0.0.0

# 프론트엔드 (포트 3000)
cd atlas-terminal/apps/web
npm run dev
```

### Git
- 커밋: `feat:`, `fix:`, `docs:`, `refactor:` 접두사
- 브랜치: `main`, `dev`, `feat/기능명`

---

## 10. Dependencies

### Python (`requirements.txt`)
```
fastapi>=0.110.0        uvicorn[standard]>=0.29.0
pydantic>=2.7.0         google-generativeai>=0.8.0
anthropic>=0.39.0       openai>=1.50.0
beautifulsoup4>=4.12.0  requests>=2.31.0
pandas>=2.0.0           lxml>=4.9.0
python-dotenv>=1.0.0    python-multipart>=0.0.9
yfinance>=0.2.40        yahooquery>=2.2.0
sec-edgar-downloader>=5.0.0  feedparser>=6.0.0
ta>=0.11.0              dart-fss>=0.4.0
numpy>=1.20.0           scipy>=1.10.0
dbnomics>=1.2.0         aiosqlite>=0.20.0
asyncpg>=0.30.0         pillow>=10.0.0
httpx>=0.27.0           pytest>=8.0.0
faster-whisper>=1.0.3   yt-dlp>=2024.10.7
srt>=3.5.3              ffmpeg-python>=0.2.0
```

### Node.js (`apps/web/package.json`)
```
next: 14.2.35           react: ^18
lightweight-charts: ^5.1.0
tailwindcss: ^3.4.1     typescript: ^5
@nivo/sankey: ^0.99.0   @nivo/bar: ^0.99.0
recharts: ^2.15.4
```

---

## 11. Environment Variables
```env
GOOGLE_API_KEY=        # Gemini API
SEC_EDGAR_EMAIL=       # SEC 정책 필수 (10-K 다운로드용)
DATABASE_URL=          # PostgreSQL (없으면 SQLite 자동)
WHISPER_MODEL_SIZE=    # faster-whisper model size (default: base, optional: small/medium)
NEWS_API_KEY=          # 선택
FMP_API_KEY=           # Financial Modeling Prep (선택 — 비율·트랜스크립트·캘린더)
ECOS_API_KEY=          # 한국은행 ECOS (선택)
DART_API_KEY=          # 금융감독원 Open DART (선택 — DART 사업보고서)
EDINET_SUBSCRIPTION_KEY=  # 일본 금융청 EDINET API v2 (선택 — 有価証券報告書)
```

---

## 12. 알려진 이슈 및 주의사항

1. **`apps/web/app/` vs `apps/web/src/app/`**: 구 TanStack Start의 `app/` 디렉토리가 `_legacy_tanstack_app`으로 이름변경됨. Next.js는 `src/app/`을 사용. 절대 루트의 `app/` 디렉토리를 만들지 말 것.

2. **Financial 데이터 혼합**: yahooquery는 12M + TTM 데이터를 섞어 반환할 수 있음. `server/routers/financials.py`의 `_filter_annual()` 함수가 TTM 필터링.

3. **CORS**: `server/main.py`에서 `localhost:3000`, `localhost:3001`, `127.0.0.1:3000` 허용 설정됨.

4. **Google Fonts**: `layout.tsx`의 `<head>`에서 Inter + JetBrains Mono 로드. `<link>` 태그 직접 삽입 방식.

---

## 13. 미구현 기능 (TODO)

- [ ] Widget-based 대시보드 (react-grid-layout) — 미구현, 패키지도 미설치
- [ ] Enhanced AI Copilot — 인용/추론 단계 표시
- [ ] Multi-LLM 시스템 (Gemini + Claude + OpenAI provider abstraction) — `ai/llm_router.py` 스캐폴딩만
- [ ] Extended DuPont 5-Factor 분석 — 현재 3-Factor만
- [x] DART 사업보고서 Filings 연동 (`/api/dart/sections/{ticker}`, `dart_filing_service`)
- [x] EDINET 링크 + 선택적 본문 (`/api/edinet/sections|links`, `EDINET_SUBSCRIPTION_KEY`)
- [x] Sankey 차트 (`research/SankeyWidget.tsx` + `@nivo/sankey`)
- [x] Radar 차트 (`/api/market/radar/{ticker}` 엔드포인트)
- [x] 종목 스크리너 + 전략 백테스트 (`/screener` 페이지)
- [x] Multi-Asset Overview — Equity/ETF/Commodity 자동분기
- [x] Macro 페이지 — FRED/Cycle/OECD/Korea/Calendar + Quadrant/YieldFX/SmartMoney
- [x] Research 대시보드 — F-Score/DuPont Tree/Sankey/Waterfall/Anomaly 그리드
- [x] 관할권 자동분기 Filings — SEC/DART/EDINET 티커 접미사 기반
- [x] 포트폴리오 OCR 스크린샷 — `/api/portfolio/screenshot` 엔드포인트 + UI 연결
- [ ] ⌘K 글로벌 커맨드 팔레트
- [ ] Settings 페이지에 FMP/ECOS/DART/EDINET 키 설정 UI 추가
- [ ] GitHub README 자동 업데이트 워크플로우

---

*마지막 수정: 2026-03-26*
