"use client";
import { useState, useEffect, useRef } from "react";

export function ChatPanel() {
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [ticker, setTicker] = useState("AAPL");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem("atlas_active_ticker");
    if (saved) setTicker(saved);
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail) setTicker(detail);
    };
    window.addEventListener("atlas-ticker-change", handler);
    return () => window.removeEventListener("atlas-ticker-change", handler);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const apiKey = localStorage.getItem("atlas_gemini_key") || "";
      const res = await fetch("/api/analysis/strategy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, question: userMsg, api_key: apiKey }),
      });
      if (res.ok) {
        const data = await res.json();
        const text = typeof data === "string" ? data : data.analysis || data.result || JSON.stringify(data);
        setMessages((prev) => [...prev, { role: "assistant", content: text }]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Settings에서 Gemini API Key를 설정해주세요." },
        ]);
      }
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "연결 오류. 다시 시도해주세요." }]);
    }
    setLoading(false);
  }

  const suggestions = [
    "Is this company undervalued?",
    "Analyze the financial health",
    "What are the key risks?",
  ];

  return (
    <aside className="w-[380px] bg-bg-secondary border-l border-border fixed top-[52px] bottom-0 right-0 flex flex-col z-40">
      <div className="p-4 border-b border-border font-bold text-lg text-text-primary">
        🤖 AI Copilot
      </div>

      <div ref={scrollRef} className="flex-1 p-4 overflow-y-auto flex flex-col gap-3">
        {messages.length === 0 ? (
          <div className="text-text-secondary text-sm">
            <p>
              Ask me anything about{" "}
              <span className="text-accent-green font-semibold">{ticker}</span>.
            </p>
            <p className="mt-3 font-semibold text-text-primary">Try:</p>
            <ul className="flex flex-col gap-1.5 mt-2">
              {suggestions.map((q) => (
                <li
                  key={q}
                  onClick={() => setInput(q)}
                  className="px-3 py-2.5 bg-bg-card rounded-lg cursor-pointer text-sm text-text-primary hover:bg-bg-hover transition-colors"
                >
                  {q}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          messages.map((m, i) => (
            <div
              key={i}
              className={`px-3.5 py-2.5 rounded-lg text-sm leading-relaxed max-w-[90%] whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-bg-card text-text-primary self-end"
                  : "bg-accent-green/10 text-text-primary self-start"
              }`}
            >
              {m.content}
            </div>
          ))
        )}
        {loading && <div className="text-accent-green text-sm animate-pulse">Thinking...</div>}
      </div>

      <div className="p-3 border-t border-border">
        <div className="flex gap-2 bg-bg-card rounded-lg border border-border px-3.5 py-2.5">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask anything..."
            className="flex-1 bg-transparent border-none text-text-primary outline-none"
          />
          <button
            onClick={handleSend}
            className="bg-accent-green text-bg-primary border-none rounded-md px-4 py-1.5 font-semibold cursor-pointer text-sm hover:opacity-90 transition-opacity"
          >
            Send
          </button>
        </div>
      </div>
    </aside>
  );
}
