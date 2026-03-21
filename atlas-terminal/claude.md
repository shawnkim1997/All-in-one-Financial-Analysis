# claude.md — ATLAS Terminal Build Guide

> 이 문서는 Claude Code 에이전트가 프로젝트를 빌드할 때 참조하는 마스터 가이드입니다.
> 모든 에이전트는 작업 시작 전 이 문서를 반드시 읽어야 합니다.
> **마지막 수정: 2026-03-21**

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

### 2.3 다단계 폴백 체인
모든 외부 API 호출은 아래 순서를 따른다:
```
yfinance (1순위) → yahooquery (2순위) → fast_info (3순위) → info (4순위)
→ balance_sheet/cashflow (5순위) → TTM 분기 합산 (6순위) → 수동 입력 (최후)
```
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
│   │   ├── layout.tsx               # 루트 레이아웃 (3-panel: Sidebar + Main + ChatPanel)
│   │   ├── page.tsx                 # Overview (Sector, DuPont, Altman Z)
│   │   ├── globals.css              # Tailwind + Terminal Noir 기본 스타일
│   │   ├── research/page.tsx        # 10-K AI 분석 + Risk Factors
│   │   ├── valuation/page.tsx       # 5-Tab: DCF, Sensitivity, Monte Carlo, Tornado, Reverse DCF
│   │   ├── technical/page.tsx       # TradingView 캔들차트 + RSI/MACD/Bollinger/Fibonacci/MA
│   │   ├── markets/page.tsx         # 재무제표 테이블 (YoY Growth + Margin %)
│   │   ├── earnings/page.tsx        # EPS Beat/Miss + Revenue + Next Earnings
│   │   ├── news/page.tsx            # Split-view: 기사 리스트 + iframe 원문
│   │   ├── portfolio/page.tsx       # 포지션 CRUD + Risk Metrics
│   │   ├── filings/page.tsx         # SEC 10-K 원문 (5개 섹션 탭 + AI 요약)
│   │   ├── settings/page.tsx        # API Key 관리
│   │   ├── components/
│   │   │   ├── sidebar.tsx          # 좌측 네비게이션 (10개 메뉴)
│   │   │   ├── ticker-bar.tsx       # 상단 실시간 지수 바 (S&P, NASDAQ, KOSPI, BTC)
│   │   │   └── chat-panel.tsx       # 우측 AI Copilot 채팅
│   │   └── lib/
│   │       ├── use-ticker.ts        # 티커 상태 훅 (localStorage + CustomEvent)
│   │       └── api.ts              # API 클라이언트 유틸
│   ├── next.config.mjs              # /api/* → localhost:8000 프록시
│   ├── tailwind.config.ts           # Terminal Noir 컬러 토큰
│   └── package.json
│
├── server/                          # FastAPI 백엔드
│   ├── main.py                      # FastAPI app + 14개 라우터 등록
│   ├── routers/                     # API 엔드포인트 (14개 라우터)
│   │   ├── analysis.py              # POST /api/analysis — Gemini LLM 분석
│   │   ├── chat.py                  # /api/chat — AI Copilot
│   │   ├── crypto.py                # /api/crypto — 암호화폐 가격
│   │   ├── earnings.py              # /api/earnings/{ticker}/history|calendar|quarterly
│   │   ├── edgar.py                 # /api/edgar — SEC 10-K 다운로드 + 파싱
│   │   ├── estimates.py             # /api/estimates — 애널리스트 추정치
│   │   ├── financials.py            # /api/financials/{ticker} — IS/BS/CF
│   │   ├── fx.py                    # /api/fx — 환율
│   │   ├── insider.py               # /api/insider/{ticker} — 내부자 거래
│   │   ├── market_data.py           # /api/market — 주가/섹터/헬스체크
│   │   ├── news.py                  # /api/news/{ticker} — Finviz + Google RSS
│   │   ├── portfolio.py             # /api/portfolio — CRUD + Risk
│   │   ├── technical.py             # /api/technical/{ticker} — 기술적 지표
│   │   └── valuation.py             # /api/valuation — DCF, Sensitivity, Monte Carlo, Tornado, Reverse DCF
│   ├── services/                    # 비즈니스 로직 (17개 서비스)
│   │   ├── crypto_fetcher.py        # Bithumb + Binance API
│   │   ├── dcf_engine.py            # excel_style_dcf, dcf_10y_2stage, reverse_dcf (scipy brentq)
│   │   ├── financial_metrics.py     # DuPont, Altman Z, Piotroski F-Score
│   │   ├── financial_metrics_ext.py # 확장 지표
│   │   ├── fx_fetcher.py            # 환율 데이터
│   │   ├── gemini_analysis.py       # Gemini 분석 로직
│   │   ├── gemini_service.py        # Gemini API 래퍼 (retry, streaming)
│   │   ├── market_data.py           # 시장 데이터 서비스
│   │   ├── market_fetcher.py        # yfinance/yahooquery 폴백 체인
│   │   ├── monte_carlo.py           # run_monte_carlo_dcf (numpy, 5000 sims)
│   │   ├── news_aggregator.py       # RSS + Finviz + Google News
│   │   ├── risk_metrics.py          # VaR, Sharpe, Sortino, MDD, Beta, Correlation
│   │   ├── screenshot_ocr.py        # Gemini Vision OCR (포트폴리오 스크린샷)
│   │   ├── sec_parser.py            # 10-K 다운로드 + HTML 파싱 + 섹션 추출 + 캐싱
│   │   ├── sensitivity.py           # build_sensitivity_matrix, build_tornado_data
│   │   ├── technical_analysis.py    # RSI, MACD, Bollinger, Ichimoku, ADX, Fibonacci
│   │   └── text_chunker.py          # smart_chunk, clean_text_for_llm
│   ├── db/                          # 데이터베이스 레이어
│   │   ├── unified_repo.py          # SQLite/PostgreSQL 통합 인터페이스
│   │   ├── cache.py                 # 캐시 저장소
│   │   ├── database.py              # SQLite 커넥션
│   │   ├── pg_database.py           # PostgreSQL 커넥션
│   │   ├── portfolio_repo.py        # 포트폴리오 SQLite CRUD
│   │   ├── pg_portfolio_repo.py     # 포트폴리오 PostgreSQL CRUD
│   │   ├── pg_cache_repo.py         # PostgreSQL 캐시
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
│       └── ticker_utils.py          # 티커 유틸리티
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
| GET | `/api/market/sector/{ticker}` | 섹터, 산업, 시총, PE, 베타, 52주 |
| GET | `/api/market/health/{ticker}` | DuPont, Altman Z, Red Flags |
| GET | `/api/market/price/{ticker}` | 현재가, 변동률 |
| GET | `/api/market/indices` | S&P 500, NASDAQ, KOSPI, BTC |

### 5.2 Financials (`/api/financials`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/financials/{ticker}` | 손익계산서 (yfinance → yahooquery 폴백) |
| GET | `/api/financials/balance/{ticker}` | 대차대조표 |
| GET | `/api/financials/cashflow/{ticker}` | 현금흐름표 |

### 5.3 Valuation (`/api/valuation`)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/valuation/dcf` | 10Y 2-Stage DCF |
| POST | `/api/valuation/sensitivity` | WACC × Terminal Growth 매트릭스 |
| POST | `/api/valuation/monte-carlo` | 5000회 시뮬레이션 + 히스토그램 |
| POST | `/api/valuation/tornado` | 변수별 민감도 순위 |
| POST | `/api/valuation/reverse-dcf` | 시장 내재 성장률 (scipy brentq) |

### 5.4 Technical (`/api/technical`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/technical/{ticker}` | RSI, MACD, Bollinger, MA, ADX, Ichimoku |
| GET | `/api/technical/{ticker}/chart` | OHLCV 캔들 데이터 |

### 5.5 Earnings (`/api/earnings`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/earnings/{ticker}/history` | EPS Beat/Miss 이력 |
| GET | `/api/earnings/{ticker}/calendar` | 다음 실적 발표일 |
| GET | `/api/earnings/{ticker}/quarterly` | 분기별 매출/순이익 |

### 5.6 Insider (`/api/insider`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/insider/{ticker}` | 최근 내부자 거래 |
| GET | `/api/insider/{ticker}/holders` | 기관투자자 보유 현황 |

### 5.7 News (`/api/news`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/news/{ticker}` | Finviz + Google News RSS |

### 5.8 SEC EDGAR (`/api/edgar`)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/edgar/download` | 10-K 다운로드 (sec-edgar-downloader) |
| GET | `/api/edgar/sections/{ticker}` | 10-K 섹션별 텍스트 (1A, 3, 7, 8, 9A) |

### 5.9 기타
| Prefix | 설명 |
|--------|------|
| `/api/analysis` | Gemini AI 분석 |
| `/api/chat` | AI Copilot 대화 |
| `/api/crypto` | 암호화폐 (Bithumb + Binance) |
| `/api/fx` | 환율 |
| `/api/estimates` | 애널리스트 추정치 |
| `/api/portfolio` | 포트폴리오 CRUD + Risk Metrics |

---

## 6. Frontend Pages (10개)

| 경로 | 파일 | 핵심 기능 |
|------|------|----------|
| `/` | `page.tsx` | Overview — 섹터/산업, 시총/PE/베타, Altman Z-Score, DuPont 분해 |
| `/research` | `research/page.tsx` | 10-K AI 분석 — MD&A + Risk Factors (Gemini) |
| `/valuation` | `valuation/page.tsx` | **5-Tab**: DCF, Sensitivity Matrix (WACC×TG), Monte Carlo (히스토그램), Tornado, Reverse DCF |
| `/technical` | `technical/page.tsx` | TradingView 캔들차트 (lightweight-charts), RSI/MACD/ATR 카드, 이동평균 테이블, Bollinger, Fibonacci |
| `/markets` | `markets/page.tsx` | 재무제표 테이블 — Revenue→EBITDA, YoY Growth 뱃지(초록/빨강), Margin % 행 |
| `/earnings` | `earnings/page.tsx` | 다음 실적일, EPS Beat/Miss 바차트, 분기 매출/순이익 |
| `/news` | `news/page.tsx` | Split-view — 좌측 기사 리스트(340px) + 우측 iframe 원문 보기 |
| `/portfolio` | `portfolio/page.tsx` | 포지션 관리 + Risk Metrics (VaR, Sharpe, MDD) |
| `/filings` | `filings/page.tsx` | SEC 10-K 원문 — 5개 섹션 탭 (Risk, MD&A, Financials, Legal, Controls) + AI Summary |
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
python-dotenv>=1.0.0    yfinance>=0.2.40
yahooquery>=2.2.0       sec-edgar-downloader>=5.0.0
feedparser>=6.0.0       ta>=0.11.0
numpy                   scipy
aiosqlite>=0.20.0       asyncpg>=0.30.0
pillow>=10.0.0
```

### Node.js (`apps/web/package.json`)
```
next: 14.2.35           react: ^18
lightweight-charts: ^5.1.0
tailwindcss: ^3.4.1     typescript: ^5
```

---

## 11. Environment Variables
```env
GOOGLE_API_KEY=        # Gemini API
SEC_EDGAR_EMAIL=       # SEC 정책 필수 (10-K 다운로드용)
DATABASE_URL=          # PostgreSQL (없으면 SQLite 자동)
NEWS_API_KEY=          # 선택
DART_API_KEY=          # 한국 공시 (선택)
```

---

## 12. 알려진 이슈 및 주의사항

1. **`apps/web/app/` vs `apps/web/src/app/`**: 구 TanStack Start의 `app/` 디렉토리가 `_legacy_tanstack_app`으로 이름변경됨. Next.js는 `src/app/`을 사용. 절대 루트의 `app/` 디렉토리를 만들지 말 것.

2. **Financial 데이터 혼합**: yahooquery는 12M + TTM 데이터를 섞어 반환할 수 있음. `server/routers/financials.py`의 `_filter_annual()` 함수가 TTM 필터링.

3. **CORS**: `server/main.py`에서 `localhost:3000`, `localhost:3001`, `127.0.0.1:3000` 허용 설정됨.

4. **Google Fonts**: `layout.tsx`의 `<head>`에서 Inter + JetBrains Mono 로드. `<link>` 태그 직접 삽입 방식.

---

## 13. 미구현 기능 (TODO)

- [ ] Widget-based 대시보드 (react-grid-layout) — 패키지 설치됨, 미구현
- [ ] Enhanced AI Copilot — 인용/추론 단계 표시
- [ ] Multi-LLM 시스템 (Gemini + Claude + OpenAI provider abstraction) — `ai/llm_router.py` 스캐폴딩만
- [ ] Extended DuPont 5-Factor 분석
- [ ] DART (한국 공시) / EDINET (일본 공시) 통합
- [ ] 포트폴리오 스크린샷 OCR (Gemini Vision) — 서비스 존재, UI 미연결
- [ ] ⌘K 글로벌 커맨드 팔레트
- [ ] Sankey (자금흐름), Radar (재무건전성) 차트
- [ ] GitHub README 자동 업데이트 워크플로우

---

*마지막 수정: 2026-03-21*
