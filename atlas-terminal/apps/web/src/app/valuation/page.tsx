"use client";
import { useEffect, useState } from "react";
import { ErrorBanner } from "../components/ui/ErrorBanner";
import { LoadingPulse } from "../components/ui/LoadingPulse";
import { SectionHeading } from "../components/ui/SectionHeading";
import { useApi } from "../lib/use-api";
import { useTicker } from "../lib/use-ticker";

interface SmartDefaults {
  wacc?: number;
  terminal_growth?: number;
  fcf_growth?: number;
}
interface OverviewResp {
  asset_type?: string;
}

interface DCFInputs {
  fcf?: number;
  total_debt?: number;
  cash?: number;
  shares?: number;
}

interface DCFResult {
  scenarios?: {
    bull?: { intrinsic_value: number; upside: number };
    base?: { intrinsic_value: number; upside: number };
    bear?: { intrinsic_value: number; upside: number };
  };
}

interface Consensus {
  target_mean?: number;
  target_high?: number;
  target_low?: number;
  recommendation?: string;
}

interface SensitivityData {
  wacc_values: number[];
  tg_values: number[];
  matrix: (number | null)[][];
}

interface TornadoItem {
  variable: string;
  low: number;
  high: number;
  base: number;
}

interface MonteCarloData {
  percentile_10: number | null;
  median: number | null;
  percentile_90: number | null;
  mean: number | null;
  prob_above_current: number | null;
  current_price: number | null;
  histogram?: { counts: number[]; bin_edges: number[] };
}

type ValuationTab = "dcf" | "sensitivity" | "montecarlo" | "tornado" | "reverse";

export default function ValuationPage() {
  const { ticker, initialized } = useTicker();
  const [wacc, setWacc] = useState(10);
  const [terminalGrowth, setTerminalGrowth] = useState(2.5);
  const [fcfGrowth, setFcfGrowth] = useState(8);
  const [dcfLoading, setDcfLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<ValuationTab>("dcf");

  // Advanced models state (user-triggered; still raw fetch — will be split in P1-3)
  const [dcfResult, setDcfResult] = useState<DCFResult | null>(null);
  const [sensitivity, setSensitivity] = useState<SensitivityData | null>(null);
  const [tornado, setTornado] = useState<TornadoItem[]>([]);
  const [monteCarlo, setMonteCarlo] = useState<MonteCarloData | null>(null);
  const [reverseDCF, setReverseDCF] = useState<{ implied_growth: number | null; current_price: number | null } | null>(null);
  const [advLoading, setAdvLoading] = useState(false);
  const [runtimeNotice, setRuntimeNotice] = useState<string>("");

  // Initial data fetch via useApi — dedupes with /page and /research overview calls.
  const inputsApi = useApi<DCFInputs>(initialized ? `/api/valuation/dcf-inputs/${ticker}` : null);
  const consensusApi = useApi<Consensus>(initialized ? `/api/valuation/consensus/${ticker}` : null);
  const defaultsApi = useApi<SmartDefaults>(initialized ? `/api/valuation/smart-defaults/${ticker}` : null);
  const overviewApi = useApi<OverviewResp>(initialized ? `/api/market/overview/${ticker}` : null);

  const inputs = inputsApi.data;
  const consensus = consensusApi.data;
  const assetType = overviewApi.data?.asset_type || "equity";
  const loading = !initialized || inputsApi.loading || consensusApi.loading || defaultsApi.loading || overviewApi.loading;

  // Apply smart defaults once loaded.
  useEffect(() => {
    const d = defaultsApi.data;
    if (!d) return;
    if (d.wacc) setWacc(d.wacc);
    if (d.terminal_growth) setTerminalGrowth(d.terminal_growth);
    if (d.fcf_growth) setFcfGrowth(d.fcf_growth);
  }, [defaultsApi.data]);

  // Reset downstream model results when ticker changes.
  useEffect(() => {
    setDcfResult(null);
    setSensitivity(null);
    setTornado([]);
    setMonteCarlo(null);
    setReverseDCF(null);
    setRuntimeNotice("");
  }, [ticker]);

  // Derived notice: prioritise runtime errors (DCF failures), then load-time warnings.
  const loadNotice =
    runtimeNotice ||
    (inputsApi.error
      ? "Could not load valuation inputs. Check the backend connection and retry."
      : !loading && (!inputs?.fcf || !inputs?.shares)
      ? `DCF inputs are incomplete for ${ticker}. Smart defaults applied — review values before running models.`
      : "");

  async function runDCF() {
    if (!inputs) return;
    setDcfLoading(true);
    try {
      const res = await fetch("/api/valuation/dcf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker,
          base_fcf: inputs.fcf,
          total_debt: inputs.total_debt,
          cash: inputs.cash,
          shares: inputs.shares,
          wacc: wacc / 100,
          terminal_growth: terminalGrowth / 100,
          fcf_growth_rate: fcfGrowth / 100,
        }),
      });
      if (res.ok) {
        setDcfResult(await res.json());
        setRuntimeNotice("");
      } else {
        setRuntimeNotice("DCF calculation failed. Verify inputs or retry shortly.");
      }
    } catch {
      setRuntimeNotice("DCF request could not reach the backend.");
    }
    setDcfLoading(false);
  }

  async function runAdvancedModel(tab: ValuationTab) {
    if (!inputs?.fcf || !inputs?.shares) return;
    setAdvLoading(true);
    const body = {
      ticker,
      fcf: inputs.fcf,
      total_debt: inputs.total_debt || 0,
      cash: inputs.cash || 0,
      shares: inputs.shares,
      wacc: wacc / 100,
      terminal_growth: terminalGrowth / 100,
      fcf_growth: fcfGrowth / 100,
    };

    try {
      if (tab === "sensitivity") {
        const res = await fetch("/api/valuation/sensitivity", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (res.ok) setSensitivity(await res.json());
      } else if (tab === "tornado") {
        const res = await fetch("/api/valuation/tornado", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (res.ok) {
          const data = await res.json();
          setTornado(data.data || []);
        }
      } else if (tab === "montecarlo") {
        const res = await fetch("/api/valuation/monte-carlo", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...body,
            wacc_mean: wacc / 100,
            wacc_std: 0.015,
            growth_mean: fcfGrowth / 100,
            growth_std: 0.03,
            term_growth: terminalGrowth / 100,
            n_simulations: 5000,
          }),
        });
        if (res.ok) setMonteCarlo(await res.json());
      } else if (tab === "reverse") {
        const res = await fetch("/api/valuation/reverse-dcf", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (res.ok) setReverseDCF(await res.json());
      }
      setRuntimeNotice("");
    } catch {
      setRuntimeNotice(`${tab} model request failed. Check the backend and retry.`);
    }
    setAdvLoading(false);
  }

  if (loading) return <LoadingPulse label="Loading..." />;

  if (assetType !== "equity") {
    return (
      <div className="atlas-page">
        <SectionHeading level={1}>{ticker} Valuation</SectionHeading>
        <div className="atlas-card p-5">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">
            {assetType === "etf" ? "ETF Valuation Mode" : "Commodity Valuation Mode"}
          </h3>
          <div className="text-text-secondary text-sm">
            {assetType === "etf"
              ? "Evaluates NAV Premium/Discount, Expense comparison, and Tracking Error. DCF is available for equities only."
              : "Evaluates Futures Curve (Contango/Backwardation) and Cost of Carry. DCF is available for equities only."}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="atlas-page">
      <SectionHeading level={1}>{ticker} Valuation</SectionHeading>

      <ErrorBanner className="mb-4" variant="info" message={loadNotice || null} />

      {/* Analyst Consensus */}
      {consensus && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          {[
            { label: "Target Mean", value: consensus.target_mean ? `$${consensus.target_mean.toFixed(2)}` : "—" },
            { label: "Target High", value: consensus.target_high ? `$${consensus.target_high.toFixed(2)}` : "—" },
            { label: "Target Low", value: consensus.target_low ? `$${consensus.target_low.toFixed(2)}` : "—" },
            { label: "Recommendation", value: consensus.recommendation?.toUpperCase() || "—" },
          ].map((m) => (
            <div key={m.label} className="bg-bg-card border border-border rounded-lg p-4">
              <div className="text-text-muted text-xs mb-1">{m.label}</div>
              <div className="text-text-primary font-semibold font-mono">{m.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex gap-1 mb-5 bg-bg-card border border-border rounded-lg p-1">
        {[
          { key: "dcf" as ValuationTab, label: "DCF Model" },
          { key: "sensitivity" as ValuationTab, label: "Sensitivity" },
          { key: "montecarlo" as ValuationTab, label: "Monte Carlo" },
          { key: "tornado" as ValuationTab, label: "Tornado" },
          { key: "reverse" as ValuationTab, label: "Reverse DCF" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 px-3 py-2 rounded-md text-sm font-mono transition-all ${
              activeTab === tab.key
                ? "bg-accent-green text-bg-primary font-semibold"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* DCF Tab */}
      {activeTab === "dcf" && (
        <>
          <div className="bg-bg-card border border-border rounded-lg p-5 mb-6">
            <h3 className="text-text-secondary text-sm font-semibold mb-4">DCF Calculator</h3>
            {inputs && (
              <div className="grid grid-cols-4 gap-3 mb-5 text-sm">
                {[
                  { label: "Free Cash Flow", value: inputs.fcf ? `$${(inputs.fcf / 1e9).toFixed(2)}B` : "—" },
                  { label: "Total Debt", value: inputs.total_debt ? `$${(inputs.total_debt / 1e9).toFixed(2)}B` : "—" },
                  { label: "Cash", value: inputs.cash ? `$${(inputs.cash / 1e9).toFixed(2)}B` : "—" },
                  { label: "Shares Out", value: inputs.shares ? `${(inputs.shares / 1e9).toFixed(2)}B` : "—" },
                ].map((m) => (
                  <div key={m.label} className="bg-bg-primary rounded-md p-3">
                    <div className="text-text-muted text-xs">{m.label}</div>
                    <div className="text-text-primary font-mono font-semibold mt-1">{m.value}</div>
                  </div>
                ))}
              </div>
            )}
            <div className="grid grid-cols-3 gap-6 mb-5">
              <SliderInput label="WACC" value={wacc} onChange={setWacc} min={5} max={20} step={0.5} suffix="%" />
              <SliderInput label="Terminal Growth" value={terminalGrowth} onChange={setTerminalGrowth} min={0} max={5} step={0.5} suffix="%" />
              <SliderInput label="FCF Growth" value={fcfGrowth} onChange={setFcfGrowth} min={0} max={30} step={1} suffix="%" />
            </div>
            <button
              onClick={runDCF}
              disabled={dcfLoading || !inputs}
              className="bg-accent-green text-bg-primary px-6 py-2 rounded-md font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {dcfLoading ? "Calculating..." : "Run DCF"}
            </button>
          </div>
          {dcfResult?.scenarios && (
            <div className="grid grid-cols-3 gap-4">
              {(["bear", "base", "bull"] as const).map((scenario) => {
                const s = dcfResult.scenarios?.[scenario];
                if (!s) return null;
                const color = scenario === "bull" ? "border-accent-green" : scenario === "bear" ? "border-accent-red" : "border-accent-blue";
                const textColor = scenario === "bull" ? "text-accent-green" : scenario === "bear" ? "text-accent-red" : "text-accent-blue";
                return (
                  <div key={scenario} className={`bg-bg-card border-2 ${color} rounded-lg p-5`}>
                    <h4 className={`${textColor} text-sm font-semibold mb-2 uppercase`}>{scenario} Case</h4>
                    <div className="text-3xl font-mono font-bold text-text-primary">
                      ${s.intrinsic_value?.toFixed(2)}
                    </div>
                    <div className={`text-sm mt-1 font-mono ${s.upside >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                      {s.upside >= 0 ? "+" : ""}{s.upside?.toFixed(1)}% upside
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* Sensitivity Tab */}
      {activeTab === "sensitivity" && (
        <div className="bg-bg-card border border-border rounded-lg p-5">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-text-secondary text-sm font-semibold">WACC vs Terminal Growth Sensitivity</h3>
            <button
              onClick={() => runAdvancedModel("sensitivity")}
              disabled={advLoading || !inputs?.fcf}
              className="bg-accent-green text-bg-primary px-4 py-1.5 rounded-md text-sm font-semibold hover:opacity-90 disabled:opacity-50"
            >
              {advLoading ? "Computing..." : "Generate"}
            </button>
          </div>
          {sensitivity && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr>
                    <th className="p-2 text-text-muted text-left">WACC \ TG</th>
                    {sensitivity.tg_values.map((tg) => (
                      <th key={tg} className="p-2 text-text-muted text-right">{tg.toFixed(1)}%</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sensitivity.wacc_values.map((w, ri) => (
                    <tr key={w} className="border-t border-border/30">
                      <td className="p-2 text-text-muted font-semibold">{w.toFixed(1)}%</td>
                      {sensitivity.matrix[ri].map((val, ci) => {
                        const isCenter = ri === Math.floor(sensitivity.wacc_values.length / 2) && ci === Math.floor(sensitivity.tg_values.length / 2);
                        return (
                          <td
                            key={ci}
                            className={`p-2 text-right ${
                              isCenter ? "bg-accent-green/20 text-accent-green font-bold" :
                              val != null && val > 0 ? "text-text-primary" : "text-text-muted"
                            }`}
                          >
                            {val != null ? `$${val.toFixed(0)}` : "—"}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!sensitivity && !advLoading && (
            <div className="text-text-muted text-center py-12 text-sm">Click Generate to build the sensitivity matrix</div>
          )}
        </div>
      )}

      {/* Monte Carlo Tab */}
      {activeTab === "montecarlo" && (
        <div className="bg-bg-card border border-border rounded-lg p-5">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-text-secondary text-sm font-semibold">Monte Carlo DCF (5,000 simulations)</h3>
            <button
              onClick={() => runAdvancedModel("montecarlo")}
              disabled={advLoading || !inputs?.fcf}
              className="bg-accent-green text-bg-primary px-4 py-1.5 rounded-md text-sm font-semibold hover:opacity-90 disabled:opacity-50"
            >
              {advLoading ? "Simulating..." : "Run Simulation"}
            </button>
          </div>
          {monteCarlo && monteCarlo.median != null && (
            <>
              <div className="grid grid-cols-5 gap-3 mb-5">
                {[
                  { label: "10th Pct", value: `$${monteCarlo.percentile_10?.toFixed(2)}`, color: "text-accent-red" },
                  { label: "Median", value: `$${monteCarlo.median?.toFixed(2)}`, color: "text-accent-yellow" },
                  { label: "Mean", value: `$${monteCarlo.mean?.toFixed(2)}`, color: "text-accent-blue" },
                  { label: "90th Pct", value: `$${monteCarlo.percentile_90?.toFixed(2)}`, color: "text-accent-green" },
                  { label: "P(> Current)", value: monteCarlo.prob_above_current != null ? `${monteCarlo.prob_above_current}%` : "—", color: "text-text-primary" },
                ].map((m) => (
                  <div key={m.label} className="bg-bg-primary rounded-lg p-3 text-center">
                    <div className="text-text-muted text-xs mb-1">{m.label}</div>
                    <div className={`font-mono font-bold text-lg ${m.color}`}>{m.value}</div>
                  </div>
                ))}
              </div>

              {/* Histogram */}
              {monteCarlo.histogram && (
                <div className="mt-4">
                  <div className="flex items-end gap-px h-40">
                    {monteCarlo.histogram.counts.map((count, i) => {
                      const maxCount = Math.max(...monteCarlo.histogram!.counts);
                      const height = maxCount > 0 ? (count / maxCount) * 100 : 0;
                      const binMid = (monteCarlo.histogram!.bin_edges[i] + monteCarlo.histogram!.bin_edges[i + 1]) / 2;
                      const isAboveCurrent = monteCarlo.current_price != null && binMid > monteCarlo.current_price;
                      return (
                        <div
                          key={i}
                          className={`flex-1 rounded-t-sm ${isAboveCurrent ? "bg-accent-green" : "bg-accent-red"}`}
                          style={{ height: `${Math.max(height, 1)}%` }}
                          title={`$${monteCarlo.histogram!.bin_edges[i].toFixed(0)}-$${monteCarlo.histogram!.bin_edges[i + 1].toFixed(0)}: ${count}`}
                        />
                      );
                    })}
                  </div>
                  <div className="flex justify-between text-text-muted text-xs font-mono mt-1">
                    <span>${monteCarlo.histogram.bin_edges[0].toFixed(0)}</span>
                    {monteCarlo.current_price && <span className="text-accent-yellow">Current: ${monteCarlo.current_price.toFixed(0)}</span>}
                    <span>${monteCarlo.histogram.bin_edges[monteCarlo.histogram.bin_edges.length - 1].toFixed(0)}</span>
                  </div>
                </div>
              )}
            </>
          )}
          {!monteCarlo && !advLoading && (
            <div className="text-text-muted text-center py-12 text-sm">Click Run Simulation to perform Monte Carlo analysis</div>
          )}
        </div>
      )}

      {/* Tornado Tab */}
      {activeTab === "tornado" && (
        <div className="bg-bg-card border border-border rounded-lg p-5">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-text-secondary text-sm font-semibold">Tornado Chart — Variable Impact (±10%)</h3>
            <button
              onClick={() => runAdvancedModel("tornado")}
              disabled={advLoading || !inputs?.fcf}
              className="bg-accent-green text-bg-primary px-4 py-1.5 rounded-md text-sm font-semibold hover:opacity-90 disabled:opacity-50"
            >
              {advLoading ? "Computing..." : "Generate"}
            </button>
          </div>
          {tornado.length > 0 && (
            <div className="space-y-3">
              {tornado.map((item) => {
                const range = item.high - item.low;
                const maxRange = Math.max(...tornado.map((t) => t.high - t.low));
                const widthPct = maxRange > 0 ? (range / maxRange) * 100 : 0;
                const baseOffset = maxRange > 0 ? ((item.base - item.low) / maxRange) * 100 : 50;
                return (
                  <div key={item.variable} className="flex items-center gap-3">
                    <div className="w-28 text-right text-text-muted text-sm shrink-0">{item.variable}</div>
                    <div className="flex-1 relative h-8 bg-bg-primary rounded overflow-hidden">
                      <div
                        className="absolute h-full bg-gradient-to-r from-accent-red via-accent-yellow to-accent-green rounded opacity-80"
                        style={{ width: `${widthPct}%`, left: 0 }}
                      />
                      <div
                        className="absolute top-0 h-full w-0.5 bg-text-primary z-10"
                        style={{ left: `${baseOffset}%` }}
                      />
                    </div>
                    <div className="w-32 shrink-0 flex justify-between text-xs font-mono">
                      <span className="text-accent-red">${item.low.toFixed(0)}</span>
                      <span className="text-accent-green">${item.high.toFixed(0)}</span>
                    </div>
                  </div>
                );
              })}
              <div className="text-text-muted text-xs mt-2 font-mono text-center">
                Base value: ${tornado[0]?.base.toFixed(2)} | Sensitivity ±10% of each variable
              </div>
            </div>
          )}
          {tornado.length === 0 && !advLoading && (
            <div className="text-text-muted text-center py-12 text-sm">Click Generate to build the tornado chart</div>
          )}
        </div>
      )}

      {/* Reverse DCF Tab */}
      {activeTab === "reverse" && (
        <div className="bg-bg-card border border-border rounded-lg p-5">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-text-secondary text-sm font-semibold">Reverse DCF — Implied Growth Rate</h3>
            <button
              onClick={() => runAdvancedModel("reverse")}
              disabled={advLoading || !inputs?.fcf}
              className="bg-accent-green text-bg-primary px-4 py-1.5 rounded-md text-sm font-semibold hover:opacity-90 disabled:opacity-50"
            >
              {advLoading ? "Computing..." : "Calculate"}
            </button>
          </div>
          {reverseDCF && (
            <div className="text-center py-8">
              <div className="text-text-muted text-sm mb-2">The market is pricing in an annual FCF growth rate of:</div>
              <div className={`text-5xl font-mono font-bold ${
                reverseDCF.implied_growth != null && reverseDCF.implied_growth >= 0 ? "text-accent-green" : "text-accent-red"
              }`}>
                {reverseDCF.implied_growth != null ? `${reverseDCF.implied_growth.toFixed(2)}%` : "N/A"}
              </div>
              <div className="text-text-muted text-sm mt-3 font-mono">
                Current Price: ${reverseDCF.current_price?.toFixed(2)} | WACC: {wacc}% | Terminal Growth: {terminalGrowth}%
              </div>
              {reverseDCF.implied_growth != null && (
                <div className="mt-4 text-sm">
                  <span className="text-text-muted">Your assumption: </span>
                  <span className="text-accent-blue font-mono font-bold">{fcfGrowth}%</span>
                  <span className="text-text-muted"> vs Market implied: </span>
                  <span className={`font-mono font-bold ${reverseDCF.implied_growth >= fcfGrowth ? "text-accent-green" : "text-accent-red"}`}>
                    {reverseDCF.implied_growth.toFixed(2)}%
                  </span>
                  <span className="text-text-muted"> → </span>
                  <span className={`font-semibold ${reverseDCF.implied_growth > fcfGrowth ? "text-accent-red" : "text-accent-green"}`}>
                    {reverseDCF.implied_growth > fcfGrowth ? "Market expects MORE growth (potentially overvalued)" : "Market expects LESS growth (potentially undervalued)"}
                  </span>
                </div>
              )}
            </div>
          )}
          {!reverseDCF && !advLoading && (
            <div className="text-text-muted text-center py-12 text-sm">Click Calculate to find the implied growth rate</div>
          )}
        </div>
      )}
    </div>
  );
}

function SliderInput({ label, value, onChange, min, max, step, suffix }: {
  label: string; value: number; onChange: (v: number) => void;
  min: number; max: number; step: number; suffix: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-2">
        <span className="text-text-muted">{label}</span>
          <span className="font-mono font-semibold text-brand-navy">{value}{suffix}</span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-brand-navy"
      />
    </div>
  );
}
