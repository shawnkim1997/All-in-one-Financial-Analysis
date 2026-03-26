"use client";

import { useEffect, useState } from "react";
import type { AnomalyExplainResult, FinancialAnomalyItem } from "./types";

type FilingFocus = "10k_mda" | "risk";

export function AnomalyChips({
  ticker,
  anomalies,
}: {
  ticker: string;
  anomalies: FinancialAnomalyItem[];
}) {
  const [focus, setFocus] = useState<FilingFocus>("10k_mda");
  const [secEmail, setSecEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [explain, setExplain] = useState<AnomalyExplainResult | null>(null);

  useEffect(() => {
    const v = localStorage.getItem("atlas_sec_email") || "";
    if (v) setSecEmail(v);
  }, []);

  async function onChipClick(a: FinancialAnomalyItem) {
    const apiKey = typeof window !== "undefined" ? localStorage.getItem("atlas_gemini_key") || "" : "";
    if (!apiKey) {
      setError("Settings에서 Gemini API 키를 저장한 뒤 다시 시도하세요.");
      setExplain(null);
      return;
    }
    const email = secEmail.trim() || (typeof window !== "undefined" ? localStorage.getItem("atlas_sec_email") || "" : "");
    if (!email.trim()) {
      setError("SEC 공정 이용 이메일을 입력하거나 localStorage `atlas_sec_email`을 설정하세요.");
      setExplain(null);
      return;
    }

    setLoading(true);
    setError(null);
    setExplain(null);
    try {
      const res = await fetch("/api/analysis/anomaly-explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker,
          api_key: apiKey,
          sec_email: email.trim(),
          account_key: a.account_key,
          display_name: a.display_name,
          direction: a.direction,
          magnitude_pct: Math.abs(a.change_pct ?? 0),
          filing_focus: focus,
        }),
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        const d = (payload as { detail?: unknown }).detail;
        const msg =
          typeof d === "string"
            ? d
            : Array.isArray(d)
              ? d.map((x: { msg?: string }) => x.msg).filter(Boolean).join("; ")
              : "";
        setError(msg || `API ${res.status}`);
        return;
      }
      const data = payload as {
        summary?: string;
        likely_causes?: unknown;
        citations?: unknown;
        confidence?: string;
      };
      setExplain({
        summary: data.summary || "",
        likely_causes: Array.isArray(data.likely_causes) ? (data.likely_causes as string[]) : [],
        citations: Array.isArray(data.citations)
          ? (data.citations as { excerpt: string; context: string }[])
          : [],
        confidence: data.confidence || "medium",
      });
    } catch {
      setError("네트워크 오류");
    } finally {
      setLoading(false);
    }
  }

  function persistEmail() {
    if (typeof window === "undefined") return;
    const t = secEmail.trim();
    if (t) localStorage.setItem("atlas_sec_email", t);
    else localStorage.removeItem("atlas_sec_email");
  }

  if (!anomalies.length) {
    return (
      <div className="text-text-muted text-sm">
        YoY 변동이 임계값(30%)을 넘는 계정이 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-text-muted text-xs">Filing</span>
        <button
          type="button"
          onClick={() => setFocus("10k_mda")}
          className={`text-xs px-2 py-1 rounded border ${focus === "10k_mda" ? "border-accent-green text-accent-green" : "border-border text-text-muted"}`}
        >
          Item 7 (MD&A)
        </button>
        <button
          type="button"
          onClick={() => setFocus("risk")}
          className={`text-xs px-2 py-1 rounded border ${focus === "risk" ? "border-accent-green text-accent-green" : "border-border text-text-muted"}`}
        >
          Risk (1A / 9A)
        </button>
      </div>
      <div className="flex flex-wrap gap-2 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="text-text-muted text-[10px] block mb-1">SEC fair-access email</label>
          <input
            type="email"
            value={secEmail}
            onChange={(e) => setSecEmail(e.target.value)}
            onBlur={persistEmail}
            placeholder="name@company.com"
            className="w-full bg-bg-primary border border-border rounded-md px-2 py-1.5 text-sm text-text-primary outline-none focus:border-accent-green"
          />
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {anomalies.map((a) => {
          const up = (a.direction || "").toLowerCase() === "up";
          const pct = a.change_pct ?? 0;
          return (
            <button
              key={`${a.account_key}-${a.display_name}`}
              type="button"
              disabled={loading}
              onClick={() => onChipClick(a)}
              className={`text-xs font-mono px-3 py-1.5 rounded-full border transition-opacity ${
                up ? "border-accent-green/60 text-accent-green" : "border-accent-red/60 text-accent-red"
              } hover:opacity-90 disabled:opacity-40 bg-bg-primary/60`}
            >
              {a.display_name} {up ? "▲" : "▼"} {Math.abs(pct).toFixed(1)}%
            </button>
          );
        })}
      </div>
      {loading && <div className="text-accent-green text-sm animate-pulse font-mono">Explaining…</div>}
      {error && <div className="text-accent-red text-sm">{error}</div>}
      {explain && (
        <div className="rounded-lg border border-border bg-bg-primary/40 p-4 space-y-3">
          <div className="flex justify-between items-center gap-2">
            <span className="text-text-muted text-xs">Confidence</span>
            <span className="text-xs font-mono text-accent-green">{explain.confidence}</span>
          </div>
          <p className="text-text-primary text-sm leading-relaxed">{explain.summary}</p>
          {explain.likely_causes.length > 0 && (
            <ul className="list-disc list-inside text-sm text-text-secondary space-y-1">
              {explain.likely_causes.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          )}
          {explain.citations.length > 0 && (
            <div className="space-y-2 border-t border-border pt-3">
              <div className="text-text-muted text-xs">Citations</div>
              {explain.citations.map((c, i) => (
                <blockquote key={i} className="text-xs text-text-secondary border-l-2 border-accent-green/40 pl-2">
                  <span className="text-text-muted">{c.context}</span>
                  <p className="mt-1 italic">{c.excerpt}</p>
                </blockquote>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
