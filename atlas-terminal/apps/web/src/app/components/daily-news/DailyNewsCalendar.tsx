"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { dateKey, isSupportedDailyNewsDate, parseDateKey, todayKey } from "../../lib/daily-news-utils";

interface DailyNewsCalendarProps {
  selectedDate: string;
  readDates: Set<string>;
  bookmarkedDates: Set<string>;
  onSelectDate: (value: string) => void;
  onUnsupportedDate: (message: string) => void;
}

const DAY_LABELS = ["S", "M", "T", "W", "T", "F", "S"];

function monthGrid(monthKey: string): (Date | null)[] {
  const month = parseDateKey(monthKey);
  const first = new Date(month.getFullYear(), month.getMonth(), 1);
  const last = new Date(month.getFullYear(), month.getMonth() + 1, 0);
  const cells: (Date | null)[] = [];

  for (let i = 0; i < first.getDay(); i += 1) cells.push(null);
  for (let day = 1; day <= last.getDate(); day += 1) {
    cells.push(new Date(month.getFullYear(), month.getMonth(), day));
  }
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

export function DailyNewsCalendar({
  selectedDate,
  readDates,
  bookmarkedDates,
  onSelectDate,
  onUnsupportedDate,
}: DailyNewsCalendarProps) {
  const [visibleMonth, setVisibleMonth] = useState(selectedDate);
  const today = todayKey();
  const cells = useMemo(() => monthGrid(visibleMonth), [visibleMonth]);

  useEffect(() => {
    setVisibleMonth(selectedDate);
  }, [selectedDate]);

  function shiftMonth(direction: number) {
    const current = parseDateKey(visibleMonth);
    setVisibleMonth(dateKey(new Date(current.getFullYear(), current.getMonth() + direction, 1)));
  }

  return (
    <section className="atlas-card p-4">
      <div className="mb-4 flex items-center justify-between">
        <button type="button" onClick={() => shiftMonth(-1)} className="rounded-md border border-border p-2 text-text-secondary hover:bg-surface-sunken">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="font-serif text-lg font-bold text-brand-navy">
          {parseDateKey(visibleMonth).toLocaleDateString(undefined, { month: "long", year: "numeric" })}
        </div>
        <button type="button" onClick={() => shiftMonth(1)} className="rounded-md border border-border p-2 text-text-secondary hover:bg-surface-sunken">
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center text-[11px] font-semibold uppercase tracking-[0.12em] text-text-muted">
        {DAY_LABELS.map((label, index) => <div key={`${label}-${index}`}>{label}</div>)}
      </div>

      <div className="mt-2 grid grid-cols-7 gap-1">
        {cells.map((cell, index) => {
          if (!cell) {
            return <div key={`blank-${index}`} className="h-12 rounded-md bg-surface-sunken/30" />;
          }

          const key = dateKey(cell);
          const selected = key === selectedDate;
          const isToday = key === today;
          const supported = isSupportedDailyNewsDate(key);
          const read = readDates.has(key);
          const bookmarked = bookmarkedDates.has(key);

          return (
            <button
              key={key}
              type="button"
              onClick={() => {
                if (!supported) {
                  onUnsupportedDate("FT RSS currently covers only the most recent 7 days. Open FT.com directly for older archive dates.");
                  return;
                }
                onSelectDate(key);
              }}
              className={`flex h-12 flex-col items-center justify-center rounded-md border text-sm transition ${
                selected
                  ? "border-brand-gold bg-brand-navy text-white"
                  : supported
                    ? "border-border bg-white text-text-primary hover:bg-surface-sunken"
                    : "border-border/50 bg-surface-sunken/50 text-text-muted"
              }`}
            >
              <span className={`font-mono ${isToday && !selected ? "text-brand-blue" : ""}`}>{cell.getDate()}</span>
              <span className="mt-1 flex items-center gap-1 text-[10px]">
                {read && <span>●</span>}
                {bookmarked && <span>★</span>}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
