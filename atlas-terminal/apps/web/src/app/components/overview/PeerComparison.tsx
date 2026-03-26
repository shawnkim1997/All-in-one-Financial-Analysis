"use client";

export interface PeerItem {
  ticker: string;
  name: string;
  market_cap: number | null;
  pe: number | null;
  pb: number | null;
  ps: number | null;
  ev_ebitda: number | null;
}

export interface PeerComparisonData {
  ticker: string;
  sector: string;
  industry: string;
  averages: {
    pe: number | null;
    pb: number | null;
    ps: number | null;
    ev_ebitda: number | null;
  };
  peers: PeerItem[];
}

function formatValue(value: number | null, type: "multiple" | "marketCap" = "multiple"): string {
  if (value == null) return "—";
  if (type === "marketCap") {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
    return `$${value.toFixed(0)}`;
  }
  return value.toFixed(2);
}

function extrema(values: Array<number | null>) {
  const numbers = values.filter((value): value is number => value != null);
  return {
    min: numbers.length ? Math.min(...numbers) : null,
    max: numbers.length ? Math.max(...numbers) : null,
  };
}

function valueClass(value: number | null, min: number | null, max: number | null): string {
  if (value == null) return "text-text-muted";
  if (min != null && value === min) return "text-accent-green";
  if (max != null && value === max) return "text-accent-red";
  return "text-text-primary";
}

export function PeerComparison({
  currentTicker,
  data,
}: {
  currentTicker: string;
  data: PeerComparisonData | null;
}) {
  if (!data || data.peers.length === 0) {
    return (
      <div className="bg-bg-card border border-border rounded-lg p-5 mt-6">
        <h3 className="text-text-secondary text-sm font-semibold mb-2">Valuation vs. Peers</h3>
        <div className="text-text-muted text-sm">Peer comparison data is not available for this ticker.</div>
      </div>
    );
  }

  const peExtrema = extrema(data.peers.map((peer) => peer.pe));
  const pbExtrema = extrema(data.peers.map((peer) => peer.pb));
  const psExtrema = extrema(data.peers.map((peer) => peer.ps));
  const evEbitdaExtrema = extrema(data.peers.map((peer) => peer.ev_ebitda));

  return (
    <div className="bg-bg-card border border-border rounded-lg p-5 mt-6">
      <div className="flex items-end justify-between gap-4 mb-4">
        <div>
          <h3 className="text-text-secondary text-sm font-semibold">Valuation vs. Peers</h3>
          <div className="text-text-muted text-xs mt-1">{data.industry || data.sector || "Industry peers"}</div>
        </div>
        <div className="text-[11px] text-text-muted font-mono flex gap-3">
          <span>Avg PE: {formatValue(data.averages.pe)}</span>
          <span>Avg PB: {formatValue(data.averages.pb)}</span>
          <span>Avg PS: {formatValue(data.averages.ps)}</span>
          <span>Avg EV/EBITDA: {formatValue(data.averages.ev_ebitda)}</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead>
            <tr className="text-left text-text-muted border-b border-border">
              <th className="py-3 pr-3 font-medium">Ticker</th>
              <th className="py-3 pr-3 font-medium">Company</th>
              <th className="py-3 pr-3 font-medium">Market Cap</th>
              <th className="py-3 pr-3 font-medium">P/E</th>
              <th className="py-3 pr-3 font-medium">P/B</th>
              <th className="py-3 pr-3 font-medium">P/S</th>
              <th className="py-3 font-medium">EV/EBITDA</th>
            </tr>
          </thead>
          <tbody>
            {data.peers.map((peer) => {
              const isCurrent = peer.ticker.toUpperCase() === currentTicker.toUpperCase();
              return (
                <tr
                  key={peer.ticker}
                  className={`border-b border-border/60 ${isCurrent ? "bg-accent-green/10" : ""}`}
                >
                  <td className="py-3 pr-3 font-mono font-semibold text-text-primary">{peer.ticker}</td>
                  <td className="py-3 pr-3 text-text-secondary">{peer.name}</td>
                  <td className="py-3 pr-3 font-mono text-text-primary">{formatValue(peer.market_cap, "marketCap")}</td>
                  <td className={`py-3 pr-3 font-mono ${valueClass(peer.pe, peExtrema.min, peExtrema.max)}`}>
                    {formatValue(peer.pe)}
                  </td>
                  <td className={`py-3 pr-3 font-mono ${valueClass(peer.pb, pbExtrema.min, pbExtrema.max)}`}>
                    {formatValue(peer.pb)}
                  </td>
                  <td className={`py-3 pr-3 font-mono ${valueClass(peer.ps, psExtrema.min, psExtrema.max)}`}>
                    {formatValue(peer.ps)}
                  </td>
                  <td className={`py-3 font-mono ${valueClass(peer.ev_ebitda, evEbitdaExtrema.min, evEbitdaExtrema.max)}`}>
                    {formatValue(peer.ev_ebitda)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
