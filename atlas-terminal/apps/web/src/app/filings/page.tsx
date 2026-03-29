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
  { key: "item1a", label: "Investment Risk (II)", short: "Risk", anchorId: "dart-item-1a" },
  { key: "item3", label: "Litigation", short: "Legal", anchorId: "dart-item-3" },
  { key: "item7", label: "Business / MD&A", short: "MD&A", anchorId: "dart-item-7" },
  { key: "item8", label: "Financial Statements", short: "Financials", anchorId: "dart-item-8" },
  { key: "item9a", label: "Internal Controls", short: "Controls", anchorId: "dart-item-9a" },
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
  const { ticker, initialized } = useTicker();
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
  const [translatedText, setTranslatedText] = useState<string>("");
  const [translating, setTranslating] = useState(false);
  const [showTranslation, setShowTranslation] = useState(false);

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
          if (data.links && typeof data.links === "object") {
            setLinkMap(data.links as Record<string, string>);
          }
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
            setInfoMessage(data.message || "DART_API_KEY is not configured.");
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
            if (data.links && typeof data.links === "object") {
              setLinkMap(data.links as Record<string, string>);
            }
            setActiveSection("item7");
            setHtmlVersion((v) => v + 1);
            setLoaded(true);
          }
        } else {
          const err = await res.json().catch(() => ({}));
          setError(err.detail || "Failed to load DART filing.");
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
        setError(err.detail || "Failed to load EDINET data.");
      }
    } catch {
      setError("Connection error. Make sure the backend server is running.");
    }
    setLoading(false);
  }

  async function runTranslation() {
    const content = sections[activeSection];
    if (!content) return;
    const apiKey = localStorage.getItem("atlas_gemini_key") || "";
    if (!apiKey) {
      setTranslatedText("Settings에서 Gemini API 키를 먼저 설정해주세요.");
      setShowTranslation(true);
      return;
    }
    setTranslating(true);
    try {
      const res = await fetch("/api/analysis/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: content.slice(0, 12000),
          target_lang: "ko",
          api_key: apiKey,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setTranslatedText(data.translated_text || "");
        setShowTranslation(true);
      } else {
        setTranslatedText("번역에 실패했습니다.");
        setShowTranslation(true);
      }
    } catch {
      setTranslatedText("번역 중 오류가 발생했습니다.");
      setShowTranslation(true);
    }
    setTranslating(false);
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
        title: "DART Annual Report",
        body: "Fetches the latest annual business report for Korean listed companies from Open DART. Ticker must be in 005930.KS format. Requires DART_API_KEY in .env.",
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
      ? "DART Filings"
      : previewJ === "EDINET"
        ? "EDINET Filings"
        : "SEC Filings";

  const needsEmail = previewJ === "SEC";

  // Auto-load filing for non-SEC jurisdictions (no email required)
  useEffect(() => {
    if (!initialized) return;
    if (!loaded && !loading && previewJ !== "SEC") {
      loadFiling();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker, initialized]);

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
                    ? "Load DART Report"
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
                : "Fetching filing data..."}
            </div>
          )}
        </div>
      )}

      {loaded && (
        <>
          {linkMap && Object.keys(linkMap).length > 0 && (
            <div className="flex flex-wrap items-center gap-2 mb-4">
              {infoMessage && <p className="w-full text-text-muted text-sm mb-1">{infoMessage}</p>}
              {Object.entries(linkMap).map(([k, v], i) => (
                <a
                  key={k}
                  href={v}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-semibold transition-opacity hover:opacity-90 ${
                    i === 0
                      ? "bg-accent-blue text-white"
                      : "bg-bg-card border border-border text-text-secondary hover:text-text-primary"
                  }`}
                >
                  {k}
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              ))}
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
                    setShowTranslation(false);
                    setTranslatedText("");
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
                <>
                  <button
                    type="button"
                    onClick={runAiSummary}
                    disabled={aiLoading}
                    className="bg-accent-blue text-white px-4 py-1.5 rounded-md text-xs font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity"
                  >
                    {aiLoading ? "Analyzing..." : "AI Summary"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (showTranslation) {
                        setShowTranslation(false);
                      } else if (translatedText) {
                        setShowTranslation(true);
                      } else {
                        runTranslation();
                      }
                    }}
                    disabled={translating}
                    className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-opacity ${
                      showTranslation
                        ? "bg-accent-green text-bg-primary hover:opacity-90"
                        : "bg-bg-card border border-accent-green/50 text-accent-green hover:opacity-90"
                    } disabled:opacity-50`}
                  >
                    {translating ? "번역 중..." : showTranslation ? "English" : "한국어"}
                  </button>
                </>
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
              <strong className="text-text-secondary">HTML snapshot</strong> is not available (e.g. only plain text was cached previously).
              The <strong className="text-text-secondary">plain text</strong> extracted from SEC is shown below.
              To view the formatted version with tables and emphasis, click <strong className="text-text-secondary">Reload</strong> to re-fetch
              and generate the HTML. (This is unrelated to Yahoo iframe blocking.)
            </p>
          )}
          {!hasHtml && previewJ !== "SEC" && currentContent && (
            <p className="text-text-muted text-sm mb-3">
              When HTML fragments are unavailable, the same content is displayed as <strong className="text-text-secondary">plain text</strong> below.
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

          {showTranslation && translatedText && (
            <div className="border border-accent-green/30 rounded-lg bg-bg-card overflow-hidden flex flex-col max-h-[min(72vh,calc(100vh-200px))] mb-4">
              <div className="px-4 py-2 border-b border-accent-green/30 bg-accent-green/5 text-xs text-accent-green shrink-0 flex items-center gap-2">
                <span className="font-semibold">한국어 번역</span>
                <span className="text-text-muted">— Gemini AI 번역</span>
              </div>
              <div
                className="overflow-y-auto flex-1 min-h-0 p-4 md:p-6 pb-10 text-sm text-text-primary leading-relaxed whitespace-pre-wrap break-words"
                style={{ WebkitOverflowScrolling: "touch" }}
              >
                {translatedText}
              </div>
            </div>
          )}

          {!showTranslation && hasHtml && (
            <FilingsViewer
              ref={viewerRef}
              html={htmlDoc}
              sections={sectionTabs}
              activeSection={activeSection}
              onActiveSectionChange={setActiveSection}
            />
          )}

          {!showTranslation && !hasHtml && currentContent && (
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
