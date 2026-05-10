"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { FTBookmark, FTHeadline } from "./daily-news-types";

const READ_URLS_KEY = "ft-read-urls";
const READ_DATES_KEY = "ft-read-dates";
const BOOKMARKS_KEY = "ft-bookmarks";
const BOOKMARK_DATES_KEY = "ft-bookmarked-dates";
const EVENT_NAME = "atlas-daily-news-sync";

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value));
}

function emitSync() {
  window.dispatchEvent(new CustomEvent(EVENT_NAME));
}

export function useReadStatus() {
  const [readUrls, setReadUrls] = useState<string[]>([]);
  const [readDates, setReadDates] = useState<string[]>([]);

  const sync = useCallback(() => {
    setReadUrls(readJson<string[]>(READ_URLS_KEY, []));
    setReadDates(readJson<string[]>(READ_DATES_KEY, []));
  }, []);

  useEffect(() => {
    sync();
    window.addEventListener(EVENT_NAME, sync);
    return () => window.removeEventListener(EVENT_NAME, sync);
  }, [sync]);

  const toggleRead = useCallback((url: string, dateKey: string) => {
    const nextUrls = new Set(readJson<string[]>(READ_URLS_KEY, []));
    const nextDates = new Set(readJson<string[]>(READ_DATES_KEY, []));
    if (nextUrls.has(url)) {
      nextUrls.delete(url);
    } else {
      nextUrls.add(url);
      nextDates.add(dateKey);
    }
    writeJson(READ_URLS_KEY, Array.from(nextUrls));
    writeJson(READ_DATES_KEY, Array.from(nextDates));
    emitSync();
  }, []);

  const readUrlSet = useMemo(() => new Set(readUrls), [readUrls]);
  const readDateSet = useMemo(() => new Set(readDates), [readDates]);

  return {
    readDates: readDateSet,
    isRead: (url: string) => readUrlSet.has(url),
    toggleRead,
  };
}

export function useBookmarks() {
  const [bookmarks, setBookmarks] = useState<FTBookmark[]>([]);
  const [bookmarkedDates, setBookmarkedDates] = useState<string[]>([]);

  const sync = useCallback(() => {
    setBookmarks(readJson<FTBookmark[]>(BOOKMARKS_KEY, []));
    setBookmarkedDates(readJson<string[]>(BOOKMARK_DATES_KEY, []));
  }, []);

  useEffect(() => {
    sync();
    window.addEventListener(EVENT_NAME, sync);
    return () => window.removeEventListener(EVENT_NAME, sync);
  }, [sync]);

  const toggleBookmark = useCallback((headline: FTHeadline, dateKey: string) => {
    const nextBookmarks = readJson<FTBookmark[]>(BOOKMARKS_KEY, []);
    const nextDates = new Set(readJson<string[]>(BOOKMARK_DATES_KEY, []));
    const existingIndex = nextBookmarks.findIndex((item) => item.url === headline.url);

    if (existingIndex >= 0) {
      nextBookmarks.splice(existingIndex, 1);
    } else {
      nextBookmarks.unshift({
        ...headline,
        date_key: dateKey,
        saved_at: new Date().toISOString(),
      });
      nextDates.add(dateKey);
    }

    writeJson(BOOKMARKS_KEY, nextBookmarks);
    writeJson(BOOKMARK_DATES_KEY, Array.from(nextDates));
    emitSync();
  }, []);

  const bookmarkSet = useMemo(() => new Set(bookmarks.map((item) => item.url)), [bookmarks]);
  const bookmarkDateSet = useMemo(() => new Set(bookmarkedDates), [bookmarkedDates]);

  return {
    bookmarks,
    bookmarkedDates: bookmarkDateSet,
    isBookmarked: (url: string) => bookmarkSet.has(url),
    toggleBookmark,
  };
}
