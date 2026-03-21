# ATLAS Terminal — 종합 프로젝트 평가 & 빌딩 가이드

---

## PART 1: 현재 프로젝트 평가

### 🟢 잘한 점 (Strengths)

**1. 하이브리드 아키텍처 — 이건 진짜 좋다**
정성(LLM)과 정량(Pandas/yfinance)을 분리한 설계는 비용 효율성과 정확도를 동시에 잡는 프로덕션 레벨 판단이다. Gemini를 텍스트 분석에만 쓰고, 숫자는 무료 API에서 가져오는 구조는 실제 FinTech 스타트업에서도 채택하는 패턴이다.

**2. 429 토큰 최적화 — 실전 문제 해결**
200페이지 10-K를 통째로 보내지 않고, Item 1A~9A만 슬라이싱 → regex 파싱 → smart_chunk로 head+tail 보존하는 전략은 토큰 80%+ 절감을 달성했다. 이건 면접에서 강력한 스토리가 된다.

**3. 다단계 폴백 시스템**
yahooquery → yfinance(fast_info → info → balance_sheet) → TTM/분기 합산 → 수동 입력 순으로 떨어지는 폴백 체인은 실사용에서 데이터 누락을 최소화한다. `_safe_float()` 일관 사용도 좋다.

**4. 10년 2단계 DCF**
5년 DCF의 터미널밸류 왜곡 문제를 인식하고 Y6~10 선형 Fade를 적용한 건 학부생 수준을 넘어선다. Damodaran 참조 패널까지 있어서 학술적 근거도 확보했다.

**5. Piotroski F-Score, Altman Z, DuPont — 정량 깊이**
단순 밸류에이션이 아닌 재무 건전성 지표까지 커버한 점이 Bloomberg Terminal 컨셉과 맞다.

### 🟡 개선이 필요한 점 (Weaknesses)

**1. app.py 단일 파일 2,846줄 — 가장 큰 기술 부채**
SEC 파싱, Gemini 호출, DCF 계산, 차트 생성, UI 렌더링이 전부 하나에 있다. 디버깅, 테스트, 협업 모두 어렵다. 모듈 분리가 최우선이다.

**2. Streamlit 한계 — Bloomberg 터미널 UI와 거리가 있다**
Streamlit은 프로토타이핑엔 최고지만, 다중 패널 동시 업데이트, 실시간 웹소켓, 커스텀 레이아웃에 제약이 크다. Next.js + FastAPI로 전환하면 진정한 터미널 UX가 가능하다.

**3. 글로벌 시장 커버리지 — 아직 US 중심**
한국(DART), 일본(EDINET), 유럽, 중국/홍콩 공시 파싱이 "Phase 2" 상태다. 가격 데이터는 yfinance 접미사로 커버되지만, 공시 분석은 미국만 된다.

**4. 포트폴리오 — 스크린샷 OCR은 있지만 지속성 부족**
Trading 212, IBKR 스크린샷 분석은 구현되었으나, 포지션 이력 추적, 수익률 시계열, 리밸런싱 인사이트가 없다. Supabase에 저장하면 해결된다.

**5. 뉴스 통합 없음**
회사 관련 뉴스가 아예 없다. Bloomberg 터미널의 핵심 기능 중 하나인 뉴스 피드가 빠져 있다.

**6. 환율/암호화폐 — 별도 탭이지만 메인 대시보드와 통합 부족**
Bithumb/Binance 가격은 있지만, 포트폴리오 총 수익률에 FX 영향이 실시간으로 반영되는 통합 뷰가 없다.

### 🔴 위험 요소 (Risks)

- `app.py` 3000줄 단일 파일은 더 커지면 유지보수 불가능해진다
- yfinance/yahooquery는 언제든 차단될 수 있다 (IP 제한)
- Gemini 무료 티어 rate limit은 프로덕션에서 문제가 된다
- SEC EDGAR User-Agent 정책 위반 시 IP 차단 가능

---

## PART 2: 발전 방향 — Next.js 기반 ATLAS Terminal

### 목표 아키텍처

```
atlas-terminal/
├── apps/
│   └── web/                          # Next.js 14 (App Router)
│       ├── app/
│       │   ├── layout.tsx            # 루트 레이아웃 (다크 테마, 글로벌 네비)
│       │   ├── page.tsx              # 메인 대시보드 (그리드 레이아웃)
│       │   ├── (dashboard)/
│       │   │   ├── overview/         # 포트폴리오 오버뷰 + 뉴스 피드
│       │   │   ├── research/         # 10-K 분석 + 뉴스 (회사별)
│       │   │   ├── valuation/        # DCF + RIM + Comps
│       │   │   ├── markets/          # 히트맵 + 환율 + 암호화폐
│       │   │   ├── portfolio/        # 포지션 관리 + 스크린샷 OCR
│       │   │   └── filings/          # SEC/DART/EDINET 원문 뷰어
│       │   └── api/                  # Route Handlers (BFF 패턴)
│       │       ├── search/
│       │       ├── news/
│       │       └── portfolio/
│       ├── components/
│       │   ├── ui/                   # shadcn/ui 기반 원자 컴포넌트
│       │   ├── charts/               # Recharts/D3 차트 컴포넌트
│       │   │   ├── SankeyFlow.tsx
│       │   │   ├── RadarHealth.tsx
│       │   │   ├── DCFWaterfall.tsx
│       │   │   └── HeatmapGrid.tsx
│       │   ├── terminal/             # 터미널 스타일 컴포넌트
│       │   │   ├── TickerBar.tsx     # 상단 실시간 티커 바
│       │   │   ├── CommandPalette.tsx # ⌘K 검색
│       │   │   ├── PanelGrid.tsx     # 리사이즈 가능 패널
│       │   │   └── NewsFeed.tsx      # 실시간 뉴스 피드
│       │   └── portfolio/
│       │       ├── ScreenshotUpload.tsx
│       │       └── PositionTable.tsx
│       ├── lib/
│       │   ├── api-client.ts         # FastAPI 호출 래퍼
│       │   └── format.ts             # 통화/숫자 포맷 유틸
│       └── styles/
│           └── terminal-theme.css    # Bloomberg 스타일 CSS 변수
│
├── server/                           # FastAPI 백엔드
│   ├── main.py                       # FastAPI 엔트리포인트
│   ├── routers/
│   │   ├── edgar.py                  # SEC EDGAR 다운로드/파싱
│   │   ├── dart.py                   # 한국 DART API
│   │   ├── edinet.py                 # 일본 EDINET API
│   │   ├── analysis.py              # Gemini LLM 분석 (MD&A, Risk)
│   │   ├── valuation.py             # DCF, RIM, Comps 계산
│   │   ├── market_data.py           # yfinance/yahooquery 래퍼
│   │   ├── news.py                  # 뉴스 집계 (RSS + API)
│   │   ├── crypto.py                # Bithumb/Binance API
│   │   ├── fx.py                    # 환율 데이터
│   │   └── portfolio.py             # 포트폴리오 CRUD + OCR
│   ├── services/
│   │   ├── gemini_service.py        # Gemini API 래퍼 (retry, chunk, stream)
│   │   ├── sec_parser.py            # 10-K HTML → 섹션 추출
│   │   ├── text_chunker.py          # smart_chunk, clean_text_for_llm
│   │   ├── dcf_engine.py            # 10Y 2-stage DCF + Reverse DCF + RIM
│   │   ├── financial_metrics.py     # DuPont, Altman Z, F-Score, Red Flags
│   │   ├── market_fetcher.py        # yfinance/yahooquery 폴백 체인
│   │   └── screenshot_ocr.py        # Gemini Vision 포트폴리오 OCR
│   ├── models/
│   │   ├── schemas.py               # Pydantic 요청/응답 스키마
│   │   └── db.py                    # Supabase 클라이언트
│   └── utils/
│       ├── safe_float.py            # _safe_float, _na 유틸
│       ├── ticker_utils.py          # get_global_ticker, infer_market
│       └── cache.py                 # Redis/인메모리 캐시 래퍼
│
├── supabase/
│   └── migrations/                  # DB 스키마 (포트폴리오, 캐시, 사용자)
│
├── claude.md                        # ← 이 파일 (에이전트 빌딩 가이드)
├── .github/
│   └── workflows/
│       └── update-readme.yml        # README 자동 업데이트 (GitHub Actions)
└── package.json
```

### UI 디자인 방향 — "Terminal Noir"

Bloomberg Terminal + Notion의 깔끔함 + 다크 모드를 결합한 디자인

**컬러 팔레트:**
- Background: `#0A0A0F` (거의 검정, 살짝 네이비)
- Surface: `#12121A` (카드/패널 배경)
- Border: `#1E1E2E` (구분선)
- Primary: `#00D4AA` (민트 그린 — 핵심 액션, 상승)
- Danger: `#FF4757` (하락, 경고)
- Text Primary: `#E8E8F0` (거의 흰색)
- Text Secondary: `#6B7280` (설명 텍스트)
- Accent: `#818CF8` (인디고 — AI 분석 결과 강조)

**타이포그래피:**
- 숫자/데이터: `JetBrains Mono` (모노스페이스, 가독성)
- 제목: `Satoshi` (기하학적 산세리프, 모던)
- 본문: `Inter` (가독성 최우선)

**핵심 UI 패턴:**
1. **Command Palette (⌘K)**: 회사 검색, 기능 이동 — Notion/Linear 스타일
2. **리사이즈 가능 패널 그리드**: react-grid-layout으로 사용자가 패널 배치 커스텀
3. **상단 티커 바**: 실시간 가격 스크롤 (주식 + 암호화폐 + 환율)
4. **사이드바 워치리스트**: 즐겨찾기 종목 실시간 업데이트
5. **AI 분석 결과**: 인디고 보더 카드 안에 스트리밍 텍스트

---

## PART 3: claude.md (Claude Code 빌딩 가이드)

아래 내용을 프로젝트 루트의 `claude.md`로 저장하면 Claude Code가 참조한다.

---
