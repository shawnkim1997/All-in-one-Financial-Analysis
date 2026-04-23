"use client";

import { useState } from "react";
import { ShieldAlert, X } from "lucide-react";
import { Badge } from "../ui/Badge";
import { ErrorBanner } from "../ui/ErrorBanner";
import { flags } from "../../lib/flags";

interface Critique {
  argument: string;
  evidence_needed: string;
  severity: "high" | "medium" | "low";
}

interface RedTeamResponse {
  ticker: string;
  source: string;
  critiques: Critique[];
  overlooked_risks: string[];
  consensus_check: string;
  strongest_pushback: string;
}

function severityVariant(severity: Critique["severity"]): "buy" | "sell" | "hold" | "neutral" {
  if (severity === "high") return "sell";
  if (severity === "medium") return "hold";
  return "neutral";
}

function toMarkdown(result: RedTeamResponse): string {
  const critiques = result.critiques
    .map((item, idx) => `${idx + 1}. **${item.severity.toUpperCase()}** ${item.argument}\n   Evidence: ${item.evidence_needed}`)
    .join("\n");
  return `# ${result.ticker} Red-Team Critique

## Strongest Pushback
${result.strongest_pushback}

## Critiques
${critiques}

## Overlooked Risks
${result.overlooked_risks.map((risk) => `- ${risk}`).join("\n")}

## Consensus Check
${result.consensus_check}
`;
}

export function RedTeamCritique({ ticker }: { ticker: string }) {
  const [open, setOpen] = useState(false);
  const [thesis, setThesis] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RedTeamResponse | null>(null);
  const [copied, setCopied] = useState(false);

  if (!flags.redteam) return null;

  async function submit() {
    const trimmed = thesis.trim();
    if (trimmed.length < 10) {
      setError("Write at least one clear sentence for the thesis.");
      return;
    }
    setLoading(true);
    setError(null);
    setCopied(false);
    try {
      const apiKey = localStorage.getItem("atlas_gemini_key") || "";
      const response = await fetch("/api/copilot/red-team", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, thesis: trimmed, api_key: apiKey }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`);
      setResult(payload as RedTeamResponse);
    } catch (err) {
      setError((err as Error).message || "Red-team critique failed.");
    } finally {
      setLoading(false);
    }
  }

  async function copyMarkdown() {
    if (!result) return;
    await navigator.clipboard.writeText(toMarkdown(result));
    setCopied(true);
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-md border border-fin-negative/30 bg-fin-negative/10 px-4 py-2 text-sm font-semibold text-fin-negative hover:bg-fin-negative/15"
      >
        <ShieldAlert className="h-4 w-4" />
        Test Your Thesis
      </button>

      {open && (
        <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-brand-navy/45 p-4" onClick={() => setOpen(false)}>
          <div
            className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-xl border border-border bg-surface-raised shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-label="Red-team critique"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
              <div>
                <h2 className="font-serif text-xl font-bold text-brand-navy">{ticker} Red-Team Critique</h2>
                <p className="mt-1 text-sm text-text-secondary">A skeptical short-seller pass on your investment thesis.</p>
              </div>
              <button type="button" onClick={() => setOpen(false)} className="rounded p-1 text-text-muted hover:bg-surface-sunken hover:text-brand-navy" aria-label="Close">
                <X className="h-5 w-5" />
              </button>
            </header>

            <div className="space-y-4 p-5">
              <textarea
                value={thesis}
                onChange={(event) => setThesis(event.target.value)}
                placeholder={`Example: ${ticker} is undervalued because revenue growth can reaccelerate while margins expand.`}
                className="min-h-32 w-full rounded-md border border-border bg-surface-overlay px-4 py-3 text-sm text-text-primary outline-none focus:border-brand-blue"
              />
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-xs text-text-muted">Uses your Gemini key if present; otherwise returns a rules-based critique.</p>
                <button
                  type="button"
                  onClick={submit}
                  disabled={loading}
                  className="rounded-md bg-brand-navy px-5 py-2 text-sm font-semibold text-white hover:bg-brand-blue disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? "Testing..." : "Run Red Team"}
                </button>
              </div>
              <ErrorBanner variant="error" message={error} />

              {result && (
                <div className="space-y-4">
                  <div className="rounded-md border border-fin-negative/25 bg-fin-negative/5 p-4">
                    <div className="mb-1 text-[11px] font-bold uppercase tracking-[0.12em] text-fin-negative">Strongest Pushback</div>
                    <p className="text-sm font-semibold text-text-primary">{result.strongest_pushback}</p>
                  </div>

                  <div className="grid grid-cols-1 gap-3">
                    {result.critiques.map((critique) => (
                      <article key={`${critique.severity}-${critique.argument}`} className="rounded-md border border-border p-4">
                        <div className="mb-2 flex items-center gap-2">
                          <Badge variant={severityVariant(critique.severity)}>{critique.severity}</Badge>
                          <span className="text-[11px] uppercase tracking-[0.1em] text-text-muted">Critique</span>
                        </div>
                        <p className="text-sm font-semibold text-text-primary">{critique.argument}</p>
                        <p className="mt-2 text-sm text-text-secondary">Evidence needed: {critique.evidence_needed}</p>
                      </article>
                    ))}
                  </div>

                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    <div className="rounded-md border border-border bg-surface-sunken p-4">
                      <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-brand-navy">Overlooked Risks</div>
                      <div className="flex flex-wrap gap-2">
                        {result.overlooked_risks.map((risk) => <Badge key={risk} variant="neutral">{risk}</Badge>)}
                      </div>
                    </div>
                    <div className="rounded-md border border-border bg-surface-sunken p-4">
                      <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-brand-navy">Consensus Check</div>
                      <p className="text-sm text-text-secondary">{result.consensus_check}</p>
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <button type="button" onClick={copyMarkdown} className="rounded border border-brand-blue px-4 py-2 text-sm font-semibold text-brand-blue hover:bg-brand-blue/10">
                      {copied ? "Copied Markdown" : "Export Markdown"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
