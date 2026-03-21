"use client";
import { useState, useEffect } from "react";

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
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      {/* Backend Status */}
      <div className="bg-bg-card border border-border rounded-lg p-4 mb-6">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">System Status</h3>
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${backendStatus === "ok" ? "bg-accent-green" : backendStatus === "error" ? "bg-accent-red" : "bg-accent-yellow animate-pulse"}`} />
          <span className="text-text-primary text-sm">
            Backend API: {backendStatus === "ok" ? "Connected" : backendStatus === "error" ? "Disconnected" : "Checking..."}
          </span>
        </div>
      </div>

      {/* API Keys */}
      <div className="bg-bg-card border border-border rounded-lg p-5 mb-6">
        <h3 className="text-text-secondary text-sm font-semibold mb-4">API Keys</h3>
        <div className="space-y-4">
          {KEYS.map((k) => (
            <div key={k.id}>
              <label className="text-text-muted text-sm mb-1.5 block">{k.label}</label>
              <div className="flex items-center gap-3">
                <input
                  type="password"
                  value={values[k.id] || ""}
                  onChange={(e) => setValues({ ...values, [k.id]: e.target.value })}
                  placeholder={k.placeholder}
                  className="flex-1 bg-bg-primary border border-border rounded-md px-3 py-2 text-text-primary outline-none focus:border-accent-green transition-colors"
                />
                <div className={`w-2.5 h-2.5 rounded-full ${values[k.id] ? "bg-accent-green" : "bg-text-muted"}`} />
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={handleSave}
          className="mt-5 bg-accent-green text-bg-primary px-6 py-2 rounded-md font-semibold hover:opacity-90 transition-opacity"
        >
          {saved ? "Saved!" : "Save Keys"}
        </button>
      </div>

      {/* Info */}
      <div className="bg-bg-card border border-border rounded-lg p-4">
        <h3 className="text-text-secondary text-sm font-semibold mb-2">About</h3>
        <div className="text-text-muted text-sm space-y-1">
          <p>ATLAS Terminal v2.0 — Advanced Trading & Liquidity Analysis System</p>
          <p>API keys are stored locally in your browser. They are never sent to our servers.</p>
        </div>
      </div>
    </div>
  );
}
