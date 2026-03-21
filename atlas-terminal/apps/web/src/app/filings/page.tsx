"use client";
import { useState } from "react";
import { useTicker } from "../lib/use-ticker";

const SECTIONS = [
  { key: "item1a", label: "Item 1A: Risk Factors", short: "Risk Factors" },
  { key: "item7", label: "Item 7: MD&A", short: "MD&A" },
  { key: "item8", label: "Item 8: Financial Statements", short: "Financials" },
  { key: "item3", label: "Item 3: Legal Proceedings", short: "Legal" },
  { key: "item9a", label: "Item 9A: Controls & Procedures", short: "Controls" },
];

export default function FilingsPage() {
  const { ticker } = useTicker();
  const [activeSection, setActiveSection] = useState("item7");
  const [sections, setSections] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [email, setEmail] = useState("kimseonpil23@gmail.com");
  const [aiSummary, setAiSummary] = useState<string>("");
  const [aiLoading, setAiLoading] = useState(false);
  const [error, setError] = useState<string>("");

  async function loadFiling() {
    setLoading(true);
    setError("");
    setSections({});
    setAiSummary("");
    try {
      const res = await fetch(`/api/edgar/sections/${ticker}?email=${encodeURIComponent(email)}`);
      if (res.ok) {
        const data = await res.json();
        setSections({
          item1a: data.item1a || "",
          item3: data.item3 || "",
          item7: data.item7 || "",
          item8: data.item8 || "",
          item9a: data.item9a || "",
        });
        setLoaded(true);
      } else {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || "Failed to load SEC filing. Try a different ticker or check your connection.");
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
      const sectionLabel = SECTIONS.find((s) => s.key === activeSection)?.label || activeSection;
      const res = await fetch("/api/analysis/mda", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker,
          question: `Summarize and analyze this 10-K ${sectionLabel} section. Highlight key risks, trends, and important disclosures:\n\n${content.slice(0, 8000)}`,
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

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">
        <span className="text-accent-green">{ticker}</span> SEC Filings
      </h1>

      {/* Load Section */}
      {!loaded && (
        <div className="bg-bg-card border border-border rounded-lg p-5 mb-6">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">10-K Annual Report</h3>
          <p className="text-text-muted text-sm mb-4">
            Downloads the latest 10-K filing from SEC EDGAR, parses and extracts individual sections for analysis.
          </p>
          <div className="flex items-center gap-3">
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="SEC EDGAR email (required)"
              className="bg-bg-primary border border-border rounded-md px-3 py-2 text-text-primary outline-none text-sm w-72 focus:border-accent-green/50"
            />
            <button
              onClick={loadFiling}
              disabled={loading || !email}
              className="bg-accent-green text-bg-primary px-5 py-2 rounded-md text-sm font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {loading ? "Downloading & Parsing..." : "Load 10-K Filing"}
            </button>
          </div>
          {error && (
            <div className="mt-3 bg-accent-red/10 border border-accent-red/30 rounded-md px-4 py-2.5 text-accent-red text-sm">
              {error}
            </div>
          )}
          {loading && (
            <div className="mt-3 text-text-muted text-sm animate-pulse">
              Downloading from SEC EDGAR... This may take 10-30 seconds for first download.
            </div>
          )}
        </div>
      )}

      {/* Loaded Content */}
      {loaded && (
        <>
          {/* Section Tabs */}
          <div className="flex gap-1 mb-4 bg-bg-card border border-border rounded-lg p-1">
            {SECTIONS.map((s) => {
              const hasContent = !!sections[s.key];
              return (
                <button
                  key={s.key}
                  onClick={() => { setActiveSection(s.key); setAiSummary(""); }}
                  className={`flex-1 px-3 py-2 rounded-md text-xs font-mono transition-all ${
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

          {/* Section Header Bar */}
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-text-primary text-sm font-semibold">
                {SECTIONS.find((s) => s.key === activeSection)?.label}
              </h2>
              {currentContent && (
                <span className="text-text-muted text-xs font-mono">{wordCount.toLocaleString()} words</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {currentContent && (
                <button
                  onClick={runAiSummary}
                  disabled={aiLoading}
                  className="bg-accent-blue text-white px-4 py-1.5 rounded-md text-xs font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity"
                >
                  {aiLoading ? "Analyzing..." : "AI Summary"}
                </button>
              )}
              <button
                onClick={loadFiling}
                disabled={loading}
                className="bg-bg-card border border-border text-text-secondary px-3 py-1.5 rounded-md text-xs hover:text-text-primary transition-colors"
              >
                Reload
              </button>
            </div>
          </div>

          {/* AI Summary */}
          {aiSummary && (
            <div className="bg-bg-card border border-accent-green/30 rounded-lg p-5 mb-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-accent-green text-sm">🤖</span>
                <h3 className="text-accent-green text-sm font-semibold">AI Analysis</h3>
              </div>
              <div className="text-text-primary text-sm leading-relaxed whitespace-pre-wrap">{aiSummary}</div>
            </div>
          )}

          {/* Filing Content - Inline Display */}
          {currentContent ? (
            <div className="bg-bg-card border border-border rounded-lg overflow-hidden">
              <div
                className="p-6 overflow-y-auto text-text-primary text-sm leading-[1.8] font-sans"
                style={{ maxHeight: "calc(100vh - 340px)" }}
              >
                {currentContent.split("\n").map((line, i) => {
                  const trimmed = line.trim();
                  if (!trimmed) return <div key={i} className="h-3" />;

                  // Detect headers (all-caps lines or lines starting with "Item")
                  const isHeader = /^(Item\s+\d|ITEM\s+\d)/i.test(trimmed) ||
                    (trimmed.length < 80 && trimmed === trimmed.toUpperCase() && /[A-Z]/.test(trimmed));
                  const isBullet = /^[•\-\*●]\s/.test(trimmed) || /^\d+\.\s/.test(trimmed);

                  if (isHeader) {
                    return (
                      <h3 key={i} className="text-accent-green font-semibold text-base mt-5 mb-2 border-b border-border/30 pb-1">
                        {trimmed}
                      </h3>
                    );
                  }
                  if (isBullet) {
                    return (
                      <div key={i} className="pl-4 py-0.5 text-text-secondary">
                        {trimmed}
                      </div>
                    );
                  }
                  return (
                    <p key={i} className="mb-1.5 text-text-primary/90">
                      {trimmed}
                    </p>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="bg-bg-card border border-border rounded-lg p-8 text-center text-text-muted">
              No content available for this section.
            </div>
          )}
        </>
      )}
    </div>
  );
}
