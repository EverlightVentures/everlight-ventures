import React from "react"
import { useApi, formatUSD, formatPrice } from "../hooks"

const PHASE_COLORS = {
  ACCUMULATION: { bg: "from-green-500/20 to-green-900/10", text: "text-green-400", icon: "+" },
  DEEP_VALUE: { bg: "from-emerald-500/20 to-emerald-900/10", text: "text-emerald-300", icon: "$$" },
  MARKUP: { bg: "from-blue-500/20 to-blue-900/10", text: "text-blue-400", icon: "^" },
  LATE_MARKUP: { bg: "from-cyan-500/20 to-cyan-900/10", text: "text-cyan-400", icon: "^" },
  DISTRIBUTION: { bg: "from-amber-500/20 to-amber-900/10", text: "text-amber-400", icon: "!" },
  EUPHORIA: { bg: "from-red-500/20 to-red-900/10", text: "text-red-400", icon: "!!" },
  MARKDOWN: { bg: "from-red-600/20 to-red-900/10", text: "text-red-500", icon: "v" },
}

function PhaseCard({ phase, bias, risk, mult, aligned, targets, months }) {
  const pc = PHASE_COLORS[phase] || PHASE_COLORS.MARKUP
  return (
    <div className={`card border border-white/5 bg-gradient-to-br ${pc.bg} relative overflow-hidden`}>
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
            <div className={`font-mono text-sm font-bold ${bias?.includes("LONG") ? "text-green-400" : bias?.includes("SHORT") ? "text-red-400" : "text-gray-400"}`}>{bias}</div>
          </div>
          <div className="text-center">
            <div className="text-[8px] text-gray-500 uppercase tracking-wider">Risk</div>
            <div className={`font-mono text-sm font-bold ${risk === "LOW" ? "text-green-400" : risk === "MEDIUM" ? "text-amber-400" : risk === "HIGH" ? "text-orange-400" : "text-red-400"}`}>{risk}</div>
          </div>
          <div className="text-center">
            <div className="text-[8px] text-gray-500 uppercase tracking-wider">Size Mult</div>
            <div className="font-mono text-sm font-bold text-white">{mult?.toFixed(2)}x</div>
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
        <div className="mt-3 text-[10px] text-gray-500">
          {months?.toFixed(1)} months post-halving (Apr 2024)
        </div>
      </div>
    </div>
  )
}

function CycleTimeline({ cycles, current }) {
  return (
    <div className="card">
      <div className="text-sm font-medium mb-3">XLM Cycle History</div>
      <div className="space-y-3">
        {(cycles || []).map((c, i) => (
          <div key={i} className="flex items-center gap-3 text-xs">
            <div className="w-16 font-mono text-gray-500">Cycle {c.cycle}</div>
            <div className="flex-1 relative h-6 bg-white/[0.03] rounded-full overflow-hidden">
              <div className="absolute inset-y-0 left-0 bg-gradient-to-r from-green-500/40 to-red-500/40 rounded-full"
                style={{ width: c.retrace_pct ? "100%" : "60%" }} />
              <div className="absolute inset-0 flex items-center justify-between px-3 text-[10px] font-mono">
                <span className="text-green-400">${c.low}</span>
                <span className="text-amber-400 font-bold">${c.high}</span>
                {c.retrace && <span className="text-red-400">${c.retrace}</span>}
              </div>
            </div>
            <div className="w-14 text-right font-mono text-gray-500">
              {c.retrace_pct ? `-${c.retrace_pct}%` : "??"}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function OpportunityScanner({ data }) {
  const { next_play_long, next_play_short, score_long, score_short, threshold,
          entry_type_long, entry_type_short, long_block, short_block,
          htf_trend, vol_phase, market_health, market_regime } = data || {}
  
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
          <div className={`text-xs font-bold ${htf_trend === "bullish" ? "text-green-400" : "text-red-400"}`}>{htf_trend || "--"}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Vol</div>
          <div className="text-xs font-bold text-gray-300">{vol_phase || "--"}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Health</div>
          <div className={`text-xs font-bold ${market_health > 50 ? "text-green-400" : market_health > 30 ? "text-amber-400" : "text-red-400"}`}>{market_health || "--"}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Regime</div>
          <div className="text-xs font-bold text-gray-300">{market_regime || "--"}</div>
        </div>
      </div>

      {/* Score gauges */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className={`rounded-xl p-3 border ${score_long >= threshold ? "border-green-400/30 bg-green-400/5" : "border-gray-700/30 bg-white/[0.02]"}`}>
          <div className="flex justify-between items-center mb-1">
            <span className="text-[9px] text-green-400/70 uppercase tracking-wider">Long</span>
            <span className="text-[9px] text-gray-500">{entry_type_long || "--"}</span>
          </div>
          <div className="flex items-end gap-1">
            <span className={`font-mono text-2xl font-black ${score_long >= threshold ? "text-green-400" : "text-gray-400"}`}>{score_long || 0}</span>
            <span className="text-gray-600 text-sm mb-0.5">/ {threshold || 60}</span>
          </div>
          <div className="w-full h-1.5 bg-gray-800 rounded-full mt-2 overflow-hidden">
            <div className={`h-full rounded-full transition-all ${score_long >= threshold ? "bg-green-400" : "bg-gray-600"}`}
              style={{ width: `${Math.min(100, ((score_long || 0) / (threshold || 60)) * 100)}%` }} />
          </div>
          {long_block && <div className="text-[9px] text-red-400/60 mt-1">{long_block}</div>}
        </div>
        <div className={`rounded-xl p-3 border ${score_short >= threshold ? "border-red-400/30 bg-red-400/5" : "border-gray-700/30 bg-white/[0.02]"}`}>
          <div className="flex justify-between items-center mb-1">
            <span className="text-[9px] text-red-400/70 uppercase tracking-wider">Short</span>
            <span className="text-[9px] text-gray-500">{entry_type_short || "--"}</span>
          </div>
          <div className="flex items-end gap-1">
            <span className={`font-mono text-2xl font-black ${score_short >= threshold ? "text-red-400" : "text-gray-400"}`}>{score_short || 0}</span>
            <span className="text-gray-600 text-sm mb-0.5">/ {threshold || 60}</span>
          </div>
          <div className="w-full h-1.5 bg-gray-800 rounded-full mt-2 overflow-hidden">
            <div className={`h-full rounded-full transition-all ${score_short >= threshold ? "bg-red-400" : "bg-gray-600"}`}
              style={{ width: `${Math.min(100, ((score_short || 0) / (threshold || 60)) * 100)}%` }} />
          </div>
          {short_block && <div className="text-[9px] text-red-400/60 mt-1">{short_block}</div>}
        </div>
      </div>

      {/* Next plays */}
      <div className="space-y-2">
        {next_play_long && (
          <div className="flex items-center gap-2 bg-green-400/5 border border-green-400/10 rounded-lg px-3 py-2">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
            <span className="text-[10px] text-green-400 font-medium">LONG</span>
            <span className="text-[10px] text-gray-400 flex-1">{next_play_long.level_name} @ ${next_play_long.trigger_price}</span>
            <span className="text-[10px] text-gray-500">{next_play_long.distance_atr} ATR</span>
            <span className={`text-[10px] font-bold ${next_play_long.readiness_pct >= 80 ? "text-green-400" : "text-amber-400"}`}>{next_play_long.readiness_pct}%</span>
          </div>
        )}
        {next_play_short && (
          <div className="flex items-center gap-2 bg-red-400/5 border border-red-400/10 rounded-lg px-3 py-2">
            <div className="w-1.5 h-1.5 rounded-full bg-red-400" />
            <span className="text-[10px] text-red-400 font-medium">SHORT</span>
            <span className="text-[10px] text-gray-400 flex-1">{next_play_short.level_name} @ ${next_play_short.trigger_price}</span>
            <span className="text-[10px] text-gray-500">{next_play_short.distance_atr} ATR</span>
            <span className={`text-[10px] font-bold ${next_play_short.readiness_pct >= 80 ? "text-red-400" : "text-amber-400"}`}>{next_play_short.readiness_pct}%</span>
          </div>
        )}
      </div>
    </div>
  )
}

function HindsightCard({ data }) {
  const h = data?.hindsight || {}
  if (!h.missed_count && h.missed_count !== 0) return null
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
          <div className={`font-mono text-xl font-bold ${h.missed_count > 0 ? "text-amber-400" : "text-green-400"}`}>{h.missed_count || 0}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-3 text-center">
          <div className="text-[8px] text-gray-500 uppercase">$ Left</div>
          <div className="font-mono text-xl font-bold text-amber-400">${h.missed_usd || 0}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-3 text-center">
          <div className="text-[8px] text-gray-500 uppercase">Pattern</div>
          <div className="font-mono text-sm font-bold text-gray-300">{h.pattern || "none"}</div>
        </div>
      </div>
      {h.lesson && h.lesson !== "none" && (
        <div className="bg-amber-400/5 border border-amber-400/10 rounded-lg px-3 py-2">
          <div className="text-[9px] text-amber-400/70 uppercase tracking-wider">Lesson</div>
          <div className="text-xs text-gray-300 mt-0.5">{h.lesson}</div>
        </div>
      )}
    </div>
  )
}

function MoonshotStatus({ data }) {
  if (!data) return null
  return (
    <div className={`card border ${data.active ? "border-amber-400/30 bg-amber-400/5" : "border-gray-700/20"}`}>
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
  )
}

function TradeAnalytics({ data }) {
  if (!data || data.error) return null
  const { total_trades, wins, losses, win_rate, avg_win, avg_loss, total_pnl,
          best_trade, worst_trade, current_streak, streak_type,
          by_strategy, long_pnl, short_pnl, long_count, short_count, daily_pnl } = data
  
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
          <div className="text-[8px] text-gray-500">Total P&L</div>
          <div className={`font-mono text-lg font-bold ${total_pnl >= 0 ? "text-green-400" : "text-red-400"}`}>{formatUSD(total_pnl)}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Win Rate</div>
          <div className="font-mono text-lg font-bold text-white">{win_rate}%</div>
          <div className="text-[9px] text-gray-500">{wins}W / {losses}L</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Avg Win</div>
          <div className="font-mono text-lg font-bold text-green-400">{formatUSD(avg_win)}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Avg Loss</div>
          <div className="font-mono text-lg font-bold text-red-400">{formatUSD(avg_loss)}</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-[8px] text-gray-500">Streak</div>
          <div className={`font-mono text-lg font-bold ${streak_type === "win" ? "text-green-400" : "text-red-400"}`}>{current_streak} {streak_type}</div>
        </div>
      </div>

      {/* Direction split */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-green-400/5 border border-green-400/10 rounded-lg p-3">
          <div className="text-[9px] text-green-400/70 uppercase tracking-wider">Longs</div>
          <div className="font-mono text-lg font-bold text-green-400">{formatUSD(long_pnl)}</div>
          <div className="text-[10px] text-gray-500">{long_count} trades</div>
        </div>
        <div className="bg-red-400/5 border border-red-400/10 rounded-lg p-3">
          <div className="text-[9px] text-red-400/70 uppercase tracking-wider">Shorts</div>
          <div className="font-mono text-lg font-bold text-red-400">{formatUSD(short_pnl)}</div>
          <div className="text-[10px] text-gray-500">{short_count} trades</div>
        </div>
      </div>

      {/* Best / Worst */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-white/[0.02] rounded-lg p-2">
          <div className="text-[9px] text-green-400/70">Best Trade</div>
          <div className="font-mono text-sm font-bold text-green-400">{formatUSD(best_trade?.pnl)}</div>
          <div className="text-[9px] text-gray-500">{best_trade?.strategy} {best_trade?.direction}</div>
        </div>
        <div className="bg-white/[0.02] rounded-lg p-2">
          <div className="text-[9px] text-red-400/70">Worst Trade</div>
          <div className="font-mono text-sm font-bold text-red-400">{formatUSD(worst_trade?.pnl)}</div>
          <div className="text-[9px] text-gray-500">{worst_trade?.strategy} {worst_trade?.direction}</div>
        </div>
      </div>

      {/* Strategy breakdown */}
      <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-2">By Strategy</div>
      <div className="space-y-1.5">
        {Object.entries(by_strategy || {}).sort((a, b) => b[1].pnl - a[1].pnl).map(([name, stats]) => (
          <div key={name} className="flex items-center gap-2 text-xs">
            <span className="w-28 text-gray-400 truncate">{name}</span>
            <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${stats.pnl >= 0 ? "bg-green-400" : "bg-red-400"}`}
                style={{ width: `${Math.min(100, Math.abs(stats.pnl) / Math.max(1, Math.abs(total_pnl)) * 100)}%` }} />
            </div>
            <span className={`font-mono w-16 text-right ${stats.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>{formatUSD(stats.pnl)}</span>
            <span className="text-gray-600 w-12 text-right">{stats.wins}W/{stats.losses}L</span>
          </div>
        ))}
      </div>

      {/* Daily P&L mini chart */}
      {daily_pnl && daily_pnl.length > 0 && (
        <div className="mt-4 pt-3 border-t border-white/5">
          <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-2">Daily P&L (last 30 days)</div>
          <div className="flex items-end gap-0.5 h-16">
            {daily_pnl.map((d, i) => {
              const max = Math.max(...daily_pnl.map(x => Math.abs(x.pnl)), 1)
              const h = Math.max(2, (Math.abs(d.pnl) / max) * 60)
              return (
                <div key={i} className="flex-1 flex flex-col justify-end items-center group relative">
                  <div className={`w-full rounded-t ${d.pnl >= 0 ? "bg-green-400/60" : "bg-red-400/60"}`} style={{ height: `${h}px` }} />
                  <div className="absolute bottom-full mb-1 hidden group-hover:block bg-gray-900 border border-gray-700 rounded px-2 py-1 text-[9px] font-mono whitespace-nowrap z-10">
                    {d.date}: {formatUSD(d.pnl)} ({d.trades}t)
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export default function MarketIntel() {
  const { data: vision } = useApi("/macro-vision", 15000)
  const { data: hindsight } = useApi("/hindsight", 10000)
  const { data: opps } = useApi("/opportunities", 5000)
  const { data: cycles } = useApi("/cycle-history", 60000)
  const { data: moonshot } = useApi("/moonshot-status", 5000)
  const { data: analytics } = useApi("/trade-analytics", 30000)
  
  const macro = vision?.macro || {}

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <div className="w-10 h-10 rounded-xl overflow-hidden shadow-lg shadow-amber-500/20"><img src="/lucrex_icon.png" alt="L" className="w-full h-full object-cover" /></div>
        <div>
          <div className="text-lg font-semibold">Market Intelligence</div>
          <div className="text-xs text-gray-500">3-layer vision: Macro (cycle) + Median (weekly) + Micro (real-time)</div>
        </div>
      </div>

      {/* Macro Phase */}
      <PhaseCard
        phase={macro.phase || vision?.phase || "--"}
        bias={vision?.combined_bias || macro.bias}
        risk={macro.risk_level || vision?.risk}
        mult={vision?.position_mult || 1}
        aligned={vision?.aligned}
        targets={macro.targets}
        months={macro.months_since_halving}
      />

      {/* Tips */}
      {vision?.capture_tips && (
        <div className="flex gap-2 flex-wrap">
          {vision.capture_tips.map((tip, i) => (
            <div key={i} className="bg-amber-400/5 border border-amber-400/10 rounded-full px-3 py-1 text-[10px] text-amber-400">{tip}</div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left column */}
        <div className="flex flex-col gap-4">
          <OpportunityScanner data={opps} />
          <MoonshotStatus data={moonshot} />
          <HindsightCard data={hindsight} />
        </div>
        
        {/* Right column */}
        <div className="flex flex-col gap-4">
          <TradeAnalytics data={analytics} />
          <CycleTimeline cycles={cycles?.cycles} current={cycles?.current_price} />
        </div>
      </div>
    </div>
  )
}
