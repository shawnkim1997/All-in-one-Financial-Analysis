"use client";
import { useEffect, useState } from "react";

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
    <header className="fixed top-0 left-0 right-0 z-50 h-[52px] bg-bg-primary border-b border-border flex items-center px-5 gap-4">
      <div className="font-mono font-bold text-accent-green text-lg mr-5">
        ATLAS<span className="text-text-secondary font-normal"> TERMINAL</span>
      </div>
      <div className="flex gap-5 overflow-hidden">
        {data.map((idx) => (
          <div key={idx.label} className="flex items-center gap-2 text-sm font-mono">
            <span className="text-text-muted">{idx.label}</span>
            <span className="text-text-primary font-semibold">{idx.price}</span>
            {idx.change !== "—" && (
              <span className={idx.positive ? "text-accent-green" : "text-accent-red"}>
                {idx.change}
              </span>
            )}
          </div>
        ))}
      </div>
    </header>
  );
}
