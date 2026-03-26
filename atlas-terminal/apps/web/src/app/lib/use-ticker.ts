"use client";
import { useState, useEffect, useCallback } from "react";
import { normalizeTickerInput } from "./ticker-alias";

const DEFAULT_TICKER = "AAPL";
const STORAGE_KEY = "atlas_active_ticker";
const EVENT_NAME = "atlas-ticker-change";

export function useTicker() {
  // Must match server render: never read localStorage in useState initializer — hydration mismatch → white screen.
  const [ticker, setTickerState] = useState(DEFAULT_TICKER);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const n = normalizeTickerInput(saved);
      if (n) setTickerState(n);
    }

    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail) setTickerState(detail);
    };
    window.addEventListener(EVENT_NAME, handler);
    return () => window.removeEventListener(EVENT_NAME, handler);
  }, []);

  const setTicker = useCallback((val: string) => {
    const upper = normalizeTickerInput(val);
    if (!upper) return;
    setTickerState(upper);
    localStorage.setItem(STORAGE_KEY, upper);
    window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: upper }));
  }, []);

  return { ticker, setTicker };
}
