"use client";

import { useEffect, useMemo, useState } from "react";
import { useTicker } from "../lib/use-ticker";

interface NewsItem {
  title: string;
  source: string;
  url: string;
  published_at: string;
  summary: string;
}

type CategoryFilter = "all" | "earnings" | "fed" | "rates" | "crypto" | "stocks";

const STOPWORDS = new Set([
  "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HER", "WAS", "ONE", "OUR", "OUT",
  "DAY", "GET", "HAS", "HIM", "HIS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "WAY", "WHO",
  "BOY", "DID", "CAR", "CEO", "CFO", "IPO", "LLC", "ETF", "USD", "GDP", "CNN", "BBC", "WSJ", "BAR",
  "BIG", "SAY", "PUT", "END", "SET", "RUN", "LOT", "LET", "TOO", "TWO", "VIA", "APP", "WEB",
]);

function extractTickers(text: string): string[] {
  const upper = text.toUpperCase();
  const re = /\b([A-Z]{2,5})\b/g;
  const found = new Set<string>();
  let m: RegExpExecArray | null;
  while ((m = re.exec(upper)) !== null) {
    const w = m[1];
    if (STOPWORDS.has(w)) continue;
    found.add(w);
  }
  return Array.from(found).slice(0, 16);
}

/** Many publishers (Yahoo, Bloomberg, WSJ, …) send X-Frame-Options / CSP so embedded iframes show a blank/broken page. */
function isIframeEmbeddingBlocked(url: string): boolean {
  try {
    const host = new URL(url).hostname.toLowerCase().replace(/^www\./, "");
    const suffixes = [
      "yahoo.com",
      "yahoo.co.jp",
      "bloomberg.com",
      "bloomberg.net",
      "wsj.com",
      "reuters.com",
      "ft.com",
      "cnbc.com",
      "marketwatch.com",
      "seekingalpha.com",
      "nytimes.com",
      "washingtonpost.com",
      "theguardian.com",
      "bbc.com",
      "bbc.co.uk",
      "forbes.com",
      "investing.com",
      "apnews.com",
      "afp.com",
    ];
    return suffixes.some((s) => host === s || host.endsWith(`.${s}`));
  } catch {
    return true;
  }
}

function matchesCategory(cat: CategoryFilter, title: string, summary: string): boolean {
  const t = `${title} ${summary}`;
  if (cat === "all") return true;
  if (cat === "earnings") return /earnings|EPS|guidance|beat|miss|revenue|quarter|Q[1-4]\s/i.test(t);
  if (cat === "fed") return /fed|FOMC|Powell|rate cut|rate hike|central bank/i.test(t);
  if (cat === "rates") return /treasury|yield|bond|10-?year|inflation|CPI|PCE/i.test(t);
  if (cat === "crypto") return /bitcoin|btc|eth|ethereum|crypto|solana|coinbase/i.test(t);
  if (cat === "stocks") return /stock|shares|Nasdaq|NYSE|S&P|equity|trading|investor/i.test(t);
  return true;
}

interface QuoteRow {
  current_price: number | null;
  change_pct: number | null;
}

export default function NewsPage() {
  const { ticker } = useTicker();
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<NewsItem | null>(null);
  const [category, setCategory] = useState<CategoryFilter>("all");
  const [keyword, setKeyword] = useState("");
  const [mentionQuotes, setMentionQuotes] = useState<Record<string, QuoteRow>>({});

  useEffect(() => {
    setLoading(true);
    setSelected(null);
    fetch(`/api/news/${ticker}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        setNews(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [ticker]);

  const filtered = useMemo(() => {
    const kw = keyword.trim().toLowerCase();
    return news.filter((item) => {
      if (!matchesCategory(category, item.title, item.summary || "")) return false;
      if (!kw) return true;
      const blob = `${item.title} ${item.summary || ""}`.toLowerCase();
      return blob.includes(kw);
    });
  }, [news, category, keyword]);

  useEffect(() => {
    if (!selected) {
      setMentionQuotes({});
      return;
    }
    const syms = extractTickers(`${selected.title} ${selected.summary || ""}`).filter((s) => s !== ticker.toUpperCase());
    const take = syms.slice(0, 8);
    if (take.length === 0) {
      setMentionQuotes({});
      return;
    }
    let cancelled = false;
    Promise.all(
      take.map((sym) =>
        fetch(`/api/market/quote/${encodeURIComponent(sym)}`)
          .then((r) => (r.ok ? r.json() : null))
          .then((j) => ({ sym, j }))
      )
    ).then((rows) => {
      if (cancelled) return;
      const next: Record<string, QuoteRow> = {};
      for (const { sym, j } of rows) {
        if (j && typeof j === "object") {
          next[sym] = {
            current_price: typeof j.current_price === "number" ? j.current_price : null,
            change_pct: typeof j.change_pct === "number" ? j.change_pct : null,
          };
        }
      }
      setMentionQuotes(next);
    });
    return () => {
      cancelled = true;
    };
  }, [selected, ticker]);

  if (loading)
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-accent-green animate-pulse font-mono">Loading...</div>
      </div>
    );

  const cats: { key: CategoryFilter; label: string }[] = [
    { key: "all", label: "All" },
    { key: "earnings", label: "Earnings" },
    { key: "fed", label: "Fed / policy" },
    { key: "rates", label: "Rates / inflation" },
    { key: "crypto", label: "Crypto" },
    { key: "stocks", label: "Equities" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">
        <span className="text-accent-green">{ticker}</span> News Feed
      </h1>

      <div className="flex flex-wrap items-center gap-2 mb-3">
        {cats.map((c) => (
          <button
            key={c.key}
            type="button"
            onClick={() => setCategory(c.key)}
            className={`px-3 py-1 rounded-md text-xs font-medium border ${
              category === c.key
                ? "bg-accent-green/15 border-accent-green text-accent-green"
                : "bg-bg-card border-border text-text-secondary hover:border-accent-green/40"
            }`}
          >
            {c.label}
          </button>
        ))}
        <input
          type="search"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="Keyword filter…"
          className="ml-2 flex-1 min-w-[140px] max-w-xs bg-bg-card border border-border rounded-md px-3 py-1 text-sm text-text-primary placeholder:text-text-muted"
        />
      </div>

      <div className="text-text-muted text-sm mb-4">
        {filtered.length} of {news.length} articles (Finviz, Google News, Yahoo)
      </div>

      <div className="flex gap-4" style={{ height: "calc(100vh - 200px)" }}>
        <div
          className={`${selected ? "w-[340px] shrink-0" : "w-full"} overflow-y-auto transition-all duration-200`}
        >
          <div className="space-y-2">
            {filtered.length > 0 ? (
              filtered.map((item) => {
                const mentions = extractTickers(`${item.title} ${item.summary || ""}`).slice(0, 5);
                return (
                  <div
                    key={item.url}
                    onClick={() => setSelected(item)}
                    className={`cursor-pointer rounded-lg p-3 transition-all border ${
                      selected?.url === item.url
                        ? "bg-accent-green/10 border-accent-green/50"
                        : "bg-bg-card border-border hover:border-accent-green/30"
                    }`}
                  >
                    <h3
                      className={`text-sm font-semibold leading-snug ${
                        selected?.url === item.url ? "text-accent-green" : "text-text-primary"
                      }`}
                    >
                      {item.title}
                    </h3>
                    {mentions.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {mentions.map((m) => (
                          <span
                            key={m}
                            className="text-[10px] px-1.5 py-0.5 bg-bg-primary border border-border rounded font-mono text-accent-blue"
                          >
                            {m}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="flex items-center gap-2 mt-2">
                      {item.source && (
                        <span className="text-[10px] px-1.5 py-0.5 bg-accent-blue/10 text-accent-blue rounded font-mono">
                          {item.source}
                        </span>
                      )}
                      <span className="text-text-muted text-[10px] font-mono">{item.published_at}</span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-text-muted text-center py-12">No articles match filters</div>
            )}
          </div>
        </div>

        {selected && (
          <div className="flex-1 flex flex-col bg-bg-card border border-border rounded-lg overflow-hidden min-w-0">
            <div className="px-5 py-4 border-b border-border bg-bg-primary/50 shrink-0">
              <h2 className="text-base font-bold text-text-primary leading-snug mb-2">{selected.title}</h2>
              {Object.keys(mentionQuotes).length > 0 && (
                <div className="mb-3 flex flex-wrap gap-2">
                  {Object.entries(mentionQuotes).map(([sym, q]) => (
                    <div
                      key={sym}
                      className="text-[11px] font-mono px-2 py-1 rounded border border-border bg-bg-primary"
                    >
                      <span className="text-accent-green">{sym}</span>
                      {q.change_pct != null && (
                        <span className={q.change_pct >= 0 ? " text-accent-green" : " text-accent-red"}>
                          {" "}
                          {q.change_pct >= 0 ? "+" : ""}
                          {q.change_pct.toFixed(2)}%
                        </span>
                      )}
                      {q.current_price != null && (
                        <span className="text-text-muted"> @ ${q.current_price.toFixed(2)}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
              <div className="flex items-center gap-3">
                {selected.source && (
                  <span className="text-xs px-2 py-0.5 bg-accent-blue/10 text-accent-blue rounded font-mono">
                    {selected.source}
                  </span>
                )}
                <span className="text-text-muted text-xs font-mono">{selected.published_at}</span>
                <a
                  href={selected.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-auto text-xs px-3 py-1 bg-accent-green text-bg-primary rounded-md font-semibold hover:opacity-90 transition-opacity"
                >
                  Open Original ↗
                </a>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  className="text-text-muted hover:text-text-primary transition-colors text-base"
                >
                  ✕
                </button>
              </div>
            </div>
            <div className="flex-1 relative min-h-[320px] bg-bg-secondary overflow-auto">
              {isIframeEmbeddingBlocked(selected.url) ? (
                <div className="flex flex-col items-center justify-center h-full min-h-[280px] p-8 text-center">
                  <p className="text-text-muted text-sm mb-2 max-w-md">
                    이 출처(Yahoo·Bloomberg 등)는 보안 정책으로 <span className="text-text-primary font-semibold">미리보기 iframe</span>을
                    허용하지 않습니다. 원문은 새 탭에서 열어 주세요.
                  </p>
                  {selected.summary ? (
                    <div className="w-full max-w-2xl mt-4 mb-6 text-left rounded-lg border border-border bg-bg-card p-4">
                      <div className="text-text-muted text-xs font-semibold uppercase tracking-wide mb-2">Summary</div>
                      <p className="text-text-secondary text-sm leading-relaxed whitespace-pre-wrap">{selected.summary}</p>
                    </div>
                  ) : null}
                  <a
                    href={selected.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent-green text-bg-primary rounded-lg font-semibold text-sm hover:opacity-90"
                  >
                    원문 열기 ↗
                  </a>
                </div>
              ) : (
                <iframe
                  src={selected.url}
                  className="w-full h-full min-h-[480px] border-0 bg-bg-primary"
                  sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
                  referrerPolicy="no-referrer"
                  title={selected.title}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
