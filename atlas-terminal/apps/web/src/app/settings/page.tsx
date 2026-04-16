"use client";
import { useState, useEffect } from "react";
import { CheckCircle2, CircleOff, LoaderCircle } from "lucide-react";
import { Card } from "../components/ui/Card";
import { SectionHeading } from "../components/ui/SectionHeading";

const KEYS = [
  { id: "atlas_gemini_key", label: "Gemini API Key", placeholder: "AIza..." },
  { id: "atlas_openai_key", label: "OpenAI API Key", placeholder: "sk-..." },
  { id: "atlas_anthropic_key", label: "Anthropic API Key", placeholder: "sk-ant-..." },
];

export default function SettingsPage() {
  const [values, setValues] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
  const [backendStatus, setBackendStatus] = useState<"checking" | "ok" | "error">("checking");

  useEffect(() => {
    // Load from localStorage
    const loaded: Record<string, string> = {};
    KEYS.forEach((k) => {
      loaded[k.id] = localStorage.getItem(k.id) || "";
    });
    setValues(loaded);

    // Check backend health
    fetch("/api/health")
      .then((r) => r.ok ? setBackendStatus("ok") : setBackendStatus("error"))
      .catch(() => setBackendStatus("error"));
  }, []);

  function handleSave() {
    Object.entries(values).forEach(([key, val]) => {
      if (val) localStorage.setItem(key, val);
      else localStorage.removeItem(key);
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="atlas-page max-w-3xl">
      <SectionHeading level={1}>Settings</SectionHeading>

      <Card title="System Status" subtitle="Local keys and backend health for your desk.">
        <div className="flex items-center gap-3">
          {backendStatus === "ok" ? (
            <CheckCircle2 className="h-5 w-5 text-fin-positive" />
          ) : backendStatus === "error" ? (
            <CircleOff className="h-5 w-5 text-fin-negative" />
          ) : (
            <LoaderCircle className="h-5 w-5 animate-spin text-brand-blue" />
          )}
          <span className="text-text-primary text-sm">
            Backend API: {backendStatus === "ok" ? "Connected" : backendStatus === "error" ? "Disconnected" : "Checking..."}
          </span>
        </div>
      </Card>

      <Card title="API Keys" subtitle="Stored locally in this browser session.">
        <div className="space-y-4">
          {KEYS.map((k) => (
            <div key={k.id}>
              <label className="mb-1.5 block text-sm text-text-muted">{k.label}</label>
              <div className="flex items-center gap-3">
                <input
                  type="password"
                  value={values[k.id] || ""}
                  onChange={(e) => setValues({ ...values, [k.id]: e.target.value })}
                  placeholder={k.placeholder}
                  className="flex-1 rounded-md border border-border bg-surface-raised px-3 py-2 text-text-primary outline-none transition-colors focus:border-brand-blue"
                />
                <div className={`h-2.5 w-2.5 rounded-full ${values[k.id] ? "bg-fin-positive" : "bg-text-muted"}`} />
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={handleSave}
          className="mt-5 rounded-md bg-brand-navy px-6 py-2 font-semibold text-white transition-colors hover:bg-brand-blue"
        >
          {saved ? "Saved!" : "Save Keys"}
        </button>
      </Card>

      <Card title="About">
        <div className="text-text-muted text-sm space-y-1">
          <p>ATLAS Terminal v2.0 — Advanced Trading & Liquidity Analysis System</p>
          <p>API keys are stored locally in your browser. They are never sent to our servers.</p>
        </div>
      </Card>
    </div>
  );
}
