"use client";
import { useEffect, useCallback } from "react";
import { useTerminal } from "@/stores/terminal";
import { normalizeTickerInput } from "./ticker-alias";

const DEFAULT_TICKER = "AAPL";
const STORAGE_KEY = "atlas_active_ticker";
const EVENT_NAME = "atlas-ticker-change";

export function useTicker() {
  const ticker = useTerminal((state) => state.activeSymbol || DEFAULT_TICKER);
  const initialized = useTerminal((state) => state.hydrated);
  const setActiveSymbol = useTerminal((state) => state.setActiveSymbol);

  useEffect(() => {
    if (!initialized) return;

    // One-time migration from the old ticker key.  The Zustand store is the
    // source of truth after Phase 2, but this preserves existing local setups.
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && normalizeTickerInput(ticker) === DEFAULT_TICKER) {
      const normalized = normalizeTickerInput(saved);
      if (normalized && normalized !== DEFAULT_TICKER) setActiveSymbol(normalized);
    }

    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail) setActiveSymbol(detail);
    };
    window.addEventListener(EVENT_NAME, handler);
    return () => window.removeEventListener(EVENT_NAME, handler);
  }, [initialized, setActiveSymbol, ticker]);

  const setTicker = useCallback((val: string) => {
    const upper = normalizeTickerInput(val);
    if (!upper) return;
    setActiveSymbol(upper);
    localStorage.setItem(STORAGE_KEY, upper);
    window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: upper }));
  }, [setActiveSymbol]);

  return { ticker, setTicker, initialized };
}
