import type { ReactNode } from "react";

interface CardProps {
  title?: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}

export function Card({
  title,
  subtitle,
  action,
  children,
  className = "",
  contentClassName = "",
}: CardProps) {
  return (
    <section className={`atlas-card ${className}`}>
      {(title || subtitle || action) && (
        <header className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div>
            {title && <h3 className="font-serif text-lg font-bold text-brand-navy">{title}</h3>}
            {subtitle && <p className="mt-1 text-sm text-text-secondary">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className={`p-5 ${contentClassName}`}>{children}</div>
    </section>
  );
}
