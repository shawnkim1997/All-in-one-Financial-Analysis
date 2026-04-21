export type TickerSuggestion = {
  ticker: string;
  name: string;
  exchange: string;
  assetType: "Equity" | "ETF" | "Commodity" | "Crypto" | "Index";
  country?: string;
  aliases: string[];
};

export const TICKER_DIRECTORY: TickerSuggestion[] = [
  {
    ticker: "BRK-B",
    name: "Berkshire Hathaway Inc. Class B",
    exchange: "NYSE",
    assetType: "Equity",
    country: "US",
    aliases: ["berkshire hathaway", "berkshire", "brk.b", "brkb", "buffett", "warren buffett", "버크셔해서웨이", "버크셔 해서웨이", "버크셔"],
  },
  {
    ticker: "BRK-A",
    name: "Berkshire Hathaway Inc. Class A",
    exchange: "NYSE",
    assetType: "Equity",
    country: "US",
    aliases: ["berkshire hathaway class a", "berkshire class a", "brk.a", "brka"],
  },
  {
    ticker: "000660.KS",
    name: "SK hynix Inc.",
    exchange: "KOSPI",
    assetType: "Equity",
    country: "KR",
    aliases: ["sk hynix", "skhynix", "hynix", "sk하이닉스", "sk 하이닉스", "에스케이하이닉스", "에스케이 하이닉스", "하이닉스"],
  },
  {
    ticker: "005930.KS",
    name: "Samsung Electronics Co., Ltd.",
    exchange: "KOSPI",
    assetType: "Equity",
    country: "KR",
    aliases: ["samsung", "samsung electronics", "삼성전자", "삼성 전자", "삼전"],
  },
  {
    ticker: "005380.KS",
    name: "Hyundai Motor Company",
    exchange: "KOSPI",
    assetType: "Equity",
    country: "KR",
    aliases: ["hyundai motor", "hyundai motors", "현대차", "현대자동차", "현대 자동차"],
  },
  {
    ticker: "035420.KS",
    name: "NAVER Corporation",
    exchange: "KOSPI",
    assetType: "Equity",
    country: "KR",
    aliases: ["naver", "네이버"],
  },
  {
    ticker: "035720.KS",
    name: "Kakao Corp.",
    exchange: "KOSPI",
    assetType: "Equity",
    country: "KR",
    aliases: ["kakao", "카카오"],
  },
  {
    ticker: "7203.T",
    name: "Toyota Motor Corporation",
    exchange: "Tokyo",
    assetType: "Equity",
    country: "JP",
    aliases: ["toyota", "toyota motor", "토요타", "도요타"],
  },
  {
    ticker: "6758.T",
    name: "Sony Group Corporation",
    exchange: "Tokyo",
    assetType: "Equity",
    country: "JP",
    aliases: ["sony", "sony group", "소니"],
  },
  {
    ticker: "NOV.F",
    name: "Novo Nordisk A/S",
    exchange: "Frankfurt",
    assetType: "Equity",
    country: "DK",
    aliases: ["novo nordisk eur", "novo nordisk euro", "novo", "novonordisk", "노보노디스크", "노보 노디스크"],
  },
  {
    ticker: "NVO",
    name: "Novo Nordisk A/S ADR",
    exchange: "NYSE",
    assetType: "Equity",
    country: "DK",
    aliases: ["novo nordisk adr", "nvo adr"],
  },
  {
    ticker: "AAPL",
    name: "Apple Inc.",
    exchange: "NASDAQ",
    assetType: "Equity",
    country: "US",
    aliases: ["apple", "애플"],
  },
  {
    ticker: "MSFT",
    name: "Microsoft Corporation",
    exchange: "NASDAQ",
    assetType: "Equity",
    country: "US",
    aliases: ["microsoft", "마이크로소프트"],
  },
  {
    ticker: "NVDA",
    name: "NVIDIA Corporation",
    exchange: "NASDAQ",
    assetType: "Equity",
    country: "US",
    aliases: ["nvidia", "엔비디아"],
  },
  {
    ticker: "TSLA",
    name: "Tesla, Inc.",
    exchange: "NASDAQ",
    assetType: "Equity",
    country: "US",
    aliases: ["tesla", "테슬라"],
  },
  {
    ticker: "GOOGL",
    name: "Alphabet Inc. Class A",
    exchange: "NASDAQ",
    assetType: "Equity",
    country: "US",
    aliases: ["google", "alphabet", "구글", "알파벳"],
  },
  {
    ticker: "META",
    name: "Meta Platforms, Inc.",
    exchange: "NASDAQ",
    assetType: "Equity",
    country: "US",
    aliases: ["meta", "facebook", "메타", "페이스북"],
  },
  {
    ticker: "AMZN",
    name: "Amazon.com, Inc.",
    exchange: "NASDAQ",
    assetType: "Equity",
    country: "US",
    aliases: ["amazon", "아마존"],
  },
  {
    ticker: "PLTR",
    name: "Palantir Technologies Inc.",
    exchange: "NASDAQ",
    assetType: "Equity",
    country: "US",
    aliases: ["palantir", "팔란티어"],
  },
  {
    ticker: "IREN",
    name: "IREN Limited",
    exchange: "NASDAQ",
    assetType: "Equity",
    country: "AU",
    aliases: ["iren", "iris energy"],
  },
  {
    ticker: "SPY",
    name: "SPDR S&P 500 ETF Trust",
    exchange: "NYSE Arca",
    assetType: "ETF",
    country: "US",
    aliases: ["s&p 500 etf", "sp500 etf", "snp 500 etf"],
  },
  {
    ticker: "QQQ",
    name: "Invesco QQQ Trust",
    exchange: "NASDAQ",
    assetType: "ETF",
    country: "US",
    aliases: ["nasdaq 100 etf", "nasdaq etf", "나스닥 etf"],
  },
  {
    ticker: "GC=F",
    name: "Gold Futures",
    exchange: "COMEX",
    assetType: "Commodity",
    aliases: ["gold", "금"],
  },
  {
    ticker: "SI=F",
    name: "Silver Futures",
    exchange: "COMEX",
    assetType: "Commodity",
    aliases: ["silver", "은"],
  },
  {
    ticker: "CL=F",
    name: "WTI Crude Oil Futures",
    exchange: "NYMEX",
    assetType: "Commodity",
    aliases: ["oil", "crude", "crude oil", "wti", "원유"],
  },
  {
    ticker: "BTC-USD",
    name: "Bitcoin USD",
    exchange: "Crypto",
    assetType: "Crypto",
    aliases: ["bitcoin", "btc", "비트코인"],
  },
  {
    ticker: "^GSPC",
    name: "S&P 500 Index",
    exchange: "Index",
    assetType: "Index",
    country: "US",
    aliases: ["s&p 500", "sp500", "snp500"],
  },
  {
    ticker: "^IXIC",
    name: "NASDAQ Composite",
    exchange: "Index",
    assetType: "Index",
    country: "US",
    aliases: ["nasdaq", "nasdaq composite", "나스닥"],
  },
];

const LEGACY_TICKER_ALIASES: Record<string, string> = {
  platinum: "PL=F",
  palladium: "PA=F",
  brent: "BZ=F",
  gas: "NG=F",
  "natural gas": "NG=F",
  copper: "HG=F",
  wheat: "ZW=F",
  corn: "ZC=F",
  soybeans: "ZS=F",
  coffee: "KC=F",
  sugar: "SB=F",
  gld: "GLD",
  slv: "SLV",
  uso: "USO",
  ung: "UNG",
  dbc: "DBC",
  gsg: "GSG",
};

function normalizeSearchText(value: string): string {
  return value
    .trim()
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[._/\\|()[\]{}'",:;]+/g, " ")
    .replace(/&/g, " and ")
    .replace(/-/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function compactSearchText(value: string): string {
  return normalizeSearchText(value).replace(/\s+/g, "");
}

function suggestionTerms(suggestion: TickerSuggestion): string[] {
  return [suggestion.ticker, suggestion.name, suggestion.exchange, suggestion.country ?? "", suggestion.assetType, ...suggestion.aliases].filter(Boolean);
}

function initials(value: string): string {
  return normalizeSearchText(value)
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .join("");
}

function scoreSuggestion(suggestion: TickerSuggestion, query: string, compactQuery: string): number {
  if (!query) return 0;

  const terms = suggestionTerms(suggestion);
  let best = 0;

  for (const term of terms) {
    const normalized = normalizeSearchText(term);
    const compact = compactSearchText(term);

    if (normalized === query) best = Math.max(best, term === suggestion.ticker ? 1200 : 1000);
    if (compact === compactQuery) best = Math.max(best, term === suggestion.ticker ? 1150 : 950);
    if (normalized.startsWith(query)) best = Math.max(best, term === suggestion.ticker ? 900 : 760);
    if (compact.startsWith(compactQuery)) best = Math.max(best, term === suggestion.ticker ? 850 : 720);
    if (normalized.includes(query)) best = Math.max(best, 520);
    if (compact.includes(compactQuery)) best = Math.max(best, 480);
    if (compactQuery.length >= 2 && initials(term) === compactQuery) best = Math.max(best, 420);
  }

  return best;
}

export function searchTickerSuggestions(raw: string, limit = 6): TickerSuggestion[] {
  const query = normalizeSearchText(raw);
  const compactQuery = compactSearchText(raw);
  if (!query) return [];

  return TICKER_DIRECTORY.map((suggestion) => ({
    suggestion,
    score: scoreSuggestion(suggestion, query, compactQuery),
  }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || a.suggestion.ticker.localeCompare(b.suggestion.ticker))
    .slice(0, limit)
    .map((item) => item.suggestion);
}

export function resolveTickerFromSearch(raw: string): string | null {
  const query = normalizeSearchText(raw);
  const compactQuery = compactSearchText(raw);
  if (!query) return null;

  for (const suggestion of TICKER_DIRECTORY) {
    const terms = suggestionTerms(suggestion);
    if (
      terms.some((term) => {
        const normalized = normalizeSearchText(term);
        const compact = compactSearchText(term);
        return normalized === query || compact === compactQuery;
      })
    ) {
      return suggestion.ticker;
    }
  }

  if (query.length >= 3) {
    const [top] = searchTickerSuggestions(raw, 1);
    if (!top) return null;
    const terms = suggestionTerms(top);
    const confidentPrefix = terms.some((term) => normalizeSearchText(term).startsWith(query) || compactSearchText(term).startsWith(compactQuery));
    if (confidentPrefix) return top.ticker;
  }

  return null;
}

export function normalizeTickerInput(raw: string): string {
  const cleaned = raw.trim();
  if (!cleaned) return "";
  const key = normalizeSearchText(cleaned);
  const mapped = resolveTickerFromSearch(cleaned) || LEGACY_TICKER_ALIASES[key] || cleaned;
  return mapped.toUpperCase();
}
