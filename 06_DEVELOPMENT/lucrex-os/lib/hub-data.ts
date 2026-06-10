/**
 * Hub KPI provider. Each domain returns a single headline metric.
 * Phase 1: real data where available, placeholders elsewhere. Wire in API in phase 2.
 */
import type { DomainKey } from "./theme";

export type HubKPI = {
  label: string;
  value: string;
  delta?: string;
  status: "active" | "idle" | "alert" | "neutral";
};

export async function getHubKPIs(): Promise<Record<DomainKey, HubKPI>> {
  // TODO phase 2: parallel fetch from Django :8504 + Supabase + Blinko
  return {
    hub: { label: "domains live", value: "9", status: "active" },
    wealth: {
      label: "current tier",
      value: "T0",
      delta: "Foundation",
      status: "active",
    },
    trading: {
      label: "XLM bot",
      value: "live",
      delta: "sniper mode",
      status: "active",
    },
    wholesale: {
      label: "active leads",
      value: "0",
      delta: "Cleveland niche",
      status: "idle",
    },
    broker: {
      label: "first deal",
      value: "$47.50",
      delta: "intro stage",
      status: "active",
    },
    content: {
      label: "queue",
      value: "8",
      delta: "IG kit",
      status: "neutral",
    },
    revenue: {
      label: "MRR",
      value: "$0",
      delta: "→ $10k goal",
      status: "idle",
    },
    intel: {
      label: "Blinko notes",
      value: "449",
      delta: "+12 this week",
      status: "active",
    },
    hive: {
      label: "agents",
      value: "63",
      delta: "12 fire teams",
      status: "active",
    },
    arcade: {
      label: "Vantaris",
      value: "build",
      delta: "blackjack v2",
      status: "neutral",
    },
  };
}
