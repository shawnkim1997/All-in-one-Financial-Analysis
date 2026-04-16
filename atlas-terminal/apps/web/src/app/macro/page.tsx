"use client";

import { useEffect, useState } from "react";

import { MacroCycleHeatmap, type MacroSnapshot } from "../components/markets/MacroCycleHeatmap";
import { OECDCycleChart, type OECDData } from "../components/markets/OECDCycleChart";
import { KoreaMonitor } from "../components/markets/KoreaMonitor";
import { EconomicCalendar } from "../components/markets/EconomicCalendar";
import { GlobalMacroQuadrantChart, type QuadrantPoint } from "../components/macro/GlobalMacroQuadrantChart";
import { YieldFxDualAxisChart, type YieldFxRow } from "../components/macro/YieldFxDualAxisChart";
import { SmartMoneyPanel } from "../components/macro/SmartMoneyPanel";
import { ErrorBanner } from "../components/ui/ErrorBanner";
import { LoadingPulse } from "../components/ui/LoadingPulse";

const FRED_PRESETS = [
  { id: "UNRATE", label: "US Unemployment %" },
  { id: "CPIAUCSL", label: "US CPI (All Urban)" },
  { id: "DFF", label: "Fed Funds Effective" },
  { id: "T10Y2Y", label: "10Y-2Y Treasury spread" },
];

interface FredPoint {
  date: string;
  value: number;
}

type MacroTab = "fred" | "cycle" | "oecd" | "korea" | "calendar" | "subfactors";

interface SubfactorIndicator {
  key: string;
  label: string;
  value: number | null;
  unit?: string;
  change_3m: number | null;
  zscore: number | null;
  signal: "improving" | "neutral" | "deteriorating";
}

interface SubfactorData {
  composite_score: number;
  cycle_stage: string;
  categories: Record<string, { score: number; indicators: SubfactorIndicator[] }>;
}

const MACRO_ERROR_MESSAGES: Record<string, string> = {
  upstream_timeout: "Upstream macro source timed out. Try again in a moment.",
  fred_empty: "FRED returned no usable series for this view.",
  fx_empty: "FX history could not be loaded for this pair.",
  invalid_pair: "This yield/FX pair is not supported.",
  missing_peer: "Peer bond series is unavailable for this pair.",
};

function formatMacroError(error: unknown, fallback: string): string {
  if (typeof error !== "string" || !error.trim()) {
    return fallback;
  }

  if (error in MACRO_ERROR_MESSAGES) {
    return MACRO_ERROR_MESSAGES[error];
  }

  if (error.startsWith("HTTP_")) {
    return `Request failed (${error.replace("HTTP_", "HTTP ")}).`;
  }

  return error.replaceAll("_", " ");
}

export default function MacroPage() {
  const [series, setSeries] = useState("UNRATE");
  const [rows, setRows] = useState<FredPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [tab, setTab] = useState<MacroTab>("fred");
  const [snap, setSnap] = useState<MacroSnapshot | null>(null);
  const [snapErr, setSnapErr] = useState<string | null>(null);
  const [oecd, setOecd] = useState<OECDData | null>(null);

  const [classicOpen, setClassicOpen] = useState(false);
  const [subfactors, setSubfactors] = useState<SubfactorData | null>(null);

  const [quadPoints, setQuadPoints] = useState<QuadrantPoint[]>([]);
  const [quadLoading, setQuadLoading] = useState(true);
  const [quadErr, setQuadErr] = useState<string | null>(null);

  const [yieldPair, setYieldPair] = useState<"usdjpy" | "eurusd" | "usdkrw">("usdjpy");
  const [yieldRows, setYieldRows] = useState<YieldFxRow[]>([]);
  const [yieldLoading, setYieldLoading] = useState(true);
  const [yieldErr, setYieldErr] = useState<string | null>(null);

  const [roroZ, setRoroZ] = useState<number | null>(null);
  const [roroLabel, setRoroLabel] = useState<string | null>(null);
  const [copperGold, setCopperGold] = useState<
    { date: string; ratio: number; ratio_ma20?: number }[]
  >([]);
  const [smartLoading, setSmartLoading] = useState(true);
  const [smartErr, setSmartErr] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setErr(null);
    const controller = new AbortController();
    fetch(`/api/macro/fred/${encodeURIComponent(series)}`, { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP_${r.status}`))))
      .then((j) => {
        setRows(Array.isArray(j.data) ? j.data : []);
        setLoading(false);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setErr(formatMacroError(error instanceof Error ? error.message : error, "Failed to load FRED series."));
        setLoading(false);
      });
    return () => controller.abort();
  }, [series]);

  useEffect(() => {
    setSnapErr(null);
    const controller = new AbortController();
    fetch("/api/macro/snapshot", { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP_${r.status}`))))
      .then((j) => {
        if (!j || typeof j !== "object") {
          setSnap(null);
          setSnapErr("Macro snapshot returned an empty payload.");
          return;
        }
        const cycleHeatmap = Array.isArray(j.cycle_heatmap) ? j.cycle_heatmap : [];
        const countryHeatmap = Array.isArray(j.country_heatmap) ? j.country_heatmap : [];
        const assetValuation = Array.isArray(j.asset_valuation) ? j.asset_valuation : [];
        const hasSnapshotData = cycleHeatmap.length > 0 || countryHeatmap.length > 0 || assetValuation.length > 0;
        if (j.error) setSnapErr(formatMacroError(j.error, "Failed to load macro snapshot."));
        else if (!hasSnapshotData) setSnapErr("Macro snapshot returned no usable data.");
        else setSnapErr(null);
        setSnap({
          updated_at: j.updated_at ?? null,
          cycle_score: typeof j.cycle_score === "number" ? j.cycle_score : 0,
          regime: String(j.regime ?? "—"),
          cycle_heatmap: cycleHeatmap,
          country_heatmap: countryHeatmap,
          asset_valuation: assetValuation,
        });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setSnap(null);
        setSnapErr(formatMacroError(error instanceof Error ? error.message : error, "Failed to load macro snapshot."));
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    fetch("/api/macro/subfactors")
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        if (j && typeof j === "object" && j.categories) setSubfactors(j);
      })
      .catch(() => setSubfactors(null));
  }, []);

  useEffect(() => {
    fetch("/api/macro/oecd/cli")
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => setOecd(j && typeof j === "object" ? j : null))
      .catch(() => setOecd(null));
  }, []);

  useEffect(() => {
    setQuadErr(null);
    setQuadLoading(true);
    const controller = new AbortController();
    fetch("/api/macro/quadrant", { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP_${r.status}`))))
      .then((j) => {
        if (!j || typeof j !== "object") {
          setQuadPoints([]);
          setQuadErr("Macro quadrant returned an empty payload.");
          return;
        }
        const points = Array.isArray(j.points) ? j.points : [];
        if (j.error) setQuadErr(formatMacroError(j.error, "Failed to load macro quadrant."));
        else if (!points.length) setQuadErr("No quadrant points were produced from current macro sources.");
        setQuadPoints(points);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setQuadPoints([]);
        setQuadErr(formatMacroError(error instanceof Error ? error.message : error, "Failed to load macro quadrant."));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setQuadLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    setYieldErr(null);
    setYieldLoading(true);
    const controller = new AbortController();
    fetch(`/api/macro/yield-fx?pair=${encodeURIComponent(yieldPair)}`, { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP_${r.status}`))))
      .then((j) => {
        if (!j || typeof j !== "object") {
          setYieldRows([]);
          setYieldErr("Yield/FX returned an empty payload.");
          return;
        }
        const seriesRows = Array.isArray(j.series) ? j.series : [];
        if (j.error) setYieldErr(formatMacroError(j.error, "Failed to load yield/FX data."));
        else if (!seriesRows.length) setYieldErr("Yield/FX returned no usable observations.");
        setYieldRows(seriesRows);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setYieldRows([]);
        setYieldErr(formatMacroError(error instanceof Error ? error.message : error, "Failed to load yield/FX data."));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setYieldLoading(false);
        }
      });
    return () => controller.abort();
  }, [yieldPair]);

  useEffect(() => {
    setSmartErr(null);
    setSmartLoading(true);
    const controller = new AbortController();
    fetch("/api/macro/smart-money", { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP_${r.status}`))))
      .then((j) => {
        if (!j || typeof j !== "object") {
          setRoroZ(null);
          setRoroLabel(null);
          setCopperGold([]);
          setSmartErr("Smart money returned an empty payload.");
          return;
        }
        const nextRoroZ = typeof j.roro_z === "number" ? j.roro_z : null;
        const nextRoroLabel = j.roro_label != null ? String(j.roro_label) : null;
        const nextCopperGold = Array.isArray(j.copper_gold) ? j.copper_gold : [];
        if (j.error) setSmartErr(formatMacroError(j.error, "Failed to load smart money data."));
        else if (nextRoroZ == null && !nextCopperGold.length) setSmartErr("Smart money inputs returned no usable data.");
        setRoroZ(nextRoroZ);
        setRoroLabel(nextRoroLabel);
        setCopperGold(nextCopperGold);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setRoroZ(null);
        setRoroLabel(null);
        setCopperGold([]);
        setSmartErr(formatMacroError(error instanceof Error ? error.message : error, "Failed to load smart money data."));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setSmartLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  const tabs: { key: MacroTab; label: string }[] = [
    { key: "fred", label: "FRED" },
    { key: "subfactors", label: "Sub-Factors" },
    { key: "cycle", label: "Cycle & valuation" },
    { key: "oecd", label: "OECD CLI" },
    { key: "korea", label: "Korea" },
    { key: "calendar", label: "Calendar" },
  ];

  return (
    <div className="p-7 max-w-7xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-2 text-text-primary">Global Macro &amp; Smart Money</h1>
        <p className="text-text-muted text-sm">
          Growth vs inflation quadrant (FRED / OECD), US–peer 10Y spreads vs FX (FRED + Yahoo), and copper/gold with a
          VIX + bond-vol RORO gauge. Quantitative series are computed in Python only.
        </p>
      </div>

      <div className="bg-bg-card border border-border rounded-lg overflow-hidden p-4">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-12 bg-bg-secondary/30 border border-border/60 rounded-lg p-4">
            <h2 className="text-sm font-semibold text-text-primary mb-1">Global macro quadrant</h2>
            <p className="text-text-muted text-xs mb-3">3M momentum Z-scores (growth vs inflation).</p>
            <ErrorBanner message={quadErr} variant="warning" className="mb-3" />
            {quadLoading ? (
              <LoadingPulse label="Loading macro quadrant…" height="h-[320px]" />
            ) : (
              <GlobalMacroQuadrantChart points={quadPoints} />
            )}
          </div>

          <div className="lg:col-span-6 bg-bg-secondary/30 border border-border/60 rounded-lg p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <h2 className="text-sm font-semibold text-text-primary">Yield spread vs FX</h2>
              <div className="flex gap-1">
                {(["usdjpy", "eurusd", "usdkrw"] as const).map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setYieldPair(p)}
                    className={`px-2 py-1 rounded text-xs font-mono border ${
                      yieldPair === p
                        ? "bg-accent-green/15 border-accent-green text-accent-green"
                        : "border-border text-text-secondary hover:bg-bg-hover"
                    }`}
                  >
                    {p.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
            <ErrorBanner message={yieldErr} variant="warning" className="mb-3" />
            {yieldLoading ? (
              <LoadingPulse label="Loading yield/FX series…" height="h-[280px]" />
            ) : (
              <YieldFxDualAxisChart pair={yieldPair} rows={yieldRows} />
            )}
          </div>

          <div className="lg:col-span-6 bg-bg-secondary/30 border border-border/60 rounded-lg p-4">
            <h2 className="text-sm font-semibold text-text-primary mb-1">Smart money &amp; RORO</h2>
            <p className="text-text-muted text-xs mb-3">HG/GC ratio and composite risk Z-score.</p>
            <ErrorBanner message={smartErr} variant="warning" className="mb-3" />
            {smartLoading ? (
              <LoadingPulse label="Loading smart money indicators…" height="h-[260px]" />
            ) : (
              <SmartMoneyPanel roroZ={roroZ} roroLabel={roroLabel} copperGold={copperGold} />
            )}
          </div>
        </div>
      </div>

      <div className="border border-border rounded-lg bg-bg-card">
        <button
          type="button"
          onClick={() => setClassicOpen(!classicOpen)}
          className="w-full text-left px-4 py-3 text-sm font-medium text-text-primary hover:bg-bg-hover flex justify-between items-center"
        >
          <span>Classic macro tools</span>
          <span className="text-text-muted font-mono text-xs">{classicOpen ? "▼" : "▶"}</span>
        </button>
        {classicOpen && (
          <div className="px-4 pb-6 pt-2 border-t border-border space-y-6">
            <div className="flex flex-wrap gap-1 bg-bg-secondary rounded-lg p-1 w-fit">
              {tabs.map((t) => (
                <button
                  key={t.key}
                  type="button"
                  onClick={() => setTab(t.key)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium ${
                    tab === t.key ? "bg-accent-green text-bg-primary" : "text-text-secondary hover:text-text-primary"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {tab === "fred" && (
              <>
                <div className="flex flex-wrap gap-2">
                  {FRED_PRESETS.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setSeries(p.id)}
                      className={`px-3 py-1.5 rounded-md text-sm font-mono border ${
                        series === p.id
                          ? "bg-accent-green/15 border-accent-green text-accent-green"
                          : "bg-bg-card border-border text-text-secondary hover:bg-bg-hover"
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>

                {loading ? (
                  <LoadingPulse label="Loading FRED series…" height="h-20" className="justify-start" />
                ) : err ? (
                  <ErrorBanner message={err} variant="error" />
                ) : (
                  <div className="bg-bg-secondary border border-border rounded-lg overflow-hidden">
                    <div className="px-4 py-2 border-b border-border text-text-muted text-sm font-mono">
                      {series} — {rows.length} observations (recent last)
                    </div>
                    <div className="max-h-[480px] overflow-y-auto">
                      <table className="w-full text-sm font-mono">
                        <thead>
                          <tr className="text-left text-text-muted border-b border-border">
                            <th className="p-3">Date</th>
                            <th className="p-3">Value</th>
                          </tr>
                        </thead>
                        <tbody>
                          {[...rows].reverse().slice(0, 60).map((r) => (
                            <tr key={r.date} className="border-b border-border/50 hover:bg-bg-hover">
                              <td className="p-2 text-text-secondary">{r.date}</td>
                              <td className="p-2 text-accent-green">{r.value}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            )}

            {tab === "subfactors" && (
              <div className="space-y-4">
                {subfactors ? (
                  <>
                    <div className="flex items-center gap-4 mb-2">
                      <div className="bg-bg-secondary border border-border rounded-lg px-4 py-2">
                        <div className="text-text-muted text-xs">Cycle Stage</div>
                        <div className="text-accent-green font-mono font-bold text-lg">{subfactors.cycle_stage}</div>
                      </div>
                      <div className="bg-bg-secondary border border-border rounded-lg px-4 py-2">
                        <div className="text-text-muted text-xs">Composite Score</div>
                        <div className={`font-mono font-bold text-lg ${subfactors.composite_score >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                          {subfactors.composite_score >= 0 ? "+" : ""}{subfactors.composite_score.toFixed(2)}
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {Object.entries(subfactors.categories).map(([catName, cat]) => (
                        <div key={catName} className="bg-bg-secondary border border-border rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="text-text-primary text-sm font-semibold">{catName}</h3>
                            <span className={`text-xs font-mono px-2 py-0.5 rounded ${cat.score >= 0.5 ? "bg-accent-green/15 text-accent-green" : cat.score <= -0.5 ? "bg-accent-red/15 text-accent-red" : "bg-bg-hover text-text-muted"}`}>
                              {cat.score >= 0 ? "+" : ""}{cat.score.toFixed(2)}
                            </span>
                          </div>
                          <div className="space-y-2">
                            {cat.indicators.map((ind) => (
                              <div key={ind.key} className="flex items-center justify-between text-sm">
                                <span className="text-text-secondary">{ind.label}</span>
                                <div className="flex items-center gap-3">
                                  <span className="text-text-primary font-mono">{ind.value != null ? ind.value : "—"}{ind.unit && ind.value != null ? ind.unit : ""}</span>
                                  {ind.change_3m != null && (
                                    <span className={`text-xs font-mono ${ind.change_3m >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                                      {ind.change_3m >= 0 ? "+" : ""}{ind.change_3m}%
                                    </span>
                                  )}
                                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                                    ind.signal === "improving" ? "bg-accent-green/15 text-accent-green" :
                                    ind.signal === "deteriorating" ? "bg-accent-red/15 text-accent-red" :
                                    "bg-bg-hover text-text-muted"
                                  }`}>
                                    {ind.signal}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="text-accent-green animate-pulse font-mono">Loading sub-factor data...</div>
                )}
              </div>
            )}

            {tab === "cycle" && (
              <div className="space-y-4">
                <ErrorBanner message={snapErr ? `Snapshot warning: ${snapErr}` : null} variant="warning" />
                <MacroCycleHeatmap data={snap} />
              </div>
            )}

            {tab === "oecd" && <OECDCycleChart data={oecd} />}

            {tab === "korea" && <KoreaMonitor />}

            {tab === "calendar" && <EconomicCalendar />}
          </div>
        )}
      </div>
    </div>
  );
}
