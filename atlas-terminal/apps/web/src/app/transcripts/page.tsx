"use client";

import { startTransition, useDeferredValue, useEffect, useState } from "react";
import { TranscriptDetailPanel } from "../components/transcripts/TranscriptDetailPanel";
import { TranscriptJobList } from "../components/transcripts/TranscriptJobList";
import { TranscriptSearchBar } from "../components/transcripts/TranscriptSearchBar";
import { TranscriptUploadForm } from "../components/transcripts/TranscriptUploadForm";
import { ErrorBanner } from "../components/ui/ErrorBanner";
import { SectionHeading } from "../components/ui/SectionHeading";
import { useVideoTranscript } from "../lib/use-video-transcript";

export default function TranscriptsPage() {
  const {
    jobs,
    selectedJobId,
    detail,
    searchResults,
    translation,
    loadingJobs,
    loadingDetail,
    submitting,
    searching,
    translating,
    error,
    selectJob,
    submitSource,
    uploadMedia,
    deleteTranscriptJob,
    searchVideos,
    clearSearch,
    translateJobToKorean,
  } = useVideoTranscript();
  const [searchQuery, setSearchQuery] = useState("");
  const deferredQuery = useDeferredValue(searchQuery);

  useEffect(() => {
    if (deferredQuery.trim().length < 2) {
      clearSearch();
      return undefined;
    }

    const timer = window.setTimeout(() => {
      void searchVideos(deferredQuery.trim());
    }, 250);

    return () => window.clearTimeout(timer);
  }, [clearSearch, deferredQuery, searchVideos]);

  return (
    <div className="atlas-page">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <SectionHeading level={1}>Transcripts</SectionHeading>
          <p className="atlas-page-subtitle">
            Extract captions or speech from YouTube clips, local media, and direct video URLs, then store the results for analysis and full-text search.
          </p>
        </div>
      </div>

      <ErrorBanner variant="error" message={error} />

      <TranscriptSearchBar
        query={searchQuery}
        searching={searching}
        results={searchResults}
        onQueryChange={setSearchQuery}
        onSelectHit={(jobId) => {
          startTransition(() => {
            selectJob(jobId);
          });
        }}
      />

      <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-4">
          <TranscriptUploadForm
            submitting={submitting}
            onSubmitSource={submitSource}
            onUploadMedia={uploadMedia}
          />
          <TranscriptJobList
            jobs={jobs}
            loading={loadingJobs}
            selectedJobId={selectedJobId}
            onSelectJob={selectJob}
            onDeleteJob={deleteTranscriptJob}
          />
        </div>

        <TranscriptDetailPanel
          detail={detail}
          loading={loadingDetail}
          translation={translation}
          translating={translating}
          onTranslate={translateJobToKorean}
        />
      </div>
    </div>
  );
}
