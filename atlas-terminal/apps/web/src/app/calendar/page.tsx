"use client";

import { ErrorBanner } from "../components/ui/ErrorBanner";
import { LoadingPulse } from "../components/ui/LoadingPulse";
import { SectionHeading } from "../components/ui/SectionHeading";
import { flags } from "../lib/flags";
import { useApi } from "../lib/use-api";

interface CalendarResponse {
  available: boolean;
  message?: string;
  from: string;
  to: string;
  grouped: Record<string, CalendarEvent[]>;
}

interface CalendarEvent {
  date?: string;
  event?: string;
  country?: string;
  impact?: string;
  actual?: string | number | null;
  estimate?: string | number | null;
  previous?: string | number | null;
  symbol?: string;
  epsEstimated?: number | null;
  revenueEstimated?: number | null;
  time?: string;
}

function eventTitle(event: CalendarEvent): string {
  return event.event || event.symbol || "Scheduled event";
}

function impactClass(impact?: string): string {
  const normalized = (impact || "").toLowerCase();
  if (normalized.includes("high")) return "border-fin-negative/40 bg-fin-negative/10 text-fin-negative";
  if (normalized.includes("medium")) return "border-fin-warning/40 bg-fin-warning/10 text-fin-warning";
  return "border-border bg-surface-sunken text-text-secondary";
}

function weekDays(from?: string): string[] {
  const start = from ? new Date(`${from}T00:00:00`) : new Date();
  const days: string[] = [];
  for (let i = 0; i < 7; i += 1) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    const day = d.getDay();
    if (day !== 0 && day !== 6) days.push(d.toISOString().slice(0, 10));
  }
  return days.slice(0, 5);
}

export default function CalendarPage() {
  const economic = useApi<CalendarResponse>(flags.calendar ? "/api/calendar/economic?days_ahead=7" : null, { cacheTtlMs: 300_000 });
  const earnings = useApi<CalendarResponse>(flags.calendar ? "/api/calendar/earnings?days_ahead=14" : null, { cacheTtlMs: 300_000 });

  if (!flags.calendar) {
    return (
      <div className="atlas-page">
        <SectionHeading level={1}>Institutional Calendar</SectionHeading>
        <ErrorBanner variant="info" message="Calendar is behind NEXT_PUBLIC_FLAG_CALENDAR. Set it to true to enable this page." />
      </div>
    );
  }

  if (economic.loading || earnings.loading) return <LoadingPulse label="Loading calendar..." />;

  const days = weekDays(economic.data?.from || earnings.data?.from);

  return (
    <div className="atlas-page">
      <SectionHeading level={1}>Institutional Calendar</SectionHeading>
      <ErrorBanner variant="info" message={economic.data?.available === false ? economic.data.message : null} />
      <ErrorBanner variant="info" message={earnings.data?.available === false ? earnings.data.message : null} />
      <ErrorBanner variant="error" message={economic.error || earnings.error} />

      <div className="grid gap-3 lg:grid-cols-5">
        {days.map((day) => (
          <div key={day} className="atlas-card min-h-[520px] p-4">
            <div className="border-b border-border pb-2">
              <div className="font-serif text-lg font-bold text-brand-navy">
                {new Date(`${day}T00:00:00`).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}
              </div>
              <div className="font-mono text-[11px] text-text-muted">{day}</div>
            </div>

            <CalendarSection title="Economic" events={economic.data?.grouped?.[day] || []} />
            <CalendarSection title="Earnings" events={earnings.data?.grouped?.[day] || []} earnings />
          </div>
        ))}
      </div>
    </div>
  );
}

function CalendarSection({ title, events, earnings = false }: { title: string; events: CalendarEvent[]; earnings?: boolean }) {
  return (
    <section className="mt-4">
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-brand-navy">{title}</div>
      <div className="space-y-2">
        {events.length > 0 ? events.slice(0, 8).map((event, index) => (
          <div key={`${eventTitle(event)}-${index}`} className={`rounded-md border p-2 text-xs ${earnings ? "border-brand-gold/40 bg-brand-gold/10 text-brand-navy" : impactClass(event.impact)}`}>
            <div className="font-semibold">{eventTitle(event)}</div>
            <div className="mt-1 flex flex-wrap gap-x-2 gap-y-1 font-mono text-[10px] opacity-80">
              {event.country && <span>{event.country}</span>}
              {event.impact && <span>{event.impact}</span>}
              {event.time && <span>{event.time}</span>}
              {event.estimate != null && <span>Est {event.estimate}</span>}
              {event.epsEstimated != null && <span>EPS {event.epsEstimated}</span>}
            </div>
          </div>
        )) : (
          <div className="rounded-md border border-border bg-surface-sunken p-3 text-xs text-text-muted">No scheduled items.</div>
        )}
      </div>
    </section>
  );
}
