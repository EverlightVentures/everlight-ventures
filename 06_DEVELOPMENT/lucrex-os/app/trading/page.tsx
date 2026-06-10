import { getBotSnapshot, getRecentDecisions, getEquitySeries, totalEquity, isLive } from "@/lib/api/xlm-bot";
import { KPICard } from "@/components/KPICard";
import { StatusBadge } from "@/components/StatusBadge";
import { ActivityFeed, type ActivityItem } from "@/components/ActivityFeed";
import { EquitySpark } from "@/components/trading/EquitySpark";
import { PriceChart } from "@/components/trading/PriceChart";
import { AIAdvisor } from "@/components/trading/AIAdvisor";
import { formatCurrency } from "@/lib/utils";
import { ExternalLink, Zap, AlertTriangle, Brain } from "lucide-react";

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const ACTION_ACCENT: Record<string, string> = {
  ENTER: "#22C55E",
  EXIT:  "#06B6D4",
  HOLD:  "#888888",
  FLAT:  "#888888",
  WAIT:  "#888888",
  STOP:  "#EF4444",
};

export default async function TradingPage() {
  const [snap, decisions, equity] = await Promise.all([
    getBotSnapshot(),
    getRecentDecisions(10),
    getEquitySeries(120),
  ]);

  if (!snap) {
    return (
      <div className="rounded-xl border border-[var(--color-alert)]/40 bg-[var(--color-alert)]/5 p-6">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle size={18} className="text-[var(--color-alert)]" />
          <h2 className="font-display text-xl font-semibold">Bot snapshot unreadable</h2>
        </div>
        <p className="text-sm text-[var(--color-muted)]">
          Cannot read /home/opc/xlm-bot/logs/dashboard_snapshot.json. Either bot is down,
          XLM_BOT_LOGS env path is wrong, or the snapshot writer crashed.
        </p>
      </div>
    );
  }

  const live = isLive(snap);
  const equityNow = totalEquity(snap);
  const inTrade = snap.state === "IN_TRADE" && snap.entry_price;
  const dailyPnL = snap.pnl_today_usd ?? 0;

  const decisionItems: ActivityItem[] = decisions.map((d, i) => ({
    id: `${d.ts}-${i}`,
    ts: d.ts,
    agent: d.action || "Bot",
    action: d.state || d.action || "",
    detail: (d.reason || d.thought || "").slice(0, 140),
    accent: ACTION_ACCENT[d.action ?? ""] ?? "#06B6D4",
  }));

  return (
    <div className="space-y-6">
      {/* Top KPIs - LIVE */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPICard
          label="Bot Status"
          value={live ? "LIVE" : "STALE"}
          hint={`${snap.state} (${snap.age_seconds ?? "?"}s ago)`}
          status={live ? (snap.safe_mode ? "alert" : "active") : "alert"}
          accent={live ? (snap.safe_mode ? "#EF4444" : "#22C55E") : "#EF4444"}
        />
        <KPICard
          label="P&amp;L Today"
          value={formatCurrency(dailyPnL)}
          hint={`${snap.trades_today ?? 0}/${snap.max_trades_per_day ?? 5} trades · ${snap.losses_today ?? 0}L`}
          status={dailyPnL >= 0 ? "active" : "alert"}
          accent={dailyPnL >= 0 ? "#22C55E" : "#EF4444"}
          delta={dailyPnL !== 0 && snap.equity_start_usd ? (dailyPnL / snap.equity_start_usd) * 100 : undefined}
        />
        <KPICard
          label="Equity"
          value={formatCurrency(equityNow, { compact: false })}
          hint={`spot $${(snap.spot_usdc ?? 0).toFixed(2)} · perp $${(snap.derivatives_usdc ?? 0).toFixed(2)}`}
          status="neutral"
          accent="#D4A843"
        />
        <KPICard
          label="XLM Price"
          value={`$${(snap.price ?? 0).toFixed(5)}`}
          hint={snap.product ?? "XLP-20DEC30-CDE"}
          status="active"
          accent="#06B6D4"
        />
      </div>

      {/* Native price chart with EMAs (lightweight-charts) */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h2 className="font-display text-xl font-semibold">{snap.product ?? "XLP"} · 15m</h2>
            <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)]">candles · ema8 · ema21 · volume</div>
          </div>
          <div className="font-mono text-2xl font-bold" style={{ color: "var(--accent)" }}>
            ${(snap.price ?? 0).toFixed(5)}
          </div>
        </div>
        <PriceChart basePath={BASE_PATH} height={400} />
      </div>

      {/* Lucrex AI Advisor */}
      <AIAdvisor snap={snap} />

      {/* Position card or signal-ready card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Zap size={16} style={{ color: "var(--accent)" }} />
              <h2 className="font-display text-xl font-semibold">
                {inTrade ? "Open Position" : "Signal Watch"}
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge variant={snap.margin_tier === "SAFE" ? "active" : snap.margin_tier === "CAUTION" ? "warn" : "alert"}>
                margin {snap.margin_tier}
              </StatusBadge>
              <StatusBadge variant={snap.safe_mode ? "alert" : "info"}>
                {snap.safe_mode ? "SAFE MODE" : snap.margin_window || "live"}
              </StatusBadge>
            </div>
          </div>

          {inTrade ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)]">Direction</div>
                <div className="font-mono text-lg font-semibold">{snap.unified_direction ?? "?"}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)]">Entry</div>
                <div className="font-mono text-lg font-semibold">${(snap.entry_price ?? 0).toFixed(5)}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)]">P&amp;L (live)</div>
                <div className={`font-mono text-lg font-semibold ${(snap.pnl_usd_live ?? 0) >= 0 ? "text-[var(--color-success)]" : "text-[var(--color-alert)]"}`}>
                  {formatCurrency(snap.pnl_usd_live ?? 0)}
                  {snap.pnl_pct != null && <span className="text-xs ml-2">({snap.pnl_pct.toFixed(2)}%)</span>}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)]">Size · Lev</div>
                <div className="font-mono text-lg font-semibold">{snap.size ?? 0}c · {snap.leverage ?? 1}x</div>
              </div>
              <div className="col-span-full text-xs text-[var(--color-muted)] pt-2 border-t border-[var(--color-border)]">
                In trade for <span className="text-[var(--color-fg)] font-semibold">{snap.time_in_trade_min ?? 0} min</span>
              </div>
            </div>
          ) : (
            <div>
              <div className="text-sm font-medium mb-2 text-[var(--color-gold-400)] flex items-center gap-2">
                <Brain size={14} /> Bot thought
              </div>
              <p className="text-sm text-[var(--color-fg)] leading-relaxed bg-[var(--color-bg)]/40 rounded-md p-3 border border-[var(--color-border)]">
                {snap.thought || "(no thought)"}
              </p>
              {snap.unified_recommendation && (
                <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                  <div>
                    <span className="text-[var(--color-muted)]">Recommendation:</span>{" "}
                    <span className="font-mono font-semibold">{snap.unified_recommendation}</span>
                  </div>
                  {snap.unified_direction && (
                    <div>
                      <span className="text-[var(--color-muted)]">Direction:</span>{" "}
                      <span className="font-mono font-semibold">{snap.unified_direction}</span>
                    </div>
                  )}
                  {snap.unified_p_win != null && (
                    <div>
                      <span className="text-[var(--color-muted)]">P(win):</span>{" "}
                      <span className="font-mono font-semibold">{(snap.unified_p_win * 100).toFixed(0)}%</span>
                    </div>
                  )}
                  {snap.unified_rr_ratio != null && (
                    <div>
                      <span className="text-[var(--color-muted)]">R:R:</span>{" "}
                      <span className="font-mono font-semibold">{snap.unified_rr_ratio.toFixed(1)}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <div className="flex items-center justify-between mb-1">
              <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)]">Equity Curve</div>
              <div className="text-xs text-[var(--color-muted)]">{equity.length}pt</div>
            </div>
            <EquitySpark points={equity} />
          </div>

          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <div className="text-[10px] uppercase tracking-widest text-[var(--color-muted)] mb-2">
              Reconcile
            </div>
            <div className="font-mono text-sm">{snap.reconcile_status}</div>
            <div className="text-xs text-[var(--color-muted)] mt-1">
              transfers today: ${snap.transfers_today_usd?.toFixed(2) ?? "0.00"}
            </div>
          </div>
        </div>
      </div>

      {/* Decision feed */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display text-xl font-semibold">Decision feed</h2>
          <a
            href="http://163.192.19.196:8502/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-[var(--color-muted)] hover:text-[var(--color-gold-400)] transition"
          >
            Deep view <ExternalLink size={11} />
          </a>
        </div>
        <ActivityFeed items={decisionItems} />
        {decisionItems.length === 0 && (
          <div className="text-sm text-[var(--color-muted)] italic">No decisions read.</div>
        )}
      </div>

      {/* Margin window context */}
      <div className="rounded-xl border border-[var(--color-warn)]/30 bg-[var(--color-warn)]/5 p-4 text-xs">
        <div className="font-medium text-[var(--color-warn)] mb-1">Margin window</div>
        <p className="text-[var(--color-muted)]">
          Intraday (5AM-1PM PT) low margin · Overnight (1PM-5AM PT) high margin.
          Bot adjusts position sizing accordingly. Safe mode auto-engages on tier breach.
        </p>
      </div>
    </div>
  );
}
