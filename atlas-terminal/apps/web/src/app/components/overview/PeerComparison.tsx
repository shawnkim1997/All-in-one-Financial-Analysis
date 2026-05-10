"use client";

export interface PeerItem {
  ticker: string;
  name: string;
  market_cap: number | null;
  pe: number | null;
  pb: number | null;
  ps: number | null;
  ev_ebitda: number | null;
  roic?: number | null;
  gross_margin?: number | null;
  rev_growth?: number | null;
}

export interface PeerComparisonData {
  ticker: string;
  primary?: string;
  sector: string;
  industry: string;
  metrics?: string[];
  matrix?: PeerItem[];
  averages: {
    pe: number | null;
    pb: number | null;
    ps: number | null;
    ev_ebitda: number | null;
    roic?: number | null;
    gross_margin?: number | null;
    rev_growth?: number | null;
  };
  peers: PeerItem[];
}

type MetricKey = "pe" | "ev_ebitda" | "roic" | "gross_margin" | "rev_growth";

const METRIC_LABELS: Record<MetricKey, string> = {
  pe: "P/E",
  ev_ebitda: "EV/EBITDA",
  roic: "ROIC",
  gross_margin: "Gross Margin",
  rev_growth: "Rev Growth",
};

const LOWER_IS_BETTER = new Set<MetricKey>(["pe", "ev_ebitda"]);
const ZERO_DECIMAL_CURRENCIES = new Set(["KRW", "JPY"]);
const CURRENCY_LOCALES: Record<string, string> = {
  KRW: "ko-KR",
  JPY: "ja-JP",
  USD: "en-US",
};

function currencyForTicker(ticker: string): string {
  const normalized = ticker.toUpperCase();
  if (normalized.endsWith(".KS") || normalized.endsWith(".KQ")) return "KRW";
  if (normalized.endsWith(".T")) return "JPY";
  return "USD";
}

function formatMarketCap(value: number | null | undefined, ticker: string): string {
  if (value == null) return "—";
  const currency = currencyForTicker(ticker);
  return new Intl.NumberFormat(CURRENCY_LOCALES[currency] || "en-US", {
    style: "currency",
    currency,
    notation: "compact",
    minimumFractionDigits: 0,
    maximumFractionDigits: ZERO_DECIMAL_CURRENCIES.has(currency) ? 1 : 2,
  }).format(value);
}

function formatValue(value: number | null | undefined, type: "multiple" | "marketCap" | "percent" = "multiple"): string {
  if (value == null) return "—";
  if (type === "marketCap") {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
    return `$${value.toFixed(0)}`;
  }
  if (type === "percent") {
    const normalized = Math.abs(value) <= 1 ? value * 100 : value;
    return `${normalized.toFixed(1)}%`;
  }
  return `${value.toFixed(1)}x`;
}

function metricType(metric: MetricKey): "multiple" | "percent" {
  return metric === "pe" || metric === "ev_ebitda" ? "multiple" : "percent";
}

function percentileScore(metric: MetricKey, value: number | null | undefined, rows: PeerItem[]): number | null {
  if (value == null) return null;
  const values = rows
    .map((row) => row[metric])
    .filter((candidate): candidate is number => typeof candidate === "number" && Number.isFinite(candidate));
  if (values.length <= 1) return 50;
  const sorted = [...values].sort((a, b) => a - b);
  const rank = sorted.filter((candidate) => candidate < value).length / (values.length - 1);
  const score = LOWER_IS_BETTER.has(metric) ? (1 - rank) * 100 : rank * 100;
  return Math.max(0, Math.min(100, score));
}

function metricCellClass(score: number | null, isPrimary: boolean): string {
  if (score == null) return isPrimary ? "text-white/60" : "text-text-muted";
  if (score >= 80) return isPrimary ? "bg-brand-gold text-brand-navy" : "bg-brand-gold/15 text-brand-navy";
  if (score <= 20) return isPrimary ? "bg-fin-negative text-white" : "bg-fin-negative/10 text-fin-negative";
  return isPrimary ? "text-white" : "text-text-primary";
}

export function PeerComparison({
  currentTicker,
  data,
}: {
  currentTicker: string;
  data: PeerComparisonData | null;
}) {
  const rows = data?.matrix?.length ? data.matrix : data?.peers ?? [];

  if (!data || rows.length === 0) {
    return (
      <div className="atlas-card mt-6 p-5">
        <h3 className="font-serif text-lg font-bold text-brand-navy mb-2">Peer Comparison</h3>
        <div className="text-text-muted text-sm">Peer comparison data is not available for this ticker.</div>
      </div>
    );
  }

  const metrics = ((data.metrics?.length ? data.metrics : ["pe", "ev_ebitda", "roic", "gross_margin", "rev_growth"])
    .filter((metric): metric is MetricKey => metric in METRIC_LABELS));

  return (
    <div className="atlas-table-shell mt-6">
      <div className="flex items-end justify-between gap-4 mb-4">
        <div className="px-5 pt-5">
          <h3 className="font-serif text-lg font-bold text-brand-navy">Peer Comparison</h3>
          <div className="text-text-muted text-xs mt-1">{data.industry || data.sector || "Industry peers"}</div>
        </div>
        <div className="hidden px-5 pt-5 text-[11px] text-text-muted font-mono gap-3 lg:flex">
          <span>Avg P/E {formatValue(data.averages.pe)}</span>
          <span>Avg EV/EBITDA {formatValue(data.averages.ev_ebitda)}</span>
          {data.averages.gross_margin != null && <span>Avg GM {formatValue(data.averages.gross_margin, "percent")}</span>}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-sm">
          <thead className="bg-surface-sunken">
            <tr className="border-y border-border-strong text-left text-[11px] uppercase tracking-[0.12em] text-brand-navy">
              <th className="py-3 px-5 font-semibold">Ticker</th>
              <th className="py-3 pr-3 font-semibold">Company</th>
              <th className="py-3 pr-3 text-right font-semibold">Market Cap</th>
              {metrics.map((metric) => (
                <th key={metric} className="py-3 pr-3 text-right font-semibold">{METRIC_LABELS[metric]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((peer) => {
              const isCurrent = peer.ticker.toUpperCase() === currentTicker.toUpperCase();
              return (
                <tr
                  key={peer.ticker}
                  className={`border-b border-border/60 ${isCurrent ? "bg-brand-navy text-white" : "hover:bg-surface-sunken"}`}
                >
                  <td className={`py-3 px-5 font-mono font-semibold ${isCurrent ? "text-brand-gold" : "text-brand-navy"}`}>
                    {peer.ticker}
                  </td>
                  <td className={`py-3 pr-3 ${isCurrent ? "text-white/80" : "text-text-secondary"}`}>{peer.name}</td>
                  <td className={`py-3 pr-3 font-mono text-right tabular-nums ${isCurrent ? "text-white" : "text-text-primary"}`}>
                    {formatMarketCap(peer.market_cap, peer.ticker)}
                  </td>
                  {metrics.map((metric) => {
                    const value = peer[metric];
                    const score = percentileScore(metric, value, rows);
                    return (
                      <td key={metric} className="py-2 pr-3 text-right">
                        <span className={`inline-flex min-w-[76px] justify-end rounded px-2 py-1 font-mono tabular-nums ${metricCellClass(score, isCurrent)}`}>
                          {formatValue(value, metricType(metric))}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="px-5 py-3 text-[11px] text-text-muted">
        Gold marks best-in-group percentile; red marks weakest percentile. For valuation multiples, lower is better.
      </div>
    </div>
  );
}
