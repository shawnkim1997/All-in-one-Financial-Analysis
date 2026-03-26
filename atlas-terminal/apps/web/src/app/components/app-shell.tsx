"use client";

import dynamic from "next/dynamic";
import { TickerBar } from "./ticker-bar";
import { ChatPanel } from "./chat-panel";

/**
 * Sidebar는 usePathname()을 씁니다. Next App Router에서 SSR 출력과 클라이언트 첫 페인트가
 * 미묘하게 어긋나면 hydration 실패 → 전체 트리가 비거나(흰 화면) 콘솔에 recoverable 에러가 납니다.
 * 서버에서는 사이드바를 그리지 않고(ssr: false) 클라이언트에서만 마운트해 그 클래스의 버그를 제거합니다.
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
