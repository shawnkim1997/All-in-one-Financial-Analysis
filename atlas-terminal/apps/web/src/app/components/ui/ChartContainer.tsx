import type { ReactNode } from "react";

interface ChartContainerProps {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}

export function ChartContainer({
  title,
  subtitle,
  children,
  className = "",
}: ChartContainerProps) {
  return (
    <section className={`atlas-card p-5 ${className}`}>
      {(title || subtitle) && (
        <div className="mb-4">
          {title && <h3 className="font-serif text-lg font-bold text-brand-navy">{title}</h3>}
          {subtitle && <p className="mt-1 text-sm text-text-secondary">{subtitle}</p>}
        </div>
      )}
      {children}
    </section>
  );
}
