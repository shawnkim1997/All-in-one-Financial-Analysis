"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Briefcase, CalendarRange, FileSearch, FileText, Globe, Landmark, LineChart, Microscope, Newspaper, Search, Settings, Sparkles, Target, TrendingUp } from "lucide-react";
import { useState } from "react";
import { useTicker } from "../lib/use-ticker";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: BarChart3 },
  { href: "/research", label: "Research", icon: Microscope },
  { href: "/valuation", label: "Valuation", icon: Landmark },
  { href: "/technical", label: "Technical", icon: TrendingUp },
  { href: "/markets", label: "Markets", icon: Globe },
  { href: "/macro", label: "Macro", icon: LineChart },
  { href: "/earnings", label: "Earnings", icon: CalendarRange },
  { href: "/news", label: "News", icon: Newspaper },
  { href: "/screener", label: "Screener", icon: Target },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/filings", label: "Filings", icon: FileSearch },
  { href: "/report", label: "Report", icon: FileText },
];

export function Sidebar() {
  const pathname = usePathname();
  const [input, setInput] = useState("");
  const { ticker, setTicker } = useTicker();

  function handleSearch() {
    const val = input.trim();
    if (val) {
      setTicker(val);
      setInput("");
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
        <div className="flex items-center gap-2 rounded-md border border-border bg-surface-sunken px-3 py-2">
          <Search className="h-4 w-4 text-text-muted" />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Search ticker..."
            className="w-full border-none bg-transparent text-sm text-text-primary outline-none"
          />
        </div>
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
