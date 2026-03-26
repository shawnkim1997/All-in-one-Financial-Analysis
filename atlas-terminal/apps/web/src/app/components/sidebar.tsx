"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { normalizeTickerInput } from "../lib/ticker-alias";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: "📊" },
  { href: "/research", label: "Research", icon: "🔬" },
  { href: "/valuation", label: "Valuation", icon: "💰" },
  { href: "/technical", label: "Technical", icon: "📈" },
  { href: "/markets", label: "Markets", icon: "🌍" },
  { href: "/macro", label: "Macro", icon: "🌐" },
  { href: "/earnings", label: "Earnings", icon: "📅" },
  { href: "/news", label: "News", icon: "📰" },
  { href: "/screener", label: "Screener", icon: "🎯" },
  { href: "/portfolio", label: "Portfolio", icon: "💼" },
  { href: "/filings", label: "Filings", icon: "📑" },
];

export function Sidebar() {
  const pathname = usePathname();
  const [input, setInput] = useState("");
  const [ticker, setTickerLocal] = useState("AAPL");

  useEffect(() => {
    const saved = localStorage.getItem("atlas_active_ticker");
    if (saved) setTickerLocal(saved);

    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail) setTickerLocal(detail);
    };
    window.addEventListener("atlas-ticker-change", handler);
    return () => window.removeEventListener("atlas-ticker-change", handler);
  }, []);

  function handleSearch() {
    const val = normalizeTickerInput(input);
    if (val) {
      setTickerLocal(val);
      localStorage.setItem("atlas_active_ticker", val);
      window.dispatchEvent(new CustomEvent("atlas-ticker-change", { detail: val }));
      setInput("");
    }
  }

  return (
    <aside className="w-[260px] bg-bg-primary border-r border-border p-4 flex flex-col gap-2 fixed top-[52px] bottom-0 left-0 overflow-y-auto z-40">
      {/* Ticker Search */}
      <div>
        <div className="flex items-center gap-2 bg-bg-card border border-border rounded-lg px-3.5 py-2.5">
          <span className="text-text-muted">🔍</span>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Search ticker..."
            className="bg-transparent border-none text-text-primary outline-none w-full"
          />
        </div>
        <div className="mt-2 px-3.5 py-1.5 bg-bg-card rounded-md flex items-center justify-between">
          <span className="text-text-muted text-sm">Active:</span>
          <span className="text-accent-green font-mono font-bold">{ticker}</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 mt-3">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          return (
            <Link key={item.href} href={item.href} className="no-underline">
              <div
                className={`flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg text-base transition-all duration-150 border-l-2 ${
                  active
                    ? "bg-accent-green/10 text-accent-green font-semibold border-accent-green"
                    : "text-text-secondary font-normal border-transparent hover:bg-bg-card"
                }`}
              >
                <span>{item.icon}</span> {item.label}
              </div>
            </Link>
          );
        })}

        <div className="border-t border-border my-2" />
        <Link href="/settings" className="no-underline">
          <div
            className={`flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg text-base transition-all duration-150 border-l-2 ${
              pathname === "/settings"
                ? "bg-accent-green/10 text-accent-green font-semibold border-accent-green"
                : "text-text-secondary font-normal border-transparent hover:bg-bg-card"
            }`}
          >
            <span>⚙️</span> Settings
          </div>
        </Link>
      </nav>
    </aside>
  );
}
