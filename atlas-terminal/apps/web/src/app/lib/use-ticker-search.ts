"use client";

import { useEffect, useMemo, useState } from "react";
import { searchLocalTickerSuggestions, type TickerSuggestion } from "./ticker-alias";

const SEARCH_ENDPOINT = "/api/search/tickers";
const DEFAULT_LIMIT = 6;
const REMOTE_FAILURE_STATUSES = new Set([404, 405, 410, 501]);
const inFlightSearches = new Map<string, Promise<TickerSuggestion[]>>();

let remoteSearchAvailable: boolean | null = null;

type RemoteTickerSuggestion = Partial<TickerSuggestion> & {
  symbol?: string;
  ticker?: string;
  name_ko?: string;
  asset_type?: string;
};

function normalizeRemoteSuggestion(candidate: RemoteTickerSuggestion): TickerSuggestion | null {
  const ticker = (candidate.ticker || candidate.symbol || "").trim().toUpperCase();
  const name = (candidate.name || "").trim();
  const exchange = (candidate.exchange || candidate.market || "").trim();
  if (!ticker || !name || !exchange) return null;

  const assetTypeValue = (candidate.assetType || candidate.asset_type || "Equity").toString().toLowerCase();
  const assetType =
    assetTypeValue === "etf"
      ? "ETF"
      : assetTypeValue === "commodity"
        ? "Commodity"
        : assetTypeValue === "crypto"
          ? "Crypto"
          : assetTypeValue === "index"
            ? "Index"
            : "Equity";

  return {
    ticker,
    name,
    nameKo: candidate.nameKo || candidate.name_ko,
    exchange,
    market: candidate.market,
    currency: candidate.currency,
    assetType,
    country: candidate.country,
    aliases: Array.isArray(candidate.aliases) ? candidate.aliases.filter((value): value is string => typeof value === "string") : [],
  };
}

async function fetchRemoteTickerSuggestions(raw: string, limit: number, signal: AbortSignal): Promise<TickerSuggestion[]> {
  if (remoteSearchAvailable === false) return [];

  const query = raw.trim();
  if (!query) return [];

  const cacheKey = `${query}::${limit}`;
  const existing = inFlightSearches.get(cacheKey);
  if (existing) return existing;

  const task = (async () => {
    const res = await fetch(`${SEARCH_ENDPOINT}?q=${encodeURIComponent(query)}&limit=${limit}`, { signal });
    if (REMOTE_FAILURE_STATUSES.has(res.status)) {
      remoteSearchAvailable = false;
      return [];
    }
    if (!res.ok) {
      throw new Error(`HTTP_${res.status}`);
    }

    remoteSearchAvailable = true;
    const payload = await res.json();
    const items: RemoteTickerSuggestion[] = Array.isArray(payload)
      ? payload
      : Array.isArray(payload?.suggestions)
        ? payload.suggestions
        : Array.isArray(payload?.results)
          ? payload.results
          : [];

    return items
      .map((item: RemoteTickerSuggestion) => normalizeRemoteSuggestion(item))
      .filter((item): item is TickerSuggestion => Boolean(item));
  })();

  inFlightSearches.set(cacheKey, task);
  try {
    return await task;
  } finally {
    inFlightSearches.delete(cacheKey);
  }
}

function mergeSuggestions(local: TickerSuggestion[], remote: TickerSuggestion[], limit: number): TickerSuggestion[] {
  const merged = new Map<string, TickerSuggestion>();
  for (const suggestion of [...remote, ...local]) {
    const key = `${suggestion.ticker}::${suggestion.exchange}`;
    if (!merged.has(key)) merged.set(key, suggestion);
  }
  return Array.from(merged.values()).slice(0, limit);
}

export function useTickerSearch(raw: string, limit = DEFAULT_LIMIT) {
  const query = raw.trim();
  const localSuggestions = useMemo(() => searchLocalTickerSuggestions(query, limit), [query, limit]);
  const [remoteSuggestions, setRemoteSuggestions] = useState<TickerSuggestion[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setRemoteSuggestions([]);

    if (!query || remoteSearchAvailable === false) {
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      setLoading(true);
      try {
        const next = await fetchRemoteTickerSuggestions(query, limit, controller.signal);
        if (!controller.signal.aborted) {
          setRemoteSuggestions(next);
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        if (error instanceof Error && error.message.startsWith("HTTP_")) {
          setRemoteSuggestions([]);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }, 140);

    return () => {
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [query, limit]);

  return {
    suggestions: mergeSuggestions(localSuggestions, remoteSuggestions, limit),
    loading,
    source: remoteSuggestions.length > 0 ? "remote" : "local",
  } as const;
}
