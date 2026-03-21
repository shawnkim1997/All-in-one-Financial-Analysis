"use client";
import { useEffect, useState } from "react";
import { useTicker } from "../lib/use-ticker";

interface NewsItem {
  title: string;
  source: string;
  url: string;
  published_at: string;
  summary: string;
}

export default function NewsPage() {
  const { ticker } = useTicker();
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    setSelectedIdx(null);
    fetch(`/api/news/${ticker}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        setNews(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [ticker]);

  if (loading)
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-accent-green animate-pulse font-mono">Loading...</div>
      </div>
    );

  const selectedItem = selectedIdx !== null ? news[selectedIdx] : null;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">
        <span className="text-accent-green">{ticker}</span> News Feed
      </h1>

      <div className="text-text-muted text-sm mb-4">
        {news.length} articles from Finviz & Google News
      </div>

      <div className="flex gap-4" style={{ height: "calc(100vh - 200px)" }}>
        {/* Article List */}
        <div
          className={`${
            selectedItem ? "w-[340px] shrink-0" : "w-full"
          } overflow-y-auto transition-all duration-200`}
        >
          <div className="space-y-2">
            {news.length > 0 ? (
              news.map((item, i) => (
                <div
                  key={i}
                  onClick={() => setSelectedIdx(i)}
                  className={`cursor-pointer rounded-lg p-3 transition-all border ${
                    selectedIdx === i
                      ? "bg-accent-green/10 border-accent-green/50"
                      : "bg-bg-card border-border hover:border-accent-green/30"
                  }`}
                >
                  <h3
                    className={`text-sm font-semibold leading-snug ${
                      selectedIdx === i ? "text-accent-green" : "text-text-primary"
                    }`}
                  >
                    {item.title}
                  </h3>
                  <div className="flex items-center gap-2 mt-2">
                    {item.source && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-accent-blue/10 text-accent-blue rounded font-mono">
                        {item.source}
                      </span>
                    )}
                    <span className="text-text-muted text-[10px] font-mono">
                      {item.published_at}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-text-muted text-center py-12">No news articles found</div>
            )}
          </div>
        </div>

        {/* Article Content - Right Panel */}
        {selectedItem && (
          <div className="flex-1 flex flex-col bg-bg-card border border-border rounded-lg overflow-hidden min-w-0">
            {/* Header */}
            <div className="px-5 py-4 border-b border-border bg-bg-primary/50 shrink-0">
              <h2 className="text-base font-bold text-text-primary leading-snug mb-2">
                {selectedItem.title}
              </h2>
              <div className="flex items-center gap-3">
                {selectedItem.source && (
                  <span className="text-xs px-2 py-0.5 bg-accent-blue/10 text-accent-blue rounded font-mono">
                    {selectedItem.source}
                  </span>
                )}
                <span className="text-text-muted text-xs font-mono">
                  {selectedItem.published_at}
                </span>
                <a
                  href={selectedItem.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-auto text-xs px-3 py-1 bg-accent-green text-bg-primary rounded-md font-semibold hover:opacity-90 transition-opacity"
                >
                  Open Original ↗
                </a>
                <button
                  onClick={() => setSelectedIdx(null)}
                  className="text-text-muted hover:text-text-primary transition-colors text-base"
                >
                  ✕
                </button>
              </div>
            </div>
            {/* Article Embed */}
            <div className="flex-1 relative bg-white">
              <iframe
                src={selectedItem.url}
                className="w-full h-full border-0"
                sandbox="allow-scripts allow-same-origin allow-popups"
                referrerPolicy="no-referrer"
                title={selectedItem.title}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
