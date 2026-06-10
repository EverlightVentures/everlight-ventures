"use client";
import { useApi, formatUSD, formatPrice } from "@/lib/api/client";
import { NewsFeed } from "@/components/intel/NewsFeed";
import { Activity, Zap } from "lucide-react";

const PHASE_COLORS: Record<string, { bg: string; text: string; icon: string }> = {
  ACCUMULATION: { bg: "from-green-500/20 to-green-900/10",   text: "text-green-400",   icon: "+" },
  DEEP_VALUE:   { bg: "from-emerald-500/20 to-emerald-900/10", text: "text-emerald-300", icon: "$$" },
  MARKUP:       { bg: "from-blue-500/20 to-blue-900/10",      text: "text-blue-400",    icon: "^" },
  LATE_MARKUP:  { bg: "from-cyan-500/20 to-cyan-900/10",      text: "text-cyan-400",    icon: "^" },
  DISTRIBUTION: { bg: "from-amber-500/20 to-amber-900/10",    text: "text-amber-400",   icon: "!" },
  EUPHORIA:     { bg: "from-red-500/20 to-red-900/10",        text: "text-red-400",     icon: "!!" },
  MARKDOWN:     { bg: "from-red-600/20 to-red-900/10",        text: "text-red-500",     icon: "v" },
};

type MacroVision = {
  phase?: string;
  combined_bias?: string;
  position_mult?: number;
  aligned?: boolean;
  risk?: string;
  capture_tips?: string[];
  macro?: {
    phase?: string;
    bias?: string;
    risk_level?: string;
    months_since_halving?: number;
    targets?: { conservative: string; moderate: string; aggressive: string };
  };
};

type Hindsight = {
  hindsight?: { missed_count?: number; missed_usd?: number; pattern?: string; lesson?: string };
};

type Opportunities = {
  next_play_long?: { level_name: string; trigger_price: number; distance_atr: number; readiness_pct: number };
  next_play_short?: { level_name: string; trigger_price: number; distance_atr: number; readiness_pct: number };
  score_long?: number;
  score_short?: number;
  threshold?: number;
  entry_type_long?: string;
  entry_type_short?: string;
  long_block?: string;
  short_block?: string;
  htf_trend?: string;
  vol_phase?: string;
  market_health?: number;
  market_regime?: string;
};

type Cycles = { cycles?: Array<{ cycle: number; low: number; high: number; retrace?: number; retrace_pct?: number }>; current_price?: number };

type Moonshot = { active?: boolean; activation_reason?: string; peak_price?: number; trailing_stop?: number; bars_active?: number };

type Analytics = {
  total_trades?: number; wins?: number; losses?: number; win_rate?: number;
  avg_win?: number; avg_loss?: number; total_pnl?: number;
  best_trade?: { pnl: number; strategy: string; direction: string };
  worst_trade?: { pnl: number; strategy: string; direction: string };
  current_streak?: number; streak_type?: string;
  by_strategy?: Record<string, { pnl: number; wins: number; losses: number }>;
  long_pnl?: number; short_pnl?: number; long_count?: number; short_count?: number;
  daily_pnl?: Array<{ date: string; pnl: number; trades: number }>;
  error?: string;
};

function PhaseCard({ vision }: { vision: MacroVision | null }) {
  const phase = vision?.macro?.phase || vision?.phase || "--";
  const pc = PHASE_COLORS[phase] || PHASE_COLORS.MARKUP;
  const bias = vision?.combined_bias || vision?.macro?.bias;
  const risk = vision?.macro?.risk_level || vision?.risk;
  const mult = vision?.position_mult ?? 1;
  const aligned = vision?.aligned;
  const targets = vision?.macro?.targets;
  const months = vision?.macro?.months_since_halving;

  return (
    <div className={`card bg-gradient-to-br ${pc.bg} relative overflow-hidden`}>
      <div className="absolute top-0 right-0 w-32 h-32 bg-white/[0.02] rounded-full blur-3xl" />
      <div className="relative">
        <div className="flex justify-between items-start mb-3">
          <div>
            <div className="text-[9px] uppercase tracking-[0.3em] text-gray-500">Cycle Phase</div>
            <div className={`text-2xl font-black ${pc.text} tracking-wide`}>{phase}</div>
          </div>
          <div className={`text-4xl font-black ${pc.text} opacity-20`}>{pc.icon}</div>
        </div>
        <div className="grid grid-cols-4 gap-3 mt-4">
          <div className="text-center">
            <div className="text-[8px] text-gray-500 uppercase tracking-wider">Bias</div>
            <div className={`font-mono text-sm font-bold ${bias?.includes("LONG") ? "text-green-400" : bias?.includes("SHORT") ? "text-red-400" : "text-gray-400"}`}>{bias ?? "--"}</div>
          </div>
          <div className="text-center">
            <div className="text-[8px] text-gray-500 uppercase tracking-wider">Risk</div>
            <div className={`font-mono text-sm font-bold ${risk === "LOW" ? "text-green-400" : risk === "MEDIUM" ? "text-amber-400" : risk === "HIGH" ? "text-orange-400" : "text-red-400"}`}>{risk ?? "--"}</div>
          </div>
          <div className="text-center">
            <div className="text-[8px] text-gray-500 uppercase tracking-wider">Size Mult</div>
            <div className="font-mono text-sm font-bold text-white">{mult.toFixed(2)}x</div>
          </div>
          <div className="text-center">
            <div className="text-[8px] text-gray-500 uppercase tracking-wider">Aligned</div>
            <div className={`font-mono text-sm font-bold ${aligned ? "text-green-400" : "text-red-400"}`}>{aligned ? "YES" : "NO"}</div>
          </div>
        </div>
        {targets && (
          <div className="mt-4 pt-3 border-t border-white/5">
            <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-2">Cycle Targets</div>
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-white/[0.03] rounded-lg px-3 py-2 text-center">
                <div className="text-[8px] text-gray-600">Conservative</div>
                <div className="font-mono text-sm font-bold text-green-400">${targets.conservative}</div>
              </div>
              <div className="bg-white/[0.03] rounded-lg px-3 py-2 text-center">
                <div className="text-[8px] text-gray-600">Moderate</div>
                <div className="font-mono text-sm font-bold text-amber-400">${targets.moderate}</div>
              </div>
              <div className="bg-white/[0.03] rounded-lg px-3 py-2 text-center">
                <div className="text-[8px] text-gray-600">Aggressive</div>
                <div className="font-mono text-sm font-bold text-red-400">${targets.aggressive}</div>
              </div>
            </div>
          </div>
        )}
        {months != null && (
          <div className="mt-3 text-[10px] text-gray-500">{months.toFixed(1)} months post-halving</div>
        )}
      </div>
    </div>
  );
}

function OpportunityScanner({ data }: { data: Opportunities | null }) {
  const d = data ?? {};
  const threshold = d.threshold ?? 60;

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-xs font-bold">S</div>
        <div>
          <div className="text-sm font-medium">Opportunity Scanner</div>
          <div className="text-[10px] text-gray-500">Real-time setup detection</div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2 mb-3">
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">HTF</div>
          <div className={`text-xs font-bold ${d.htf_trend === "bullish" ? "text-green-400" : "text-red-400"}`}>{d.htf_trend ?? "--"}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Vol</div>
          <div className="text-xs font-bold text-gray-300">{d.vol_phase ?? "--"}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Health</div>
          <div className={`text-xs font-bold ${(d.market_health ?? 0) > 50 ? "text-green-400" : (d.market_health ?? 0) > 30 ? "text-amber-400" : "text-red-400"}`}>{d.market_health ?? "--"}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Regime</div>
          <div className="text-xs font-bold text-gray-300">{d.market_regime ?? "--"}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className={`rounded-xl p-3 border ${(d.score_long ?? 0) >= threshold ? "border-green-400/30 bg-green-400/5" : "border-gray-700/30 bg-white/[0.02]"}`}>
          <div className="flex justify-between items-center mb-1">
            <span className="text-[9px] text-green-400/70 uppercase tracking-wider">Long</span>
            <span className="text-[9px] text-gray-500">{d.entry_type_long ?? "--"}</span>
          </div>
          <div className="flex items-end gap-1">
            <span className={`font-mono text-2xl font-black ${(d.score_long ?? 0) >= threshold ? "text-green-400" : "text-gray-400"}`}>{d.score_long ?? 0}</span>
            <span className="text-gray-600 text-sm mb-0.5">/ {threshold}</span>
          </div>
          <div className="w-full h-1.5 bg-gray-800 rounded-full mt-2 overflow-hidden">
            <div className={`h-full rounded-full transition-all ${(d.score_long ?? 0) >= threshold ? "bg-green-400" : "bg-gray-600"}`} style={{ width: `${Math.min(100, ((d.score_long ?? 0) / threshold) * 100)}%` }} />
          </div>
          {d.long_block && <div className="text-[9px] text-red-400/60 mt-1">{d.long_block}</div>}
        </div>
        <div className={`rounded-xl p-3 border ${(d.score_short ?? 0) >= threshold ? "border-red-400/30 bg-red-400/5" : "border-gray-700/30 bg-white/[0.02]"}`}>
          <div className="flex justify-between items-center mb-1">
            <span className="text-[9px] text-red-400/70 uppercase tracking-wider">Short</span>
            <span className="text-[9px] text-gray-500">{d.entry_type_short ?? "--"}</span>
          </div>
          <div className="flex items-end gap-1">
            <span className={`font-mono text-2xl font-black ${(d.score_short ?? 0) >= threshold ? "text-red-400" : "text-gray-400"}`}>{d.score_short ?? 0}</span>
            <span className="text-gray-600 text-sm mb-0.5">/ {threshold}</span>
          </div>
          <div className="w-full h-1.5 bg-gray-800 rounded-full mt-2 overflow-hidden">
            <div className={`h-full rounded-full transition-all ${(d.score_short ?? 0) >= threshold ? "bg-red-400" : "bg-gray-600"}`} style={{ width: `${Math.min(100, ((d.score_short ?? 0) / threshold) * 100)}%` }} />
          </div>
          {d.short_block && <div className="text-[9px] text-red-400/60 mt-1">{d.short_block}</div>}
        </div>
      </div>

      <div className="space-y-2">
        {d.next_play_long && (
          <div className="flex items-center gap-2 bg-green-400/5 border border-green-400/10 rounded-lg px-3 py-2">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
            <span className="text-[10px] text-green-400 font-medium">LONG</span>
            <span className="text-[10px] text-gray-400 flex-1">{d.next_play_long.level_name} @ ${d.next_play_long.trigger_price}</span>
            <span className="text-[10px] text-gray-500">{d.next_play_long.distance_atr} ATR</span>
            <span className={`text-[10px] font-bold ${d.next_play_long.readiness_pct >= 80 ? "text-green-400" : "text-amber-400"}`}>{d.next_play_long.readiness_pct}%</span>
          </div>
        )}
        {d.next_play_short && (
          <div className="flex items-center gap-2 bg-red-400/5 border border-red-400/10 rounded-lg px-3 py-2">
            <div className="w-1.5 h-1.5 rounded-full bg-red-400" />
            <span className="text-[10px] text-red-400 font-medium">SHORT</span>
            <span className="text-[10px] text-gray-400 flex-1">{d.next_play_short.level_name} @ ${d.next_play_short.trigger_price}</span>
            <span className="text-[10px] text-gray-500">{d.next_play_short.distance_atr} ATR</span>
            <span className={`text-[10px] font-bold ${d.next_play_short.readiness_pct >= 80 ? "text-red-400" : "text-amber-400"}`}>{d.next_play_short.readiness_pct}%</span>
          </div>
        )}
      </div>
    </div>
  );
}

function HindsightCard({ data }: { data: Hindsight | null }) {
  const h = data?.hindsight ?? {};
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-xs font-bold">H</div>
        <div>
          <div className="text-sm font-medium">Hindsight Analyzer</div>
          <div className="text-[10px] text-gray-500">Self-review of missed opportunities (6h lookback)</div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3 mb-3">
        <div className="bg-white/[0.03] rounded-lg p-3 text-center">
          <div className="text-[8px] text-gray-500 uppercase">Missed</div>
          <div className={`font-mono text-xl font-bold ${(h.missed_count ?? 0) > 0 ? "text-amber-400" : "text-green-400"}`}>{h.missed_count ?? 0}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-3 text-center">
          <div className="text-[8px] text-gray-500 uppercase">$ Left</div>
          <div className="font-mono text-xl font-bold text-amber-400">${h.missed_usd ?? 0}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-3 text-center">
          <div className="text-[8px] text-gray-500 uppercase">Pattern</div>
          <div className="font-mono text-sm font-bold text-gray-300">{h.pattern ?? "none"}</div>
        </div>
      </div>
      {h.lesson && h.lesson !== "none" && (
        <div className="bg-amber-400/5 border border-amber-400/10 rounded-lg px-3 py-2">
          <div className="text-[9px] text-amber-400/70 uppercase tracking-wider">Lesson</div>
          <div className="text-xs text-gray-300 mt-0.5">{h.lesson}</div>
        </div>
      )}
    </div>
  );
}

function MoonshotStatus({ data }: { data: Moonshot | null }) {
  if (!data) return null;
  return (
    <div className={`card ${data.active ? "border-amber-400/30 bg-amber-400/5" : ""}`}>
      <div className="flex items-center gap-2 mb-2">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-lg ${data.active ? "bg-gradient-to-br from-amber-400 to-orange-600 text-black" : "bg-gray-800 text-gray-500"}`}>
          {data.active ? "R" : "-"}
        </div>
        <div>
          <div className="text-sm font-medium">{data.active ? "MOONSHOT ACTIVE" : "Moonshot Mode"}</div>
          <div className="text-[10px] text-gray-500">{data.active ? data.activation_reason : "Waiting for velocity + profit trigger"}</div>
        </div>
      </div>
      {data.active && (
        <div className="grid grid-cols-3 gap-2 mt-2">
          <div className="bg-white/[0.03] rounded-lg p-2 text-center">
            <div className="text-[8px] text-gray-500">Peak</div>
            <div className="font-mono text-sm font-bold text-amber-400">{formatPrice(data.peak_price)}</div>
          </div>
          <div className="bg-white/[0.03] rounded-lg p-2 text-center">
            <div className="text-[8px] text-gray-500">Trail Stop</div>
            <div className="font-mono text-sm font-bold text-red-400">{formatPrice(data.trailing_stop)}</div>
          </div>
          <div className="bg-white/[0.03] rounded-lg p-2 text-center">
            <div className="text-[8px] text-gray-500">Bars</div>
            <div className="font-mono text-sm font-bold">{data.bars_active}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function CycleTimeline({ data }: { data: Cycles | null }) {
  return (
    <div className="card">
      <div className="text-sm font-medium mb-3">XLM Cycle History</div>
      <div className="space-y-3">
        {(data?.cycles ?? []).map((c, i) => (
          <div key={i} className="flex items-center gap-3 text-xs">
            <div className="w-16 font-mono text-gray-500">Cycle {c.cycle}</div>
            <div className="flex-1 relative h-6 bg-white/[0.03] rounded-full overflow-hidden">
              <div className="absolute inset-y-0 left-0 bg-gradient-to-r from-green-500/40 to-red-500/40 rounded-full" style={{ width: c.retrace_pct ? "100%" : "60%" }} />
              <div className="absolute inset-0 flex items-center justify-between px-3 text-[10px] font-mono">
                <span className="text-green-400">${c.low}</span>
                <span className="text-amber-400 font-bold">${c.high}</span>
                {c.retrace && <span className="text-red-400">${c.retrace}</span>}
              </div>
            </div>
            <div className="w-14 text-right font-mono text-gray-500">{c.retrace_pct ? `-${c.retrace_pct}%` : "??"}</div>
          </div>
        ))}
        {(!data?.cycles || data.cycles.length === 0) && (
          <div className="text-xs text-gray-500 italic">No cycle history available.</div>
        )}
      </div>
    </div>
  );
}

function TradeAnalytics({ data }: { data: Analytics | null }) {
  if (!data || data.error) return null;
  const total = data.total_pnl ?? 0;

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-xs font-bold">A</div>
        <div>
          <div className="text-sm font-medium">Trade Analytics</div>
          <div className="text-[10px] text-gray-500">Performance breakdown across all strategies</div>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-2 mb-4">
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Total P&amp;L</div>
          <div className={`font-mono text-lg font-bold ${total >= 0 ? "text-green-400" : "text-red-400"}`}>{formatUSD(total)}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Win Rate</div>
          <div className="font-mono text-lg font-bold text-white">{data.win_rate ?? 0}%</div>
          <div className="text-[9px] text-gray-500">{data.wins ?? 0}W / {data.losses ?? 0}L</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Avg Win</div>
          <div className="font-mono text-lg font-bold text-green-400">{formatUSD(data.avg_win)}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Avg Loss</div>
          <div className="font-mono text-lg font-bold text-red-400">{formatUSD(data.avg_loss)}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Streak</div>
          <div className={`font-mono text-lg font-bold ${data.streak_type === "win" ? "text-green-400" : "text-red-400"}`}>{data.current_streak ?? 0} {data.streak_type ?? ""}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-green-400/5 border border-green-400/10 rounded-lg p-3">
          <div className="text-[9px] text-green-400/70 uppercase tracking-wider">Longs</div>
          <div className="font-mono text-lg font-bold text-green-400">{formatUSD(data.long_pnl)}</div>
          <div className="text-[10px] text-gray-500">{data.long_count ?? 0} trades</div>
        </div>
        <div className="bg-red-400/5 border border-red-400/10 rounded-lg p-3">
          <div className="text-[9px] text-red-400/70 uppercase tracking-wider">Shorts</div>
          <div className="font-mono text-lg font-bold text-red-400">{formatUSD(data.short_pnl)}</div>
          <div className="text-[10px] text-gray-500">{data.short_count ?? 0} trades</div>
        </div>
      </div>

      {data.by_strategy && Object.keys(data.by_strategy).length > 0 && (
        <>
          <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-2">By Strategy</div>
          <div className="space-y-1.5">
            {Object.entries(data.by_strategy).sort(([, a], [, b]) => b.pnl - a.pnl).map(([name, stats]) => (
              <div key={name} className="flex items-center gap-2 text-xs">
                <span className="w-28 text-gray-400 truncate">{name}</span>
                <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${stats.pnl >= 0 ? "bg-green-400" : "bg-red-400"}`} style={{ width: `${Math.min(100, Math.abs(stats.pnl) / Math.max(1, Math.abs(total)) * 100)}%` }} />
                </div>
                <span className={`font-mono w-16 text-right ${stats.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>{formatUSD(stats.pnl)}</span>
                <span className="text-gray-600 w-12 text-right">{stats.wins}W/{stats.losses}L</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function MarketIntelPage() {
  const { data: vision } = useApi<MacroVision>("/api/trading/proxy/macro-vision", 15000);
  const { data: hindsight } = useApi<Hindsight>("/api/trading/proxy/hindsight", 10000);
  const { data: opps } = useApi<Opportunities>("/api/trading/proxy/opportunities", 5000);
  const { data: cycles } = useApi<Cycles>("/api/trading/proxy/cycle-history", 60000);
  const { data: moonshot } = useApi<Moonshot>("/api/trading/proxy/moonshot-status", 5000);
  const { data: analytics } = useApi<Analytics>("/api/trading/proxy/trade-analytics", 30000);

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-4 page-enter">
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-300 to-orange-600 flex items-center justify-center font-black text-black text-lg shadow-lg shadow-amber-500/20">M</div>
        <div>
          <div className="text-2xl font-bold gradient-gold tracking-wider flex items-center gap-2">
            <Activity size={18} /> MARKET INTELLIGENCE
          </div>
          <div className="text-xs text-gray-500">3-layer vision + Blinko news feed · feeds the bot, you read it too</div>
        </div>
      </div>

      <PhaseCard vision={vision} />

      {vision?.capture_tips && vision.capture_tips.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {vision.capture_tips.map((tip, i) => (
            <div key={i} className="bg-amber-400/5 border border-amber-400/10 rounded-full px-3 py-1 text-[10px] text-amber-400 inline-flex items-center gap-1">
              <Zap size={9} /> {tip}
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="flex flex-col gap-4">
          <OpportunityScanner data={opps} />
          <MoonshotStatus data={moonshot} />
          <HindsightCard data={hindsight} />
        </div>
        <div className="flex flex-col gap-4">
          <NewsFeed limit={15} query="market" />
          <TradeAnalytics data={analytics} />
          <CycleTimeline data={cycles} />
        </div>
      </div>
    </div>
  );
}
