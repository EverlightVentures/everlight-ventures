"use client";
import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { StatusBadge } from "@/components/StatusBadge";
import { TrendingUp, TrendingDown, Activity } from "lucide-react";

const SCENARIOS = [
  { key: "base",    label: "Base case (current trajectory)",       cagr: 0.45, vol: 0.20, color: "#D4A843" },
  { key: "boom",    label: "Boom (Wholesale + Bot scale)",         cagr: 0.85, vol: 0.30, color: "#22C55E" },
  { key: "drawdown", label: "Drawdown (Recession + RE freeze)",    cagr: 0.05, vol: 0.45, color: "#EF4444" },
  { key: "tcja",    label: "TCJA sunset realized",                 cagr: 0.35, vol: 0.25, color: "#F59E0B" },
  { key: "pr",      label: "PR Act 60 + offshore at T9",           cagr: 0.55, vol: 0.18, color: "#06B6D4" },
];

function projectNetWorth(start: number, years: number, cagr: number) {
  const out: { year: number; value: number }[] = [];
  for (let y = 0; y <= years; y++) {
    out.push({ year: 2026 + y, value: Math.round(start * Math.pow(1 + cagr, y)) });
  }
  return out;
}

const STARTING = 0;
const SEED = 50_000;

export default function ScenariosPage() {
  const [active, setActive] = useState(SCENARIOS.map((s) => s.key));

  const chartData: Array<Record<string, number>> = [];
  for (let y = 0; y <= 15; y++) {
    const row: Record<string, number> = { year: 2026 + y };
    for (const s of SCENARIOS) {
      row[s.key] = Math.round(SEED * Math.pow(1 + s.cagr, y));
    }
    chartData.push(row);
  }

  return (
    <div>
      <div className="mb-6">
        <div className="text-[10px] uppercase tracking-[0.25em] text-[var(--color-gold-500)] mb-1">
          06_Scenarios
        </div>
        <h2 className="font-display text-2xl md:text-3xl font-semibold">Stress tests</h2>
        <p className="text-sm text-[var(--color-muted)] mt-1 max-w-3xl">
          Pre-positioned responses. Each scenario assumes a $50k seed (post-first-deal) and projects 15 years.
          CAGR and volatility shown beside each toggle. Toggle scenarios on the left to compare.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1 space-y-2">
          {SCENARIOS.map((s) => {
            const on = active.includes(s.key);
            return (
              <button
                key={s.key}
                onClick={() =>
                  setActive((prev) =>
                    prev.includes(s.key) ? prev.filter((k) => k !== s.key) : [...prev, s.key]
                  )
                }
                className={`w-full text-left rounded-lg border p-3 transition ${
                  on
                    ? "bg-[var(--color-surface)] border-[var(--color-gold-700)]"
                    : "bg-[var(--color-surface)]/40 border-[var(--color-border)] opacity-50"
                }`}
              >
                <div className="flex items-start gap-2">
                  <span
                    className="mt-1.5 h-2 w-2 rounded-full flex-shrink-0"
                    style={{ background: s.color }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm">{s.label}</div>
                    <div className="text-[11px] text-[var(--color-muted)] font-mono mt-0.5">
                      CAGR {(s.cagr * 100).toFixed(0)}% · vol {(s.vol * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <div className="lg:col-span-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <div className="h-80 md:h-96">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2A2A2A" />
                <XAxis dataKey="year" stroke="#888" tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }} />
                <YAxis
                  stroke="#888"
                  tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
                  tickFormatter={(v) => v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : `$${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  contentStyle={{
                    background: "#141414",
                    border: "1px solid #2A2A2A",
                    borderRadius: 8,
                    fontFamily: "JetBrains Mono",
                  }}
                  labelStyle={{ color: "#D4A843" }}
                  formatter={(v: number) => [`$${v.toLocaleString()}`, ""]}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {SCENARIOS.filter((s) => active.includes(s.key)).map((s) => (
                  <Line
                    key={s.key}
                    type="monotone"
                    dataKey={s.key}
                    name={s.label.split(" (")[0]}
                    stroke={s.color}
                    strokeWidth={2}
                    dot={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="flex items-start gap-2 text-[var(--color-success)]">
              <TrendingUp size={14} className="mt-0.5 flex-shrink-0" />
              <span className="text-[var(--color-muted)]">
                <span className="text-[var(--color-fg)] font-medium">Boom path:</span> Wholesale velocity + bot scaling pushes 85% CAGR. T6 by 2029.
              </span>
            </div>
            <div className="flex items-start gap-2 text-[var(--color-alert)]">
              <TrendingDown size={14} className="mt-0.5 flex-shrink-0" />
              <span className="text-[var(--color-muted)]">
                <span className="text-[var(--color-fg)] font-medium">Drawdown:</span> Capital preservation engine activates. Liquidity Crisis playbook in 03_Engines.
              </span>
            </div>
            <div className="flex items-start gap-2 text-[var(--color-gold-500)]">
              <Activity size={14} className="mt-0.5 flex-shrink-0" />
              <span className="text-[var(--color-muted)]">
                <span className="text-[var(--color-fg)] font-medium">Base:</span> 45% CAGR keeps T6 cliff inside the window. SLAT urgency stays low.
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-display text-lg font-semibold">Disclaimer</h3>
          <StatusBadge variant="muted">research only</StatusBadge>
        </div>
        <p className="text-xs text-[var(--color-muted)] leading-relaxed">
          These projections are deterministic compound-growth models. Actual outcomes depend on market regime,
          tax law, deployment cadence, and execution quality. Real Monte Carlo lives in the Hive (run via
          <span className="text-[var(--color-gold-400)] mx-1">strategic_modeler</span>
          agent and writes to <code>06_Scenarios/</code>). This view is the at-a-glance intuition layer.
        </p>
      </div>
    </div>
  );
}
