"use client";
import { useEffect, useState } from "react";
import { Dot } from "lucide-react";

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

export function TickerBar() {
  const [data, setData] = useState<IndexData[]>(
    INDICES.map((i) => ({ ...i, price: "—", change: "—", positive: true }))
  );

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`/api/market/indices`);
        if (res.ok) {
          const json = await res.json();
          if (Array.isArray(json)) {
            setData(json);
          }
        }
      } catch {
        // keep defaults
      }
    }
    load();
    const iv = setInterval(load, 60_000);
    return () => clearInterval(iv);
  }, []);

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
