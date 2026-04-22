"use client";

import type { CSSProperties } from "react";
import { useState } from "react";
import { ErrorBanner } from "../ui/ErrorBanner";
import { LoadingPulse } from "../ui/LoadingPulse";
import { flags } from "../../lib/flags";
import { useApi } from "../../lib/use-api";

interface CorrelationResponse {
  available: boolean;
  message?: string;
  window: number;
  range?: string;
  tickers: string[];
  matrix: Array<Array<number | null>>;
}

const WINDOWS = [30, 90, 180] as const;

function cellStyleFor(value: number | null): CSSProperties {
  if (value == null) return { backgroundColor: "#F1F3F6", color: "#6B7B8D" };
  const clamped = Math.max(-1, Math.min(1, value));
  if (clamped < 0) {
    const intensity = Math.abs(clamped);
    return {
      backgroundColor: `rgba(46, 91, 154, ${0.12 + intensity * 0.58})`,
      color: intensity > 0.58 ? "#FFFFFF" : "#1B2A4A",
    };
  }
  return {
    backgroundColor: `rgba(192, 57, 43, ${0.1 + clamped * 0.58})`,
    color: clamped > 0.58 ? "#FFFFFF" : "#1A1A2E",
  };
}

function labelFor(value: number | null): string {
  return value == null ? "—" : value.toFixed(2);
}

export function CorrelationMatrix() {
  const [windowDays, setWindowDays] = useState<(typeof WINDOWS)[number]>(90);
  const url = flags.correlation ? `/api/portfolio/correlation?window=${windowDays}` : null;
  const { data, loading, error } = useApi<CorrelationResponse>(url, { cacheTtlMs: 300_000 });

  if (!flags.correlation) return null;

  return (
    <section className="atlas-card mb-6">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border px-5 py-4">
        <div>
          <h3 className="font-serif text-lg font-bold text-brand-navy">Cross-Asset Correlation</h3>
          <p className="mt-1 text-xs text-text-muted">Daily-return matrix for current portfolio positions.</p>
        </div>
        <div className="flex gap-2">
          {WINDOWS.map((days) => (
            <button
              key={days}
              type="button"
              onClick={() => setWindowDays(days)}
              className={`rounded border px-3 py-1.5 text-xs font-semibold ${windowDays === days ? "border-brand-navy bg-brand-navy text-white" : "border-border text-text-secondary hover:bg-surface-sunken"}`}
            >
              {days}D
            </button>
          ))}
        </div>
      </div>
      <div className="p-5">
        <ErrorBanner variant="error" message={error} className="mb-4" />
        {loading ? <LoadingPulse height="h-32" label="Loading correlation..." /> : (
          <>
            {data && !data.available && <ErrorBanner variant="info" message={data.message || "Not enough positions to compute correlation."} className="mb-4" />}
            {data?.available && (
              <div className="overflow-x-auto">
                <table className="min-w-[620px] border-separate border-spacing-1 text-xs">
                  <thead>
                    <tr>
                      <th className="px-2 py-2 text-left text-[11px] uppercase tracking-[0.1em] text-text-muted">Ticker</th>
                      {data.tickers.map((ticker) => (
                        <th key={ticker} className="px-2 py-2 text-center font-mono text-[11px] text-brand-navy">{ticker}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.tickers.map((ticker, rowIdx) => (
                      <tr key={ticker}>
                        <th className="sticky left-0 bg-surface-raised px-2 py-2 text-left font-mono text-brand-navy">{ticker}</th>
                        {data.tickers.map((colTicker, colIdx) => {
                          const value = data.matrix[rowIdx]?.[colIdx] ?? null;
                          return (
                            <td
                              key={`${ticker}-${colTicker}`}
                              className="h-10 min-w-16 rounded text-center font-mono tabular-nums shadow-[inset_0_0_0_1px_rgba(255,255,255,0.45)]"
                              style={cellStyleFor(value)}
                              title={value == null ? "Insufficient overlap" : `${ticker} and ${colTicker}: ${(value * 100).toFixed(0)}% co-movement correlation`}
                            >
                              {labelFor(value)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="mt-3 flex flex-wrap gap-3 text-[11px] text-text-muted">
                  <span>Blue = negative correlation</span>
                  <span>White = low correlation</span>
                  <span>Red = positive correlation</span>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
