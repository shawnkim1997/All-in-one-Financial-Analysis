"use client";

import { useEffect, useMemo, useState } from "react";
import { HeadlineCard } from "../components/daily-news/HeadlineCard";
import { DailyNewsCalendar } from "../components/daily-news/DailyNewsCalendar";
import { ErrorBanner } from "../components/ui/ErrorBanner";
import { LoadingPulse } from "../components/ui/LoadingPulse";
import { SectionHeading } from "../components/ui/SectionHeading";
import type { FTHeadline } from "../lib/daily-news-types";
import { addDays, formatNewsHeading, isSupportedDailyNewsDate, todayKey } from "../lib/daily-news-utils";
import { useBookmarks, useReadStatus } from "../lib/use-daily-news";

export default function DailyNewsPage() {
  const [selectedDate, setSelectedDate] = useState(todayKey());
  const [headlines, setHeadlines] = useState<FTHeadline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [todayLink, setTodayLink] = useState("https://www.ft.com/todaysnewspaper/international");
  const [hasGeminiKey, setHasGeminiKey] = useState(false);
  const { readDates, isRead, toggleRead } = useReadStatus();
  const { bookmarkedDates, isBookmarked, toggleBookmark } = useBookmarks();

  useEffect(() => {
    const apiKey = localStorage.getItem("atlas_gemini_key") || "";
    setHasGeminiKey(Boolean(apiKey.trim()));

    fetch("/api/daily-news/today-link")
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (payload?.url) setTodayLink(payload.url);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;

    if (!isSupportedDailyNewsDate(selectedDate)) {
      setHeadlines([]);
      setLoading(false);
      setNotice("FT RSS currently covers only the most recent 7 days. Use the FT ePaper link for older archive dates.");
      return () => {
        cancelled = true;
      };
    }

    setLoading(true);
    setError(null);
    const apiKey = localStorage.getItem("atlas_gemini_key") || "";
    setHasGeminiKey(Boolean(apiKey.trim()));
    const headers = apiKey.trim() ? { "x-gemini-api-key": apiKey.trim() } : undefined;
    fetch(`/api/daily-news/${selectedDate}`, { headers })
      .then(async (response) => {
        if (!response.ok) {
          const payload = await response.json().catch(() => null);
          throw new Error(payload?.detail || "Failed to load daily FT headlines.");
        }
        return response.json();
      })
      .then((payload: FTHeadline[]) => {
        if (cancelled) return;
        setHeadlines(Array.isArray(payload) ? payload : []);
        setNotice(null);
      })
      .catch((fetchError: Error) => {
        if (cancelled) return;
        setHeadlines([]);
        setError(fetchError.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedDate]);

  const selectedLabel = useMemo(() => formatNewsHeading(selectedDate), [selectedDate]);

  return (
    <div className="atlas-page">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <SectionHeading level={1}>Daily News</SectionHeading>
          <p className="mt-1 text-sm text-text-secondary">Financial Times headlines with Korean summary and one-click FT open-in-new-tab workflow.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => setSelectedDate(todayKey())} className="rounded-md border border-border bg-white px-3 py-2 text-sm font-semibold text-brand-navy hover:bg-surface-sunken">
            Today
          </button>
          <button type="button" onClick={() => setSelectedDate(addDays(todayKey(), -1))} className="rounded-md border border-border bg-white px-3 py-2 text-sm font-semibold text-brand-navy hover:bg-surface-sunken">
            Yesterday
          </button>
          <a href={todayLink} target="_blank" rel="noopener noreferrer" className="rounded-md bg-brand-navy px-3 py-2 text-sm font-semibold text-white hover:bg-brand-blue">
            FT ePaper 전체 보기 ↗
          </a>
        </div>
      </div>

      <ErrorBanner variant="info" message={notice} className="mb-4" />
      <ErrorBanner
        variant="info"
        message={hasGeminiKey ? null : "Set your Gemini API key in Settings to see Korean headline and lede translation. Without it, FT originals still load in English."}
        className="mb-4"
      />
      <ErrorBanner variant="error" message={error} className="mb-4" />

      <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        <DailyNewsCalendar
          selectedDate={selectedDate}
          readDates={readDates}
          bookmarkedDates={bookmarkedDates}
          onSelectDate={setSelectedDate}
          onUnsupportedDate={setNotice}
        />

        <section className="min-w-0">
          <div className="atlas-card mb-4 p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="font-serif text-2xl font-bold text-brand-navy">{selectedLabel}</h2>
                <p className="mt-1 text-sm text-text-muted">{headlines.length} FT headlines</p>
              </div>
            </div>
          </div>

          {loading ? (
            <LoadingPulse label="Loading FT headlines..." />
          ) : headlines.length === 0 ? (
            <div className="atlas-card p-6 text-sm text-text-muted">
              No FT headlines were found for this date. Weekend or RSS coverage gaps can produce empty days.
            </div>
          ) : (
            <div className="space-y-4">
              {headlines.map((headline) => {
                const articleDate = headline.published_at.slice(0, 10);
                return (
                  <HeadlineCard
                    key={headline.url}
                    headline={headline}
                    isRead={isRead(headline.url)}
                    isBookmarked={isBookmarked(headline.url)}
                    onToggleRead={() => toggleRead(headline.url, articleDate)}
                    onToggleBookmark={() => toggleBookmark(headline, articleDate)}
                  />
                );
              })}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
