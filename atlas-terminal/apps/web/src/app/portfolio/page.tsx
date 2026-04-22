"use client";
import { useState, useEffect } from "react";
import { AlertTriangle, Check, CheckCircle2, CircleX, Pencil, Trash2 } from "lucide-react";
import { CorrelationMatrix } from "../components/portfolio/CorrelationMatrix";

interface Position {
  id?: string;
  ticker: string;
  company_name?: string;
  quantity: number;
  avg_price: number;
  current_price?: number;
  market_value?: number;
  pnl?: number;
  pnl_pct?: number;
  confidence?: string;
  method?: string;
  avg_price_currency?: string;
  stock_currency?: string;
  currency?: string;
  account_currency?: string;
  current_value_account?: number;
  total_pnl?: number;
  yf_ticker?: string;
  avg_method?: string;
  exchange?: string;
}

interface ExchangeOption {
  exchange: string;
  yf_ticker: string;
  currency: string;
  default?: boolean;
}

export default function PortfolioPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [form, setForm] = useState({ ticker: "", quantity: "", avg_price: "" });
  const [loading, setLoading] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [ocrPositions, setOcrPositions] = useState<Position[]>([]);
  const [ocrError, setOcrError] = useState<string>("");
  const [ocrWarnings, setOcrWarnings] = useState<string[]>([]);
  const [ocrAccountCurrency, setOcrAccountCurrency] = useState<string>("USD");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValues, setEditValues] = useState({ qty: "", avgPrice: "" });
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [displayCurrency, setDisplayCurrency] = useState("USD");
  const [fxRates, setFxRates] = useState<Record<string, number>>({});
  const [exchangeSelections, setExchangeSelections] = useState<Record<string, string>>({});
  const [exchangeOptions, setExchangeOptions] = useState<Record<string, ExchangeOption[]>>({});

  useEffect(() => {
    fetchPortfolio();
    fetch("/api/fx/rates")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data) return;
        setFxRates(data.rates || data);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!ocrPositions.length) return;
    ocrPositions.forEach(async (pos, idx) => {
      const rowKey = `${pos.ticker}-${idx}`;
      const res = await fetch(`/api/portfolio/exchange-options/${pos.ticker}`);
      const data = await res.json().catch(() => null);
      const opts = Array.isArray(data?.options) ? data.options : [];
      if (opts.length > 0) {
        setExchangeOptions((prev) => ({ ...prev, [rowKey]: opts }));
        const def =
          opts.find((o: ExchangeOption) => o.exchange === pos.exchange) ||
          opts.find((o: ExchangeOption) => o.default) ||
          opts[0];
        setExchangeSelections((prev) => ({ ...prev, [rowKey]: def.exchange }));
      }
    });
  }, [ocrPositions]);

  async function fetchPortfolio() {
    setLoading(true);
    try {
      const res = await fetch("/api/portfolio/summary");
      if (res.ok) {
        const data = await res.json();
        setPositions(data.positions || []);
      } else {
        // fallback: try basic positions list
        const res2 = await fetch("/api/portfolio/positions");
        if (res2.ok) {
          const data2 = await res2.json();
          setPositions(Array.isArray(data2) ? data2 : []);
        }
      }
    } catch {
      // Portfolio may not have data yet
    }
    setLoading(false);
  }

  async function addPosition() {
    const t = form.ticker.trim().toUpperCase();
    const q = parseFloat(form.quantity);
    const p = parseFloat(form.avg_price);
    if (!t || isNaN(q) || isNaN(p)) return;

    try {
      const res = await fetch("/api/portfolio/positions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: t, quantity: q, avg_price: p }),
      });
      if (res.ok) {
        setForm({ ticker: "", quantity: "", avg_price: "" });
        fetchPortfolio();
      }
    } catch {
      // error
    }
  }

  async function uploadForOcr(file: File) {
    setIsProcessing(true);
    setOcrError("");
    try {
      const geminiKey = localStorage.getItem("atlas_gemini_key") || "";
      if (!geminiKey.trim()) {
        setOcrPositions([]);
        setOcrError("Gemini API key is missing. Please save your Gemini API Key in Settings first.");
        return;
      }

      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/portfolio/ocr", {
        method: "POST",
        body: fd,
        headers: geminiKey ? { "x-gemini-api-key": geminiKey } : undefined,
      });
      const data = await res.json().catch(() => null);
      const message =
        data?.error ||
        data?.detail ||
        (Array.isArray(data?.detail) ? data.detail.map((d: { msg?: string }) => d?.msg).filter(Boolean).join(", ") : "") ||
        (res.ok ? "" : `HTTP ${res.status}`);
      if (!res.ok || data?.error) {
        setOcrPositions([]);
        setOcrError(message || "OCR failed");
      } else {
        setOcrPositions(Array.isArray(data?.positions) ? data.positions : []);
        setOcrWarnings(Array.isArray(data?.warnings) ? data.warnings : []);
        setOcrAccountCurrency(data?.account_currency || data?.total_value?.currency || "USD");
        if (!Array.isArray(data?.positions) || data.positions.length === 0) {
          setOcrError("OCR completed but no positions were found. Try again with a clearer screenshot showing the table.");
        }
      }
    } catch {
      setOcrPositions([]);
      setOcrError("Network error during OCR upload");
    } finally {
      setIsProcessing(false);
    }
  }

  async function importOcrPositions() {
    if (!ocrPositions.length) return;
    const failed: string[] = [];
    for (let idx = 0; idx < ocrPositions.length; idx += 1) {
      const p = ocrPositions[idx];
      try {
        const rowKey = `${p.ticker}-${idx}`;
        const res = await fetch("/api/portfolio/positions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ticker: p.ticker,
            company_name: p.company_name || "",
            quantity: p.quantity,
            avg_price: p.avg_price,
            currency: p.avg_price_currency || p.stock_currency || "USD",
            exchange: exchangeSelections[rowKey] || p.exchange || "",
            source: "ocr",
          }),
        });
        if (!res.ok) failed.push(p.ticker);
      } catch {
        failed.push(p.ticker);
      }
    }
    if (failed.length > 0) {
      setOcrError(`Some imports failed: ${failed.join(", ")}. Keeping Import Results.`);
      return;
    }
    setOcrPositions([]);
    setOcrWarnings([]);
    setExchangeSelections({});
    setExchangeOptions({});
    setOcrError("");
    await fetchPortfolio();
  }

  function updateOcrPosition(idx: number, key: "quantity" | "avg_price", value: string) {
    setOcrPositions((prev) =>
      prev.map((p, i) => {
        if (i !== idx) return p;
        const n = Number(value);
        if (Number.isNaN(n)) return p;
        return { ...p, [key]: n };
      }),
    );
  }

  async function handleExchangeChange(idx: number, exchange: string) {
    const pos = ocrPositions[idx];
    if (!pos) return;
    const rowKey = `${pos.ticker}-${idx}`;
    setExchangeSelections((prev) => ({ ...prev, [rowKey]: exchange }));
    const res = await fetch("/api/portfolio/ocr/recalculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_currency: ocrAccountCurrency,
        position: pos,
        selected_exchange: exchange,
      }),
    });
    const data = await res.json().catch(() => null);
    if (res.ok && data?.position) {
      setOcrPositions((prev) => prev.map((p, i) => (i === idx ? { ...p, ...data.position, exchange } : p)));
    }
  }

  async function handleDelete(positionId: string) {
    try {
      const res = await fetch(`/api/portfolio/positions/${positionId}`, { method: "DELETE" });
      if (res.ok) {
        setPositions((prev) => prev.filter((p) => p.id !== positionId));
      }
    } finally {
      setDeleteConfirmId(null);
    }
  }

  async function handleSaveEdit(positionId: string) {
    const qty = parseFloat(editValues.qty);
    const avgPrice = parseFloat(editValues.avgPrice);
    if (isNaN(qty) || isNaN(avgPrice)) return;
    const res = await fetch(`/api/portfolio/positions/${positionId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantity: qty, avg_price: avgPrice }),
    });
    if (res.ok) {
      setPositions((prev) =>
        prev.map((p) => (p.id === positionId ? { ...p, quantity: qty, avg_price: avgPrice } : p)),
      );
      setEditingId(null);
      await fetchPortfolio();
    }
  }

  function convertAmount(amount: number, fromCurrency: string, toCurrency: string): number {
    if (!amount || Number.isNaN(amount)) return 0;
    const from = (fromCurrency || "USD").toUpperCase();
    const to = (toCurrency || "USD").toUpperCase();
    if (from === to) return amount;
    const key = `${from}_${to}`;
    const rate = fxRates[key] || 1;
    return amount * rate;
  }

  function getCurrencySymbol(currency: string): string {
    const symbols: Record<string, string> = { USD: "$", GBP: "£", KRW: "₩", EUR: "€", JPY: "¥", CNY: "¥" };
    return symbols[currency] || currency;
  }

  function formatCurrencyValue(amount: number, currency: string): string {
    const symbol = getCurrencySymbol(currency);
    if (currency === "KRW" || currency === "JPY") return `${symbol}${Math.round(amount).toLocaleString()}`;
    return `${symbol}${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  const totalValue = positions.reduce((s, p) => {
    const valueRaw = p.market_value || p.quantity * (p.current_price || p.avg_price);
    const src = (p.stock_currency || p.currency || "USD").toUpperCase();
    return s + convertAmount(valueRaw, src, displayCurrency);
  }, 0);
  const totalCost = positions.reduce((s, p) => {
    const src = (p.currency || p.avg_price_currency || p.stock_currency || "USD").toUpperCase();
    return s + convertAmount(p.quantity * p.avg_price, src, displayCurrency);
  }, 0);
  const totalGL = totalValue - totalCost;

  return (
    <div>
      <div className="portfolio-header">
        <h1 className="text-2xl font-bold">Portfolio</h1>
        <div className="currency-toggle">
          {["USD", "GBP", "KRW", "EUR", "JPY"].map((cur) => (
            <button
              key={cur}
              className={`currency-btn ${displayCurrency === cur ? "active" : ""}`}
              onClick={() => setDisplayCurrency(cur)}
            >
              {getCurrencySymbol(cur)} {cur}
            </button>
          ))}
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <div className="text-text-muted text-xs mb-1">Total Value</div>
          <div className="text-text-primary font-mono font-bold text-xl">{formatCurrencyValue(totalValue, displayCurrency)}</div>
        </div>
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <div className="text-text-muted text-xs mb-1">Total Cost</div>
          <div className="text-text-primary font-mono font-bold text-xl">{formatCurrencyValue(totalCost, displayCurrency)}</div>
        </div>
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <div className="text-text-muted text-xs mb-1">Total P&L</div>
          <div className={`font-mono font-bold text-xl ${totalGL >= 0 ? "text-accent-green" : "text-accent-red"}`}>
            {totalGL >= 0 ? "+" : ""}{formatCurrencyValue(Math.abs(totalGL), displayCurrency)}
          </div>
        </div>
      </div>

      <CorrelationMatrix />

      {/* Add Position */}
      <div className="bg-bg-card border border-border rounded-lg p-4 mb-6">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">Add Position</h3>
        <div className="flex gap-3">
          <input
            value={form.ticker}
            onChange={(e) => setForm({ ...form, ticker: e.target.value })}
            placeholder="Ticker"
            className="bg-bg-primary border border-border rounded-md px-3 py-2 text-text-primary outline-none w-32"
          />
          <input
            value={form.quantity}
            onChange={(e) => setForm({ ...form, quantity: e.target.value })}
            placeholder="Quantity"
            type="number"
            className="bg-bg-primary border border-border rounded-md px-3 py-2 text-text-primary outline-none w-32"
          />
          <input
            value={form.avg_price}
            onChange={(e) => setForm({ ...form, avg_price: e.target.value })}
            placeholder="Avg Price"
            type="number"
            className="bg-bg-primary border border-border rounded-md px-3 py-2 text-text-primary outline-none w-32"
          />
          <button onClick={addPosition} className="bg-accent-green text-bg-primary px-5 py-2 rounded-md font-semibold hover:opacity-90 transition-opacity">
            Add
          </button>
        </div>
      </div>

      {/* OCR Screenshot Import */}
      <div className="bg-bg-card border border-border rounded-lg p-4 mb-6">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">Import from Screenshot (OCR)</h3>
        <div
          className={`border-2 border-dashed ${isDragging ? "border-accent-blue bg-accent-blue/5" : "border-border"} rounded-lg p-10 text-center cursor-pointer mb-4`}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            setIsDragging(false);
          }}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            const f = e.dataTransfer.files?.[0];
            if (f) uploadForOcr(f);
          }}
          onClick={() => document.getElementById("ocr-file-input")?.click()}
        >
          {isProcessing ? (
            <p className="text-accent-green animate-pulse font-mono">AI is analyzing positions...</p>
          ) : (
            <>
              <span className="text-3xl mb-3 block">📸</span>
              <p className="text-text-secondary text-sm">Drag & drop a Trading 212 / IBKR screenshot</p>
            </>
          )}
        </div>
        <input
          id="ocr-file-input"
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) uploadForOcr(f);
          }}
        />
        {ocrError && <p className="text-accent-red text-sm mb-3">{ocrError}</p>}
        {ocrPositions.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="text-text-primary text-sm">
                Import Results: {ocrPositions.length} positions
              </div>
              <div className="text-text-muted text-xs">
                Account Currency: <span className="font-mono text-text-primary">{ocrAccountCurrency}</span>
              </div>
            </div>
            {ocrWarnings.length > 0 && (
              <details className="mb-3 bg-accent-yellow/10 border border-accent-yellow/30 rounded-md p-3">
                <summary className="text-accent-yellow text-sm cursor-pointer">Warnings ({ocrWarnings.length})</summary>
                <ul className="mt-2 space-y-1 text-xs text-text-secondary">
                  {ocrWarnings.map((w, i) => <li key={i}>- {w}</li>)}
                </ul>
              </details>
            )}
            <div className="overflow-auto border border-border rounded-md mb-3">
              <table className="w-full text-xs ocr-result-table">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left px-3 py-2 text-text-muted">Ticker</th>
                    <th className="text-left px-3 py-2 text-text-muted">Exchange</th>
                    <th className="text-left px-3 py-2 text-text-muted">Qty</th>
                    <th className="text-left px-3 py-2 text-text-muted">Avg</th>
                    <th className="text-left px-3 py-2 text-text-muted">Now</th>
                    <th className="text-left px-3 py-2 text-text-muted">Value ({ocrAccountCurrency})</th>
                    <th className="text-left px-3 py-2 text-text-muted">P&L %</th>
                    <th className="text-left px-3 py-2 text-text-muted">Conf</th>
                  </tr>
                </thead>
                <tbody>
                  {ocrPositions.map((p, i) => (
                    <tr key={`${p.ticker}-${i}`} className="border-b border-border/40">
                      {(() => {
                        const rowKey = `${p.ticker}-${i}`;
                        const opts = exchangeOptions[rowKey] || [];
                        const hasMultiple = opts.length > 1;
                        return (
                          <>
                      <td className="px-3 py-2 text-accent-green font-mono">{p.ticker}</td>
                      <td className="px-3 py-2 text-text-primary font-mono">
                        {hasMultiple ? (
                          <select
                            className="bg-bg-primary border border-border rounded px-2 py-1 text-xs"
                            value={exchangeSelections[rowKey] || p.exchange || ""}
                            onChange={(e) => handleExchangeChange(i, e.target.value)}
                          >
                            {opts.map((o) => (
                              <option key={o.exchange} value={o.exchange}>
                                {o.exchange} ({o.currency})
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="text-text-muted text-xs">{(opts[0]?.exchange || p.exchange || p.stock_currency || "Default")}</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-text-primary font-mono">
                        <input
                          type="number"
                          value={p.quantity ?? 0}
                          onChange={(e) => updateOcrPosition(i, "quantity", e.target.value)}
                          className="w-28 bg-bg-primary border border-border rounded px-2 py-1"
                        />
                      </td>
                      <td className="px-3 py-2 text-text-primary font-mono">
                        <input
                          type="number"
                          value={p.avg_price ?? 0}
                          onChange={(e) => updateOcrPosition(i, "avg_price", e.target.value)}
                          className="w-24 bg-bg-primary border border-border rounded px-2 py-1"
                        />
                        <span className="ml-1 text-text-muted">{p.avg_price_currency || p.stock_currency || "USD"}</span>
                      </td>
                      <td className="px-3 py-2 text-text-primary font-mono">
                        {p.current_price != null ? `${p.current_price.toFixed(2)} ${p.stock_currency || ""}` : "—"}
                      </td>
                      <td className="px-3 py-2 text-text-primary font-mono">
                        {p.current_value_account != null ? p.current_value_account.toLocaleString() : "—"}
                      </td>
                      <td className={`px-3 py-2 font-mono ${(p.pnl_pct || 0) >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                        {p.pnl_pct != null ? `${p.pnl_pct >= 0 ? "+" : ""}${p.pnl_pct.toFixed(2)}%` : "—"}
                      </td>
                      <td className="px-3 py-2">
                        {p.confidence === "high" ? (
                          <CheckCircle2 className="h-4 w-4 text-fin-positive" />
                        ) : p.confidence === "medium" ? (
                          <AlertTriangle className="h-4 w-4 text-fin-warning" />
                        ) : (
                          <CircleX className="h-4 w-4 text-fin-negative" />
                        )}
                      </td>
                          </>
                        );
                      })()}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => { setOcrPositions([]); setOcrWarnings([]); setOcrError(""); }}
                className="px-5 py-2 rounded-md border border-border text-text-secondary"
              >
                Cancel
              </button>
              <button onClick={importOcrPositions} className="inline-flex items-center gap-2 bg-accent-green text-bg-primary px-5 py-2 rounded-md font-semibold hover:opacity-90 transition-opacity">
                <Check className="h-4 w-4" />
                Add All to Portfolio
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Positions Table */}
      {positions.length > 0 ? (
        <div className="bg-bg-card border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {["Ticker", "Exchange", "Qty", "Avg Price", "Price", "Value", "P&L", "P&L %", "Actions"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-text-muted font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {positions.map((p, i) => {
                const pid = p.id || `${p.ticker}-${i}`;
                const price = p.current_price || p.avg_price;
                const valueRaw = p.market_value || p.quantity * price;
                const srcValueCurrency = (p.stock_currency || p.currency || "USD").toUpperCase();
                const value = convertAmount(valueRaw, srcValueCurrency, displayCurrency);
                const costRaw = p.quantity * p.avg_price;
                const srcCostCurrency = (p.currency || p.avg_price_currency || p.stock_currency || "USD").toUpperCase();
                const cost = convertAmount(costRaw, srcCostCurrency, displayCurrency);
                const gl = p.pnl != null ? convertAmount(p.pnl, srcValueCurrency, displayCurrency) : (value - cost);
                const glPct = p.pnl_pct ?? ((price / p.avg_price - 1) * 100);
                return (
                  <tr key={pid} className="border-b border-border/50 hover:bg-bg-hover/30">
                    <td className="px-4 py-2.5 font-mono font-semibold text-accent-green">{p.ticker}</td>
                    <td className="px-4 py-2.5 font-mono text-text-muted">{p.exchange || "—"}</td>
                    <td className="px-4 py-2.5 font-mono text-text-primary">
                      {editingId === pid ? (
                        <input
                          type="number"
                          step="any"
                          value={editValues.qty}
                          onChange={(e) => setEditValues((prev) => ({ ...prev, qty: e.target.value }))}
                          className="w-28 bg-bg-primary border border-accent-blue rounded px-2 py-1"
                          autoFocus
                        />
                      ) : (
                        p.quantity
                      )}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-text-primary">
                      {editingId === pid ? (
                        <input
                          type="number"
                          step="0.01"
                          value={editValues.avgPrice}
                          onChange={(e) => setEditValues((prev) => ({ ...prev, avgPrice: e.target.value }))}
                          className="w-24 bg-bg-primary border border-accent-blue rounded px-2 py-1"
                        />
                      ) : (
                        <>{formatCurrencyValue(convertAmount(p.avg_price, srcCostCurrency, displayCurrency), displayCurrency)}</>
                      )}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-text-primary">{formatCurrencyValue(convertAmount(price, srcValueCurrency, displayCurrency), displayCurrency)}</td>
                    <td className="px-4 py-2.5 font-mono text-text-primary">{formatCurrencyValue(value, displayCurrency)}</td>
                    <td className={`px-4 py-2.5 font-mono ${gl >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                      {gl >= 0 ? "+" : "-"}{formatCurrencyValue(Math.abs(gl), displayCurrency)}
                    </td>
                    <td className={`px-4 py-2.5 font-mono ${glPct >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                      {glPct >= 0 ? "+" : ""}{glPct.toFixed(1)}%
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {editingId === pid ? (
                        <div className="flex gap-1 justify-end">
                          <button onClick={() => handleSaveEdit(pid)} className="flex h-8 w-8 items-center justify-center rounded bg-accent-green/20 hover:bg-accent-green/30">
                            <Check className="h-4 w-4" />
                          </button>
                          <button onClick={() => setEditingId(null)} className="flex h-8 w-8 items-center justify-center rounded bg-bg-primary hover:bg-bg-hover">
                            <CircleX className="h-4 w-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex gap-1 justify-end">
                          <button
                            onClick={() => {
                              setEditingId(pid);
                              setEditValues({ qty: String(p.quantity), avgPrice: String(p.avg_price) });
                            }}
                            className="flex h-8 w-8 items-center justify-center rounded hover:bg-bg-hover"
                            title="Edit position"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(pid)}
                            className="flex h-8 w-8 items-center justify-center rounded hover:bg-accent-red/20"
                            title="Delete position"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : !loading ? (
        <div className="bg-bg-card border border-border rounded-lg p-8 text-center text-text-muted">
          No positions yet. Add your first position above.
        </div>
      ) : null}

      {deleteConfirmId && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[1000]" onClick={() => setDeleteConfirmId(null)}>
          <div className="bg-bg-card border border-border rounded-xl p-6 max-w-sm w-full" onClick={(e) => e.stopPropagation()}>
            <p className="text-text-primary mb-1">Are you sure you want to delete this?</p>
            <p className="text-text-muted text-sm mb-4">This action cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteConfirmId(null)} className="px-4 py-2 border border-border rounded-md text-text-secondary">Cancel</button>
              <button onClick={() => handleDelete(deleteConfirmId)} className="px-4 py-2 bg-accent-red text-white rounded-md">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
