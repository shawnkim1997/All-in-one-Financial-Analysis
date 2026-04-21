"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { tinykeys, type TinyKeysHandler } from "tinykeys";
import { useTerminal } from "@/stores/terminal";

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select" || target.isContentEditable;
}

function focusElement(selector: string) {
  const el = document.querySelector<HTMLElement>(selector);
  el?.focus();
}

export function useKeyboardShortcuts() {
  const router = useRouter();
  const activeSymbol = useTerminal((state) => state.activeSymbol);
  const addToWatchlist = useTerminal((state) => state.addToWatchlist);

  useEffect(() => {
    const focusTickerSearch: TinyKeysHandler = (event) => {
      event.preventDefault();
      focusElement("#atlas-ticker-search");
    };

    const focusTickerSearchWhenIdle: TinyKeysHandler = (event) => {
      if (isEditableTarget(event.target)) return;
      event.preventDefault();
      focusElement("#atlas-ticker-search");
    };

    const focusCopilotWhenIdle: TinyKeysHandler = (event) => {
      if (isEditableTarget(event.target)) return;
      event.preventDefault();
      focusElement("#atlas-copilot-input");
    };

    const addCurrentSymbolToWatchlist: TinyKeysHandler = (event) => {
      if (isEditableTarget(event.target)) return;
      event.preventDefault();
      addToWatchlist(activeSymbol || undefined);
    };

    const navigateWhenIdle = (href: string): TinyKeysHandler => (event) => {
      if (isEditableTarget(event.target)) return;
      event.preventDefault();
      router.push(href);
    };

    const dispatchTabShortcut = (index: number): TinyKeysHandler => (event) => {
      if (isEditableTarget(event.target)) return;
      window.dispatchEvent(new CustomEvent("atlas-terminal-tab-shortcut", { detail: { index } }));
    };

    return tinykeys(window, {
      "$mod+KeyK": focusTickerSearch,
      KeyG: focusTickerSearchWhenIdle,
      Slash: focusCopilotWhenIdle,
      KeyW: addCurrentSymbolToWatchlist,
      KeyP: navigateWhenIdle("/portfolio"),
      KeyM: navigateWhenIdle("/macro"),
      KeyN: navigateWhenIdle("/news"),
      Digit1: dispatchTabShortcut(0),
      Digit2: dispatchTabShortcut(1),
      Digit3: dispatchTabShortcut(2),
    });
  }, [activeSymbol, addToWatchlist, router]);
}
