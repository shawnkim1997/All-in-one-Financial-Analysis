"use client";
import { useEffect } from "react";
import { Dot } from "lucide-react";
import { useApi } from "../lib/use-api";

interface IndexData {
  label: string;
  symbol: string;
  price: string;
  change: string;
  positive: boolean;
}

const INDICES = [
  { label: "S&P 500", symbol: "^GSPC" },
  { label: "NASDAQ", symbol: "^IXIC" },
  { label: "KOSPI", symbol: "^KS11" },
  { label: "BTC", symbol: "BTC-USD" },
];

const DEFAULT_INDICES: IndexData[] = INDICES.map((i) => ({ ...i, price: "—", change: "—", positive: true }));

export function TickerBar() {
  const indices = useApi<IndexData[]>("/api/market/indices", { cacheTtlMs: 60_000 });

  useEffect(() => {
    const iv = setInterval(indices.refetch, 60_000);
    return () => clearInterval(iv);
  }, [indices.refetch]);

  const data = Array.isArray(indices.data) ? indices.data : DEFAULT_INDICES;

  return (
    <header className="fixed left-0 right-0 top-0 z-50 flex h-[56px] items-center gap-4 border-b border-border bg-surface-raised px-5 shadow-card">
      <div className="mr-4 flex items-baseline gap-2">
        <span className="font-serif text-xl font-bold text-brand-navy">ATLAS</span>
        <span className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-gold">
          Morgan Terminal
        </span>
      </div>
      <div className="flex gap-5 overflow-hidden">
        {data.map((idx) => (
          <div key={idx.label} className="flex items-center gap-1.5 text-sm font-mono">
            <span className="text-text-muted">{idx.label}</span>
            <span className="text-text-primary font-semibold">{idx.price}</span>
            {idx.change !== "—" && (
              <span className={`inline-flex items-center ${idx.positive ? "text-fin-positive" : "text-fin-negative"}`}>
                <Dot className="-mx-1 h-4 w-4" />
                {idx.change}
              </span>
            )}
          </div>
        ))}
      </div>
    </header>
  );
}
