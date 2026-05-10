"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Briefcase, CalendarDays, CalendarRange, FileSearch, FileText, FileVideo, Globe, Landmark, LineChart, Microscope, Newspaper, Search, Settings, Sparkles, Target, TrendingUp } from "lucide-react";
import { useMemo, useState } from "react";
import { flags } from "../lib/flags";
import { searchTickerSuggestions, type TickerSuggestion } from "../lib/ticker-alias";
import { useTicker } from "../lib/use-ticker";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: BarChart3 },
  { href: "/research", label: "Research", icon: Microscope },
  { href: "/valuation", label: "Valuation", icon: Landmark },
  { href: "/technical", label: "Technical", icon: TrendingUp },
  { href: "/markets", label: "Markets", icon: Globe },
  { href: "/macro", label: "Macro", icon: LineChart },
  { href: "/earnings", label: "Earnings", icon: CalendarRange },
  ...(flags.calendar ? [{ href: "/calendar", label: "Calendar", icon: CalendarDays }] : []),
  { href: "/news", label: "News", icon: Newspaper },
  { href: "/transcripts", label: "Transcripts", icon: FileVideo },
  { href: "/screener", label: "Screener", icon: Target },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/filings", label: "Filings", icon: FileSearch },
  { href: "/report", label: "Report", icon: FileText },
];

export function Sidebar() {
  const pathname = usePathname();
  const [input, setInput] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const { ticker, setTicker } = useTicker();
  const suggestions = useMemo(() => searchTickerSuggestions(input, 5), [input]);
  const showSuggestions = input.trim().length > 0 && suggestions.length > 0;

  function selectSuggestion(suggestion: TickerSuggestion) {
    setTicker(suggestion.ticker);
    setInput("");
    setHighlightedIndex(0);
  }

  function handleSearch() {
    const val = input.trim();
    if (val) {
      const bestMatch = suggestions[highlightedIndex] ?? suggestions[0];
      if (bestMatch) {
        selectSuggestion(bestMatch);
        return;
      }
      setTicker(val);
      setInput("");
      setHighlightedIndex(0);
    }
  }

  function handleInputChange(value: string) {
    setInput(value);
    setHighlightedIndex(0);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      handleSearch();
      return;
    }

    if (!showSuggestions) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlightedIndex((current) => (current + 1) % suggestions.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlightedIndex((current) => (current - 1 + suggestions.length) % suggestions.length);
    } else if (event.key === "Escape") {
      setInput("");
      setHighlightedIndex(0);
    }
  }

  return (
    <aside className="fixed bottom-0 left-0 top-[56px] z-40 flex w-[260px] flex-col gap-2 overflow-y-auto border-r border-border bg-surface-raised px-4 py-5 shadow-card">
      <div className="rounded-md border border-border bg-surface-raised p-3 shadow-card">
        <div className="mb-2 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-text-muted">
              Active Terminal
            </div>
            <div className="mt-1 font-serif text-lg font-bold text-brand-navy">ATLAS Desk</div>
          </div>
          <Sparkles className="h-4 w-4 text-brand-gold" />
        </div>
        <div
          role="combobox"
          aria-expanded={showSuggestions}
          aria-controls="ticker-suggestions"
          aria-haspopup="listbox"
          className="flex items-center gap-2 rounded-md border border-border bg-surface-sunken px-3 py-2"
        >
          <Search className="h-4 w-4 text-text-muted" />
          <input
            id="atlas-ticker-search"
            value={input}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search ticker or company..."
            aria-label="Search ticker or company"
            aria-autocomplete="list"
            className="w-full border-none bg-transparent text-sm text-text-primary outline-none"
          />
        </div>
        {showSuggestions && (
          <div id="ticker-suggestions" role="listbox" className="mt-2 overflow-hidden rounded-md border border-border bg-surface-raised shadow-card">
            {suggestions.map((suggestion, index) => {
              const active = index === highlightedIndex;
              return (
                <button
                  key={`${suggestion.ticker}-${suggestion.exchange}`}
                  type="button"
                  role="option"
                  aria-selected={active}
                  onMouseDown={(event) => {
                    event.preventDefault();
                    selectSuggestion(suggestion);
                  }}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  className={`w-full px-3 py-2 text-left transition-colors ${
                    active ? "bg-brand-navy text-white" : "bg-surface-raised text-text-primary hover:bg-surface-sunken"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className={`font-mono text-sm font-bold ${active ? "text-brand-gold" : "text-brand-navy"}`}>{suggestion.ticker}</span>
                    <span className={`rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.08em] ${
                      active ? "border-white/20 text-white/70" : "border-border text-text-muted"
                    }`}>
                      {suggestion.exchange}
                    </span>
                  </div>
                  <div className={`mt-0.5 truncate text-xs ${active ? "text-white/80" : "text-text-secondary"}`}>{suggestion.name}</div>
                </button>
              );
            })}
          </div>
        )}
        {input.trim().length > 0 && suggestions.length === 0 && (
          <div className="mt-2 rounded-md border border-border bg-surface-sunken px-3 py-2 text-xs text-text-muted">
            No match yet. Press Enter to use <span className="font-mono text-brand-navy">{input.trim().toUpperCase()}</span>.
          </div>
        )}
        <div className="mt-3 flex items-center justify-between rounded-md bg-brand-navy px-3 py-2 text-white">
          <span className="text-xs uppercase tracking-[0.12em] text-white/70">Ticker</span>
          <span className="font-mono text-sm font-bold text-brand-gold">{ticker}</span>
        </div>
      </div>

      <nav className="mt-3 flex flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href} className="no-underline">
              <div
                className={`flex items-center gap-3 rounded-md border-l-4 px-3.5 py-2.5 text-sm transition-all duration-150 ${
                  active
                    ? "border-brand-gold bg-surface-sunken font-semibold text-brand-navy"
                    : "border-transparent text-text-secondary hover:bg-surface-sunken hover:text-brand-navy"
                }`}
              >
                <Icon className={`h-[18px] w-[18px] ${active ? "text-brand-gold" : "text-brand-navy"}`} />
                {item.label}
              </div>
            </Link>
          );
        })}

        <div className="my-2 border-t border-border" />
        <Link href="/settings" className="no-underline">
          <div
            className={`flex items-center gap-3 rounded-md border-l-4 px-3.5 py-2.5 text-sm transition-all duration-150 ${
              pathname === "/settings"
                ? "border-brand-gold bg-surface-sunken font-semibold text-brand-navy"
                : "border-transparent text-text-secondary hover:bg-surface-sunken hover:text-brand-navy"
            }`}
          >
            <Settings className={`h-[18px] w-[18px] ${pathname === "/settings" ? "text-brand-gold" : "text-brand-navy"}`} />
            Settings
          </div>
        </Link>
      </nav>
    </aside>
  );
}
