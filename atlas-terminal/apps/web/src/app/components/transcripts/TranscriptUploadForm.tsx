"use client";

import { Link2, PlayCircle, UploadCloud, type LucideIcon } from "lucide-react";
import { useState } from "react";
import { Card } from "../ui/Card";
import type { VideoSourceType } from "../../lib/video-transcript-types";

interface TranscriptUploadFormProps {
  submitting: boolean;
  onSubmitSource: (url: string, sourceType: VideoSourceType, language?: string) => Promise<unknown>;
  onUploadMedia: (file: File, language?: string) => Promise<unknown>;
}

type InputMode = "youtube" | "url" | "upload";

const TABS: Array<{ id: InputMode; label: string; icon: LucideIcon }> = [
  { id: "youtube", label: "YouTube", icon: PlayCircle },
  { id: "url", label: "Web URL", icon: Link2 },
  { id: "upload", label: "Upload", icon: UploadCloud },
];

export function TranscriptUploadForm({ submitting, onSubmitSource, onUploadMedia }: TranscriptUploadFormProps) {
  const [mode, setMode] = useState<InputMode>("youtube");
  const [sourceValue, setSourceValue] = useState("");
  const [language, setLanguage] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  async function handleSubmit() {
    setLocalError(null);
    try {
      if (mode === "upload") {
        if (!selectedFile) {
          setLocalError("Choose an mp4, audio file, or subtitle file first.");
          return;
        }
        await onUploadMedia(selectedFile, language);
        setSelectedFile(null);
        return;
      }

      if (!sourceValue.trim()) {
        setLocalError(mode === "youtube" ? "Paste a YouTube URL to continue." : "Paste a media URL or local file path to continue.");
        return;
      }

      await onSubmitSource(sourceValue.trim(), mode === "youtube" ? "youtube" : "url", language);
      setSourceValue("");
    } catch {
      // Parent hook already surfaces the actionable error banner.
    }
  }

  return (
    <Card
      title="New Transcript Job"
      subtitle="YouTube captions are tried first, then local Whisper transcription. Gemini analysis uses the key saved in Settings."
    >
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-2">
          {TABS.map(({ id, label, icon: Icon }) => {
            const active = mode === id;
            return (
              <button
                key={id}
                type="button"
                onClick={() => setMode(id)}
                className={`flex items-center justify-center gap-2 rounded-md border px-3 py-2 text-sm font-semibold transition-colors ${
                  active
                    ? "border-brand-navy bg-brand-navy text-white"
                    : "border-border bg-bg-card text-text-secondary hover:bg-surface-sunken hover:text-brand-navy"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            );
          })}
        </div>

        {mode === "upload" ? (
          <label className="block rounded-md border border-dashed border-border-strong bg-bg-primary p-4 text-sm text-text-secondary">
            <span className="mb-2 block font-semibold text-brand-navy">Upload local media</span>
            <input
              type="file"
              accept="video/*,audio/*,.mp4,.mov,.m4a,.mp3,.wav,.srt,.vtt"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              className="block w-full text-sm text-text-secondary file:mr-3 file:rounded-md file:border-0 file:bg-brand-navy file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-brand-blue"
            />
            <span className="mt-2 block text-xs text-text-muted">
              Supported: mp4, mov, m4a, mp3, wav, srt, vtt
            </span>
            {selectedFile && (
              <span className="mt-3 block rounded-md border border-brand-gold/40 bg-brand-gold/10 px-3 py-2 font-mono text-xs text-brand-navy">
                {selectedFile.name}
              </span>
            )}
          </label>
        ) : (
          <label className="block">
            <span className="mb-1.5 block text-sm text-text-muted">
              {mode === "youtube" ? "YouTube URL" : "Video URL or local path"}
            </span>
            <input
              value={sourceValue}
              onChange={(event) => setSourceValue(event.target.value)}
              placeholder={mode === "youtube" ? "https://www.youtube.com/watch?v=..." : "https://example.com/video.mp4 or /Users/.../clip.mp4"}
              className="w-full rounded-md border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary outline-none transition-colors focus:border-brand-blue"
            />
          </label>
        )}

        <label className="block">
          <span className="mb-1.5 block text-sm text-text-muted">Language hint (optional)</span>
          <input
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
            placeholder="en, ko, ja ..."
            className="w-full rounded-md border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary outline-none transition-colors focus:border-brand-blue"
          />
        </label>

        {localError && (
          <div className="rounded-md border border-fin-warning/40 bg-fin-warning/10 px-3 py-2 text-sm text-fin-warning">
            {localError}
          </div>
        )}

        <button
          type="button"
          onClick={() => void handleSubmit()}
          disabled={submitting}
          className="w-full rounded-md bg-brand-navy px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-blue disabled:cursor-not-allowed disabled:opacity-70"
        >
          {submitting ? "Submitting..." : "Submit Transcript Job"}
        </button>
      </div>
    </Card>
  );
}
