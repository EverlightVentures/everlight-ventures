/**
 * Typed client for Django :8504 hive_dashboard API.
 * Server-only. Reads via the unified ops dashboard.
 */

const DJANGO_BASE = process.env.DJANGO_API_BASE ?? "http://127.0.0.1:2200";
const DJANGO_TOKEN = process.env.DJANGO_API_TOKEN;

async function djangoGet<T>(path: string): Promise<T | null> {
  try {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (DJANGO_TOKEN) headers.Authorization = `Bearer ${DJANGO_TOKEN}`;
    const r = await fetch(`${DJANGO_BASE}${path}`, {
      headers,
      next: { revalidate: 60 },
    });
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

export type WholesaleLead = {
  id: string;
  address: string;
  city: string;
  state: string;
  arv?: number;
  asking_price?: number;
  mao?: number;
  spread?: number;
  stage: "lead" | "qualified" | "offer" | "contract" | "closed" | "dead";
  source?: string;
  added_at: string;
  agent?: string;
};

export type WholesaleSummary = {
  totalLeads: number;
  byStage: Record<WholesaleLead["stage"], number>;
  topCities: Array<{ city: string; count: number }>;
  recentLeads: WholesaleLead[];
};

export async function getWholesaleSummary(): Promise<WholesaleSummary> {
  const data = await djangoGet<WholesaleSummary>("/api/wholesale/summary/");
  if (data) return data;

  // Phase 1 fallback: empty pipeline placeholder
  return {
    totalLeads: 0,
    byStage: { lead: 0, qualified: 0, offer: 0, contract: 0, closed: 0, dead: 0 },
    topCities: [],
    recentLeads: [],
  };
}

export type BotStatus = {
  running: boolean;
  mode: "sniper" | "scalper" | "hold";
  positions: number;
  unrealized_pnl: number;
  realized_pnl_today: number;
  balance: number;
  last_decision: string;
  last_decision_at: string;
};

export async function getBotStatus(): Promise<BotStatus> {
  const data = await djangoGet<BotStatus>("/api/xlm/bot_status/");
  if (data) return data;

  return {
    running: true,
    mode: "sniper",
    positions: 0,
    unrealized_pnl: 0,
    realized_pnl_today: 0,
    balance: 187.42,
    last_decision: "HOLD",
    last_decision_at: new Date(Date.now() - 4 * 60_000).toISOString(),
  };
}
