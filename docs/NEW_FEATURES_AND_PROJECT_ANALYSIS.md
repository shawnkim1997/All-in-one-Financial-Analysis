# AGENT.md 기반 프로젝트 분석 — 새로 추가된 기능 상세

> All-in-One Financial Analysis Dashboard  
> 작성 목적: AGENT.md 및 .agent/ 문서를 기준으로, PRD 대비 **현재 프로젝트에 새로 추가·확장된 기능**을 정리한 문서입니다.

---

## 1. 프로젝트 개요 (AGENT.md 기준)

- **프로젝트명:** All-in-One Financial Analysis Dashboard (10-K-summariser-project)
- **진입점:** `AGENT.md` → `.agent/` 내 PRD, Architecture, Data Flows, Directory Map, ADL, Infra, Rules 등 참조
- **아키텍처:** 정성(LLM·Gemini) / 정량(yfinance·yahooquery) **하이브리드 분리**

---

## 2. PRD에 명시된 기본 기능 (기준선)

| 탭 | PRD 핵심 내용 |
|----|----------------|
| **Tab 1** | 10-K Item 1A·Item 7 → Gemini로 경영 전략·리스크 분석 |
| **Tab 2** | 10년 2단계 DCF, Bull/Base/Bear, WACC·Terminal Growth 슬라이더 |
| **Tab 3** | 산업별 동종사 멀티플(P/E, EV/EBITDA, P/B), Gemini 산업 전망 |

---

## 3. 새로 추가·확장된 기능 (상세)

### 3.1 다국가·다시장 지원 (Multi-Market)

- **내용:** 미국 외 **한국(KOSPI/KOSDAQ), 일본(Nikkei), 영국(LSE)** 시장 지원.
- **구현:**
  - `MARKET_OPTIONS`: US, South Korea, Japan, UK 선택.
  - `get_global_ticker(ticker, market)`: 시장별 Yahoo 식별자 접미사 부여 (`.KS`, `.KQ`, `.T`, `.L`).
  - `infer_market_from_ticker(ticker)`: 티커 접미사로 시장 자동 추론 (Deep-Dive 라우팅용).
- **의미:** PRD는 미국 중심이었으나, 비미국 주식 검색·정량 데이터 조회까지 확장됨.

---

### 3.2 Forensic Audit (Item 3 & 9A)

- **내용:** 리스크 분석에 **Item 3(법적 분쟁)·Item 9A(내부통제)** 기반 포렌식 검토를 추가.
- **구현:**
  - `_gemini_forensic_audit()`: Item 3·9A 텍스트만 Gemini에 넘겨 회계·내부통제 리스크 요약.
  - Tab 1 "Analyze Risk Factors (Item 1A)" 실행 시: Item 1A 스트리밍 결과 **뒤에** Forensic Audit 블록을 붙여 최종 출력.
  - UI: "View Previous Risk & **Forensic** Analysis" expander로 이전 분석 재표시.
- **의미:** PRD의 "Item 1A 리스크"를 넘어, 법적·내부통제 리스크까지 한 번에 제공.

---

### 3.3 실시간 스트리밍 (Streaming)

- **내용:** Gemini 응답을 **실시간 스트리밍**으로 표시.
- **구현:**
  - `_generate_stream()`: `stream=True`로 청크 단위 yield.
  - `get_gemini_item7_strategy_stream()`, `get_gemini_item1a_risks_stream()`: Generator 반환.
  - `st.write_stream(stream_gen)`: 첫 단어는 약 5–10초 내, 이후 실시간 유입.
- **의미:** PRD에 없던 "스트리밍" 명시였으나, 현재는 MD&A 전략·리스크 모두 스트리밍으로 구현됨.

---

### 3.4 API 키·이메일 로컬 저장 (Remember me)

- **내용:** 사이드바에서 **"Remember API key & email"** 선택 시 로컬에 저장·복원.
- **구현:**
  - `.app_prefs.json` (프로젝트 루트, `.gitignore` 대상)에 `google_api_key`, `sec_email` 저장.
  - `_load_prefs()` / `_save_prefs()`로 읽기·쓰기.
  - 체크 해제 시 파일 삭제로 저장 중단.
- **의미:** PRD의 "사이드바 전역 설정"을 넘어 **영구 저장** 옵션이 추가됨.

---

### 3.5 10-K Item 8 LLM 추출 (정량 보강)

- **내용:** Tab 1 Financial Health에서 **10-K Item 8(재무제표)** 본문을 Gemini로 해석해 Sankey·Radar·Piotroski에 사용.
- **구현:**
  - `get_sec_financials_llm(api_key, item8, ticker)`: Item 8 텍스트 → 구조화된 재무 수치 추출.
  - `sankey_data_from_ai()`, `radar_metrics_from_ai()`, `piotroski_from_ai()`: AI 추출 결과로 차트·F-Score 계산.
  - 미국·API 키·이메일 있을 때만 호출; 실패 시 기존처럼 yfinance 기반으로 폴백.
- **의미:** ADL-001 "Item 8은 yfinance로 대체"를 유지하면서, **선택적으로** 10-K 원문 기반 정량 분석을 추가한 확장.

---

### 3.6 Financial Health 확장 (Sankey·Radar·F-Score·Altman·Red Flags·YoY·섹터 지표)

- **Sankey:** 손익 흐름 (Revenue → COGS/Gross Profit → OpEx/OpInc → Tax/Interest/Net Income), AI 또는 yfinance.
- **Radar:** ROE, Current Ratio, Asset Turnover, Equity Multiplier, Revenue YoY 정규화 5축; **수동 입력 폴백**(Manual Data Entry expander) 제공.
- **Piotroski F-Score:** 9점 체크리스트; Item 8 LLM 또는 yfinance/TTM.
- **Altman Z-Score:** Safe/Grey/Distress 구간 표시.
- **Red Flags:** Current Ratio < 1.0, Interest Coverage < 1.5 등 조건부 경고.
- **Sector-specific metrics:** `get_sector_specific_metrics()` — Tech(Rule of 40, FCF margin, R&D%), Retail(재고회전율, 영업이익률), Financials(ROE, ROA) 등.
- **YoY 비율 변화:** DuPont·재무 비율의 전년 대비 변화 테이블; **녹색(개선)/빨간색(악화)** 조건부 스타일.
- **분기 모멘텀:** 분기별(QoQ) 테이블 + Change(%) 컬럼 스타일링.
- **의미:** PRD의 "Sankey, Radar, F-Score"를 넘어 Red Flags, YoY, 섹터별 지표, 수동 Radar, 분기 테이블까지 포함한 **정량 헬스 대시보드**로 확장됨.

---

### 3.7 DCF 탭 확장 (Smart Defaults·애널리스트·Damodaran)

- **Smart Defaults:** `get_dcf_smart_defaults()`  
  Beta(CAPM), revenueGrowth/earningsGrowth 기반으로 WACC·Terminal Growth·FCF 성장률 초기값 자동 설정.
- **Reference 패널 (expander):**
  - **Analyst consensus:** `get_analyst_consensus()` — 목표가(target mean price), 추천(recommendationKey), Revenue/Earnings growth 추정.
  - **Damodaran:** 섹터별 WACC 참조값, ERP 4.6%, Rf 4.2%, methodology 링크.
- **5년 트렌드:** Revenue·Net Income·Operating Margin %·FCF YoY 메트릭 + Plotly 5년 Revenue & FCF 라인 차트.
- **의미:** PRD의 "슬라이더 지원"에 더해 **자동 가정치**, **애널리스트·Damodaran 참조**, **5년 트렌드 시각화**가 추가됨.

---

### 3.8 기업 검색·다국어 힌트

- **내용:** 사이드바 "Company search"에서 **이름 검색** 후 티커 선택.
- **구현:**
  - `yq_search(query)`로 검색; EQUITY/ETF만 사용, INDEX/MUTUALFUND 제외.
  - placeholder/도움말: "e.g. Apple, **삼성**, Mitsubishi" — 다국어 검색 유도.
  - 선택 옵션: `[Exchange] Symbol - Name` 형식으로 표시.
- **의미:** PRD의 "전역 설정·검색"을 구체화하고, 비영어권 사용자를 위한 다국어 검색 경로를 명시한 확장.

---

### 3.9 비미국 시장 안내 (DART·EDINET·LSE)

- **내용:** Tab 1 Deep-Dive에서 **한국/일본/UK** 선택 시 별도 안내.
- **구현:**
  - 한국: "DART API integration for Korean MD&A is currently under construction. Please check back in Phase 2."
  - 일본/UK: "EDINET/LSE document parsing is currently under development."
  - 미국만 전체 정성 플로우(10-K 다운로드·Gemini) 실행.
- **의미:** PRD에는 없던 **다국가 로드맵**을 UI에 반영한 기능.

---

### 3.10 10-K 영구 캐시 및 캐시 안내

- **내용:** `data/{TICKER}_latest.json`에 Item 1A·3·7·8·9A 추출 결과 저장; 재실행 시 다운로드·파싱 생략.
- **구현:** `get_10k_sections()`에서 캐시 존재 시 로드만 수행. UI 캡션: "10-K sections are cached in **data/**; repeat runs use cache for instant AI analysis."
- **의미:** PRD/flows의 "캐싱"을 **영구 캐시**와 **사용자 안내**까지 명확히 한 구현.

---

### 3.11 Industry Comps 조건부 포맷팅

- **내용:** Tab 3 Comps 테이블에서 **열별 최소/최대**에 따라 셀 색상 적용.
- **구현:** Forward P/E, EV/EBITDA, P/B 각 열에 대해 최소값 녹색, 최대값 빨간색; 캡션으로 "Lowest = green (undervalued), highest = red" 설명.
- **의미:** PRD의 "동종사 멀티플 비교"에 **시각적 상대 밸류** 판단을 더한 확장.

---

## 4. 요약 표

| 구분 | PRD/기본 | 현재 구현 (추가·확장) |
|------|----------|------------------------|
| 시장 | US 중심 | US + 한국·일본·UK (티커 정규화·Phase 2 안내) |
| 리스크 | Item 1A | Item 1A + **Forensic (Item 3·9A)** |
| 출력 | 일괄 응답 | **실시간 스트리밍** |
| 설정 저장 | 없음 | **Remember me → .app_prefs.json** |
| 정량 소스 | yfinance | yfinance + **Item 8 LLM** (선택) |
| Financial Health | Sankey·Radar·F-Score | + Altman·Red Flags·YoY·**섹터별 지표**·수동 Radar·분기 테이블 |
| DCF | 슬라이더·3시나리오 | + **Smart Defaults**·**애널리스트 컨센서스**·**Damodaran**·**5년 트렌드** |
| 검색 | 전역 설정 | **다국어 힌트**·거래소 표시·EQUITY만 필터 |
| Comps | 테이블 | **최소/최대 조건부 색상** |
| 캐시 | 문서상 캐싱 | **영구 캐시** + UI 안내 |

---

## 5. 참고 문서 (AGENT.md)

| 문서 | 경로 | 역할 |
|------|------|------|
| PRD | `.agent/prd.md` | 프로젝트 비전, 3탭 요구사항 |
| Architecture | `.agent/architecture.mermaid` | 시스템 구조 다이어그램 |
| Data Flows | `.agent/flows.md` | 정성/정량 파이프라인 |
| Directory Map | `.agent/directory_map.md` | 파일 구조 |
| ADL | `.agent/adl.yaml` | 아키텍처 결정 (429, 10년 DCF, 폴백) |
| Infra | `.agent/infra.yaml` | 의존성·인프라 |
| Rules | `.agent/rules.md` | 개발 가드레일 |

---

*이 문서는 프로젝트 루트의 `docs/NEW_FEATURES_AND_PROJECT_ANALYSIS.md`로 저장되었으며, 다운로드 후 공유·보관용으로 사용할 수 있습니다.*
