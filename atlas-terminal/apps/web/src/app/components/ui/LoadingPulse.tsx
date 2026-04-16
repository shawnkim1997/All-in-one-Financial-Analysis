"use client";

import { LoaderCircle } from "lucide-react";

interface LoadingPulseProps {
  label?: string;
  height?: string;
  className?: string;
}

export function LoadingPulse({ label = "Loading…", height = "h-64", className = "" }: LoadingPulseProps) {
  return (
    <div className={`flex items-center justify-center ${height} ${className}`}>
      <div className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-raised px-4 py-2 text-sm text-brand-navy shadow-card">
        <LoaderCircle className="h-4 w-4 animate-spin text-brand-blue" />
        <span className="font-mono">{label}</span>
      </div>
    </div>
  );
}
