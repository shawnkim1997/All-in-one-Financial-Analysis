"use client";

import { useCallback, useEffect, useState } from "react";
import type { VideoJob, VideoJobDetailResponse, VideoSearchHit, VideoSourceType, VideoTranslation } from "./video-transcript-types";

const PENDING_STATUSES = new Set(["queued", "fetching", "transcribing", "analyzing"]);

function getGeminiHeader(): HeadersInit {
  if (typeof window === "undefined") return {};
  const apiKey = (localStorage.getItem("atlas_gemini_key") || "").trim();
  return apiKey ? { "x-gemini-api-key": apiKey } : {};
}

function sortJobs(jobs: VideoJob[]): VideoJob[] {
  return [...jobs].sort((left, right) => right.created_at.localeCompare(left.created_at));
}

export function useVideoTranscript() {
  const [jobs, setJobs] = useState<VideoJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [detail, setDetail] = useState<VideoJobDetailResponse | null>(null);
  const [searchResults, setSearchResults] = useState<VideoSearchHit[]>([]);
  const [translationsByJob, setTranslationsByJob] = useState<Record<string, VideoTranslation>>({});
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [searching, setSearching] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const request = useCallback(async (path: string, init?: RequestInit, json = true) => {
    const response = await fetch(`/api/video${path}`, {
      ...init,
      headers: {
        ...(json ? { "Content-Type": "application/json" } : {}),
        ...getGeminiHeader(),
        ...(init?.headers ?? {}),
      },
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || `Request failed with status ${response.status}.`);
    }

    return response.json();
  }, []);

  const refreshJobs = useCallback(async (showSpinner = true) => {
    if (showSpinner) setLoadingJobs(true);
    try {
      const rows = (await request("/jobs")) as VideoJob[];
      const sorted = sortJobs(rows);
      setJobs(sorted);
      setSelectedJobId((current) => {
        if (current && sorted.some((job) => job.job_id === current)) {
          return current;
        }
        return sorted[0]?.job_id ?? null;
      });
      if (sorted.length === 0) {
        setDetail(null);
      }
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Failed to load transcript jobs.");
    } finally {
      if (showSpinner) setLoadingJobs(false);
    }
  }, [request]);

  const loadJobDetail = useCallback(async (jobId: string, showSpinner = true) => {
    if (showSpinner) setLoadingDetail(true);
    try {
      const payload = (await request(`/jobs/${jobId}`)) as VideoJobDetailResponse;
      setDetail(payload);
      setJobs((current) => {
        const merged = current.some((job) => job.job_id === payload.job.job_id)
          ? current.map((job) => (job.job_id === payload.job.job_id ? payload.job : job))
          : [payload.job, ...current];
        return sortJobs(merged);
      });
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Failed to load transcript detail.");
    } finally {
      if (showSpinner) setLoadingDetail(false);
    }
  }, [request]);

  useEffect(() => {
    void refreshJobs();
  }, [refreshJobs]);

  useEffect(() => {
    if (!selectedJobId) return;
    void loadJobDetail(selectedJobId);
  }, [selectedJobId, loadJobDetail]);

  useEffect(() => {
    if (!selectedJobId || !detail || detail.job.job_id !== selectedJobId) return undefined;
    if (!PENDING_STATUSES.has(detail.job.status)) return undefined;

    const timer = window.setInterval(() => {
      void loadJobDetail(selectedJobId, false);
      void refreshJobs(false);
    }, 5000);

    return () => window.clearInterval(timer);
  }, [detail, loadJobDetail, refreshJobs, selectedJobId]);

  const submitSource = useCallback(async (url: string, sourceType: VideoSourceType, language?: string) => {
    setSubmitting(true);
    try {
      const job = (await request("/submit", {
        method: "POST",
        body: JSON.stringify({
          url,
          source_type: sourceType,
          language: language?.trim() || null,
        }),
      })) as VideoJob;
      setJobs((current) => sortJobs([job, ...current.filter((item) => item.job_id !== job.job_id)]));
      setSelectedJobId(job.job_id);
      setDetail({ job, transcript: null });
      setError(null);
      return job;
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Failed to submit transcript job.";
      setError(message);
      throw requestError;
    } finally {
      setSubmitting(false);
    }
  }, [request]);

  const uploadMedia = useCallback(async (file: File, language?: string) => {
    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (language?.trim()) {
        formData.append("language", language.trim());
      }
      const job = (await request("/upload", {
        method: "POST",
        body: formData,
      }, false)) as VideoJob;
      setJobs((current) => sortJobs([job, ...current.filter((item) => item.job_id !== job.job_id)]));
      setSelectedJobId(job.job_id);
      setDetail({ job, transcript: null });
      setError(null);
      return job;
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Failed to upload media.";
      setError(message);
      throw requestError;
    } finally {
      setSubmitting(false);
    }
  }, [request]);

  const deleteTranscriptJob = useCallback(async (jobId: string) => {
    try {
      await request(`/jobs/${jobId}`, { method: "DELETE" });
      setJobs((current) => {
        const nextJobs = current.filter((job) => job.job_id !== jobId);
        if (selectedJobId === jobId) {
          setSelectedJobId(nextJobs[0]?.job_id ?? null);
          if (nextJobs.length === 0) {
            setDetail(null);
          }
        }
        return nextJobs;
      });
      setTranslationsByJob((current) => {
        const next = { ...current };
        delete next[jobId];
        return next;
      });
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Failed to delete transcript job.");
    }
  }, [request, selectedJobId]);

  const searchVideos = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const rows = (await request(`/search?q=${encodeURIComponent(query.trim())}`)) as VideoSearchHit[];
      setSearchResults(rows);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Failed to search transcripts.");
    } finally {
      setSearching(false);
    }
  }, [request]);

  const clearSearch = useCallback(() => {
    setSearchResults([]);
  }, []);

  const translateJobToKorean = useCallback(async (jobId: string) => {
    setTranslating(true);
    try {
      const payload = (await request(`/jobs/${jobId}/translate?target_language=ko`, {
        method: "POST",
      })) as VideoTranslation;
      setTranslationsByJob((current) => ({
        ...current,
        [jobId]: payload,
      }));
      setError(null);
      return payload;
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Failed to translate transcript.");
      throw requestError;
    } finally {
      setTranslating(false);
    }
  }, [request]);

  return {
    jobs,
    selectedJobId,
    detail,
    searchResults,
    translation: detail ? translationsByJob[detail.job.job_id] ?? null : null,
    loadingJobs,
    loadingDetail,
    submitting,
    searching,
    translating,
    error,
    selectJob: setSelectedJobId,
    refreshJobs,
    submitSource,
    uploadMedia,
    deleteTranscriptJob,
    searchVideos,
    clearSearch,
    translateJobToKorean,
  };
}
