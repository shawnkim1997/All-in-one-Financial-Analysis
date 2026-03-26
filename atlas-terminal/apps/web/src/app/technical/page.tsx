"use client";
import { useEffect, useState, useRef } from "react";
import { useTicker } from "../lib/use-ticker";

interface Indicators {
  ticker: string;
  current_price: number;
  rsi_14: number;
  sma: { sma_20: number; sma_50: number; sma_200: number | null };
  ema: { ema_12: number; ema_26: number };
  macd: { macd: number; signal: number; histogram: number };
  bollinger_bands: { upper: number; middle: number; lower: number };
  atr_14: number;
}

interface ChartBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface FibLevels {
  ticker: string;
  high_52w: number;
  low_52w: number;
  current_price: number;
  levels: Record<string, number>;
}

export default function TechnicalPage() {
  const { ticker } = useTicker();
  const [indicators, setIndicators] = useState<Indicators | null>(null);
  const [bars, setBars] = useState<ChartBar[]>([]);
  const [fib, setFib] = useState<FibLevels | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("6mo");
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch(`/api/technical/${ticker}/indicators`).then((r) => r.ok ? r.json() : null),
      fetch(`/api/technical/${ticker}/chart-data?period=${period}`).then((r) => r.ok ? r.json() : null),
      fetch(`/api/technical/${ticker}/fibonacci`).then((r) => r.ok ? r.json() : null),
    ]).then(([ind, chart, fibData]) => {
      setIndicators(ind);
      setBars(chart?.bars || []);
      setFib(fibData);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [ticker, period]);

  // Render chart using lightweight-charts
  useEffect(() => {
    if (!chartRef.current || bars.length === 0) return;
    // v5 typings omit series helpers; runtime still exposes addCandlestickSeries etc.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let chart: any = null;
    (async () => {
      try {
        const { createChart } = await import("lightweight-charts");
        chartRef.current!.innerHTML = "";
        chart = createChart(chartRef.current!, {
          width: chartRef.current!.clientWidth,
          height: 400,
          layout: { background: { color: "#1A1A26" }, textColor: "#9CA3AF" },
          grid: { vertLines: { color: "#2A2A3A" }, horzLines: { color: "#2A2A3A" } },
          crosshair: { mode: 0 },
          timeScale: { borderColor: "#2A2A3A" },
        });
        const candlestickSeries = chart.addCandlestickSeries({
          upColor: "#00D4AA",
          downColor: "#FF4757",
          borderUpColor: "#00D4AA",
          borderDownColor: "#FF4757",
          wickUpColor: "#00D4AA",
          wickDownColor: "#FF4757",
        });
        candlestickSeries.setData(bars);

        const volumeSeries = chart.addHistogramSeries({
          priceFormat: { type: "volume" },
          priceScaleId: "",
        });
        volumeSeries.priceScale().applyOptions({
          scaleMargins: { top: 0.8, bottom: 0 },
        });
        volumeSeries.setData(
          bars.map((b) => ({
            time: b.time,
            value: b.volume,
            color: b.close >= b.open ? "rgba(0,212,170,0.3)" : "rgba(255,71,87,0.3)",
          }))
        );

        chart.timeScale().fitContent();

        const handleResize = () => {
          if (chartRef.current) chart.applyOptions({ width: chartRef.current.clientWidth });
        };
        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
      } catch {
        // lightweight-charts not available
      }
    })();
    return () => { if (chart) chart.remove(); };
  }, [bars]);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-accent-green animate-pulse font-mono">Loading...</div></div>;

  const rsiColor = indicators?.rsi_14
    ? indicators.rsi_14 > 70 ? "text-accent-red" : indicators.rsi_14 < 30 ? "text-accent-green" : "text-text-primary"
    : "text-text-primary";

  const macdSignal = indicators?.macd
    ? indicators.macd.histogram > 0 ? "Bullish" : "Bearish"
    : "—";

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">
        <span className="text-accent-green">{ticker}</span> Technical Analysis
      </h1>

      {/* Period Selector */}
      <div className="flex gap-2 mb-4">
        {["1mo", "3mo", "6mo", "1y", "2y"].map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3 py-1.5 rounded-md text-sm font-mono transition-all ${
              period === p
                ? "bg-accent-green text-bg-primary font-semibold"
                : "bg-bg-card text-text-secondary hover:bg-bg-card/80"
            }`}
          >
            {p.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="bg-bg-card border border-border rounded-lg p-4 mb-6">
        <div ref={chartRef} className="w-full" style={{ minHeight: 400 }} />
      </div>

      {/* Indicator Cards */}
      {indicators && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          <div className="bg-bg-card border border-border rounded-lg p-4">
            <div className="text-text-muted text-xs mb-1">Current Price</div>
            <div className="text-text-primary font-mono font-bold text-xl">${indicators.current_price?.toFixed(2)}</div>
          </div>
          <div className="bg-bg-card border border-border rounded-lg p-4">
            <div className="text-text-muted text-xs mb-1">RSI (14)</div>
            <div className={`font-mono font-bold text-xl ${rsiColor}`}>{indicators.rsi_14}</div>
            <div className="text-text-muted text-xs mt-1">
              {indicators.rsi_14 > 70 ? "Overbought" : indicators.rsi_14 < 30 ? "Oversold" : "Neutral"}
            </div>
          </div>
          <div className="bg-bg-card border border-border rounded-lg p-4">
            <div className="text-text-muted text-xs mb-1">MACD Signal</div>
            <div className={`font-mono font-bold text-xl ${indicators.macd.histogram > 0 ? "text-accent-green" : "text-accent-red"}`}>
              {macdSignal}
            </div>
            <div className="text-text-muted text-xs mt-1 font-mono">H: {indicators.macd.histogram.toFixed(4)}</div>
          </div>
          <div className="bg-bg-card border border-border rounded-lg p-4">
            <div className="text-text-muted text-xs mb-1">ATR (14)</div>
            <div className="text-text-primary font-mono font-bold text-xl">{indicators.atr_14}</div>
            <div className="text-text-muted text-xs mt-1">Volatility</div>
          </div>
        </div>
      )}

      {/* Moving Averages & Bollinger */}
      {indicators && (
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-bg-card border border-border rounded-lg p-5">
            <h3 className="text-text-secondary text-sm font-semibold mb-3">Moving Averages</h3>
            <div className="space-y-2">
              {[
                { label: "SMA 20", value: indicators.sma.sma_20, signal: indicators.current_price > indicators.sma.sma_20 },
                { label: "SMA 50", value: indicators.sma.sma_50, signal: indicators.current_price > indicators.sma.sma_50 },
                { label: "SMA 200", value: indicators.sma.sma_200, signal: indicators.sma.sma_200 ? indicators.current_price > indicators.sma.sma_200 : null },
                { label: "EMA 12", value: indicators.ema.ema_12, signal: indicators.current_price > indicators.ema.ema_12 },
                { label: "EMA 26", value: indicators.ema.ema_26, signal: indicators.current_price > indicators.ema.ema_26 },
              ].map((ma) => (
                <div key={ma.label} className="flex justify-between items-center text-sm">
                  <span className="text-text-muted">{ma.label}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-text-primary font-mono">{ma.value != null ? `$${ma.value.toFixed(2)}` : "—"}</span>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                      ma.signal === true ? "bg-accent-green/20 text-accent-green" :
                      ma.signal === false ? "bg-accent-red/20 text-accent-red" : "bg-bg-primary text-text-muted"
                    }`}>
                      {ma.signal === true ? "ABOVE" : ma.signal === false ? "BELOW" : "N/A"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-bg-card border border-border rounded-lg p-5">
            <h3 className="text-text-secondary text-sm font-semibold mb-3">Bollinger Bands (20, 2)</h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">Upper Band</span>
                <span className="text-accent-red font-mono">${indicators.bollinger_bands.upper.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">Middle Band</span>
                <span className="text-accent-yellow font-mono">${indicators.bollinger_bands.middle.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">Lower Band</span>
                <span className="text-accent-green font-mono">${indicators.bollinger_bands.lower.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm border-t border-border pt-3">
                <span className="text-text-muted">BB Width</span>
                <span className="text-text-primary font-mono">
                  {((indicators.bollinger_bands.upper - indicators.bollinger_bands.lower) / indicators.bollinger_bands.middle * 100).toFixed(2)}%
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">%B Position</span>
                <span className="text-text-primary font-mono">
                  {((indicators.current_price - indicators.bollinger_bands.lower) / (indicators.bollinger_bands.upper - indicators.bollinger_bands.lower) * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* MACD Detail */}
            <h3 className="text-text-secondary text-sm font-semibold mb-3 mt-5">MACD (12, 26, 9)</h3>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">MACD Line</span>
                <span className="text-text-primary font-mono">{indicators.macd.macd.toFixed(4)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">Signal Line</span>
                <span className="text-text-primary font-mono">{indicators.macd.signal.toFixed(4)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">Histogram</span>
                <span className={`font-mono ${indicators.macd.histogram > 0 ? "text-accent-green" : "text-accent-red"}`}>
                  {indicators.macd.histogram.toFixed(4)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Fibonacci Levels */}
      {fib && (
        <div className="bg-bg-card border border-border rounded-lg p-5">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">Fibonacci Retracement</h3>
          <div className="grid grid-cols-7 gap-3">
            {Object.entries(fib.levels).map(([level, price]) => {
              const isNear = Math.abs(price - fib.current_price) / fib.current_price < 0.02;
              return (
                <div key={level} className={`text-center p-3 rounded-lg ${isNear ? "bg-accent-green/10 border border-accent-green" : "bg-bg-primary"}`}>
                  <div className="text-text-muted text-xs mb-1">{level}</div>
                  <div className={`font-mono text-sm font-semibold ${isNear ? "text-accent-green" : "text-text-primary"}`}>
                    ${price.toFixed(2)}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 text-text-muted text-xs font-mono">
            52W Range: ${fib.low_52w.toFixed(2)} — ${fib.high_52w.toFixed(2)} | Current: ${fib.current_price.toFixed(2)}
          </div>
        </div>
      )}
    </div>
  );
}
