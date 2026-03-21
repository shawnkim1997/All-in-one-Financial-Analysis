"use client";
import { useState, useEffect } from "react";

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
}

export default function PortfolioPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [form, setForm] = useState({ ticker: "", quantity: "", avg_price: "" });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPortfolio();
  }, []);

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

  const totalValue = positions.reduce((s, p) => s + (p.market_value || p.quantity * (p.current_price || p.avg_price)), 0);
  const totalCost = positions.reduce((s, p) => s + p.quantity * p.avg_price, 0);
  const totalGL = totalValue - totalCost;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Portfolio</h1>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <div className="text-text-muted text-xs mb-1">Total Value</div>
          <div className="text-text-primary font-mono font-bold text-xl">${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        </div>
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <div className="text-text-muted text-xs mb-1">Total Cost</div>
          <div className="text-text-primary font-mono font-bold text-xl">${totalCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        </div>
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <div className="text-text-muted text-xs mb-1">Total P&L</div>
          <div className={`font-mono font-bold text-xl ${totalGL >= 0 ? "text-accent-green" : "text-accent-red"}`}>
            {totalGL >= 0 ? "+" : ""}${totalGL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>
      </div>

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

      {/* Positions Table */}
      {positions.length > 0 ? (
        <div className="bg-bg-card border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {["Ticker", "Qty", "Avg Price", "Price", "Value", "P&L", "P&L %"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-text-muted font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {positions.map((p, i) => {
                const price = p.current_price || p.avg_price;
                const value = p.market_value || p.quantity * price;
                const gl = p.pnl ?? (value - p.quantity * p.avg_price);
                const glPct = p.pnl_pct ?? ((price / p.avg_price - 1) * 100);
                return (
                  <tr key={p.id || `${p.ticker}-${i}`} className="border-b border-border/50 hover:bg-bg-hover/30">
                    <td className="px-4 py-2.5 font-mono font-semibold text-accent-green">{p.ticker}</td>
                    <td className="px-4 py-2.5 font-mono text-text-primary">{p.quantity}</td>
                    <td className="px-4 py-2.5 font-mono text-text-primary">${p.avg_price.toFixed(2)}</td>
                    <td className="px-4 py-2.5 font-mono text-text-primary">${price.toFixed(2)}</td>
                    <td className="px-4 py-2.5 font-mono text-text-primary">${value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className={`px-4 py-2.5 font-mono ${gl >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                      {gl >= 0 ? "+" : ""}${gl.toFixed(2)}
                    </td>
                    <td className={`px-4 py-2.5 font-mono ${glPct >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                      {glPct >= 0 ? "+" : ""}{glPct.toFixed(1)}%
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
    </div>
  );
}
