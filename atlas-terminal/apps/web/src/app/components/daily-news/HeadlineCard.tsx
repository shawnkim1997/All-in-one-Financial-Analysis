"use client";

import Image from "next/image";

import type { FTHeadline } from "../../lib/daily-news-types";

interface HeadlineCardProps {
  headline: FTHeadline;
  isRead: boolean;
  isBookmarked: boolean;
  onToggleRead: () => void;
  onToggleBookmark: () => void;
}

export function HeadlineCard({
  headline,
  isRead,
  isBookmarked,
  onToggleRead,
  onToggleBookmark,
}: HeadlineCardProps) {
  const displayTitle = headline.title_ko || headline.title_en;
  const displayLede = headline.lede_ko || headline.lede_en || "Preview unavailable. Open the original FT article for the full story.";

  return (
    <article className="atlas-card overflow-hidden">
      <div className="flex flex-col gap-4 p-5 lg:flex-row">
        <div className="w-full shrink-0 lg:w-40">
          {headline.image ? (
            <Image
              src={headline.image}
              alt={headline.title_en}
              width={160}
              height={112}
              className="h-28 w-full rounded-md object-cover"
            />
          ) : (
            <div className="flex h-28 items-center justify-center rounded-md border border-border bg-surface-sunken px-4 text-center">
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-navy">
                {headline.section || "FT"}
              </span>
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.12em]">
            <span className="rounded border border-brand-gold/40 bg-brand-gold/10 px-2 py-1 text-brand-navy">
              {headline.section || "Financial Times"}
            </span>
            <span className="font-mono text-text-muted">
              {new Date(headline.published_at).toLocaleString()}
            </span>
          </div>

          <h3 className="font-serif text-xl font-bold text-brand-navy">{displayTitle}</h3>
          <p className="mt-1 text-sm text-text-muted">{headline.title_en}</p>
          <p
            className="mt-3 text-sm leading-6 text-text-secondary"
            style={{ display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}
          >
            {displayLede}
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            <a
              href={headline.url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md bg-brand-navy px-3 py-2 text-sm font-semibold text-white transition hover:bg-brand-blue"
            >
              FT에서 원문 열기 ↗
            </a>
            <button
              type="button"
              onClick={onToggleRead}
              className={`rounded-md border px-3 py-2 text-sm font-semibold transition ${
                isRead
                  ? "border-fin-positive/40 bg-fin-positive/10 text-fin-positive"
                  : "border-border bg-surface-sunken text-text-secondary hover:border-brand-blue/40 hover:text-brand-navy"
              }`}
            >
              {isRead ? "읽음 ✓" : "읽음 표시"}
            </button>
            <button
              type="button"
              onClick={onToggleBookmark}
              className={`rounded-md border px-3 py-2 text-sm font-semibold transition ${
                isBookmarked
                  ? "border-brand-gold/40 bg-brand-gold/10 text-brand-navy"
                  : "border-border bg-surface-sunken text-text-secondary hover:border-brand-gold/40 hover:text-brand-navy"
              }`}
            >
              {isBookmarked ? "★ 북마크됨" : "☆ 북마크"}
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}
