"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { normalizeTickerInput } from "@/app/lib/ticker-alias";

export type Currency = "USD" | "EUR" | "KRW" | "JPY" | "DKK" | "GBP";
export type TerminalTheme = "bloomberg" | "minimal";
export type TerminalPage =
  | "equity"
  | "portfolio"
  | "macro"
  | "news"
  | "screener"
  | "research"
  | "valuation"
  | "technical"
  | "markets"
  | "earnings"
  | "filings"
  | "report"
  | "settings";

export interface GridLayout {
  columns?: number;
  rows?: number;
  widgets?: string[];
  [key: string]: unknown;
}

export interface CopilotContext {
  activeSymbol: string | null;
  activePage: TerminalPage;
  recentSymbols: string[];
  currency: Currency;
  theme: TerminalTheme;
  watchlist: string[];
}

interface PersistedTerminalState {
  activeSymbol: string | null;
  activePage: TerminalPage;
  recentSymbols: string[];
  currency: Currency;
  theme: TerminalTheme;
  watchlist: string[];
  layouts: Record<string, GridLayout>;
}

export interface TerminalState extends PersistedTerminalState {
  hydrated: boolean;
  buildCopilotContext: () => CopilotContext;
  setHydrated: (hydrated: boolean) => void;
  setActiveSymbol: (symbol: string) => void;
  setActivePage: (page: TerminalPage) => void;
  setCurrency: (currency: Currency) => void;
  setTheme: (theme: TerminalTheme) => void;
  addToWatchlist: (symbol?: string) => void;
  removeFromWatchlist: (symbol: string) => void;
  setLayout: (key: string, layout: GridLayout) => void;
}

const DEFAULT_SYMBOL = "AAPL";
const MAX_RECENT_SYMBOLS = 10;

function normalizeSymbol(symbol: string): string {
  return normalizeTickerInput(symbol);
}

function nextRecentSymbols(symbol: string, recentSymbols: string[]) {
  return [symbol, ...recentSymbols.filter((item) => item !== symbol)].slice(0, MAX_RECENT_SYMBOLS);
}

export function terminalPageFromPathname(pathname: string): TerminalPage {
  const firstSegment = pathname.split("/").filter(Boolean)[0] || "";
  if (firstSegment === "portfolio") return "portfolio";
  if (firstSegment === "macro") return "macro";
  if (firstSegment === "news") return "news";
  if (firstSegment === "screener") return "screener";
  if (firstSegment === "research") return "research";
  if (firstSegment === "valuation") return "valuation";
  if (firstSegment === "technical") return "technical";
  if (firstSegment === "markets") return "markets";
  if (firstSegment === "earnings") return "earnings";
  if (firstSegment === "filings") return "filings";
  if (firstSegment === "report") return "report";
  if (firstSegment === "settings") return "settings";
  return "equity";
}

export const useTerminal = create<TerminalState>()(
  persist(
    (set, get) => ({
      activeSymbol: DEFAULT_SYMBOL,
      activePage: "equity",
      recentSymbols: [DEFAULT_SYMBOL],
      currency: "USD",
      theme: "bloomberg",
      watchlist: [],
      layouts: {},
      hydrated: false,

      buildCopilotContext: () => {
        const state = get();
        return {
          activeSymbol: state.activeSymbol,
          activePage: state.activePage,
          recentSymbols: state.recentSymbols,
          currency: state.currency,
          theme: state.theme,
          watchlist: state.watchlist,
        };
      },

      setHydrated: (hydrated) => set({ hydrated }),

      setActiveSymbol: (symbol) => {
        const normalized = normalizeSymbol(symbol);
        if (!normalized) return;
        set((state) => ({
          activeSymbol: normalized,
          recentSymbols: nextRecentSymbols(normalized, state.recentSymbols),
        }));
      },

      setActivePage: (page) => set({ activePage: page }),
      setCurrency: (currency) => set({ currency }),
      setTheme: (theme) => set({ theme }),

      addToWatchlist: (symbol) => {
        const normalized = normalizeSymbol(symbol || get().activeSymbol || "");
        if (!normalized) return;
        set((state) => ({
          watchlist: state.watchlist.includes(normalized) ? state.watchlist : [...state.watchlist, normalized],
        }));
      },

      removeFromWatchlist: (symbol) => {
        const normalized = normalizeSymbol(symbol);
        set((state) => ({ watchlist: state.watchlist.filter((item) => item !== normalized) }));
      },

      setLayout: (key, layout) => {
        set((state) => ({ layouts: { ...state.layouts, [key]: layout } }));
      },
    }),
    {
      name: "atlas-terminal",
      version: 1,
      storage: createJSONStorage(() => localStorage),
      partialize: (state): PersistedTerminalState => ({
        activeSymbol: state.activeSymbol,
        activePage: state.activePage,
        recentSymbols: state.recentSymbols,
        currency: state.currency,
        theme: state.theme,
        watchlist: state.watchlist,
        layouts: state.layouts,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated(true);
      },
    },
  ),
);
