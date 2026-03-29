"use client";

import dynamic from "next/dynamic";
import { TickerBar } from "./ticker-bar";
import { ChatPanel } from "./chat-panel";

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
        className="w-[260px] fixed top-[52px] bottom-0 left-0 z-40 border-r border-border bg-bg-primary"
        aria-hidden
      />
    ),
  },
);

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <>
      <TickerBar />
      <div className="flex min-h-screen pt-[52px]">
        <SidebarClient />
        <main className="flex-1 ml-[260px] mr-[380px] p-7 bg-bg-primary min-h-[calc(100vh-52px)] transition-all duration-200">
          {children}
        </main>
        <ChatPanel />
      </div>
    </>
  );
}
