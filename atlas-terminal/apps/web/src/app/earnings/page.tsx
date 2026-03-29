"use client";
import { useEffect, useState } from "react";
import { useTicker } from "../lib/use-ticker";

interface EarningsRecord {
  date: string;
  eps_actual: number | null;
  eps_estimate: number | null;
  surprise: number | null;
}

interface CalendarData {
  next_earnings: string | null;
  revenue_estimate: number | null;
  eps_estimate: number | null;
}

interface QuarterlyData {
  period: string;
  revenue: number | null;
  earnings: number | null;
}

interface DeltaData {
  available: boolean;
  latest_quarter?: string;
  prev_quarter?: string;
  revenue_delta_pct?: number | null;
  earnings_delta_pct?: number | null;
  eps_trend?: { date: string; surprise_pct: number }[];
  ai_summary?: string | null;
}

export default function EarningsPage() {
  const { ticker, initialized } = useTicker();
  const [assetType, setAssetType] = useState<string>("equity");
  const [history, setHistory] = useState<EarningsRecord[]>([]);
  const [calendar, setCalendar] = useState<CalendarData | null>(null);
  const [quarterly, setQuarterly] = useState<QuarterlyData[]>([]);
  const [delta, setDelta] = useState<DeltaData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!initialized) return;
    setLoading(true);
    Promise.all([
      fetch(`/api/earnings/${ticker}/history`).then((r) => r.ok ? r.json() : null),
      fetch(`/api/earnings/${ticker}/calendar`).then((r) => r.ok ? r.json() : null),
      fetch(`/api/earnings/${ticker}/quarterly`).then((r) => r.ok ? r.json() : null),
      fetch(`/api/market/overview/${ticker}`).then((r) => r.ok ? r.json() : null),
      fetch(`/api/earnings/${ticker}/delta`).then((r) => r.ok ? r.json() : null),
    ]).then(([h, c, q, o, d]) => {
      setHistory(h?.history || []);
      setCalendar(c);
      setQuarterly(q?.quarterly || []);
      setAssetType(o?.asset_type || "equity");
      setDelta(d?.available ? d : null);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [ticker, initialized]);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-accent-green animate-pulse font-mono">Loading...</div></div>;

  if (assetType !== "equity") {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">
          <span className="text-accent-green">{ticker}</span> Earnings
        </h1>
        <div className="bg-bg-card border border-border rounded-lg p-5 text-text-secondary text-sm">
          Earnings data is not available for this asset type ({assetType}).
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">
        <span className="text-accent-green">{ticker}</span> Earnings
      </h1>

      {/* Next Earnings + Estimates */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-bg-card border border-accent-green rounded-lg p-4">
          <div className="text-text-muted text-xs mb-1">Next Earnings Date</div>
          <div className="text-accent-green font-mono font-bold text-lg">
            {calendar?.next_earnings || "TBD"}
          </div>
        </div>
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <div className="text-text-muted text-xs mb-1">EPS Estimate</div>
          <div className="text-text-primary font-mono font-bold text-lg">
            {calendar?.eps_estimate != null ? `$${calendar.eps_estimate.toFixed(2)}` : "—"}
          </div>
        </div>
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <div className="text-text-muted text-xs mb-1">Revenue Estimate</div>
          <div className="text-text-primary font-mono font-bold text-lg">
            {calendar?.revenue_estimate != null ? `$${(calendar.revenue_estimate / 1e9).toFixed(2)}B` : "—"}
          </div>
        </div>
      </div>

      {/* Earnings Delta — What Changed */}
      {delta && (
        <div className="bg-bg-card border border-accent-blue/40 rounded-lg p-5 mb-6">
          <h3 className="text-accent-blue text-sm font-semibold mb-3">
            Earnings Delta — {delta.latest_quarter} vs {delta.prev_quarter}
          </h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <div className="text-text-muted text-xs mb-1">Revenue Change</div>
              <div className={`text-2xl font-mono font-bold ${delta.revenue_delta_pct != null && delta.revenue_delta_pct >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                {delta.revenue_delta_pct != null ? `${delta.revenue_delta_pct >= 0 ? "+" : ""}${delta.revenue_delta_pct}%` : "—"}
              </div>
            </div>
            <div>
              <div className="text-text-muted text-xs mb-1">Earnings Change</div>
              <div className={`text-2xl font-mono font-bold ${delta.earnings_delta_pct != null && delta.earnings_delta_pct >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                {delta.earnings_delta_pct != null ? `${delta.earnings_delta_pct >= 0 ? "+" : ""}${delta.earnings_delta_pct}%` : "—"}
              </div>
            </div>
          </div>
          {delta.eps_trend && delta.eps_trend.length > 0 && (
            <div className="flex gap-2 mb-3">
              {delta.eps_trend.map((e, i) => (
                <div key={i} className="text-xs font-mono px-2 py-1 bg-bg-primary rounded border border-border">
                  <span className="text-text-muted">{e.date.slice(5)}</span>{" "}
                  <span className={e.surprise_pct >= 0 ? "text-accent-green" : "text-accent-red"}>
                    {e.surprise_pct >= 0 ? "+" : ""}{e.surprise_pct}%
                  </span>
                </div>
              ))}
            </div>
          )}
          {delta.ai_summary && (
            <p className="text-text-secondary text-sm leading-relaxed border-t border-border pt-3">
              {delta.ai_summary}
            </p>
          )}
        </div>
      )}

      {/* EPS History — Beat/Miss Chart */}
      <div className="bg-bg-card border border-border rounded-lg p-5 mb-6">
        <h3 className="text-text-secondary text-sm font-semibold mb-4">EPS History — Beat/Miss</h3>
        {history.length > 0 ? (
          <div className="space-y-0">
            {/* Visual bars */}
            <div className="flex items-end gap-2 h-32 mb-4">
              {history.map((h, i) => {
                const beat = h.eps_actual != null && h.eps_estimate != null && h.eps_actual >= h.eps_estimate;
                const barHeight = h.surprise != null ? Math.min(Math.abs(h.surprise) * 2, 100) : 20;
                return (
                  <div key={i} className="flex-1 flex flex-col items-center justify-end h-full">
                    <div
                      className={`w-full rounded-t-sm ${beat ? "bg-accent-green" : "bg-accent-red"}`}
                      style={{ height: `${Math.max(barHeight, 8)}%` }}
                    />
                    <div className="text-text-muted text-[10px] mt-1 font-mono">{h.date?.slice(0, 7)}</div>
                  </div>
                );
              })}
            </div>

            {/* Table */}
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left text-text-muted py-2 font-normal">Date</th>
                  <th className="text-right text-text-muted py-2 font-normal">EPS Estimate</th>
                  <th className="text-right text-text-muted py-2 font-normal">EPS Actual</th>
                  <th className="text-right text-text-muted py-2 font-normal">Surprise %</th>
                  <th className="text-right text-text-muted py-2 font-normal">Result</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h, i) => {
                  const beat = h.eps_actual != null && h.eps_estimate != null && h.eps_actual >= h.eps_estimate;
                  return (
                    <tr key={i} className="border-b border-border/50">
                      <td className="py-2 text-text-primary font-mono">{h.date}</td>
                      <td className="py-2 text-text-secondary font-mono text-right">
                        {h.eps_estimate != null ? `$${h.eps_estimate.toFixed(2)}` : "—"}
                      </td>
                      <td className="py-2 text-text-primary font-mono text-right font-semibold">
                        {h.eps_actual != null ? `$${h.eps_actual.toFixed(2)}` : "—"}
                      </td>
                      <td className={`py-2 font-mono text-right ${h.surprise != null && h.surprise >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                        {h.surprise != null ? `${h.surprise >= 0 ? "+" : ""}${h.surprise.toFixed(2)}%` : "—"}
                      </td>
                      <td className="py-2 text-right">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                          beat ? "bg-accent-green/20 text-accent-green" : "bg-accent-red/20 text-accent-red"
                        }`}>
                          {beat ? "BEAT" : "MISS"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-text-muted text-center py-8">No earnings history available</div>
        )}
      </div>

      {/* Quarterly Revenue & Earnings */}
      {quarterly.length > 0 && (
        <div className="bg-bg-card border border-border rounded-lg p-5">
          <h3 className="text-text-secondary text-sm font-semibold mb-4">Quarterly Revenue & Earnings</h3>
          <div className="grid grid-cols-4 gap-3">
            {quarterly.map((q, i) => (
              <div key={i} className="bg-bg-primary rounded-lg p-4">
                <div className="text-text-muted text-xs mb-2 font-mono">{q.period}</div>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-text-muted">Revenue</span>
                    <span className="text-text-primary font-mono">
                      {q.revenue != null ? `$${(q.revenue / 1e9).toFixed(2)}B` : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-text-muted">Earnings</span>
                    <span className={`font-mono ${q.earnings != null && q.earnings >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                      {q.earnings != null ? `$${(q.earnings / 1e9).toFixed(2)}B` : "—"}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
