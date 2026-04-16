"use client";

import { useEffect, useRef, useState } from "react";
import { chartPalette, lightweightTheme } from "../lib/chart-theme";

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
  max_drawdown_pct?: number;
  equity_curve?: number[];
  benchmark_curve?: number[];
  dates?: string[];
  benchmark_ticker?: string;
}

interface PortfolioResult {
  error?: string;
  total_return_pct?: number;
  benchmark_return_pct?: number;
  alpha?: number;
  sharpe_ratio?: number;
  sortino_ratio?: number;
  max_drawdown_pct?: number;
  contributions?: Record<string, number>;
  equity_curve?: number[];
  benchmark_curve?: number[];
  dates?: string[];
  benchmark_ticker?: string;
}

export default function ScreenerPage() {
  const [tab, setTab] = useState<"screener" | "backtest" | "portfolio">("screener");
  const [rows, setRows] = useState<ScreenerRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [peMax, setPeMax] = useState("25");
  const [sector, setSector] = useState("");
  const [divMin, setDivMin] = useState("");

  const [btTicker, setBtTicker] = useState("AAPL");
  const [btBenchmark, setBtBenchmark] = useState("SPY");
  const [rebalanceMonths, setRebalanceMonths] = useState("");
  const [strategy, setStrategy] = useState("sma_crossover");
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2026-03-01");
  const [btResult, setBtResult] = useState<BacktestResult | null>(null);
  const [btLoading, setBtLoading] = useState(false);
  const chartRef = useRef<HTMLDivElement>(null);

  // Portfolio backtest state
  const [ptTickers, setPtTickers] = useState("AAPL, MSFT, GOOG");
  const [ptWeights, setPtWeights] = useState("40, 30, 30");
  const [ptBenchmark, setPtBenchmark] = useState("SPY");
  const [ptRebal, setPtRebal] = useState("3");
  const [ptStart, setPtStart] = useState("2021-01-01");
  const [ptEnd, setPtEnd] = useState("2026-01-01");
  const [ptResult, setPtResult] = useState<PortfolioResult | null>(null);
  const [ptLoading, setPtLoading] = useState(false);
  const ptChartRef = useRef<HTMLDivElement>(null);

  async function runPortfolioBacktest() {
    setPtLoading(true);
    try {
      const tickers = ptTickers.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean);
      const weights = ptWeights.split(",").map((s) => parseFloat(s.trim())).filter((n) => !isNaN(n));
      const res = await fetch("/api/screener/portfolio-backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tickers,
          weights: weights.length === tickers.length ? weights : undefined,
          start_date: ptStart,
          end_date: ptEnd,
          rebalance_months: parseInt(ptRebal, 10) || 3,
          benchmark_ticker: ptBenchmark || "SPY",
        }),
      });
      setPtResult(await res.json());
    } catch {
      setPtResult(null);
    } finally {
      setPtLoading(false);
    }
  }

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
      const body: Record<string, unknown> = {
        ticker: btTicker,
        strategy,
        start_date: startDate,
        end_date: endDate,
        benchmark_ticker: btBenchmark || "SPY",
      };
      const rm = parseInt(rebalanceMonths, 10);
      if (!Number.isNaN(rm) && rm > 0) body.rebalance_months = rm;

      const res = await fetch("/api/screener/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setBtResult(await res.json());
    } catch {
      setBtResult(null);
    } finally {
      setBtLoading(false);
    }
  }

  useEffect(() => {
    if (!btResult?.equity_curve || !btResult.benchmark_curve || !btResult.dates || !chartRef.current) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let chart: any = null;
    const el = chartRef.current;
    let onResize: (() => void) | null = null;

    import("lightweight-charts")
      .then(({ createChart }) => {
        if (!el) return;
        el.innerHTML = "";
        chart = createChart(el, {
          width: el.clientWidth,
          height: 320,
          ...lightweightTheme,
          crosshair: { mode: 0 },
        });
        const strat = chart.addLineSeries({ color: chartPalette.navy, lineWidth: 2 });
        strat.setData(
          btResult.dates!.map((d, i) => ({
            time: d as string & { __brand?: "Time" },
            value: btResult.equity_curve![i],
          }))
        );
        const bench = chart.addLineSeries({ color: chartPalette.blue, lineWidth: 2 });
        bench.setData(
          btResult.dates!.map((d, i) => ({
            time: d as string & { __brand?: "Time" },
            value: btResult.benchmark_curve![i],
          }))
        );
        chart.timeScale().fitContent();
        onResize = () => {
          if (el && chart) chart.applyOptions({ width: el.clientWidth });
        };
        window.addEventListener("resize", onResize);
      })
      .catch(() => {});

    return () => {
      if (onResize) window.removeEventListener("resize", onResize);
      if (chart) chart.remove();
    };
  }, [btResult]);

  useEffect(() => {
    if (!ptResult?.equity_curve || !ptResult.benchmark_curve || !ptResult.dates || !ptChartRef.current) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let chart: any = null;
    const el = ptChartRef.current;
    let onResize: (() => void) | null = null;

    import("lightweight-charts")
      .then(({ createChart }) => {
        if (!el) return;
        el.innerHTML = "";
        chart = createChart(el, {
          width: el.clientWidth,
          height: 320,
          ...lightweightTheme,
          crosshair: { mode: 0 },
        });
        const port = chart.addLineSeries({ color: chartPalette.navy, lineWidth: 2 });
        port.setData(
          ptResult.dates!.map((d, i) => ({
            time: d as string & { __brand?: "Time" },
            value: ptResult.equity_curve![i],
          }))
        );
        const bench = chart.addLineSeries({ color: chartPalette.blue, lineWidth: 2 });
        bench.setData(
          ptResult.dates!.map((d, i) => ({
            time: d as string & { __brand?: "Time" },
            value: ptResult.benchmark_curve![i],
          }))
        );
        chart.timeScale().fitContent();
        onResize = () => {
          if (el && chart) chart.applyOptions({ width: el.clientWidth });
        };
        window.addEventListener("resize", onResize);
      })
      .catch(() => {});

    return () => {
      if (onResize) window.removeEventListener("resize", onResize);
      if (chart) chart.remove();
    };
  }, [ptResult]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Stock Screener</h1>

      <div className="flex gap-1 mb-4 bg-bg-card rounded-lg p-1 w-fit">
        <button
          type="button"
          onClick={() => setTab("screener")}
          className={`px-4 py-2 rounded-md text-sm font-medium ${tab === "screener" ? "bg-accent-green text-bg-primary" : "text-text-secondary"}`}
        >
          Screener
        </button>
        <button
          type="button"
          onClick={() => setTab("backtest")}
          className={`px-4 py-2 rounded-md text-sm font-medium ${tab === "backtest" ? "bg-accent-green text-bg-primary" : "text-text-secondary"}`}
        >
          Backtest
        </button>
        <button
          type="button"
          onClick={() => setTab("portfolio")}
          className={`px-4 py-2 rounded-md text-sm font-medium ${tab === "portfolio" ? "bg-accent-green text-bg-primary" : "text-text-secondary"}`}
        >
          Portfolio
        </button>
      </div>

      {tab === "screener" ? (
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <div className="flex flex-wrap gap-2 mb-3">

            <input
              value={peMax}
              onChange={(e) => setPeMax(e.target.value)}
              placeholder="P/E < 25"
              className="bg-bg-primary border border-border rounded px-3 py-2 text-sm"
            />
            <input
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              placeholder="Sector (optional)"
              className="bg-bg-primary border border-border rounded px-3 py-2 text-sm"
            />
            <input
              value={divMin}
              onChange={(e) => setDivMin(e.target.value)}
              placeholder="Div Yield > %"
              className="bg-bg-primary border border-border rounded px-3 py-2 text-sm"
            />
            <button type="button" onClick={runScreener} className="bg-accent-green text-bg-primary px-4 py-2 rounded font-semibold">
              {loading ? "Running..." : "Run Screener"}
            </button>
          </div>
          <div className="overflow-auto border border-border rounded-md">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  {["Ticker", "Name", "Sector", "Price", "P/E", "MCap", "Change"].map((h) => (
                    <th key={h} className="text-left px-3 py-2 text-text-muted">
                      {h}
                    </th>
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
                    <td className={`px-3 py-2 font-mono ${(r.change_pct || 0) >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                      {r.change_pct != null ? `${r.change_pct >= 0 ? "+" : ""}${r.change_pct.toFixed(2)}%` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : tab === "backtest" ? (
        <div className="bg-bg-card border border-border rounded-lg p-4 space-y-4">
          <div className="flex flex-wrap gap-2 mb-3">
            <input
              value={btTicker}
              onChange={(e) => setBtTicker(e.target.value.toUpperCase())}
              placeholder="Ticker"
              className="bg-bg-primary border border-border rounded px-3 py-2 text-sm"
            />
            <input
              value={btBenchmark}
              onChange={(e) => setBtBenchmark(e.target.value.toUpperCase())}
              placeholder="Benchmark (e.g. SPY)"
              className="bg-bg-primary border border-border rounded px-3 py-2 text-sm w-36"
            />
            <input
              value={rebalanceMonths}
              onChange={(e) => setRebalanceMonths(e.target.value)}
              placeholder="Rebal. months (opt)"
              className="bg-bg-primary border border-border rounded px-3 py-2 text-sm w-40"
            />
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)} className="bg-bg-primary border border-border rounded px-3 py-2 text-sm">
              <option value="sma_crossover">SMA Crossover</option>
              <option value="rsi_oversold">RSI Oversold</option>
              <option value="buy_and_hold">Buy & Hold</option>
            </select>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="bg-bg-primary border border-border rounded px-3 py-2 text-sm" />
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="bg-bg-primary border border-border rounded px-3 py-2 text-sm" />
            <button type="button" onClick={runBacktest} className="bg-accent-green text-bg-primary px-4 py-2 rounded font-semibold">
              {btLoading ? "Running..." : "Run Backtest"}
            </button>
          </div>
          <p className="text-text-muted text-xs">
            Strategy (green) vs benchmark buy‑hold (blue). Optional rebalance: hold signal fixed for N calendar months, then refresh.
          </p>
          {btResult && !btResult.error && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                <Metric label="Return" value={`${btResult.total_return_pct}%`} />
                <Metric label={`Bench (${btResult.benchmark_ticker || btBenchmark})`} value={`${btResult.benchmark_return_pct}%`} />
                <Metric label="Alpha" value={`${btResult.alpha}%`} />
                <Metric label="Sharpe" value={`${btResult.sharpe_ratio}`} />
                <Metric label="Max DD" value={`${btResult.max_drawdown_pct}%`} />
              </div>
              <div ref={chartRef} className="w-full min-h-[320px] rounded-lg border border-border overflow-hidden" />
            </>
          )}
          {btResult?.error && <p className="text-accent-red text-sm">{btResult.error}</p>}
        </div>
      ) : tab === "portfolio" ? (
        <div className="bg-bg-card border border-border rounded-lg p-4 space-y-4">
          <div className="flex flex-wrap gap-2 mb-3">
            <input
              value={ptTickers}
              onChange={(e) => setPtTickers(e.target.value.toUpperCase())}
              placeholder="Tickers (comma sep)"
              className="bg-bg-primary border border-border rounded px-3 py-2 text-sm flex-1 min-w-[200px]"
            />
            <input
              value={ptWeights}
              onChange={(e) => setPtWeights(e.target.value)}
              placeholder="Weights (e.g. 40, 30, 30)"
              className="bg-bg-primary border border-border rounded px-3 py-2 text-sm w-48"
            />
            <input
              value={ptBenchmark}
              onChange={(e) => setPtBenchmark(e.target.value.toUpperCase())}
              placeholder="Benchmark"
              className="bg-bg-primary border border-border rounded px-3 py-2 text-sm w-28"
            />
            <input
              value={ptRebal}
              onChange={(e) => setPtRebal(e.target.value)}
              placeholder="Rebal months"
              className="bg-bg-primary border border-border rounded px-3 py-2 text-sm w-28"
            />
            <input type="date" value={ptStart} onChange={(e) => setPtStart(e.target.value)} className="bg-bg-primary border border-border rounded px-3 py-2 text-sm" />
            <input type="date" value={ptEnd} onChange={(e) => setPtEnd(e.target.value)} className="bg-bg-primary border border-border rounded px-3 py-2 text-sm" />
            <button type="button" onClick={runPortfolioBacktest} className="bg-accent-green text-bg-primary px-4 py-2 rounded font-semibold">
              {ptLoading ? "Running..." : "Run Portfolio"}
            </button>
          </div>
          <p className="text-text-muted text-xs">
            Multi-asset portfolio (green) vs benchmark (blue). Weights are rebalanced every N months.
          </p>
          {ptResult && !ptResult.error && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
                <Metric label="Return" value={`${ptResult.total_return_pct}%`} />
                <Metric label={`Bench (${ptResult.benchmark_ticker || ptBenchmark})`} value={`${ptResult.benchmark_return_pct}%`} />
                <Metric label="Alpha" value={`${ptResult.alpha}%`} />
                <Metric label="Sharpe" value={`${ptResult.sharpe_ratio}`} />
                <Metric label="Sortino" value={`${ptResult.sortino_ratio}`} />
                <Metric label="Max DD" value={`${ptResult.max_drawdown_pct}%`} />
              </div>
              {ptResult.contributions && (
                <div className="bg-bg-primary border border-border rounded-md p-3">
                  <div className="text-text-muted text-xs mb-2">Contribution by Ticker</div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(ptResult.contributions).map(([t, c]) => (
                      <div key={t} className="text-xs font-mono px-2 py-1 rounded border border-border">
                        <span className="text-accent-green">{t}</span>{" "}
                        <span className={c >= 0 ? "text-accent-green" : "text-accent-red"}>
                          {c >= 0 ? "+" : ""}{c}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div ref={ptChartRef} className="w-full min-h-[320px] rounded-lg border border-border overflow-hidden" />
            </>
          )}
          {ptResult?.error && <p className="text-accent-red text-sm">{ptResult.error}</p>}
        </div>
      ) : null}
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
