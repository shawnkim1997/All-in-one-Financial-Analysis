export type VideoSourceType = "youtube" | "url" | "local";
export type VideoJobStatus = "queued" | "fetching" | "transcribing" | "analyzing" | "completed" | "failed";

export interface VideoJob {
  job_id: string;
  status: VideoJobStatus;
  source_url: string;
  source_type: VideoSourceType;
  progress: number;
  error: string | null;
  title: string | null;
  duration_sec: number | null;
  language: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface VideoTranscript {
  job_id: string;
  text: string;
  summary: string | null;
  keywords: string[];
  topics: string[];
  sentiment: "positive" | "neutral" | "negative" | null;
  intent: string | null;
}

export interface VideoSearchHit {
  job_id: string;
  title: string | null;
  snippet: string;
  rank: number;
}

export interface VideoJobDetailResponse {
  job: VideoJob;
  transcript: VideoTranscript | null;
}

export interface VideoTranslation {
  job_id: string;
  target_language: string;
  summary: string | null;
  keywords: string[];
  topics: string[];
  intent: string | null;
  text: string;
}
