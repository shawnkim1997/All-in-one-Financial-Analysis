"use client";

import type { ReactNode } from "react";
import { AlertTriangle, Info, TriangleAlert } from "lucide-react";

export type BannerVariant = "error" | "info" | "warning";

interface ErrorBannerProps {
  message: string | null | undefined;
  variant?: BannerVariant;
  className?: string;
  icon?: ReactNode;
}

/**
 * Unified info / warning / error banner used across ATLAS pages.
 *
 * Design contract (preserved through the upcoming Morgan Stanley Blue redesign):
 *   - "info" / "warning": soft yellow border+background, never red.
 *     Used when data is partially missing or a dependency is degraded.
 *   - "error": red. Reserved for true failures the user must act on.
 *
 * If `message` is falsy, renders nothing (drop-in safe).
 */
export function ErrorBanner({ message, variant = "info", className = "", icon }: ErrorBannerProps) {
  if (!message) return null;
  const base = "rounded-md border px-4 py-3 text-sm shadow-card";
  const toneMap: Record<BannerVariant, string> = {
    info: "border-brand-gold/40 bg-brand-gold/10 text-brand-navy",
    warning: "border-fin-warning/40 bg-fin-warning/10 text-fin-warning",
    error: "border-fin-negative/40 bg-fin-negative/10 text-fin-negative",
  };
  const defaultIcon =
    variant === "error" ? <AlertTriangle className="h-4 w-4" /> :
    variant === "warning" ? <TriangleAlert className="h-4 w-4" /> :
    <Info className="h-4 w-4" />;
  return (
    <div
      className={`${base} ${toneMap[variant]} ${className}`}
      role={variant === "error" ? "alert" : "status"}
    >
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 shrink-0">{icon ?? defaultIcon}</span>
        <span>{message}</span>
      </div>
    </div>
  );
}
