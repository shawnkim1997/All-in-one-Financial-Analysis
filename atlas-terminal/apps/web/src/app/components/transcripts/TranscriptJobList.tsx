"use client";

import { AlertTriangle, CheckCircle2, Clock3, LoaderCircle, Trash2 } from "lucide-react";
import { Card } from "../ui/Card";
import { LoadingPulse } from "../ui/LoadingPulse";
import type { VideoJob, VideoJobStatus } from "../../lib/video-transcript-types";

interface TranscriptJobListProps {
  jobs: VideoJob[];
  loading: boolean;
  selectedJobId: string | null;
  onSelectJob: (jobId: string) => void;
  onDeleteJob: (jobId: string) => Promise<unknown>;
}

const STATUS_LABELS: Record<VideoJobStatus, string> = {
  queued: "Queued",
  fetching: "Fetching",
  transcribing: "Transcribing",
  analyzing: "Analyzing",
  completed: "Completed",
  failed: "Failed",
};

const STATUS_TONES: Record<VideoJobStatus, string> = {
  queued: "border-border bg-surface-sunken text-text-secondary",
  fetching: "border-brand-gold/40 bg-brand-gold/10 text-brand-navy",
  transcribing: "border-brand-blue/40 bg-brand-blue/10 text-brand-blue",
  analyzing: "border-brand-gold/40 bg-brand-gold/10 text-brand-navy",
  completed: "border-fin-positive/40 bg-fin-positive/10 text-fin-positive",
  failed: "border-fin-negative/40 bg-fin-negative/10 text-fin-negative",
};

function StatusIcon({ status }: { status: VideoJobStatus }) {
  if (status === "completed") return <CheckCircle2 className="h-4 w-4" />;
  if (status === "failed") return <AlertTriangle className="h-4 w-4" />;
  if (status === "queued") return <Clock3 className="h-4 w-4" />;
  return <LoaderCircle className="h-4 w-4 animate-spin" />;
}

export function TranscriptJobList({
  jobs,
  loading,
  selectedJobId,
  onSelectJob,
  onDeleteJob,
}: TranscriptJobListProps) {
  return (
    <Card title="Recent Jobs" subtitle="Select a job to inspect progress, summary, and full transcript.">
      {loading && jobs.length === 0 ? (
        <LoadingPulse label="Loading transcript jobs..." height="h-48" />
      ) : jobs.length === 0 ? (
        <div className="rounded-md border border-dashed border-border-strong bg-bg-primary px-4 py-10 text-center text-sm text-text-muted">
          No transcript jobs yet. Submit a video, podcast clip, or subtitle file to get started.
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => {
            const active = selectedJobId === job.job_id;
            return (
              <div
                key={job.job_id}
                className={`w-full rounded-md border p-3 text-left transition-colors ${
                  active
                    ? "border-brand-gold bg-brand-gold/10"
                    : "border-border bg-surface-raised hover:bg-surface-sunken"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <button type="button" onClick={() => onSelectJob(job.job_id)} className="min-w-0 flex-1 text-left">
                    <div className="truncate font-semibold text-brand-navy">
                      {job.title || job.source_url}
                    </div>
                    <div className="mt-1 truncate font-mono text-xs text-text-muted">
                      {job.source_url}
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => void onDeleteJob(job.job_id)}
                    className="rounded-md border border-border px-2 py-1 text-text-muted transition-colors hover:bg-surface-sunken hover:text-fin-negative"
                    aria-label={`Delete transcript job ${job.title || job.job_id}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold ${STATUS_TONES[job.status]}`}>
                    <StatusIcon status={job.status} />
                    {STATUS_LABELS[job.status]}
                  </span>
                  <span className="text-xs font-mono text-text-muted">{job.progress}%</span>
                  {job.language && <span className="text-xs font-mono text-brand-blue">{job.language.toUpperCase()}</span>}
                  {job.duration_sec != null && <span className="text-xs font-mono text-text-muted">{job.duration_sec}s</span>}
                </div>

                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-sunken">
                  <div className="h-full rounded-full bg-brand-navy transition-[width] duration-500" style={{ width: `${Math.max(4, job.progress)}%` }} />
                </div>

                <div className="mt-2 text-[11px] uppercase tracking-[0.1em] text-text-muted">
                  {new Date(job.created_at).toLocaleString()}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
