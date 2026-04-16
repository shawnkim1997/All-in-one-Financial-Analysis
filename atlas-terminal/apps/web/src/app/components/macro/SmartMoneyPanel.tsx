"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { chartPalette } from "../../lib/chart-theme";

export interface CopperGoldRow {
  date: string;
  ratio: number;
  ratio_ma20?: number;
}

function RoroGauge({ z, label }: { z: number | null; label: string | null }) {
  const v = z == null || Number.isNaN(z) ? 0 : Math.max(-3, Math.min(3, z));
  const angle = ((v + 3) / 6) * 180;
  const rad = (angle * Math.PI) / 180;
  const cx = 100;
  const cy = 100;
  const r = 70;
  const x2 = cx + r * Math.cos(Math.PI - rad);
  const y2 = cy - r * Math.sin(Math.PI - rad);

  return (
    <div className="flex flex-col items-center justify-center min-w-[200px]">
      <p className="text-text-muted text-xs font-mono mb-2">RORO (VIX + bond vol Z)</p>
      <svg viewBox="0 0 200 110" className="w-52 h-28">
        <path
          d="M 30 100 A 70 70 0 0 1 170 100"
          fill="none"
          stroke={chartPalette.grid}
          strokeWidth="10"
          strokeLinecap="round"
        />
        <path
          d="M 30 100 A 70 70 0 0 1 170 100"
          fill="none"
          stroke="url(#roroGrad)"
          strokeWidth="10"
          strokeLinecap="round"
          opacity={0.35}
        />
        <defs>
          <linearGradient id="roroGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={chartPalette.red} />
            <stop offset="50%" stopColor={chartPalette.gold} />
            <stop offset="100%" stopColor={chartPalette.green} />
          </linearGradient>
        </defs>
        <line x1={cx} y1={cy} x2={x2} y2={y2} stroke={chartPalette.text} strokeWidth="3" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="6" fill={chartPalette.navy} />
        <text x="30" y="108" fill={chartPalette.textMuted} fontSize="9" fontFamily="monospace">
          Fear
        </text>
        <text x="150" y="108" fill={chartPalette.textMuted} fontSize="9" fontFamily="monospace">
          Greed
        </text>
      </svg>
      <p className="mt-1 font-mono text-lg text-brand-navy">{label ?? "—"}</p>
      <p className="text-text-muted text-xs font-mono">Z = {z != null ? z.toFixed(2) : "—"}</p>
    </div>
  );
}

export function SmartMoneyPanel({
  roroZ,
  roroLabel,
  copperGold,
}: {
  roroZ: number | null;
  roroLabel: string | null;
  copperGold: CopperGoldRow[];
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">
      <div className="flex items-center justify-center rounded-lg border border-border/50 bg-surface-sunken p-4">
        <RoroGauge z={roroZ} label={roroLabel} />
      </div>
      <div className="min-h-[260px]">
        <p className="text-text-muted text-xs font-mono mb-2">Copper / Gold</p>
        {!copperGold.length ? (
          <div className="h-[240px] flex items-center justify-center text-text-muted text-sm font-mono">
            No copper/gold series.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={copperGold} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={chartPalette.grid} />
              <XAxis dataKey="date" tick={{ fill: chartPalette.textMuted, fontSize: 9 }} minTickGap={32} />
              <YAxis tick={{ fill: chartPalette.textMuted, fontSize: 10 }} domain={["auto", "auto"]} />
              <Tooltip
                contentStyle={{ background: chartPalette.canvas, border: `1px solid ${chartPalette.grid}`, fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="ratio" name="Cu/Au" stroke={chartPalette.gold} dot={false} strokeWidth={2} />
              <Line
                type="monotone"
                dataKey="ratio_ma20"
                name="MA20"
                stroke={chartPalette.blue}
                dot={false}
                strokeWidth={1.5}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
