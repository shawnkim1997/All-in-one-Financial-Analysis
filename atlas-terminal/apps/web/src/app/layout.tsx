import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "./components/sidebar";
import { TickerBar } from "./components/ticker-bar";
import { ChatPanel } from "./components/chat-panel";

export const metadata: Metadata = {
  title: "ATLAS Terminal",
  description: "Advanced Trading & Liquidity Analysis System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <TickerBar />
        <div className="flex pt-[52px] min-h-screen">
          <Sidebar />
          <main className="flex-1 ml-[260px] mr-[380px] p-7 bg-bg-primary min-h-[calc(100vh-52px)] transition-all duration-200">
            {children}
          </main>
          <ChatPanel />
        </div>
      </body>
    </html>
  );
}
