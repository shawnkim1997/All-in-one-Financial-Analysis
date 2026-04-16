import type { ReactNode } from "react";

interface TabItem<T extends string> {
  key: T;
  label: ReactNode;
}

interface TabsProps<T extends string> {
  items: TabItem<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}

export function Tabs<T extends string>({ items, value, onChange, className = "" }: TabsProps<T>) {
  return (
    <div className={`flex gap-1 rounded-md border border-border bg-surface-sunken p-1 ${className}`}>
      {items.map((item) => {
        const active = item.key === value;
        return (
          <button
            key={item.key}
            type="button"
            onClick={() => onChange(item.key)}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-semibold transition-colors ${
              active
                ? "bg-brand-navy text-text-inverse shadow-sm"
                : "text-text-secondary hover:bg-surface-raised hover:text-brand-navy"
            }`}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
