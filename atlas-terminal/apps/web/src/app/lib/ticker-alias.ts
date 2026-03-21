const TICKER_ALIASES: Record<string, string> = {
  // Commodities (natural language -> futures ticker)
  gold: "GC=F",
  silver: "SI=F",
  platinum: "PL=F",
  palladium: "PA=F",
  oil: "CL=F",
  crude: "CL=F",
  "crude oil": "CL=F",
  brent: "BZ=F",
  gas: "NG=F",
  "natural gas": "NG=F",
  copper: "HG=F",
  wheat: "ZW=F",
  corn: "ZC=F",
  soybeans: "ZS=F",
  coffee: "KC=F",
  sugar: "SB=F",

  // Popular commodity ETFs
  gld: "GLD",
  slv: "SLV",
  uso: "USO",
  ung: "UNG",
  dbc: "DBC",
  gsg: "GSG",
};

export function normalizeTickerInput(raw: string): string {
  const cleaned = raw.trim();
  if (!cleaned) return "";
  const key = cleaned.toLowerCase();
  const mapped = TICKER_ALIASES[key] || cleaned;
  return mapped.toUpperCase();
}

