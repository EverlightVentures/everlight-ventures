/**
 * Live XLM bot data layer.
 * Reads directly from xlm-bot's runtime files on Oracle.
 * Server-only.
 */
import fs from "node:fs/promises";
import path from "node:path";

const XLM_LOGS = process.env.XLM_BOT_LOGS ?? "/home/opc/xlm-bot/logs";

export type BotSnapshot = {
  ts: string;
  state: string;
  last_action: string;
  thought: string;
  price: number;
  product: string;
  safe_mode: boolean;
  margin_tier: string;
  active_mr: number;
  spot_usdc: number;
  derivatives_usdc: number;
  transfers_today_usd: number;
  reconcile_status: string;
  trades_today: number;
  losses_today: number;
  max_trades_per_day: number;
  pnl_today_usd: number;
  equity_start_usd: number;
  margin_window: string;
  cooldown: number;
  // Active position (only meaningful when state == IN_TRADE)
  entry_time?: string | null;
  entry_price?: number | null;
  pnl_pct?: number | null;
  pnl_usd_live?: number | null;
  size?: number | null;
  leverage?: number | null;
  time_in_trade_min?: number | null;
  // AI executive output
  unified_recommendation?: string;
  unified_direction?: string;
  unified_p_win?: number;
  unified_rr_ratio?: number;
  unified_narrative?: string;
  // Risk
  trap_analysis?: { warning?: string; conviction?: string } | null;
  // Telemetry
  age_seconds?: number;
};

export type BotDecision = {
  ts: string;
  action: string;
  reason?: string;
  thought?: string;
  state?: string;
  price?: number;
};

export async function getBotSnapshot(): Promise<BotSnapshot | null> {
  try {
    const raw = await fs.readFile(path.join(XLM_LOGS, "dashboard_snapshot.json"), "utf-8");
    const snap = JSON.parse(raw) as BotSnapshot;
    if (snap.ts) {
      snap.age_seconds = Math.floor((Date.now() - new Date(snap.ts).getTime()) / 1000);
    }
    return snap;
  } catch {
    return null;
  }
}

export async function getRecentDecisions(limit = 12): Promise<BotDecision[]> {
  try {
    const filepath = path.join(XLM_LOGS, "decisions.jsonl");
    // Read tail efficiently for a large file: open last 256KB
    const stat = await fs.stat(filepath);
    const start = Math.max(0, stat.size - 256 * 1024);
    const fd = await fs.open(filepath, "r");
    const buf = Buffer.alloc(stat.size - start);
    await fd.read(buf, 0, buf.length, start);
    await fd.close();
    const text = buf.toString("utf-8");
    const lines = text.split("\n").filter(Boolean);
    const tail = lines.slice(-limit);
    const decisions: BotDecision[] = [];
    for (const line of tail) {
      try {
        const d = JSON.parse(line) as BotDecision;
        decisions.push(d);
      } catch {
        // skip malformed
      }
    }
    return decisions.reverse();
  } catch {
    return [];
  }
}

export type EquityPoint = { ts: string; equity_usd: number };

export async function getEquitySeries(limit = 200): Promise<EquityPoint[]> {
  try {
    const filepath = path.join(XLM_LOGS, "equity_series.jsonl");
    const stat = await fs.stat(filepath);
    const start = Math.max(0, stat.size - 64 * 1024);
    const fd = await fs.open(filepath, "r");
    const buf = Buffer.alloc(stat.size - start);
    await fd.read(buf, 0, buf.length, start);
    await fd.close();
    const lines = buf.toString("utf-8").split("\n").filter(Boolean);
    const points: EquityPoint[] = [];
    for (const line of lines.slice(-limit)) {
      try {
        const d = JSON.parse(line);
        if (d.ts && (d.equity_usd != null || d.equity != null)) {
          points.push({ ts: d.ts, equity_usd: d.equity_usd ?? d.equity });
        }
      } catch {
        // skip
      }
    }
    return points;
  } catch {
    return [];
  }
}

export function totalEquity(snap: BotSnapshot): number {
  return (snap.spot_usdc ?? 0) + (snap.derivatives_usdc ?? 0);
}

export function isLive(snap: BotSnapshot): boolean {
  return (snap.age_seconds ?? Infinity) < 120;
}

export type ClosedTrade = {
  entry_time: string;
  exit_time: string;
  product_id: string;
  side: string;
  size: number;
  entry_price: number;
  exit_price: number;
  pnl_usd: number;
  pnl_pct: number;
  exit_reason: string;
  time_in_trade_min: number;
  total_fees_usd: number;
  strategy_regime?: string;
  confluence_score?: number;
};

function num(v: string | undefined): number {
  if (v == null || v === "") return 0;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function parseCsvLine(line: string): string[] {
  // Lightweight CSV split: trades.csv has no embedded commas in quoted fields per
  // the bot writer at xlm_bot/csv_writer.py; a naive split is sufficient.
  return line.split(",");
}

export async function getClosedTrades(limit = 200): Promise<ClosedTrade[]> {
  try {
    const filepath = path.join(XLM_LOGS, "trades.csv");
    const stat = await fs.stat(filepath);
    // Read up to last 1 MB; that is ~10k trades, far more than any reasonable limit.
    const start = Math.max(0, stat.size - 1024 * 1024);
    const fd = await fs.open(filepath, "r");
    const buf = Buffer.alloc(stat.size - start);
    await fd.read(buf, 0, buf.length, start);
    await fd.close();
    const text = buf.toString("utf-8");
    const lines = text.split("\n").filter(Boolean);
    if (lines.length === 0) return [];
    // Header: read from the first chunk if we started mid-file (it might be partial),
    // so always read header from offset 0 separately.
    let header: string[];
    if (start === 0) {
      header = parseCsvLine(lines[0]);
    } else {
      const headerFd = await fs.open(filepath, "r");
      const headerBuf = Buffer.alloc(2048);
      await headerFd.read(headerBuf, 0, headerBuf.length, 0);
      await headerFd.close();
      header = parseCsvLine(headerBuf.toString("utf-8").split("\n")[0]);
    }
    const idx: Record<string, number> = {};
    header.forEach((h, i) => { idx[h.trim()] = i; });

    const dataLines = start === 0 ? lines.slice(1) : lines.slice(1); // skip first partial line if mid-file
    const trades: ClosedTrade[] = [];
    for (const line of dataLines) {
      const cells = parseCsvLine(line);
      if (cells.length < 5) continue;
      const exit_price = num(cells[idx.exit_price]);
      const pnl_usd_str = cells[idx.pnl_usd];
      if (!exit_price || pnl_usd_str == null || pnl_usd_str === "") continue;
      trades.push({
        entry_time: cells[idx.entry_time] ?? cells[idx.timestamp] ?? "",
        exit_time: cells[idx.exit_time] ?? "",
        product_id: cells[idx.product_id] ?? "",
        side: cells[idx.side] ?? "",
        size: num(cells[idx.size]),
        entry_price: num(cells[idx.entry_price]),
        exit_price,
        pnl_usd: num(pnl_usd_str),
        pnl_pct: num(cells[idx.pnl_pct]),
        exit_reason: cells[idx.exit_reason] ?? "",
        time_in_trade_min: num(cells[idx.time_in_trade_min]),
        total_fees_usd: num(cells[idx.total_fees_usd]),
        strategy_regime: cells[idx.strategy_regime],
        confluence_score: num(cells[idx.confluence_score]),
      });
    }
    trades.sort((a, b) => (b.exit_time || "").localeCompare(a.exit_time || ""));
    return trades.slice(0, limit);
  } catch {
    return [];
  }
}

export type TradeStats = {
  count: number;
  wins: number;
  losses: number;
  winRate: number;
  totalPnl: number;
  totalFees: number;
  avgPnl: number;
  bestTrade: number;
  worstTrade: number;
};

export function computeTradeStats(trades: ClosedTrade[]): TradeStats {
  if (trades.length === 0) {
    return { count: 0, wins: 0, losses: 0, winRate: 0, totalPnl: 0, totalFees: 0, avgPnl: 0, bestTrade: 0, worstTrade: 0 };
  }
  let wins = 0, losses = 0, totalPnl = 0, totalFees = 0, best = -Infinity, worst = Infinity;
  for (const t of trades) {
    if (t.pnl_usd > 0) wins++; else if (t.pnl_usd < 0) losses++;
    totalPnl += t.pnl_usd;
    totalFees += t.total_fees_usd;
    if (t.pnl_usd > best) best = t.pnl_usd;
    if (t.pnl_usd < worst) worst = t.pnl_usd;
  }
  return {
    count: trades.length,
    wins,
    losses,
    winRate: trades.length > 0 ? (wins / trades.length) * 100 : 0,
    totalPnl,
    totalFees,
    avgPnl: totalPnl / trades.length,
    bestTrade: best === -Infinity ? 0 : best,
    worstTrade: worst === Infinity ? 0 : worst,
  };
}
