"use client";

import dynamic from "next/dynamic";
import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { TickerBar } from "./ticker-bar";
import { ChatPanel } from "./chat-panel";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";
import { terminalPageFromPathname, useTerminal } from "@/stores/terminal";

/**
 * Sidebar uses usePathname(). In Next App Router, if SSR output and client first paint
 * mismatch even slightly, hydration fails — the whole tree empties (white screen) or
 * console shows recoverable errors. We skip sidebar on server (ssr: false) and mount
 * only on client to eliminate this class of bugs.
 */
const SidebarClient = dynamic(
  () => import("./sidebar").then((m) => ({ default: m.Sidebar })),
  {
    ssr: false,
    loading: () => (
      <aside
        className="fixed bottom-0 left-0 top-[56px] z-40 w-[260px] border-r border-border bg-surface-raised"
        aria-hidden
      />
    ),
  },
);

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const setActivePage = useTerminal((state) => state.setActivePage);
  useKeyboardShortcuts();

  useEffect(() => {
    setActivePage(terminalPageFromPathname(pathname));
  }, [pathname, setActivePage]);

  return (
    <>
      <TickerBar />
      <div className="flex min-h-screen bg-surface-canvas pt-[56px]">
        <SidebarClient />
        <main className="ml-[260px] mr-[380px] min-h-[calc(100vh-56px)] flex-1 bg-transparent p-7 transition-all duration-200">
          {children}
        </main>
        <ChatPanel />
      </div>
    </>
  );
}
