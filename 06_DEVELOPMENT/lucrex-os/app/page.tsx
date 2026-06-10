import Link from "next/link";
import { getBotSnapshot, isLive, totalEquity } from "@/lib/api/xlm-bot";
import { getStateGates, getBuyers, computeBuyerStats } from "@/lib/api/wholesale";
import { getPriorities, tierForNetWorth } from "@/lib/wealth";
import { NewsFeed } from "@/components/intel/NewsFeed";
import { formatUSD, formatPrice, daysUntil } from "@/lib/utils";
import {
  TrendingUp, Wallet, Shield, Users, Crown, Brain, Zap,
  AlertTriangle, ArrowRight, Activity, DollarSign, FileSignature, Newspaper
} from "lucide-react";

export const dynamic = "force-dynamic";

const TCJA_SUNSET = "2026-12-31T00:00:00Z";

export default async function CEOHome() {
  const [snap, gates, buyers, prio] = await Promise.all([
    getBotSnapshot(),
    getStateGates(),
    getBuyers(),
    getPriorities(),
  ]);

  const buyerStats = computeBuyerStats(buyers);
  const tierInfo = tierForNetWorth(0);
  const sunsetDays = daysUntil(TCJA_SUNSET);
  const live = snap ? isLive(snap) : false;
  const equity = snap ? totalEquity(snap) : 0;
  const dailyPnL = snap?.pnl_today_usd ?? 0;
  const activeStates = Object.values(gates.states).filter((s) => s.active_in_pipeline).length;
  const blockedStates = Object.values(gates.states).filter((s) => !s.sms_allowed || !s.cold_call_allowed).length;
  const respondedBuyers = buyerStats.responded;

  return (
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto space-y-6 page-enter">
      {/* Hero */}
      <div className="flex items-end justify-between flex-wrap gap-4 mb-2">
        <div>
          <div className="text-[10px] uppercase tracking-[0.3em] text-amber-400 mb-1">
            {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })} · Lucrex OS
          </div>
          <h1 className="font-display text-3xl md:text-5xl font-semibold leading-tight">
            <span className="gradient-gold">The mind</span> behind <span className="gradient-gold">the money.</span>
          </h1>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="px-2 py-1 rounded border border-amber-400/30 text-amber-400 font-mono">{tierInfo.current.tier} · {tierInfo.current.label}</span>
          <span className={`px-2 py-1 rounded border ${sunsetDays < 90 ? "border-red-400/30 text-red-400" : "border-amber-400/30 text-amber-400"} font-mono`}>
            TCJA {sunsetDays}d
          </span>
        </div>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2.5">
        <Link href="/trading" className="metric-card block">
          <div className="text-[8px] uppercase tracking-widest text-gray-500 mb-1">Bot</div>
          <div className={`font-mono text-lg font-bold ${live ? "text-green-400" : "text-red-400"}`}>{live ? "LIVE" : "DOWN"}</div>
          <div className="text-[9px] text-gray-600 mt-0.5 truncate">{snap?.state ?? "?"}</div>
        </Link>
        <Link href="/trading" className="metric-card block">
          <div className="text-[8px] uppercase tracking-widest text-gray-500 mb-1">Day P&amp;L</div>
          <div className={`font-mono text-lg font-bold ${dailyPnL >= 0 ? "text-green-400" : "text-red-400"}`}>{formatUSD(dailyPnL)}</div>
          <div className="text-[9px] text-gray-600 mt-0.5">{snap?.trades_today ?? 0}t · {snap?.losses_today ?? 0}L</div>
        </Link>
        <Link href="/trading" className="metric-card block">
          <div className="text-[8px] uppercase tracking-widest text-gray-500 mb-1">XLM</div>
          <div className="font-mono text-lg font-bold gradient-gold">${formatPrice(snap?.price)}</div>
          <div className="text-[9px] text-gray-600 mt-0.5 truncate">{snap?.product?.split("-")[0] ?? "XLP"}</div>
        </Link>
        <Link href="/trading" className="metric-card block">
          <div className="text-[8px] uppercase tracking-widest text-gray-500 mb-1">Equity</div>
          <div className="font-mono text-lg font-bold text-white">{formatUSD(equity)}</div>
          <div className="text-[9px] text-gray-600 mt-0.5">spot+perp</div>
        </Link>
        <Link href="/revenue" className="metric-card block">
          <div className="text-[8px] uppercase tracking-widest text-gray-500 mb-1">MRR</div>
          <div className="font-mono text-lg font-bold text-amber-400">$0</div>
          <div className="text-[9px] text-gray-600 mt-0.5">→ $10k goal</div>
        </Link>
        <Link href="/buyers" className="metric-card block">
          <div className="text-[8px] uppercase tracking-widest text-gray-500 mb-1">Buyers</div>
          <div className="font-mono text-lg font-bold text-blue-400">{buyerStats.total}</div>
          <div className="text-[9px] text-gray-600 mt-0.5">{respondedBuyers} responded</div>
        </Link>
        <Link href="/compliance" className="metric-card block">
          <div className="text-[8px] uppercase tracking-widest text-gray-500 mb-1">Active States</div>
          <div className="font-mono text-lg font-bold text-purple-400">{activeStates}</div>
          <div className="text-[9px] text-gray-600 mt-0.5">{blockedStates} gated</div>
        </Link>
        <Link href="/wealth" className="metric-card block">
          <div className="text-[8px] uppercase tracking-widest text-gray-500 mb-1">Net Worth</div>
          <div className="font-mono text-lg font-bold text-emerald-400">$0</div>
          <div className="text-[9px] text-gray-600 mt-0.5">next: {tierInfo.next?.tier ?? "max"}</div>
        </Link>
      </div>

      {/* Center grid: bot + AI thought + revenue + pipeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* AI advisor + bot */}
        <div className="lg:col-span-2 card relative overflow-hidden">
          <div className="absolute -top-16 -right-16 w-48 h-48 rounded-full bg-amber-400/5 blur-3xl pointer-events-none" />
          <div className="relative">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <div className="h-9 w-9 rounded-lg bg-amber-400/10 border border-amber-400/30 flex items-center justify-center">
                  <Brain size={18} className="text-amber-400" />
                </div>
                <div>
                  <h2 className="font-display text-lg font-semibold leading-tight">Lucrex Advisor</h2>
                  <div className="text-[10px] uppercase tracking-widest text-gray-500">live executive AI mode</div>
                </div>
              </div>
              {snap?.unified_recommendation && (
                <span className={`px-3 py-1.5 rounded-md text-xs font-bold uppercase border ${
                  snap.unified_recommendation === "ENTER" ? "bg-green-400/10 text-green-400 border-green-400/30" :
                  snap.unified_recommendation === "WAIT"  ? "bg-amber-400/10 text-amber-400 border-amber-400/30" :
                  "bg-blue-400/10 text-blue-400 border-blue-400/30"
                }`}>
                  {snap.unified_recommendation}{snap.unified_direction && ` ${snap.unified_direction}`}
                </span>
              )}
            </div>

            <div className="border-l-2 border-amber-400/50 pl-3 mb-4">
              <div className="text-[9px] uppercase tracking-widest text-amber-400 mb-1 flex items-center gap-1.5">
                <Zap size={9} /> Bot thought
              </div>
              <p className="text-sm text-gray-200 leading-relaxed">{snap?.thought ?? "(no snapshot)"}</p>
            </div>

            {snap?.unified_narrative && (
              <div className="text-xs text-gray-500 leading-relaxed mb-3 line-clamp-3">{snap.unified_narrative}</div>
            )}

            <div className="grid grid-cols-4 gap-2 mt-3 pt-3 border-t border-white/[0.04]">
              <div>
                <div className="text-[8px] uppercase text-gray-500">Margin</div>
                <div className={`font-mono text-sm font-bold ${snap?.margin_tier === "SAFE" ? "text-green-400" : "text-amber-400"}`}>{snap?.margin_tier ?? "?"}</div>
              </div>
              <div>
                <div className="text-[8px] uppercase text-gray-500">Window</div>
                <div className="font-mono text-sm font-bold text-gray-300">{snap?.margin_window ?? "?"}</div>
              </div>
              <div>
                <div className="text-[8px] uppercase text-gray-500">P(win)</div>
                <div className="font-mono text-sm font-bold text-amber-400">{snap?.unified_p_win != null ? `${(snap.unified_p_win * 100).toFixed(0)}%` : "--"}</div>
              </div>
              <div>
                <div className="text-[8px] uppercase text-gray-500">R:R</div>
                <div className="font-mono text-sm font-bold text-amber-400">{snap?.unified_rr_ratio?.toFixed(1) ?? "--"}</div>
              </div>
            </div>

            <Link href="/trading" className="mt-4 inline-flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition">
              Open trading desk <ArrowRight size={12} />
            </Link>
          </div>
        </div>

        {/* Wealth + sunset */}
        <Link href="/wealth" className="card group block">
          <div className="flex items-center gap-2 mb-3">
            <Crown size={16} className="text-amber-400" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">Wealth OS</h2>
          </div>
          <div className="font-mono text-4xl font-black gradient-gold mb-1">{tierInfo.current.tier}</div>
          <div className="text-xs text-gray-400">{tierInfo.current.label}</div>
          <div className="mt-4 pt-3 border-t border-white/[0.04] space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-500">Net worth</span>
              <span className="font-mono">$0</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Next trigger</span>
              <span className="font-mono text-amber-400">{tierInfo.next?.tier ?? "max"} · ${(tierInfo.next?.minNetWorth ?? 0) / 1000}k</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">TCJA sunset</span>
              <span className={`font-mono ${sunsetDays < 90 ? "text-red-400" : "text-amber-400"}`}>{sunsetDays}d</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Priorities</span>
              <span className={`font-mono ${prio.allFilled ? "text-green-400" : "text-amber-400"}`}>{prio.allFilled ? "calibrated" : "needs input"}</span>
            </div>
          </div>
          <div className="mt-3 text-[10px] text-amber-400/70 group-hover:text-amber-400 transition flex items-center gap-1">open layers · tiers · credits <ArrowRight size={9} /></div>
        </Link>
      </div>

      {/* Pipeline overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link href="/buyers" className="card group block">
          <div className="flex items-center gap-2 mb-3">
            <Users size={14} className="text-blue-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Cash Buyers</h3>
          </div>
          <div className="font-mono text-2xl font-bold text-blue-400">{buyerStats.total}</div>
          <div className="text-[10px] text-gray-500 mt-1">{Object.keys(buyerStats.byState).length} states · {buyerStats.totalOutreach} touches</div>
          <div className="mt-3 grid grid-cols-3 gap-1.5">
            {Object.entries(buyerStats.byState).sort(([,a],[,b])=>b-a).slice(0,3).map(([s,n]) => (
              <div key={s} className="text-[10px] bg-blue-400/5 rounded px-2 py-1 text-center">
                <div className="font-mono text-blue-400 font-bold">{n}</div>
                <div className="text-gray-500">{s}</div>
              </div>
            ))}
          </div>
        </Link>

        <Link href="/compliance" className="card group block">
          <div className="flex items-center gap-2 mb-3">
            <Shield size={14} className="text-purple-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Compliance</h3>
          </div>
          <div className="font-mono text-2xl font-bold text-purple-400">{Object.keys(gates.states).length}</div>
          <div className="text-[10px] text-gray-500 mt-1">states tracked · {activeStates} active</div>
          <div className="mt-3 flex flex-wrap gap-1">
            {Object.entries(gates.states).slice(0,8).map(([code, s]) => (
              <span key={code} className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                s.risk_rating === "low" ? "bg-green-400/10 text-green-400" :
                s.risk_rating === "high" ? "bg-red-400/10 text-red-400" :
                "bg-amber-400/10 text-amber-400"
              }`}>{code}</span>
            ))}
          </div>
        </Link>

        <Link href="/contracts" className="card group block">
          <div className="flex items-center gap-2 mb-3">
            <FileSignature size={14} className="text-cyan-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Contracts</h3>
          </div>
          <div className="font-mono text-2xl font-bold text-cyan-400">templates</div>
          <div className="text-[10px] text-gray-500 mt-1">state matrix · assignment · addenda</div>
          <div className="mt-3 text-[10px] text-cyan-400/70 group-hover:text-cyan-400 transition flex items-center gap-1">
            open library <ArrowRight size={9} />
          </div>
        </Link>

        <Link href="/revenue" className="card group block">
          <div className="flex items-center gap-2 mb-3">
            <DollarSign size={14} className="text-green-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Revenue</h3>
          </div>
          <div className="font-mono text-2xl font-bold text-green-400">$0</div>
          <div className="text-[10px] text-gray-500 mt-1">MRR · 6 streams</div>
          <div className="mt-3 text-[10px]">
            <span className="text-gray-600">Goal:</span>{" "}
            <span className="text-amber-400 font-mono">$10k/mo</span>
          </div>
        </Link>
      </div>

      {/* News + activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <NewsFeed limit={10} query="market" />
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Activity size={14} className="text-amber-400" />
            <h3 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">Quick Drill</h3>
          </div>
          <div className="space-y-1.5 text-sm">
            {[
              { href: "/trading", label: "Trading desk", color: "text-green-400" },
              { href: "/intel", label: "Market intel", color: "text-amber-400" },
              { href: "/wealth/priorities", label: "Set wealth priorities", color: prio.allFilled ? "text-gray-400" : "text-amber-400" },
              { href: "/wealth/credits", label: "Credits engine", color: "text-emerald-400" },
              { href: "/buyers", label: "Buyer database", color: "text-blue-400" },
              { href: "/compliance", label: "State compliance", color: "text-purple-400" },
              { href: "/contracts", label: "Contracts library", color: "text-cyan-400" },
              { href: "/legal", label: "Legal library", color: "text-pink-400" },
            ].map((l) => (
              <Link key={l.href} href={l.href} className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-white/[0.03] transition group">
                <span className={l.color}>{l.label}</span>
                <ArrowRight size={11} className="text-gray-600 group-hover:text-amber-400 transition" />
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom: priorities reminder if not filled */}
      {!prio.allFilled && (
        <Link href="/wealth/priorities" className="card border-amber-400/30 bg-amber-400/5 block hover:bg-amber-400/10 transition">
          <div className="flex items-start gap-3">
            <AlertTriangle size={16} className="text-amber-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <div className="text-sm font-medium text-amber-400">Wealth OS not yet calibrated</div>
              <div className="text-xs text-gray-400 mt-1">
                Fill the 10 weight sliders to unlock per-tier strategy recommendations and the Hive dispatch.
              </div>
            </div>
            <ArrowRight size={14} className="text-amber-400 mt-1" />
          </div>
        </Link>
      )}
    </div>
  );
}
