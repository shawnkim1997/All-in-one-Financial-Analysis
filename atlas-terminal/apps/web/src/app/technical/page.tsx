"use client";
import { useEffect, useState, useRef } from "react";
import { ChartContainer } from "../components/ui/ChartContainer";
import { LoadingPulse } from "../components/ui/LoadingPulse";
import { SectionHeading } from "../components/ui/SectionHeading";
import { StatCard } from "../components/ui/StatCard";
import { chartPalette, lightweightTheme } from "../lib/chart-theme";
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
  const { ticker, initialized } = useTicker();
  const [indicators, setIndicators] = useState<Indicators | null>(null);
  const [bars, setBars] = useState<ChartBar[]>([]);
  const [fib, setFib] = useState<FibLevels | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("6mo");
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!initialized) return;
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
  }, [ticker, period, initialized]);

  // Render chart using lightweight-charts v5
  useEffect(() => {
    if (!chartRef.current || bars.length === 0) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let chart: any = null;
    let resizeHandler: (() => void) | null = null;
    (async () => {
      try {
        const lc = await import("lightweight-charts");
        chartRef.current!.innerHTML = "";
        chart = lc.createChart(chartRef.current!, {
          width: chartRef.current!.clientWidth,
          height: 400,
          ...lightweightTheme,
          crosshair: { mode: 0 },
        });

        // v5 API: use addSeries with series type constructor
        const CandlestickSeries = (lc as Record<string, unknown>).CandlestickSeries;
        const HistogramSeries = (lc as Record<string, unknown>).HistogramSeries;

        if (CandlestickSeries && typeof chart.addSeries === "function") {
          // v5 path
          const candlestickSeries = chart.addSeries(CandlestickSeries, {
            upColor: chartPalette.green,
            downColor: chartPalette.red,
            borderUpColor: chartPalette.green,
            borderDownColor: chartPalette.red,
            wickUpColor: chartPalette.green,
            wickDownColor: chartPalette.red,
          });
          candlestickSeries.setData(bars);

          const volumeSeries = chart.addSeries(HistogramSeries, {
            priceFormat: { type: "volume" },
            priceScaleId: "volume",
          });
          volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 },
          });
          volumeSeries.setData(
            bars.map((b: ChartBar) => ({
              time: b.time,
              value: b.volume,
              color: b.close >= b.open ? "rgba(45,139,94,0.24)" : "rgba(192,57,43,0.24)",
            }))
          );
        } else if (typeof chart.addCandlestickSeries === "function") {
          // v4 fallback
          const candlestickSeries = chart.addCandlestickSeries({
            upColor: chartPalette.green,
            downColor: chartPalette.red,
            borderUpColor: chartPalette.green,
            borderDownColor: chartPalette.red,
            wickUpColor: chartPalette.green,
            wickDownColor: chartPalette.red,
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
            bars.map((b: ChartBar) => ({
              time: b.time,
              value: b.volume,
              color: b.close >= b.open ? "rgba(45,139,94,0.24)" : "rgba(192,57,43,0.24)",
            }))
          );
        }

        chart.timeScale().fitContent();

        resizeHandler = () => {
          if (chartRef.current) chart.applyOptions({ width: chartRef.current.clientWidth });
        };
        window.addEventListener("resize", resizeHandler);
      } catch (e) {
        console.error("lightweight-charts render error:", e);
      }
    })();
    return () => {
      if (resizeHandler) window.removeEventListener("resize", resizeHandler);
      if (chart) chart.remove();
    };
  }, [bars]);

  if (loading) return <LoadingPulse label="Loading technical data…" />;

  const macdSignal = indicators?.macd
    ? indicators.macd.histogram > 0 ? "Bullish" : "Bearish"
    : "—";

  return (
    <div className="atlas-page">
      <SectionHeading level={1}>{ticker} Technical Analysis</SectionHeading>

      {/* Period Selector */}
      <div className="flex gap-2 mb-4">
        {["1mo", "3mo", "6mo", "1y", "2y"].map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`rounded-md px-3 py-1.5 text-sm font-mono transition-all ${
              period === p
                ? "bg-brand-navy text-white font-semibold"
                : "bg-surface-raised text-text-secondary shadow-card hover:bg-surface-sunken"
            }`}
          >
            {p.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Chart */}
      <ChartContainer title="Candlestick Chart" subtitle="OHLC with volume profile." className="mb-6">
        <div ref={chartRef} className="w-full" style={{ minHeight: 400 }} />
      </ChartContainer>

      {/* Indicator Cards */}
      {indicators && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          <StatCard label="Current Price" value={`$${indicators.current_price?.toFixed(2)}`} />
          <StatCard
            label="RSI (14)"
            value={indicators.rsi_14}
            tone={indicators.rsi_14 > 70 ? "negative" : indicators.rsi_14 < 30 ? "positive" : "default"}
            detail={indicators.rsi_14 > 70 ? "Overbought" : indicators.rsi_14 < 30 ? "Oversold" : "Neutral"}
          />
          <StatCard
            label="MACD Signal"
            value={macdSignal}
            tone={indicators.macd.histogram > 0 ? "positive" : "negative"}
            detail={`H: ${indicators.macd.histogram.toFixed(4)}`}
          />
          <StatCard label="ATR (14)" value={indicators.atr_14} detail="Volatility" />
        </div>
      )}

      {/* Moving Averages & Bollinger */}
      {indicators && (
        <div className="grid grid-cols-2 gap-4 mb-6">
          <ChartContainer title="Moving Averages">
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
                      ma.signal === true ? "bg-fin-positive/15 text-fin-positive" :
                      ma.signal === false ? "bg-fin-negative/15 text-fin-negative" : "bg-surface-sunken text-text-muted"
                    }`}>
                      {ma.signal === true ? "ABOVE" : ma.signal === false ? "BELOW" : "N/A"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </ChartContainer>

          <ChartContainer title="Bollinger Bands" subtitle="20-period, 2 standard deviations.">
            <h3 className="text-text-secondary text-sm font-semibold mb-3">Bollinger Bands (20, 2)</h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">Upper Band</span>
                <span className="font-mono text-fin-negative">${indicators.bollinger_bands.upper.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">Middle Band</span>
                <span className="font-mono text-brand-gold">${indicators.bollinger_bands.middle.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text-muted">Lower Band</span>
                <span className="font-mono text-fin-positive">${indicators.bollinger_bands.lower.toFixed(2)}</span>
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
                <span className={`font-mono ${indicators.macd.histogram > 0 ? "text-fin-positive" : "text-fin-negative"}`}>
                  {indicators.macd.histogram.toFixed(4)}
                </span>
              </div>
            </div>
          </ChartContainer>
        </div>
      )}

      {/* Fibonacci Levels */}
      {fib && (
        <ChartContainer title="Fibonacci Retracement">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">Fibonacci Retracement</h3>
          <div className="grid grid-cols-7 gap-3">
            {Object.entries(fib.levels).map(([level, price]) => {
              const isNear = Math.abs(price - fib.current_price) / fib.current_price < 0.02;
              return (
                <div key={level} className={`rounded-lg p-3 text-center ${isNear ? "border border-brand-gold bg-brand-gold/10" : "bg-surface-sunken"}`}>
                  <div className="text-text-muted text-xs mb-1">{level}</div>
                  <div className={`font-mono text-sm font-semibold ${isNear ? "text-brand-navy" : "text-text-primary"}`}>
                    ${price.toFixed(2)}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 text-text-muted text-xs font-mono">
            52W Range: ${fib.low_52w.toFixed(2)} — ${fib.high_52w.toFixed(2)} | Current: ${fib.current_price.toFixed(2)}
          </div>
        </ChartContainer>
      )}
    </div>
  );
}
