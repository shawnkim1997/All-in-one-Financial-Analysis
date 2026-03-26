"use client";

import { useState, useEffect, useMemo } from "react";

interface CalendarEvent {
  datetime: string;
  country: string;
  country_flag: string;
  indicator: string;
  importance: string;
  previous: number | null;
  forecast: number | null;
  actual: number | null;
  surprise: number | null;
  surprise_label: string;
}

interface CalendarData {
  events: CalendarEvent[];
  next_high_impact: CalendarEvent | null;
  total: number;
  error?: string;
}

const IMPORTANCE_STYLES: Record<string, string> = {
  high: "bg-accent-red/20 text-accent-red",
  medium: "bg-accent-yellow/15 text-accent-yellow",
  low: "bg-bg-primary text-text-muted",
};

const SURPRISE_STYLES: Record<string, string> = {
  positive: "text-accent-green",
  negative: "text-accent-red",
  "in-line": "text-text-muted",
  pending: "text-text-muted italic",
};

function num(v: number | null): string {
  if (v == null) return "—";
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function EconomicCalendar() {
  const [data, setData] = useState<CalendarData | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    fetch("/api/macro/economic-calendar?days=7")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    if (!data) return [];
    if (filter === "all") return data.events;
    return data.events.filter((e) => e.importance === filter);
  }, [data, filter]);

  if (loading) {
    return (
      <div className="bg-bg-card border border-border rounded-lg p-8 text-center">
        <div className="text-accent-green animate-pulse font-mono">Loading calendar...</div>
      </div>
    );
  }

  if (!data || data.error) {
    return (
      <div className="bg-bg-card border border-border rounded-lg p-4">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">Economic Calendar</h3>
        <div className="text-text-muted text-sm">{data?.error || "Calendar data unavailable."}</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Next High Impact Banner */}
      {data.next_high_impact && (
        <div className="bg-accent-red/10 border border-accent-red/30 rounded-lg p-3 flex items-center gap-3">
          <div className="text-accent-red text-lg font-bold">!</div>
          <div>
            <div className="text-text-primary text-sm font-semibold">
              Next High-Impact: {data.next_high_impact.country_flag} {data.next_high_impact.indicator}
            </div>
            <div className="text-text-muted text-xs">
              {data.next_high_impact.datetime} | Forecast: {num(data.next_high_impact.forecast)}
            </div>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="bg-bg-card border border-border rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-text-secondary text-sm font-semibold">Economic Calendar</h3>
          <div className="flex gap-1">
            {["all", "high", "medium", "low"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`text-[11px] px-2.5 py-1 rounded font-medium transition-colors ${
                  filter === f ? "bg-accent-green text-bg-primary" : "text-text-muted hover:text-text-secondary"
                }`}
              >
                {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="text-text-muted text-sm text-center py-8">No events match the current filter.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] text-sm">
              <thead>
                <tr className="border-b border-border text-text-muted text-left">
                  <th className="py-2 pr-2 w-16">Time</th>
                  <th className="py-2 pr-2 w-12"></th>
                  <th className="py-2 pr-2">Event</th>
                  <th className="py-2 pr-2 w-16">Impact</th>
                  <th className="py-2 pr-2 w-20 text-right">Previous</th>
                  <th className="py-2 pr-2 w-20 text-right">Forecast</th>
                  <th className="py-2 pr-2 w-20 text-right">Actual</th>
                  <th className="py-2 w-20 text-right">Surprise</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((evt, idx) => (
                  <tr key={idx} className="border-b border-border/30 hover:bg-bg-primary/30 transition-colors">
                    <td className="py-2 pr-2 text-text-muted font-mono text-xs">{evt.datetime || "—"}</td>
                    <td className="py-2 pr-2 text-center">{evt.country_flag || evt.country}</td>
                    <td className="py-2 pr-2 text-text-primary">{evt.indicator}</td>
                    <td className="py-2 pr-2">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${IMPORTANCE_STYLES[evt.importance] || ""}`}>
                        {evt.importance}
                      </span>
                    </td>
                    <td className="py-2 pr-2 text-right font-mono text-text-muted">{num(evt.previous)}</td>
                    <td className="py-2 pr-2 text-right font-mono text-text-secondary">{num(evt.forecast)}</td>
                    <td className={`py-2 pr-2 text-right font-mono font-semibold ${
                      evt.actual != null && evt.forecast != null
                        ? evt.actual > evt.forecast ? "text-accent-green" : evt.actual < evt.forecast ? "text-accent-red" : "text-text-primary"
                        : "text-text-primary"
                    }`}>
                      {num(evt.actual)}
                    </td>
                    <td className={`py-2 text-right font-mono text-xs ${SURPRISE_STYLES[evt.surprise_label] || ""}`}>
                      {evt.surprise_label === "pending"
                        ? "pending"
                        : evt.surprise != null
                          ? `${evt.surprise > 0 ? "+" : ""}${(evt.surprise * 100).toFixed(1)}%`
                          : "—"
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="text-text-muted text-xs mt-2">{data.total} events total</div>
      </div>
    </div>
  );
}
