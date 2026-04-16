interface MetricChangeProps {
  value: number | null;
  suffix?: string;
  className?: string;
}

export function MetricChange({ value, suffix = "%", className = "" }: MetricChangeProps) {
  if (value == null || Number.isNaN(value)) {
    return <span className={`font-mono text-xs text-text-muted ${className}`}>N/A</span>;
  }

  const tone = value > 0 ? "text-fin-positive" : value < 0 ? "text-fin-negative" : "text-fin-neutral";
  return (
    <span className={`font-mono text-xs font-semibold ${tone} ${className}`}>
      {value > 0 ? "+" : ""}
      {value.toFixed(1)}
      {suffix}
    </span>
  );
}
