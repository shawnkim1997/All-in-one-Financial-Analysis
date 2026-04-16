import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "default" | "positive" | "negative" | "accent";
  className?: string;
}

const toneClass: Record<NonNullable<StatCardProps["tone"]>, string> = {
  default: "text-text-primary",
  positive: "text-fin-positive",
  negative: "text-fin-negative",
  accent: "text-brand-blue",
};

export function StatCard({
  label,
  value,
  detail,
  tone = "default",
  className = "",
}: StatCardProps) {
  return (
    <div className={`atlas-card p-4 ${className}`}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-text-muted">{label}</div>
      <div className={`mt-2 font-mono text-[22px] font-bold leading-tight ${toneClass[tone]}`}>{value}</div>
      {detail && <div className="mt-2 text-xs text-text-secondary">{detail}</div>}
    </div>
  );
}
