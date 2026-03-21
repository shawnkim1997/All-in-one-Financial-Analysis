"use client";
import { useState } from "react";

interface ScreenerRow {
  ticker: string;
  name?: string;
  sector?: string;
  market_cap?: number;
  pe?: number;
  div_yield?: number;
  price?: number;
  change_pct?: number;
}

interface BacktestResult {
  error?: string;
  total_return_pct?: number;
  benchmark_return_pct?: number;
  alpha?: number;
  sharpe_ratio?: number;
}

export default function ScreenerPage() {
  const [tab, setTab] = useState<"screener" | "backtest">("screener");
  const [rows, setRows] = useState<ScreenerRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [peMax, setPeMax] = useState("25");
  const [sector, setSector] = useState("");
  const [divMin, setDivMin] = useState("");

  const [btTicker, setBtTicker] = useState("AAPL");
  const [strategy, setStrategy] = useState("sma_crossover");
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2026-03-01");
  const [btResult, setBtResult] = useState<BacktestResult | null>(null);
  const [btLoading, setBtLoading] = useState(false);

  async function runScreener() {
    setLoading(true);
    try {
      const res = await fetch("/api/screener/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pe_max: peMax ? parseFloat(peMax) : undefined,
          sector: sector || undefined,
          div_yield_min: divMin ? parseFloat(divMin) : undefined,
        }),
      });
      const data = await res.json();
      setRows(Array.isArray(data) ? data : []);
    } catch {
      setRows([]);
    } finally {
      setLoading(false);
    }
  }

  async function runBacktest() {
    setBtLoading(true);
    try {
      const res = await fetch("/api/screener/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: btTicker,
          strategy,
          start_date: startDate,
          end_date: endDate,
        }),
      });
      setBtResult(await res.json());
    } catch {
      setBtResult(null);
    } finally {
      setBtLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Stock Screener</h1>

      <div className="flex gap-1 mb-4 bg-bg-card rounded-lg p-1 w-fit">
        <button
          onClick={() => setTab("screener")}
          className={`px-4 py-2 rounded-md text-sm font-medium ${tab === "screener" ? "bg-accent-green text-bg-primary" : "text-text-secondary"}`}
        >
          Screener
        </button>
        <button
          onClick={() => setTab("backtest")}
          className={`px-4 py-2 rounded-md text-sm font-medium ${tab === "backtest" ? "bg-accent-green text-bg-primary" : "text-text-secondary"}`}
        >
          Backtest
        </button>
      </div>

      {tab === "screener" ? (
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <div className="flex flex-wrap gap-2 mb-3">
            <input value={peMax} onChange={(e) => setPeMax(e.target.value)} placeholder="P/E < 25" className="bg-bg-primary border border-border rounded px-3 py-2 text-sm" />
            <input value={sector} onChange={(e) => setSector(e.target.value)} placeholder="Sector (optional)" className="bg-bg-primary border border-border rounded px-3 py-2 text-sm" />
            <input value={divMin} onChange={(e) => setDivMin(e.target.value)} placeholder="Div Yield > %" className="bg-bg-primary border border-border rounded px-3 py-2 text-sm" />
            <button onClick={runScreener} className="bg-accent-green text-bg-primary px-4 py-2 rounded font-semibold">
              {loading ? "Running..." : "Run Screener"}
            </button>
          </div>
          <div className="overflow-auto border border-border rounded-md">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  {["Ticker", "Name", "Sector", "Price", "P/E", "MCap", "Change"].map((h) => (
                    <th key={h} className="text-left px-3 py-2 text-text-muted">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={`${r.ticker}-${i}`} className="border-b border-border/40">
                    <td className="px-3 py-2 text-accent-green font-mono">{r.ticker}</td>
                    <td className="px-3 py-2 text-text-primary">{r.name || "—"}</td>
                    <td className="px-3 py-2 text-text-secondary">{r.sector || "—"}</td>
                    <td className="px-3 py-2 text-text-primary font-mono">{r.price != null ? `$${r.price.toFixed(2)}` : "—"}</td>
                    <td className="px-3 py-2 text-text-primary font-mono">{r.pe != null ? r.pe.toFixed(1) : "—"}</td>
                    <td className="px-3 py-2 text-text-primary font-mono">{r.market_cap ? `${(r.market_cap / 1e9).toFixed(1)}B` : "—"}</td>
                    <td className={`px-3 py-2 font-mono ${((r.change_pct || 0) >= 0) ? "text-accent-green" : "text-accent-red"}`}>
                      {r.change_pct != null ? `${r.change_pct >= 0 ? "+" : ""}${r.change_pct.toFixed(2)}%` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <div className="flex flex-wrap gap-2 mb-3">
            <input value={btTicker} onChange={(e) => setBtTicker(e.target.value.toUpperCase())} placeholder="Ticker" className="bg-bg-primary border border-border rounded px-3 py-2 text-sm" />
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)} className="bg-bg-primary border border-border rounded px-3 py-2 text-sm">
              <option value="sma_crossover">SMA Crossover</option>
              <option value="rsi_oversold">RSI Oversold</option>
              <option value="buy_and_hold">Buy & Hold</option>
            </select>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="bg-bg-primary border border-border rounded px-3 py-2 text-sm" />
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="bg-bg-primary border border-border rounded px-3 py-2 text-sm" />
            <button onClick={runBacktest} className="bg-accent-green text-bg-primary px-4 py-2 rounded font-semibold">
              {btLoading ? "Running..." : "Run Backtest"}
            </button>
          </div>
          {btResult && !btResult.error && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <Metric label="Return" value={`${btResult.total_return_pct}%`} />
              <Metric label="Benchmark" value={`${btResult.benchmark_return_pct}%`} />
              <Metric label="Alpha" value={`${btResult.alpha}%`} />
              <Metric label="Sharpe" value={`${btResult.sharpe_ratio}`} />
            </div>
          )}
          {btResult?.error && <p className="text-accent-red text-sm">{btResult.error}</p>}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-bg-primary border border-border rounded-md p-3">
      <div className="text-text-muted text-xs">{label}</div>
      <div className="text-text-primary font-mono font-semibold">{value}</div>
    </div>
  );
}
