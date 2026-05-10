"use client";

import { LoaderCircle, Search } from "lucide-react";
import type { VideoSearchHit } from "../../lib/video-transcript-types";

interface TranscriptSearchBarProps {
  query: string;
  searching: boolean;
  results: VideoSearchHit[];
  onQueryChange: (value: string) => void;
  onSelectHit: (jobId: string) => void;
}

function renderSnippet(snippet: string) {
  return snippet.split(/(\[[^\]]+\])/g).map((part, index) => (
    part.startsWith("[") && part.endsWith("]") ? (
      <mark key={`${part}-${index}`} className="rounded bg-brand-gold/30 px-0.5 text-brand-navy">
        {part.slice(1, -1)}
      </mark>
    ) : (
      <span key={`${part}-${index}`}>{part}</span>
    )
  ));
}

export function TranscriptSearchBar({
  query,
  searching,
  results,
  onQueryChange,
  onSelectHit,
}: TranscriptSearchBarProps) {
  const showResults = query.trim().length >= 2;

  return (
    <div className="atlas-card overflow-hidden">
      <div className="flex items-center gap-3 border-b border-border px-4 py-3">
        <Search className="h-4 w-4 text-text-muted" />
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Search saved transcripts for earnings, margins, AI, guidance..."
          className="w-full bg-transparent text-sm text-text-primary outline-none"
        />
        {searching && <LoaderCircle className="h-4 w-4 animate-spin text-brand-blue" />}
      </div>

      {showResults && (
        <div className="max-h-72 overflow-auto bg-surface-raised">
          {results.length > 0 ? (
            results.map((hit) => (
              <button
                key={`${hit.job_id}-${hit.rank}`}
                type="button"
                onClick={() => onSelectHit(hit.job_id)}
                className="block w-full border-b border-border px-4 py-3 text-left transition-colors hover:bg-surface-sunken"
              >
                <div className="truncate font-semibold text-brand-navy">
                  {hit.title || hit.job_id}
                </div>
                <div className="mt-1 text-sm leading-6 text-text-secondary">
                  {renderSnippet(hit.snippet)}
                </div>
              </button>
            ))
          ) : !searching ? (
            <div className="px-4 py-6 text-sm text-text-muted">
              No saved transcript matched this query yet.
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
