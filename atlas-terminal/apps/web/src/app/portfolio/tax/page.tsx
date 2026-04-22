"use client";

import { useState } from "react";
import { ErrorBanner } from "../../components/ui/ErrorBanner";
import { LoadingPulse } from "../../components/ui/LoadingPulse";
import { StatCard } from "../../components/ui/StatCard";
import { flags } from "../../lib/flags";
import { useApi } from "../../lib/use-api";

type IncomeBand = "basic" | "higher";

interface CgtPosition {
  ticker: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  cost_currency: string;
  current_currency: string;
  cost_gbp: number;
  value_gbp: number;
  gain_gbp: number;
  gain_per_share_gbp: number;
}

interface OptimalRealization {
  ticker: string;
  shares_to_sell: number;
  estimated_gain_gbp: number;
}

interface CgtResponse {
  income_band: IncomeBand;
  total_unrealized_gain_gbp: number;
  allowance: number;
  allowance_remaining: number;
  taxable_if_sold_all: number;
  tax_if_sold_all: number;
  rate: number;
  optimal_realization: OptimalRealization[];
  positions: CgtPosition[];
  tax_year_end: string;
  fx_source: string;
  disclaimer: string;
}

function gbp(value: number): string {
  return `£${value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

function statusFor(data: CgtResponse | null): { label: string; tone: "positive" | "negative" | "accent" } {
  if (!data) return { label: "—", tone: "accent" };
  if (data.total_unrealized_gain_gbp <= data.allowance * 0.75) return { label: "Under allowance", tone: "positive" };
  if (data.total_unrealized_gain_gbp <= data.allowance) return { label: "Approaching limit", tone: "accent" };
  return { label: "Allowance exceeded", tone: "negative" };
}

export default function PortfolioTaxPage() {
  const [incomeBand, setIncomeBand] = useState<IncomeBand>("higher");
  const url = flags.cgt ? `/api/tax/uk/cgt/local?income_band=${incomeBand}` : null;
  const { data, loading, error } = useApi<CgtResponse>(url, { cacheTtlMs: 60_000 });
  const status = statusFor(data);

  if (!flags.cgt) {
    return (
      <div className="atlas-page">
        <ErrorBanner variant="info" message="UK CGT calculator is disabled. Set NEXT_PUBLIC_FLAG_CGT=true to enable it." />
      </div>
    );
  }

  return (
    <div className="atlas-page">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-serif text-3xl font-bold text-brand-navy">UK CGT Calculator</h1>
          <p className="mt-1 text-sm text-text-secondary">Allowance simulation for current portfolio positions.</p>
        </div>
        <div className="flex gap-2">
          {(["basic", "higher"] as IncomeBand[]).map((band) => (
            <button
              key={band}
              type="button"
              onClick={() => setIncomeBand(band)}
              className={`rounded border px-4 py-2 text-xs font-semibold capitalize ${incomeBand === band ? "border-brand-navy bg-brand-navy text-white" : "border-border text-text-secondary hover:bg-surface-sunken"}`}
            >
              {band} rate
            </button>
          ))}
        </div>
      </div>

      <ErrorBanner variant="warning" message="Not tax advice. This uses static FX estimates and simplified Section 104 pooling assumptions. Check HMRC guidance before acting." className="mb-5" />
      <ErrorBanner variant="error" message={error} className="mb-5" />

      {loading ? <LoadingPulse height="h-48" label="Calculating CGT..." /> : (
        <>
          <div className="mb-6 grid grid-cols-1 gap-3 md:grid-cols-4">
            <StatCard label="Status" value={status.label} tone={status.tone} />
            <StatCard label="Unrealized Gain" value={data ? gbp(data.total_unrealized_gain_gbp) : "—"} />
            <StatCard label="Allowance Left" value={data ? gbp(data.allowance_remaining) : "—"} tone={data && data.allowance_remaining <= 0 ? "negative" : "positive"} />
            <StatCard label="Tax If Sold All" value={data ? gbp(data.tax_if_sold_all) : "—"} tone={data && data.tax_if_sold_all > 0 ? "negative" : "default"} />
          </div>

          <section className="atlas-card mb-6">
            <header className="border-b border-border px-5 py-4">
              <h2 className="font-serif text-lg font-bold text-brand-navy">Allowance Use Plan</h2>
              <p className="mt-1 text-xs text-text-muted">Greedy estimate of sales that could use the annual allowance without exceeding it.</p>
            </header>
            <div className="p-5">
              {data?.optimal_realization.length ? (
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {data.optimal_realization.map((item) => (
                    <div key={item.ticker} className="rounded-md border border-border bg-surface-sunken p-4">
                      <div className="font-mono text-lg font-bold text-brand-navy">{item.ticker}</div>
                      <div className="mt-2 text-sm text-text-secondary">
                        Sell <span className="font-mono text-text-primary">{item.shares_to_sell.toLocaleString()}</span> shares for about <span className="font-mono text-fin-positive">{gbp(item.estimated_gain_gbp)}</span> gain.
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-text-muted">No positive gains available to realize against the allowance.</div>
              )}
            </div>
          </section>

          <section className="atlas-table-shell">
            <div className="border-b border-border px-5 py-4">
              <h2 className="font-serif text-lg font-bold text-brand-navy">Position Gains</h2>
              <p className="mt-1 text-xs text-text-muted">FX source: {data?.fx_source || "—"} · Tax year end: {data?.tax_year_end || "—"}</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] text-sm">
                <thead className="bg-surface-sunken">
                  <tr className="border-y border-border-strong text-[11px] uppercase tracking-[0.12em] text-brand-navy">
                    <th className="px-5 py-3 text-left font-semibold">Ticker</th>
                    <th className="px-3 py-3 text-right font-semibold">Qty</th>
                    <th className="px-3 py-3 text-right font-semibold">Cost</th>
                    <th className="px-3 py-3 text-right font-semibold">Value</th>
                    <th className="px-3 py-3 text-right font-semibold">Gain</th>
                    <th className="px-5 py-3 text-right font-semibold">Gain / Share</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.positions || []).map((position) => (
                    <tr key={position.ticker} className="border-b border-border/60 hover:bg-surface-sunken">
                      <td className="px-5 py-3 font-mono font-bold text-brand-navy">{position.ticker}</td>
                      <td className="px-3 py-3 text-right font-mono tabular-nums text-text-primary">{position.quantity.toLocaleString()}</td>
                      <td className="px-3 py-3 text-right font-mono tabular-nums text-text-secondary">{gbp(position.cost_gbp)}</td>
                      <td className="px-3 py-3 text-right font-mono tabular-nums text-text-secondary">{gbp(position.value_gbp)}</td>
                      <td className={`px-3 py-3 text-right font-mono tabular-nums ${position.gain_gbp >= 0 ? "text-fin-positive" : "text-fin-negative"}`}>{gbp(position.gain_gbp)}</td>
                      <td className="px-5 py-3 text-right font-mono tabular-nums text-text-primary">£{position.gain_per_share_gbp.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
