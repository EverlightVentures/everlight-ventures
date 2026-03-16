"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn, getTrendSign } from "@/lib/utils";
import type { KpiMetric } from "@/types";

// ============================================================
// Types
// ============================================================
interface KpiCardProps {
  metric: KpiMetric;
  icon: React.ReactNode;
  className?: string;
  animate?: boolean;
}

// ============================================================
// Glow color map
// ============================================================
const GLOW_CONFIG = {
  violet: {
    numberClass: "glow-number-violet",
    iconBg: "rgba(124,58,237,0.12)",
    iconBorder: "rgba(124,58,237,0.2)",
    iconColor: "#A78BFA",
    cardBorder: "rgba(124,58,237,0.15)",
    cardGlow: "rgba(124,58,237,0.06)",
    shimmer: "rgba(124,58,237,0.04)",
  },
  gold: {
    numberClass: "glow-number-gold",
    iconBg: "rgba(245,158,11,0.12)",
    iconBorder: "rgba(245,158,11,0.2)",
    iconColor: "#FCD34D",
    cardBorder: "rgba(245,158,11,0.15)",
    cardGlow: "rgba(245,158,11,0.06)",
    shimmer: "rgba(245,158,11,0.04)",
  },
  success: {
    numberClass: "glow-number-success",
    iconBg: "rgba(16,185,129,0.12)",
    iconBorder: "rgba(16,185,129,0.2)",
    iconColor: "#34D399",
    cardBorder: "rgba(16,185,129,0.15)",
    cardGlow: "rgba(16,185,129,0.06)",
    shimmer: "rgba(16,185,129,0.04)",
  },
  danger: {
    numberClass: "text-red-400",
    iconBg: "rgba(239,68,68,0.12)",
    iconBorder: "rgba(239,68,68,0.2)",
    iconColor: "#F87171",
    cardBorder: "rgba(239,68,68,0.15)",
    cardGlow: "rgba(239,68,68,0.06)",
    shimmer: "rgba(239,68,68,0.04)",
  },
} as const;

// ============================================================
// Trend Indicator
// ============================================================
function TrendIndicator({ metric }: { metric: KpiMetric }) {
  const { trend, change } = metric;

  if (trend === "neutral") {
    return (
      <span className="flex items-center gap-1 text-[#5C5C7A] text-xs font-medium">
        <Minus size={12} />
        <span>No change</span>
      </span>
    );
  }

  const isUp = trend === "up";
  const colorClass = isUp ? "text-emerald-400" : "text-red-400";
  const TrendIcon = isUp ? TrendingUp : TrendingDown;
  const bgColor = isUp ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)";

  return (
    <span
      className={cn("flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-md", colorClass)}
      style={{ background: bgColor }}
    >
      <TrendIcon size={11} strokeWidth={2.5} />
      <span>
        {getTrendSign(change)}{Math.abs(change).toFixed(1)}%
      </span>
    </span>
  );
}

// ============================================================
// Main KpiCard Component
// ============================================================
export default function KpiCard({ metric, icon, className, animate = true }: KpiCardProps) {
  const glowCfg = GLOW_CONFIG[metric.glowColor];

  const displayValue = typeof metric.value === "number"
    ? `${metric.prefix ?? ""}${metric.value.toLocaleString("en-US")}${metric.suffix ?? ""}`
    : `${metric.prefix ?? ""}${metric.value}${metric.suffix ?? ""}`;

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl p-5 group cursor-default",
        "transition-all duration-300 hover:-translate-y-0.5",
        animate && "animate-fade-up",
        className
      )}
      style={{
        background: "linear-gradient(135deg, #16161F 0%, #111118 100%)",
        border: `1px solid ${glowCfg.cardBorder}`,
        boxShadow: `0 1px 3px rgba(0,0,0,0.5), 0 4px 16px rgba(0,0,0,0.3), 0 0 40px ${glowCfg.cardGlow}, inset 0 1px 0 rgba(255,255,255,0.04)`,
      }}
    >
      {/* Background shimmer on hover */}
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
        style={{
          background: `radial-gradient(ellipse 100% 100% at 50% 0%, ${glowCfg.shimmer} 0%, transparent 70%)`,
        }}
      />

      {/* Top row: label + icon */}
      <div className="flex items-start justify-between mb-4">
        <span className="text-[12px] font-semibold tracking-[0.06em] uppercase text-[#5C5C7A]">
          {metric.label}
        </span>
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{
            background: glowCfg.iconBg,
            border: `1px solid ${glowCfg.iconBorder}`,
            color: glowCfg.iconColor,
          }}
        >
          {icon}
        </div>
      </div>

      {/* Primary number */}
      <div className="mb-3">
        <span
          className={cn("text-3xl font-bold tracking-tight leading-none", glowCfg.numberClass)}
          style={{ fontFamily: "'DM Sans', sans-serif" }}
        >
          {displayValue}
        </span>
      </div>

      {/* Footer: trend + description */}
      <div className="flex items-center justify-between">
        <TrendIndicator metric={metric} />
        {metric.description && (
          <span className="text-[11px] text-[#5C5C7A] text-right leading-tight max-w-[60%]">
            {metric.description}
          </span>
        )}
      </div>

      {/* Bottom glow line */}
      <div
        className="absolute bottom-0 left-0 right-0 h-px"
        style={{
          background: `linear-gradient(90deg, transparent 0%, ${glowCfg.cardBorder} 50%, transparent 100%)`,
        }}
      />
    </div>
  );
}
