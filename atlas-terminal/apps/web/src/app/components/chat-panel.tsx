"use client";
import { useState, useEffect, useRef } from "react";
import { Bot, SendHorizontal } from "lucide-react";
import { useTicker } from "../lib/use-ticker";

export function ChatPanel() {
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { ticker } = useTicker();

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
          { role: "assistant", content: "Please set your Gemini API Key in Settings." },
        ]);
      }
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Connection error. Please try again." }]);
    }
    setLoading(false);
  }

  const suggestions = [
    "Is this company undervalued?",
    "Analyze the financial health",
    "What are the key risks?",
  ];

  return (
    <aside className="fixed bottom-0 right-0 top-[56px] z-40 flex w-[380px] flex-col border-l border-border bg-surface-raised">
      <div className="border-b border-border bg-surface-sunken px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-brand-navy/10 p-2 text-brand-navy">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <div className="font-serif text-lg font-bold text-brand-navy">AI Copilot</div>
            <div className="text-xs uppercase tracking-[0.12em] text-text-muted">Context: {ticker}</div>
          </div>
        </div>
      </div>

      <div ref={scrollRef} className="flex flex-1 flex-col gap-3 overflow-y-auto bg-transparent p-4">
        {messages.length === 0 ? (
          <div className="text-sm text-text-secondary">
            <p>
              Ask me anything about <span className="font-semibold text-brand-navy">{ticker}</span>.
            </p>
            <p className="mt-4 text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">Suggested prompts</p>
            <ul className="mt-2 flex flex-col gap-2">
              {suggestions.map((q) => (
                <li
                  key={q}
                  onClick={() => setInput(q)}
                  className="cursor-pointer rounded-md border border-border bg-surface-raised px-3 py-2.5 text-sm text-text-primary shadow-card transition-colors hover:bg-surface-sunken"
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
              className={`max-w-[90%] whitespace-pre-wrap rounded-md px-3.5 py-2.5 text-sm leading-relaxed shadow-card ${
                m.role === "user"
                  ? "self-end bg-brand-navy text-white"
                  : "self-start border border-border bg-surface-raised text-text-primary"
              }`}
            >
              {m.content}
            </div>
          ))
        )}
        {loading && <div className="text-sm text-brand-blue animate-pulse">Thinking...</div>}
      </div>

      <div className="border-t border-border bg-surface-raised p-3">
        <div className="flex gap-2 rounded-md border border-border bg-surface-sunken px-3.5 py-2.5">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask anything..."
            className="flex-1 border-none bg-transparent text-text-primary outline-none"
          />
          <button
            onClick={handleSend}
            className="inline-flex items-center gap-1 rounded-md border-none bg-brand-navy px-4 py-1.5 text-sm font-semibold text-white transition-opacity hover:bg-brand-blue"
          >
            <SendHorizontal className="h-4 w-4" />
            Send
          </button>
        </div>
      </div>
    </aside>
  );
}
