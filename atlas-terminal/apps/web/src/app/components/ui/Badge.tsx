import type { ReactNode } from "react";

interface BadgeProps {
  variant: "buy" | "sell" | "hold" | "neutral";
  children?: ReactNode;
  className?: string;
}

const badgeClasses: Record<BadgeProps["variant"], string> = {
  buy: "bg-fin-positive/10 text-fin-positive border-fin-positive/20",
  sell: "bg-fin-negative/10 text-fin-negative border-fin-negative/20",
  hold: "bg-brand-gold/15 text-brand-navy border-brand-gold/40",
  neutral: "bg-surface-sunken text-text-secondary border-border",
};

export function Badge({ variant, children, className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-bold uppercase tracking-[0.08em] ${badgeClasses[variant]} ${className}`}
    >
      {children ?? variant}
    </span>
  );
}
