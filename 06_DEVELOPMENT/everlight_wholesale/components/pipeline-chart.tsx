"use client";

import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";

export function PipelineChart({
  data,
}: {
  data: { state: string; total: number; contactable: number; in_seq: number; replied: number }[];
}) {
  return (
    <div className="bg-card-gradient border border-ash rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-[10px] tracking-[0.3em] text-fog uppercase">By state</div>
          <h3 className="font-display text-xl text-ivory mt-1">Lead distribution</h3>
        </div>
        <div className="flex items-center gap-3 text-[11px]">
          <Legend color="#D4A843" label="total" />
          <Legend color="#EAD08B" label="contactable" />
          <Legend color="#65D195" label="in-seq" />
        </div>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
          <XAxis
            dataKey="state"
            axisLine={false}
            tickLine={false}
            stroke="#9A9A9A"
            style={{ fontSize: 11, fontFamily: "Inter" }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            stroke="#9A9A9A"
            style={{ fontSize: 11, fontFamily: "Inter" }}
          />
          <Tooltip
            cursor={{ fill: "rgba(212,168,67,0.05)" }}
            contentStyle={{
              background: "#141414",
              border: "1px solid #222",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: "#D4A843" }}
          />
          <Bar dataKey="total" fill="#D4A843" radius={[4, 4, 0, 0]} barSize={14}>
            {data.map((_, i) => <Cell key={i} fill="#D4A843" />)}
          </Bar>
          <Bar dataKey="contactable" fill="#EAD08B" radius={[4, 4, 0, 0]} barSize={14} />
          <Bar dataKey="in_seq" fill="#65D195" radius={[4, 4, 0, 0]} barSize={14} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5 text-fog">
      <span className="w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}
