import { History, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { getClosedTrades, computeTradeStats, type ClosedTrade } from "@/lib/api/xlm-bot";
import { DataTable, type Column } from "@/components/DataTable";
import { formatCurrency } from "@/lib/utils";

export const dynamic = "force-dynamic";

function fmtTime(iso: string): string {
  if (!iso) return "--";
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", {
      month: "short", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hour12: false,
      timeZone: "America/Los_Angeles",
    });
  } catch {
    return iso.slice(0, 16);
  }
}

function fmtDuration(min: number): string {
  if (!min || !Number.isFinite(min)) return "--";
  if (min < 1) return `${Math.round(min * 60)}s`;
  if (min < 60) return `${min.toFixed(1)}m`;
  const h = Math.floor(min / 60);
  const m = Math.round(min - h * 60);
  return `${h}h ${m}m`;
}

const REASON_BADGE: Record<string, string> = {
  tp1:           "bg-amber-400/10 text-amber-300 border-amber-400/30",
  tp2:           "bg-amber-400/15 text-amber-200 border-amber-400/40",
  tp3:           "bg-amber-400/20 text-amber-100 border-amber-400/50",
  stop_loss:     "bg-red-400/[0.06] text-red-300/80 border-red-400/20",
  trailing_stop: "bg-amber-400/[0.06] text-amber-400/70 border-amber-400/20",
  manual:        "bg-white/[0.04] text-gray-300 border-white/[0.08]",
  smart_exit:    "bg-amber-400/[0.06] text-amber-300/80 border-amber-400/20",
};

function reasonClass(r: string): string {
  const key = (r || "").toLowerCase();
  for (const [k, cls] of Object.entries(REASON_BADGE)) {
    if (key.includes(k)) return cls;
  }
  return "bg-white/[0.03] text-gray-400 border-white/[0.06]";
}

export default async function TradeHistoryPage() {
  const trades = await getClosedTrades(200);
  const stats = computeTradeStats(trades);

  const columns: Column<ClosedTrade>[] = [
    {
      key: "exit_time",
      header: "Exit",
      cell: (t) => (
        <div className="text-[11px] text-gray-300">
          <div className="font-mono">{fmtTime(t.exit_time)}</div>
          <div className="text-[9px] text-gray-600">{fmtTime(t.entry_time)} entry</div>
        </div>
      ),
    },
    {
      key: "side",
      header: "Side",
      cell: (t) => (
        <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-semibold border ${
          t.side.toLowerCase() === "long" || t.side.toLowerCase() === "buy"
            ? "bg-amber-400/10 text-amber-300 border-amber-400/30"
            : "bg-white/[0.04] text-gray-300 border-white/[0.08]"
        }`}>
          {t.side || "?"}
        </span>
      ),
    },
    {
      key: "pnl_usd",
      header: "PnL",
      align: "right",
      cell: (t) => (
        <div className="flex items-center justify-end gap-1">
          {t.pnl_usd >= 0
            ? <ArrowUpRight size={12} className="text-amber-400" />
            : <ArrowDownRight size={12} className="text-red-400/70" />
          }
          <span className={`font-mono text-sm font-bold ${t.pnl_usd >= 0 ? "text-amber-400" : "text-red-400/80"}`}>
            {t.pnl_usd >= 0 ? "+" : ""}{t.pnl_usd.toFixed(2)}
          </span>
        </div>
      ),
    },
    {
      key: "pnl_pct",
      header: "%",
      align: "right",
      cell: (t) => (
        <span className={`font-mono text-[11px] ${t.pnl_pct >= 0 ? "text-amber-400/70" : "text-red-400/60"}`}>
          {t.pnl_pct >= 0 ? "+" : ""}{t.pnl_pct.toFixed(2)}%
        </span>
      ),
    },
    {
      key: "exit_reason",
      header: "Reason",
      cell: (t) => (
        <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-semibold border ${reasonClass(t.exit_reason)}`}>
          {t.exit_reason || "--"}
        </span>
      ),
    },
    {
      key: "duration",
      header: "Duration",
      align: "right",
      cell: (t) => <span className="font-mono text-[11px] text-gray-400">{fmtDuration(t.time_in_trade_min)}</span>,
    },
    {
      key: "fees",
      header: "Fees",
      align: "right",
      cell: (t) => <span className="font-mono text-[11px] text-gray-500">${t.total_fees_usd.toFixed(3)}</span>,
    },
  ];

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 page-enter">
      <div>
        <h1 className="text-2xl font-bold gradient-gold tracking-wider flex items-center gap-2">
          <History size={20} /> TRADE HISTORY
        </h1>
        <p className="text-xs text-gray-500 mt-1">
          Last {stats.count} closed trades from XLM bot
        </p>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Closed</div>
          <div className="font-mono text-2xl font-bold text-[#E8E8E8]">{stats.count}</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Win Rate</div>
          <div className={`font-mono text-2xl font-bold ${stats.winRate >= 50 ? "text-amber-400" : "text-amber-400/60"}`}>
            {stats.winRate.toFixed(0)}%
          </div>
          <div className="text-[9px] text-gray-600 mt-0.5">{stats.wins}W / {stats.losses}L</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Total PnL</div>
          <div className={`font-mono text-2xl font-bold ${stats.totalPnl >= 0 ? "text-amber-400" : "text-red-400/80"}`}>
            {stats.totalPnl >= 0 ? "+" : ""}{formatCurrency(stats.totalPnl)}
          </div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Avg / Trade</div>
          <div className={`font-mono text-2xl font-bold ${stats.avgPnl >= 0 ? "text-amber-400" : "text-red-400/80"}`}>
            {stats.avgPnl >= 0 ? "+" : ""}${stats.avgPnl.toFixed(2)}
          </div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Best</div>
          <div className="font-mono text-2xl font-bold text-amber-400">+${stats.bestTrade.toFixed(2)}</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Total Fees</div>
          <div className="font-mono text-2xl font-bold text-gray-500">${stats.totalFees.toFixed(2)}</div>
        </div>
      </div>

      <DataTable
        columns={columns}
        rows={trades}
        rowKey={(t, i) => `${t.exit_time}-${i}`}
        empty="No closed trades yet. Bot is either in position or has not opened one."
        caption={
          <>
            <div className="text-sm font-semibold text-amber-400/80 uppercase tracking-wider">Closed Trades</div>
            <div className="text-[9px] text-gray-500 font-mono">most recent first</div>
          </>
        }
      />
    </div>
  );
}
