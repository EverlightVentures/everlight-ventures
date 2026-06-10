"use client";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from "recharts";

export type PriorityWeights = {
  TAX_MINIMIZATION: number;
  LIQUIDITY: number;
  ASSET_PROTECTION: number;
  GROWTH_LEVERAGE: number;
  GEOGRAPHIC_FREEDOM: number;
  PRIVACY: number;
  GENERATIONAL: number;
  SPEED_OF_DEPLOY: number;
  COMPLEXITY_TOLERANCE: number;
  ETHICS_FLOOR: number;
};

const LABELS: Record<keyof PriorityWeights, string> = {
  TAX_MINIMIZATION: "Tax Min",
  LIQUIDITY: "Liquidity",
  ASSET_PROTECTION: "Protection",
  GROWTH_LEVERAGE: "Growth",
  GEOGRAPHIC_FREEDOM: "Geo Free",
  PRIVACY: "Privacy",
  GENERATIONAL: "Gen'l",
  SPEED_OF_DEPLOY: "Speed",
  COMPLEXITY_TOLERANCE: "Complex",
  ETHICS_FLOOR: "Ethics",
};

export function RadarPriorities({ weights }: { weights: PriorityWeights | null }) {
  if (!weights) {
    return (
      <div className="h-72 flex flex-col items-center justify-center text-center px-6">
        <div className="text-sm text-[var(--color-muted)] mb-2">PRIORITIES.md not yet filled</div>
        <div className="text-xs text-[var(--color-faint)]">
          Set 10 weights (1--10) and Lucrex calibrates every tier to your values.
        </div>
      </div>
    );
  }

  const data = (Object.keys(weights) as Array<keyof PriorityWeights>).map((k) => ({
    axis: LABELS[k],
    value: weights[k],
  }));

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} margin={{ top: 12, right: 32, bottom: 12, left: 32 }}>
          <PolarGrid stroke="#2A2A2A" />
          <PolarAngleAxis
            dataKey="axis"
            tick={{ fill: "#888888", fontSize: 11, fontFamily: "Inter" }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 10]}
            tick={{ fill: "#555", fontSize: 9 }}
            stroke="#2A2A2A"
          />
          <Radar
            name="weights"
            dataKey="value"
            stroke="#D4A843"
            fill="#D4A843"
            fillOpacity={0.35}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
