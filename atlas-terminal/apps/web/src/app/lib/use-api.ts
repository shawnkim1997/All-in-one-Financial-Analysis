"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * useApi — A lightweight fetch hook for ATLAS Terminal.
 *
 * Features:
 *  - Hydration-safe (doesn't fire on the server).
 *  - Automatic AbortController management across deps changes / unmount.
 *  - Module-scoped in-flight request dedup: same URL + same method share a promise.
 *  - Parses `{ detail }` and `{ error }` backend error shapes.
 *  - Conditional fetch via `opts.enabled` or passing `url = null`.
 *  - Manual `refetch()` escape hatch.
 *
 * We intentionally do NOT cache responses. A future SWR migration can layer caching
 * on top without changing the hook surface.
 */

type Json = unknown;

interface InFlightEntry {
  promise: Promise<Response>;
  controller: AbortController;
  refCount: number;
}

const inflight = new Map<string, InFlightEntry>();

function makeKey(url: string, method: string, body?: string): string {
  return `${method.toUpperCase()} ${url}${body ? ` :: ${body}` : ""}`;
}

async function sharedFetch(
  url: string,
  init: RequestInit,
  externalSignal: AbortSignal,
): Promise<Response> {
  const method = (init.method || "GET").toUpperCase();
  const bodyKey = typeof init.body === "string" ? init.body : undefined;
  const key = makeKey(url, method, bodyKey);

  let entry = inflight.get(key);
  if (!entry) {
    const controller = new AbortController();
    const promise = fetch(url, { ...init, signal: controller.signal }).finally(() => {
      inflight.delete(key);
    });
    entry = { promise, controller, refCount: 0 };
    inflight.set(key, entry);
  }
  entry.refCount += 1;

  const onAbort = () => {
    if (!entry) return;
    entry.refCount -= 1;
    // Only abort the underlying request if no other caller still needs it.
    if (entry.refCount <= 0) {
      entry.controller.abort();
      inflight.delete(key);
    }
  };
  if (externalSignal.aborted) {
    onAbort();
    throw new DOMException("Aborted", "AbortError");
  }
  externalSignal.addEventListener("abort", onAbort, { once: true });

  try {
    // Clone so multiple consumers can each call .json() on the response.
    const resp = await entry.promise;
    return resp.clone();
  } finally {
    externalSignal.removeEventListener("abort", onAbort);
  }
}

async function parseError(resp: Response): Promise<string> {
  try {
    const data = await resp.clone().json();
    if (data && typeof data === "object") {
      const obj = data as Record<string, unknown>;
      if (typeof obj.detail === "string") return obj.detail;
      if (typeof obj.error === "string") return obj.error;
      if (typeof obj.message === "string") return obj.message;
    }
  } catch {
    /* fall through */
  }
  try {
    const txt = await resp.text();
    if (txt) return txt.slice(0, 240);
  } catch {
    /* ignore */
  }
  return `HTTP ${resp.status} ${resp.statusText || ""}`.trim();
}

export interface UseApiOptions {
  enabled?: boolean;
  method?: "GET" | "POST";
  body?: Json;
  headers?: Record<string, string>;
}

export interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useApi<T = unknown>(
  url: string | null,
  opts: UseApiOptions = {},
): UseApiResult<T> {
  const { enabled = true, method = "GET", body, headers } = opts;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(url) && enabled !== false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const bodyStr = body !== undefined ? JSON.stringify(body) : undefined;

  useEffect(() => {
    if (!url || enabled === false) {
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    const init: RequestInit = {
      method,
      headers: {
        ...(bodyStr ? { "Content-Type": "application/json" } : {}),
        ...(headers || {}),
      },
      body: bodyStr,
    };

    sharedFetch(url, init, controller.signal)
      .then(async (resp) => {
        if (!resp.ok) {
          const msg = await parseError(resp);
          throw new Error(msg);
        }
        const ct = resp.headers.get("content-type") || "";
        const payload = ct.includes("application/json") ? await resp.json() : await resp.text();
        if (!mountedRef.current || controller.signal.aborted) return;
        setData(payload as T);
        setError(null);
      })
      .catch((err: unknown) => {
        if ((err as Error)?.name === "AbortError") return;
        if (!mountedRef.current) return;
        setError((err as Error)?.message || "Request failed");
        setData(null);
      })
      .finally(() => {
        if (!mountedRef.current || controller.signal.aborted) return;
        setLoading(false);
      });

    return () => {
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, method, bodyStr, enabled, tick]);

  const refetch = useCallback(() => {
    setTick((t) => t + 1);
  }, []);

  return { data, loading, error, refetch };
}
