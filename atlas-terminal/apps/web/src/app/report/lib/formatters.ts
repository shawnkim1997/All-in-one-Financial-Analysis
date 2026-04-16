/**
 * Formatting + lookup helpers shared across every report section.
 *
 * `getValue` implements the multi-key column lookup pattern documented in
 * `claude.md` §2.5 — yfinance and yahooquery use different field names for the
 * same metric, so callers pass a pipe-separated list of candidates.
 */

/** Map ISO currency codes → display symbol and decimal places. */
const CURRENCY_MAP: Record<string, { sym: string; decimals: number }> = {
  USD: { sym: "$",  decimals: 2 },
  KRW: { sym: "₩",  decimals: 0 },
  JPY: { sym: "¥",  decimals: 0 },
  CNY: { sym: "¥",  decimals: 2 },
  HKD: { sym: "HK$", decimals: 2 },
  EUR: { sym: "€",  decimals: 2 },
  GBP: { sym: "£",  decimals: 2 },
  INR: { sym: "₹",  decimals: 0 },
  TWD: { sym: "NT$", decimals: 0 },
  SGD: { sym: "S$",  decimals: 2 },
  CAD: { sym: "C$",  decimals: 2 },
  AUD: { sym: "A$",  decimals: 2 },
};

export function currencySymbol(currency?: string | null): string {
  if (!currency) return "$";
  return CURRENCY_MAP[currency.toUpperCase()]?.sym ?? currency;
}

export function fmtB(v: number | null | undefined, currency?: string | null): string {
  if (v == null || isNaN(v)) return "N/A";
  const s = currencySymbol(currency);
  if (Math.abs(v) >= 1e12) return `${s}${(v / 1e12).toFixed(1)}T`;
  if (Math.abs(v) >= 1e9)  return `${s}${(v / 1e9).toFixed(1)}B`;
  if (Math.abs(v) >= 1e6)  return `${s}${(v / 1e6).toFixed(0)}M`;
  return `${s}${v.toFixed(0)}`;
}

export function fmtPct(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return "N/A";
  return `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;
}

export function fmtPrice(v: number | null | undefined, currency?: string | null): string {
  if (v == null || isNaN(v)) return "N/A";
  const info = CURRENCY_MAP[(currency ?? "USD").toUpperCase()] ?? { sym: currencySymbol(currency), decimals: 2 };
  return `${info.sym}${v.toLocaleString("en-US", { minimumFractionDigits: info.decimals, maximumFractionDigits: info.decimals })}`;
}

export function getValue(data: Record<string, unknown>, key: string): number | null {
  for (const k of key.split("|")) {
    const v = data[k.trim()];
    if (v != null && typeof v === "number" && !isNaN(v)) return v;
  }
  return null;
}

export async function fetchJson<T = unknown>(url: string, opts?: RequestInit): Promise<T | null> {
  try {
    const r = await fetch(url, opts);
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

/**
 * Tiny markdown→HTML used by AI section bodies. Intentionally minimal — we
 * trust Gemini's structured output and avoid pulling in a full markdown lib.
 */
export function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n- /g, "<br/>&bull; ")
    .replace(/\n\* /g, "<br/>&bull; ")
    .replace(/\n/g, "<br/>");
}
