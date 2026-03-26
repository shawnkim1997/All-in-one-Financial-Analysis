/** Match server `infer_filing_jurisdiction` for Filings page routing. */
export type FilingJurisdiction = "SEC" | "DART" | "EDINET";

export function inferFilingJurisdiction(ticker: string): FilingJurisdiction {
  const t = (ticker || "").trim().toUpperCase();
  if (t.endsWith(".KS") || t.endsWith(".KQ")) return "DART";
  if (t.endsWith(".T")) return "EDINET";
  return "SEC";
}
