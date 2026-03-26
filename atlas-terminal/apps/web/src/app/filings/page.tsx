"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  FilingsViewer,
  type FilingsViewerHandle,
  type FilingSectionTab,
} from "../components/filings/FilingsViewer";
import { inferFilingJurisdiction, type FilingJurisdiction } from "../lib/filing-jurisdiction";
import { useTicker } from "../lib/use-ticker";

const SECTIONS_SEC: FilingSectionTab[] = [
  { key: "item1a", label: "Item 1A: Risk Factors", short: "Risk Factors", anchorId: "sec-item-1a" },
  { key: "item3", label: "Item 3: Legal Proceedings", short: "Legal", anchorId: "sec-item-3" },
  { key: "item7", label: "Item 7: MD&A", short: "MD&A", anchorId: "sec-item-7" },
  { key: "item8", label: "Item 8: Financial Statements", short: "Financials", anchorId: "sec-item-8" },
  { key: "item9a", label: "Item 9A: Controls & Procedures", short: "Controls", anchorId: "sec-item-9a" },
];

const SECTIONS_DART: FilingSectionTab[] = [
  { key: "item1a", label: "투자위험 (II)", short: "투자위험", anchorId: "dart-item-1a" },
  { key: "item3", label: "소송 등", short: "소송", anchorId: "dart-item-3" },
  { key: "item7", label: "사업의 내용 / MD&A", short: "사업·MD&A", anchorId: "dart-item-7" },
  { key: "item8", label: "재무에 관한 사항", short: "재무", anchorId: "dart-item-8" },
  { key: "item9a", label: "내부통제", short: "내부통제", anchorId: "dart-item-9a" },
];

const SECTIONS_EDINET: FilingSectionTab[] = [
  { key: "item1a", label: "リスク情報", short: "リスク", anchorId: "edinet-item-1a" },
  { key: "item3", label: "訴訟 (該当時)", short: "訴訟", anchorId: "edinet-item-3" },
  { key: "item7", label: "事業の状況 / MD&A", short: "MD&A", anchorId: "edinet-item-7" },
  { key: "item8", label: "財務諸表", short: "財務", anchorId: "edinet-item-8" },
  { key: "item9a", label: "内部統制", short: "内部統制", anchorId: "edinet-item-9a" },
];

function sectionsForJurisdiction(j: FilingJurisdiction): FilingSectionTab[] {
  if (j === "DART") return SECTIONS_DART;
  if (j === "EDINET") return SECTIONS_EDINET;
  return SECTIONS_SEC;
}

function mapApiSource(s: string | undefined): FilingJurisdiction {
  if (s === "dart") return "DART";
  if (s === "edinet") return "EDINET";
  return "SEC";
}

export default function FilingsPage() {
  const { ticker } = useTicker();
  const viewerRef = useRef<FilingsViewerHandle | null>(null);
  const [activeSection, setActiveSection] = useState("item7");
  const [sections, setSections] = useState<Record<string, string>>({});
  const [htmlDoc, setHtmlDoc] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [email, setEmail] = useState("");
  const [aiSummary, setAiSummary] = useState<string>("");
  const [aiLoading, setAiLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const [htmlVersion, setHtmlVersion] = useState(0);
  const [filingSource, setFilingSource] = useState<FilingJurisdiction | null>(null);
  const [linkMap, setLinkMap] = useState<Record<string, string> | null>(null);
  const [infoMessage, setInfoMessage] = useState<string>("");

  const previewJ = inferFilingJurisdiction(ticker);
  const activeJurisdiction = filingSource ?? previewJ;
  const sectionTabs = useMemo(() => sectionsForJurisdiction(activeJurisdiction), [activeJurisdiction]);

  async function loadFiling() {
    setLoading(true);
    setError("");
    setSections({});
    setHtmlDoc("");
    setAiSummary("");
    setLinkMap(null);
    setInfoMessage("");
    const j = inferFilingJurisdiction(ticker);

    try {
      if (j === "SEC") {
        const qs = new URLSearchParams({
          email,
          include_html: "true",
        });
        const res = await fetch(`/api/edgar/sections/${encodeURIComponent(ticker)}?${qs.toString()}`);
        if (res.ok) {
          const data = await res.json();
          setFilingSource(mapApiSource(data.source));
          setSections({
            item1a: data.item1a || "",
            item3: data.item3 || "",
            item7: data.item7 || "",
            item8: data.item8 || "",
            item9a: data.item9a || "",
          });
          setHtmlDoc(typeof data.html === "string" ? data.html : "");
          setActiveSection("item7");
          setHtmlVersion((v) => v + 1);
          setLoaded(true);
        } else {
          const err = await res.json().catch(() => ({}));
          setError(err.detail || "Failed to load SEC filing. Try a different ticker or check your connection.");
        }
        setLoading(false);
        return;
      }

      if (j === "DART") {
        const res = await fetch(
          `/api/dart/sections/${encodeURIComponent(ticker)}?include_html=true`,
        );
        if (res.ok) {
          const data = await res.json();
          setFilingSource(mapApiSource(data.source));
          if (data.configured === false) {
            setInfoMessage(data.message || "DART_API_KEY가 설정되지 않았습니다.");
            setLoaded(false);
          } else {
            setSections({
              item1a: data.item1a || "",
              item3: data.item3 || "",
              item7: data.item7 || "",
              item8: data.item8 || "",
              item9a: data.item9a || "",
            });
            setHtmlDoc(typeof data.html === "string" ? data.html : "");
            setActiveSection("item7");
            setHtmlVersion((v) => v + 1);
            setLoaded(true);
          }
        } else {
          const err = await res.json().catch(() => ({}));
          setError(err.detail || "DART 공시를 불러오지 못했습니다.");
        }
        setLoading(false);
        return;
      }

      // EDINET
      const res = await fetch(
        `/api/edinet/sections/${encodeURIComponent(ticker)}?include_html=true`,
      );
      if (res.ok) {
        const data = await res.json();
        setFilingSource(mapApiSource(data.source));
        setSections({
          item1a: data.item1a || "",
          item3: data.item3 || "",
          item7: data.item7 || "",
          item8: data.item8 || "",
          item9a: data.item9a || "",
        });
        setHtmlDoc(typeof data.html === "string" ? data.html : "");
        if (data.links && typeof data.links === "object") {
          setLinkMap(data.links as Record<string, string>);
        }
        if (data.message) setInfoMessage(data.message);
        setActiveSection("item7");
        setHtmlVersion((v) => v + 1);
        setLoaded(true);
      } else {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || "EDINET 데이터를 불러오지 못했습니다.");
      }
    } catch {
      setError("Connection error. Make sure the backend server is running.");
    }
    setLoading(false);
  }

  async function runAiSummary() {
    const content = sections[activeSection];
    if (!content) return;
    const apiKey = localStorage.getItem("atlas_gemini_key") || "";
    if (!apiKey) {
      setAiSummary("Please set your Gemini API key in Settings first.");
      return;
    }
    setAiLoading(true);
    try {
      const sectionLabel = sectionTabs.find((s) => s.key === activeSection)?.label || activeSection;
      const res = await fetch("/api/analysis/mda", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker,
          question: `Summarize and analyze this filing section (${sectionLabel}). Highlight key risks, trends, and important disclosures:\n\n${content.slice(0, 8000)}`,
          api_key: apiKey,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setAiSummary(typeof data === "string" ? data : data.analysis || JSON.stringify(data));
      }
    } catch {
      setAiSummary("Error generating summary.");
    }
    setAiLoading(false);
  }

  const currentContent = sections[activeSection] || "";
  const wordCount = currentContent ? currentContent.split(/\s+/).length : 0;
  const hasHtml = htmlDoc.length > 0;

  const item7Anchor = sectionTabs.find((s) => s.key === "item7")?.anchorId ?? "sec-item-7";

  useEffect(() => {
    if (!hasHtml || htmlVersion === 0) return;
    const t = window.setTimeout(() => viewerRef.current?.scrollToAnchor(item7Anchor), 250);
    return () => window.clearTimeout(t);
  }, [hasHtml, htmlVersion, ticker, item7Anchor]);

  const intro = useMemo(() => {
    if (previewJ === "DART") {
      return {
        title: "DART 사업보고서",
        body: "한국 상장사 최신 사업보고서(연간)를 Open DART에서 받아 옵니다. 티커는 005930.KS 형식이어야 합니다. DART_API_KEY가 .env에 필요합니다.",
      };
    }
    if (previewJ === "EDINET") {
      return {
        title: "EDINET 有価証券報告書",
        body: "東京 (.T) 銘柄の有価証券報告書。APIキー (EDINET_SUBSCRIPTION_KEY) がある場合はZIPから本文を取得します。ない場合は公式リンクのみ表示します。",
      };
    }
    return {
      title: "10-K Annual Report (SEC)",
      body: "Downloads the latest 10-K from SEC EDGAR. The filing is shown with original HTML tables and emphasis, restyled for the terminal dark theme. Section tabs scroll to Item 1A, MD&A, and more.",
    };
  }, [previewJ]);

  const pageTitle =
    previewJ === "DART"
      ? "DART 공시"
      : previewJ === "EDINET"
        ? "EDINET Filings"
        : "SEC Filings";

  const needsEmail = previewJ === "SEC";

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">
        <span className="text-accent-green">{ticker}</span> {pageTitle}
      </h1>

      {!loaded && (
        <div className="bg-bg-card border border-border rounded-lg p-5 mb-6">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">{intro.title}</h3>
          <p className="text-text-muted text-sm mb-4">{intro.body}</p>
          <div className="flex items-center gap-3 flex-wrap">
            {needsEmail && (
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="SEC EDGAR email (required)"
                className="bg-bg-primary border border-border rounded-md px-3 py-2 text-text-primary outline-none text-sm w-72 focus:border-accent-green/50"
              />
            )}
            <button
              onClick={loadFiling}
              disabled={loading || (needsEmail && !email)}
              className="bg-accent-green text-bg-primary px-5 py-2 rounded-md text-sm font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {loading
                ? "Loading..."
                : previewJ === "SEC"
                  ? "Load 10-K Filing"
                  : previewJ === "DART"
                    ? "사업보고서 불러오기"
                    : "Load EDINET filing"}
            </button>
          </div>
          {infoMessage && (
            <div className="mt-3 bg-accent-yellow/10 border border-accent-yellow/30 rounded-md px-4 py-2.5 text-accent-yellow text-sm">
              {infoMessage}
            </div>
          )}
          {error && (
            <div className="mt-3 bg-accent-red/10 border border-accent-red/30 rounded-md px-4 py-2.5 text-accent-red text-sm">
              {error}
            </div>
          )}
          {loading && (
            <div className="mt-3 text-text-muted text-sm animate-pulse">
              {previewJ === "SEC"
                ? "Downloading from SEC EDGAR... This may take 10-30 seconds for first download."
                : "공시 원본을 가져오는 중입니다..."}
            </div>
          )}
        </div>
      )}

      {loaded && (
        <>
          {linkMap && Object.keys(linkMap).length > 0 && (
            <div className="bg-bg-card border border-border rounded-lg p-4 mb-4 text-sm text-text-secondary">
              {infoMessage && <p className="mb-2 text-text-muted">{infoMessage}</p>}
              <ul className="list-disc list-inside space-y-1">
                {Object.entries(linkMap).map(([k, v]) => (
                  <li key={k}>
                    <a
                      href={v}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent-blue hover:underline"
                    >
                      {k}: {v}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex gap-1 mb-3 bg-bg-card border border-border rounded-lg p-1 flex-wrap">
            {sectionTabs.map((s) => {
              const hasContent = !!sections[s.key];
              return (
                <button
                  key={s.key}
                  type="button"
                  onClick={() => {
                    setActiveSection(s.key);
                    setAiSummary("");
                    if (hasHtml) {
                      viewerRef.current?.scrollToAnchor(s.anchorId);
                    }
                  }}
                  className={`flex-1 min-w-[88px] px-3 py-2 rounded-md text-xs font-mono transition-all ${
                    activeSection === s.key
                      ? "bg-accent-green text-bg-primary font-semibold"
                      : hasContent
                        ? "text-text-secondary hover:text-text-primary"
                        : "text-text-muted/50"
                  }`}
                >
                  {s.short}
                </button>
              );
            })}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2">
              <h2 className="text-text-primary text-sm font-semibold">
                {sectionTabs.find((s) => s.key === activeSection)?.label}
              </h2>
              {currentContent && (
                <span className="text-text-muted text-xs font-mono">{wordCount.toLocaleString()} words (plain cache)</span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {currentContent && (
                <button
                  type="button"
                  onClick={runAiSummary}
                  disabled={aiLoading}
                  className="bg-accent-blue text-white px-4 py-1.5 rounded-md text-xs font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity"
                >
                  {aiLoading ? "Analyzing..." : "AI Summary"}
                </button>
              )}
              <button
                type="button"
                onClick={loadFiling}
                disabled={loading}
                className="bg-bg-card border border-border text-text-secondary px-3 py-1.5 rounded-md text-xs hover:text-text-primary transition-colors"
              >
                Reload
              </button>
            </div>
          </div>

          {!hasHtml && previewJ === "SEC" && (
            <p className="text-text-muted text-sm mb-3">
              <strong className="text-text-secondary">서식 HTML 스냅샷</strong>이 아직 없습니다(예: 예전에 텍스트만 캐시된 경우).
              아래에 SEC에서 추출한 <strong className="text-text-secondary">평문</strong>이 그대로 표시됩니다.
              표·강조가 있는 원문 형태를 보려면 <strong className="text-text-secondary">Reload</strong>로 다시 받아
              HTML을 만드세요. (야후 iframe 차단과는 무관합니다.)
            </p>
          )}
          {!hasHtml && previewJ !== "SEC" && currentContent && (
            <p className="text-text-muted text-sm mb-3">
              HTML 조각이 없을 때는 아래 <strong className="text-text-secondary">평문</strong>으로 동일 내용을 표시합니다.
            </p>
          )}

          {aiSummary && (
            <div className="bg-bg-card border border-accent-green/30 rounded-lg p-5 mb-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-accent-green text-sm">AI</span>
                <h3 className="text-accent-green text-sm font-semibold">Analysis</h3>
              </div>
              <div className="text-text-primary text-sm leading-relaxed whitespace-pre-wrap">{aiSummary}</div>
            </div>
          )}

          {hasHtml && (
            <FilingsViewer
              ref={viewerRef}
              html={htmlDoc}
              sections={sectionTabs}
              activeSection={activeSection}
              onActiveSectionChange={setActiveSection}
            />
          )}

          {!hasHtml && currentContent && (
            <div className="border border-border rounded-lg bg-bg-card overflow-hidden flex flex-col max-h-[min(72vh,calc(100vh-200px))]">
              <div className="px-4 py-2 border-b border-border bg-bg-primary/50 text-xs text-text-muted shrink-0">
                Plain text (cached) — same source as AI Summary; formatted HTML viewer is optional.
              </div>
              <div
                className="overflow-y-auto flex-1 min-h-0 p-4 md:p-6 pb-10 text-sm text-text-primary leading-relaxed whitespace-pre-wrap break-words font-mono"
                style={{ WebkitOverflowScrolling: "touch" }}
              >
                {currentContent}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
