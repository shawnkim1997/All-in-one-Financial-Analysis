"use client";

import { Check, Copy, Languages, Search } from "lucide-react";
import { useDeferredValue, useMemo, useState } from "react";
import { Card } from "../ui/Card";
import { ErrorBanner } from "../ui/ErrorBanner";
import { LoadingPulse } from "../ui/LoadingPulse";
import type { VideoJobDetailResponse, VideoTranslation } from "../../lib/video-transcript-types";

interface TranscriptDetailPanelProps {
  detail: VideoJobDetailResponse | null;
  loading: boolean;
  translation: VideoTranslation | null;
  translating: boolean;
  onTranslate: (jobId: string) => Promise<unknown>;
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function sentimentTone(sentiment: string | null | undefined) {
  if (sentiment === "positive") return "border-fin-positive/40 bg-fin-positive/10 text-fin-positive";
  if (sentiment === "negative") return "border-fin-negative/40 bg-fin-negative/10 text-fin-negative";
  return "border-border bg-surface-sunken text-text-secondary";
}

function highlightText(text: string, query: string) {
  if (!query.trim()) return text;
  const matcher = new RegExp(`(${escapeRegExp(query)})`, "ig");
  const lowered = query.toLowerCase();
  return text.split(matcher).map((part, index) => (
    part.toLowerCase() === lowered ? (
      <mark key={`${part}-${index}`} className="rounded bg-brand-gold/30 px-0.5 text-brand-navy">
        {part}
      </mark>
    ) : (
      <span key={`${part}-${index}`}>{part}</span>
    )
  ));
}

export function TranscriptDetailPanel({
  detail,
  loading,
  translation,
  translating,
  onTranslate,
}: TranscriptDetailPanelProps) {
  const [query, setQuery] = useState("");
  const [copied, setCopied] = useState(false);
  const [showTranslation, setShowTranslation] = useState(false);
  const deferredQuery = useDeferredValue(query);
  const transcriptText = showTranslation ? (translation?.text || "") : (detail?.transcript?.text || "");
  const highlightedTranscript = useMemo(
    () => highlightText(transcriptText, deferredQuery),
    [deferredQuery, transcriptText],
  );

  async function handleCopy() {
    if (!transcriptText) return;
    await navigator.clipboard.writeText(transcriptText);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  if (loading && !detail) {
    return <LoadingPulse label="Loading transcript detail..." height="h-[560px]" />;
  }

  if (!detail) {
    return (
      <Card title="Transcript Detail" subtitle="Choose a job to inspect its summary, keywords, and transcript text.">
        <div className="rounded-md border border-dashed border-border-strong bg-bg-primary px-4 py-16 text-center text-sm text-text-muted">
          Select a transcript job from the left column or search your saved transcripts above.
        </div>
      </Card>
    );
  }

  const { job, transcript } = detail;
  const displaySummary = showTranslation ? (translation?.summary || transcript?.summary) : transcript?.summary;
  const displayKeywords = showTranslation ? (translation?.keywords || transcript?.keywords || []) : (transcript?.keywords || []);
  const displayTopics = showTranslation ? (translation?.topics || transcript?.topics || []) : (transcript?.topics || []);
  const displayIntent = showTranslation ? (translation?.intent || transcript?.intent) : transcript?.intent;

  async function handleTranslateToggle() {
    if (!transcript) return;
    if (showTranslation) {
      setShowTranslation(false);
      return;
    }
    if (!translation) {
      await onTranslate(job.job_id);
    }
    setShowTranslation(true);
  }

  return (
    <div className="space-y-4">
      <Card
        title={job.title || "Transcript Detail"}
        subtitle={`${job.source_type.toUpperCase()} • ${job.language?.toUpperCase() || "auto"} • ${job.duration_sec != null ? `${job.duration_sec}s` : "duration pending"}`}
        action={transcript ? (
          <button
            type="button"
            onClick={() => void handleTranslateToggle()}
            disabled={translating}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-semibold text-brand-navy transition-colors hover:bg-surface-sunken disabled:cursor-not-allowed disabled:opacity-70"
          >
            <Languages className="h-4 w-4" />
            {showTranslation ? "원문 보기" : translating ? "번역 중..." : "한국어 번역"}
          </button>
        ) : undefined}
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${sentimentTone(job.status === "failed" ? "negative" : transcript?.sentiment)}`}>
              {job.status === "failed" ? "Failed" : `Sentiment: ${transcript?.sentiment || "pending"}`}
            </span>
            <span className="rounded-full border border-border bg-surface-sunken px-3 py-1 text-xs font-mono text-text-secondary">
              {job.status.toUpperCase()} · {job.progress}%
            </span>
          </div>

          <ErrorBanner variant="error" message={job.error} />
          <ErrorBanner
            variant="info"
            message={job.status !== "completed" && job.status !== "failed" ? "This job is still processing. The panel will refresh every 5 seconds." : null}
          />
          <ErrorBanner
            variant="info"
            message={showTranslation ? "한국어 번역본을 보고 있습니다. 필요하면 다시 눌러 원문으로 돌아갈 수 있습니다." : null}
          />

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(260px,0.8fr)]">
            <section className="rounded-md border border-border bg-bg-primary p-4">
              <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-text-secondary">Summary</div>
              <p className="text-sm leading-7 text-text-primary">
                {displaySummary || "Summary will appear here once transcript extraction and analysis complete."}
              </p>
            </section>

            <section className="space-y-4 rounded-md border border-border bg-surface-raised p-4">
              <div>
                <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-text-secondary">Keywords</div>
                <div className="flex flex-wrap gap-2">
                  {displayKeywords.map((keyword) => (
                    <span key={keyword} className="rounded-full border border-brand-blue/30 bg-brand-blue/10 px-2.5 py-1 text-xs font-semibold text-brand-blue">
                      #{keyword}
                    </span>
                  ))}
                  {displayKeywords.length === 0 && (
                    <span className="text-sm text-text-muted">Keywords pending.</span>
                  )}
                </div>
              </div>

              <div>
                <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-text-secondary">Topics</div>
                <div className="flex flex-wrap gap-2">
                  {displayTopics.map((topic) => (
                    <span key={topic} className="rounded-full border border-brand-gold/40 bg-brand-gold/10 px-2.5 py-1 text-xs font-semibold text-brand-navy">
                      {topic}
                    </span>
                  ))}
                  {displayTopics.length === 0 && (
                    <span className="text-sm text-text-muted">Topics pending.</span>
                  )}
                </div>
              </div>

              <div>
                <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-text-secondary">Intent</div>
                <p className="text-sm leading-6 text-text-secondary">
                  {displayIntent || "Intent analysis pending."}
                </p>
              </div>
            </section>
          </div>
        </div>
      </Card>

      <Card
        title="Full Transcript"
        subtitle="Search within the extracted text, then copy the full transcript for downstream research."
        action={(
          <button
            type="button"
            onClick={() => void handleCopy()}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-semibold text-brand-navy transition-colors hover:bg-surface-sunken"
          >
            {copied ? <Check className="h-4 w-4 text-fin-positive" /> : <Copy className="h-4 w-4" />}
            {copied ? "Copied" : "Copy"}
          </button>
        )}
      >
        <div className="mb-4 flex items-center gap-2 rounded-md border border-border bg-surface-raised px-3 py-2">
          <Search className="h-4 w-4 text-text-muted" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search inside this transcript..."
            className="w-full bg-transparent text-sm text-text-primary outline-none"
          />
        </div>

        {transcript ? (
          <div className="max-h-[72vh] overflow-auto rounded-md border border-border bg-bg-primary p-4 font-mono text-sm leading-7 text-text-primary whitespace-pre-wrap">
            {highlightedTranscript}
          </div>
        ) : (
          <div className="rounded-md border border-dashed border-border-strong bg-bg-primary px-4 py-16 text-center text-sm text-text-muted">
            Transcript text will appear here once extraction completes.
          </div>
        )}
      </Card>
    </div>
  );
}
