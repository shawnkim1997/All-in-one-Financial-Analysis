"use client";

import { ErrorBanner } from "../ui/ErrorBanner";
import { LoadingPulse } from "../ui/LoadingPulse";
import { StatCard } from "../ui/StatCard";
import { flags } from "../../lib/flags";
import { useApi } from "../../lib/use-api";

interface HolderRow {
  name: string;
  shares: number | null;
  pct: number | null;
  change: number | null;
  value: number | null;
}

interface OwnershipResponse {
  ticker: string;
  available: boolean;
  source: string | null;
  institutional_pct: number | null;
  insider_pct: number | null;
  float_pct: number | null;
  institutions: HolderRow[];
  insiders: HolderRow[];
}

function formatPct(value: number | null): string {
  return value == null ? "—" : `${value.toFixed(1)}%`;
}

function formatShares(value: number | null): string {
  if (value == null) return "—";
  const abs = Math.abs(value);
  if (abs >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toFixed(0);
}

function formatChange(value: number | null): string {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatShares(value)}`;
}

function formatValue(value: number | null): string {
  if (value == null) return "—";
  const abs = Math.abs(value);
  if (abs >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  return `$${value.toFixed(0)}`;
}

function HolderTable({ title, rows }: { title: string; rows: HolderRow[] }) {
  return (
    <div className="overflow-hidden rounded-md border border-border">
      <div className="border-b border-border bg-surface-sunken px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-brand-navy">
        {title}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-sm">
          <thead>
            <tr className="border-b border-border text-[11px] uppercase tracking-[0.1em] text-text-muted">
              <th className="px-4 py-2 text-left font-semibold">Holder</th>
              <th className="px-3 py-2 text-right font-semibold">Shares</th>
              <th className="px-3 py-2 text-right font-semibold">%</th>
              <th className="px-3 py-2 text-right font-semibold">Change</th>
              <th className="px-4 py-2 text-right font-semibold">Value</th>
            </tr>
          </thead>
          <tbody>
            {rows.length > 0 ? rows.map((row) => (
              <tr key={`${title}-${row.name}`} className="border-b border-border/60 last:border-0 hover:bg-surface-sunken">
                <td className="max-w-[240px] truncate px-4 py-2.5 font-semibold text-brand-navy">{row.name}</td>
                <td className="px-3 py-2.5 text-right font-mono tabular-nums text-text-primary">{formatShares(row.shares)}</td>
                <td className="px-3 py-2.5 text-right font-mono tabular-nums text-text-primary">{formatPct(row.pct)}</td>
                <td className={`px-3 py-2.5 text-right font-mono tabular-nums ${row.change == null ? "text-text-muted" : row.change >= 0 ? "text-fin-positive" : "text-fin-negative"}`}>
                  {formatChange(row.change)}
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular-nums text-text-secondary">{formatValue(row.value)}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-text-muted">No holder rows available.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function OwnershipBar({ data }: { data: OwnershipResponse }) {
  const institutional = data.institutional_pct ?? 0;
  const insider = data.insider_pct ?? 0;
  const float = data.float_pct ?? Math.max(0, 100 - institutional - insider);
  const total = institutional + insider + float || 100;
  const instWidth = (institutional / total) * 100;
  const insiderWidth = (insider / total) * 100;
  const floatWidth = Math.max(0, 100 - instWidth - insiderWidth);

  return (
    <div>
      <div className="mb-2 flex justify-between text-[11px] font-mono uppercase tracking-[0.08em] text-text-muted">
        <span>Institutional</span>
        <span>Insider</span>
        <span>Float / Retail</span>
      </div>
      <div className="flex h-4 overflow-hidden rounded-full border border-border bg-surface-sunken" aria-label="Ownership breakdown">
        <div className="bg-brand-navy" style={{ width: `${instWidth}%` }} />
        <div className="bg-brand-gold" style={{ width: `${insiderWidth}%` }} />
        <div className="bg-brand-blue/35" style={{ width: `${floatWidth}%` }} />
      </div>
    </div>
  );
}

export function Ownership({ ticker }: { ticker: string }) {
  const url = flags.ownership ? `/api/market/ownership/${encodeURIComponent(ticker)}` : null;
  const { data, loading, error } = useApi<OwnershipResponse>(url, { cacheTtlMs: 300_000 });

  if (!flags.ownership) return null;

  return (
    <section className="atlas-card mt-6">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border px-5 py-4">
        <div>
          <h3 className="font-serif text-lg font-bold text-brand-navy">Ownership</h3>
          <p className="mt-1 text-xs text-text-muted">
            Institutional and insider holder snapshot{data?.source ? ` via ${data.source}` : ""}.
          </p>
        </div>
      </div>
      <div className="space-y-5 p-5">
        <ErrorBanner variant="error" message={error} />
        {loading ? <LoadingPulse height="h-32" label="Loading ownership..." /> : (
          <>
            {!data?.available && (
              <ErrorBanner variant="info" message="Ownership data is not available for this ticker yet." />
            )}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <StatCard label="Institutional" value={formatPct(data?.institutional_pct ?? null)} />
              <StatCard label="Insider" value={formatPct(data?.insider_pct ?? null)} tone="accent" />
              <StatCard label="Float / Retail" value={formatPct(data?.float_pct ?? null)} />
            </div>
            {data && <OwnershipBar data={data} />}
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <HolderTable title="Top Institutional Holders" rows={data?.institutions ?? []} />
              <HolderTable title="Insider Activity / Holders" rows={data?.insiders ?? []} />
            </div>
          </>
        )}
      </div>
    </section>
  );
}
