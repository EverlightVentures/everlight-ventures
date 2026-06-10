"use client";
import { LineChart, Line, ResponsiveContainer, Tooltip, YAxis } from "recharts";
import type { EquityPoint } from "@/lib/api/xlm-bot";

export function EquitySpark({ points }: { points: EquityPoint[] }) {
  if (!points.length) {
    return (
      <div className="h-24 flex items-center justify-center text-xs text-[var(--color-muted)]">
        no equity series yet
      </div>
    );
  }
  const data = points.map((p) => ({ t: new Date(p.ts).getTime(), v: p.equity_usd }));
  const min = Math.min(...data.map((d) => d.v));
  const max = Math.max(...data.map((d) => d.v));
  const last = data[data.length - 1].v;
  const first = data[0].v;
  const trendUp = last >= first;

  return (
    <div className="h-24">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
          <YAxis hide domain={[min * 0.995, max * 1.005]} />
          <Tooltip
            contentStyle={{ background: "#141414", border: "1px solid #2A2A2A", borderRadius: 6, fontSize: 11 }}
            labelFormatter={() => ""}
            formatter={(v: number) => [`$${v.toFixed(2)}`, "equity"]}
          />
          <Line
            type="monotone"
            dataKey="v"
            stroke={trendUp ? "#22C55E" : "#EF4444"}
            strokeWidth={1.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
