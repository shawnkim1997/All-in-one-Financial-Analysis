"use client";
import { useEffect, useState } from "react";
import { useTicker } from "../lib/use-ticker";

interface PiotroskiData {
  score?: number;
  details?: Record<string, { pass: boolean; value: number }>;
}

interface RadarData {
  roe?: number;
  roa?: number;
  gross_margin?: number;
  current_ratio?: number;
  revenue_growth?: number;
}

export default function ResearchPage() {
  const { ticker } = useTicker();
  const [piotroski, setPiotroski] = useState<PiotroskiData | null>(null);
  const [radar, setRadar] = useState<RadarData | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<string>("");
  const [aiLoading, setAiLoading] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch(`/api/market/piotroski/${ticker}`).then((r) => r.ok ? r.json() : null),
      fetch(`/api/market/radar/${ticker}`).then((r) => r.ok ? r.json() : null),
    ]).then(([p, r]) => {
      setPiotroski(p);
      setRadar(r);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [ticker]);

  async function runAiAnalysis() {
    const apiKey = localStorage.getItem("atlas_gemini_key") || "";
    if (!apiKey) {
      setAiAnalysis("Please set your Gemini API key in Settings first.");
      return;
    }
    setAiLoading(true);
    try {
      const res = await fetch("/api/analysis/strategy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, question: `Comprehensive research analysis of ${ticker}: competitive position, growth catalysts, and risks`, api_key: apiKey }),
      });
      if (res.ok) {
        const data = await res.json();
        setAiAnalysis(typeof data === "string" ? data : data.analysis || JSON.stringify(data));
      } else {
        setAiAnalysis("API error. Check your Gemini key in Settings.");
      }
    } catch {
      setAiAnalysis("Connection error.");
    }
    setAiLoading(false);
  }

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-accent-green animate-pulse font-mono">Loading...</div></div>;

  const fScore = piotroski?.score ?? 0;
  const fColor = fScore >= 7 ? "text-accent-green" : fScore >= 4 ? "text-accent-yellow" : "text-accent-red";

  const radarMetrics = radar ? [
    { label: "ROE", value: radar.roe, max: 30 },
    { label: "ROA", value: radar.roa, max: 20 },
    { label: "Gross Margin", value: radar.gross_margin, max: 100 },
    { label: "Current Ratio", value: radar.current_ratio, max: 3 },
    { label: "Revenue Growth", value: radar.revenue_growth, max: 50 },
  ] : [];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">
        <span className="text-accent-green">{ticker}</span> Research
      </h1>

      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Piotroski F-Score */}
        <div className="bg-bg-card border border-border rounded-lg p-5">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">Piotroski F-Score</h3>
          <div className={`text-5xl font-mono font-bold ${fColor}`}>{fScore}/9</div>
          <div className="text-text-muted text-xs mt-2">
            {fScore >= 7 ? "Strong" : fScore >= 4 ? "Moderate" : "Weak"} financial strength
          </div>
          {piotroski?.details && (
            <div className="mt-4 space-y-1.5">
              {Object.entries(piotroski.details).map(([key, val]) => (
                <div key={key} className="flex justify-between text-sm">
                  <span className="text-text-muted">{key}</span>
                  <span className={val.pass ? "text-accent-green" : "text-accent-red"}>
                    {val.pass ? "✓" : "✗"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Financial Radar */}
        <div className="bg-bg-card border border-border rounded-lg p-5">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">Financial Radar</h3>
          {radarMetrics.length > 0 ? (
            <div className="space-y-3">
              {radarMetrics.map((m) => {
                const pct = m.value != null ? Math.min((m.value / m.max) * 100, 100) : 0;
                const color = pct > 66 ? "bg-accent-green" : pct > 33 ? "bg-accent-yellow" : "bg-accent-red";
                return (
                  <div key={m.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-text-muted">{m.label}</span>
                      <span className="text-text-primary font-mono">{m.value?.toFixed(1) ?? "—"}%</span>
                    </div>
                    <div className="h-2 bg-bg-primary rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-text-muted">No data available</div>
          )}
        </div>
      </div>

      {/* AI Analysis */}
      <div className="bg-bg-card border border-border rounded-lg p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-text-secondary text-sm font-semibold">AI Research Analysis</h3>
          <button
            onClick={runAiAnalysis}
            disabled={aiLoading}
            className="bg-accent-green text-bg-primary px-4 py-1.5 rounded-md text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {aiLoading ? "Analyzing..." : "Run Analysis"}
          </button>
        </div>
        {aiAnalysis ? (
          <pre className="text-text-primary text-sm whitespace-pre-wrap leading-relaxed font-sans">{aiAnalysis}</pre>
        ) : (
          <div className="text-text-muted text-sm">Click &quot;Run Analysis&quot; to generate AI-powered research report.</div>
        )}
      </div>
    </div>
  );
}
