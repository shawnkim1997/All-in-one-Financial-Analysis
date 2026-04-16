import type { ReactNode } from "react";

interface SectionHeadingProps {
  level?: 1 | 2 | 3;
  children: ReactNode;
  className?: string;
}

export function SectionHeading({
  level = 2,
  children,
  className = "",
}: SectionHeadingProps) {
  if (level === 1) {
    return <h1 className={`atlas-page-title ${className}`}>{children}</h1>;
  }

  if (level === 3) {
    return (
      <h3 className={`text-xs font-semibold uppercase tracking-[0.18em] text-text-secondary ${className}`}>
        {children}
      </h3>
    );
  }

  return <h2 className={`atlas-section-title ${className}`}>{children}</h2>;
}
