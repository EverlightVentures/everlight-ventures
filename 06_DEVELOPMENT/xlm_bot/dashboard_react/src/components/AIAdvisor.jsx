import React from "react"
import { useApi } from "../hooks"

function ThoughtBubble({ type, thought, ts }) {
  const colors = {
    trading_mindset: { bg: "bg-blue-400/5", border: "border-blue-400/20", icon: "M", label: "Mindset" },
    macro_vision: { bg: "bg-purple-400/5", border: "border-purple-400/20", icon: "V", label: "Macro Vision" },
    hindsight_scan: { bg: "bg-amber-400/5", border: "border-amber-400/20", icon: "H", label: "Hindsight" },
    unified_score: { bg: "bg-green-400/5", border: "border-green-400/20", icon: "S", label: "Score" },
    unified_hold: { bg: "bg-gray-400/5", border: "border-gray-400/20", icon: "W", label: "Waiting" },
  }
  const c = colors[type] || colors.unified_hold
  return (
    <div className={`px-3 py-2 rounded-lg ${c.bg} border ${c.border} mb-1.5`}>
      <div className="flex items-center gap-2 mb-0.5">
        <span className="text-[8px] font-bold uppercase text-gray-500">{c.label}</span>
        <span className="text-[8px] text-gray-600 font-mono">{ts}</span>
      </div>
      <div className="text-[10px] text-gray-300 leading-relaxed">{thought}</div>
    </div>
  )
}

export default function AIAdvisor() {
  const { data } = useApi("/report-card", 5000)

  const ai = data?.ai_advisor || {}
  const insight = ai.last_insight || {}
  const mods = ai.modifiers_active || {}
  const thoughts = ai.thought_process || []
  const scenarios = ai.scenarios || []
  const combo = data?.combo || {}
  const trap = data?.trap_analysis || {}

  if (!data?.active) {
    return (
      <div className="card border-dashed border-gray-700/50">
        <div className="text-center py-4">
          <div className="text-[10px] uppercase tracking-widest text-gray-600">AI Advisor</div>
          <div className="text-xs text-gray-500 mt-1">Waiting for bot cycle...</div>
        </div>
      </div>
    )
  }

  const modEntries = Object.entries(mods).sort((a, b) => b[1] - a[1])
  const positiveMods = modEntries.filter(([, v]) => v > 0)
  const negativeMods = modEntries.filter(([, v]) => v < 0)

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="card relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-12 bg-gradient-to-r from-blue-500/10 to-purple-500/10 opacity-60" />
        <div className="relative">
          <div className="flex justify-between items-start mb-3">
            <div>
              <div className="text-[9px] uppercase tracking-widest text-gray-500">AI Advisor</div>
              <div className="text-sm font-bold text-white mt-0.5">
                {insight.recommendation === "ENTER" ? "GO" : "WATCHING"}
                {insight.direction && ` ${insight.direction.toUpperCase()}`}
              </div>
              {insight.entry_type && (
                <div className="text-[10px] text-gray-400 mt-0.5">{insight.entry_type.replace(/_/g, " ")}</div>
              )}
            </div>
            <div className="text-right">
              {insight.score != null && (
                <div className={`font-mono text-xl font-black ${insight.score >= (insight.threshold || 60) ? "text-green-400" : "text-gray-400"}`}>
                  {insight.score}<span className="text-sm text-gray-600">/{insight.threshold || 60}</span>
                </div>
              )}
              {insight.quality_tier && (
                <div className={`text-[9px] font-bold ${
                  insight.quality_tier === "MONSTER" ? "text-amber-400" :
                  insight.quality_tier === "FULL" ? "text-green-400" :
                  "text-gray-400"
                }`}>{insight.quality_tier}</div>
              )}
            </div>
          </div>

          {/* Narrative */}
          {insight.narrative && (
            <div className="px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.05] mb-3">
              <div className="text-[11px] text-gray-300 leading-relaxed">{insight.narrative}</div>
            </div>
          )}

          {/* Foresight summary */}
          {ai.foresight_bias && (
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <span className="text-[8px] uppercase text-gray-500">Outlook:</span>
              <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${
                ai.foresight_bias === "bearish" ? "bg-red-400/10 text-red-400 border border-red-400/20" :
                ai.foresight_bias === "bullish" ? "bg-green-400/10 text-green-400 border border-green-400/20" :
                "bg-gray-400/10 text-gray-400 border border-gray-400/20"
              }`}>{ai.foresight_bias}</span>
              {ai.foresight_rsi && ai.foresight_rsi !== "neutral" && (
                <span className={`text-[9px] px-1.5 py-0.5 rounded ${
                  ai.foresight_rsi === "oversold" ? "bg-green-400/10 text-green-400 border border-green-400/20" :
                  "bg-red-400/10 text-red-400 border border-red-400/20"
                }`}>{ai.foresight_rsi}</span>
              )}
              {ai.projected_profit && (
                <span className="text-[9px] text-amber-400 font-mono">{ai.projected_profit}/day</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Two columns: Modifiers + Scenarios */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* Active Modifiers */}
        <div className="card">
          <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">What's Influencing Decisions</div>
          {positiveMods.length > 0 && (
            <div className="mb-2">
              <div className="text-[8px] text-green-400/60 uppercase mb-1">Confirming</div>
              {positiveMods.map(([k, v]) => (
                <div key={k} className="flex justify-between items-center py-0.5">
                  <span className="text-[10px] text-gray-300 capitalize">{k.replace(/_/g, " ")}</span>
                  <span className="font-mono text-[10px] text-green-400">+{v}</span>
                </div>
              ))}
            </div>
          )}
          {negativeMods.length > 0 && (
            <div>
              <div className="text-[8px] text-red-400/60 uppercase mb-1">Headwinds</div>
              {negativeMods.map(([k, v]) => (
                <div key={k} className="flex justify-between items-center py-0.5">
                  <span className="text-[10px] text-gray-300 capitalize">{k.replace(/_/g, " ")}</span>
                  <span className="font-mono text-[10px] text-red-400">{v}</span>
                </div>
              ))}
            </div>
          )}
          {modEntries.length === 0 && (
            <div className="text-[10px] text-gray-600">No active modifiers this cycle</div>
          )}
        </div>

        {/* Scenarios */}
        <div className="card">
          <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">Anticipated Plays</div>
          {scenarios.length > 0 ? scenarios.map((s, i) => (
            <div key={i} className={`flex justify-between items-center py-1.5 ${i > 0 ? "border-t border-gray-800/30" : ""}`}>
              <div className="flex items-center gap-2">
                <span className={`text-[8px] px-1 py-0.5 rounded font-bold ${
                  s.probability === "high" ? "bg-green-400/10 text-green-400" : "bg-amber-400/10 text-amber-400"
                }`}>{s.probability}</span>
                <span className={`text-[9px] font-bold uppercase ${
                  s.direction === "long" ? "text-green-400" : s.direction === "short" ? "text-red-400" : "text-blue-400"
                }`}>{s.direction}</span>
                <span className="text-[10px] text-gray-300">{s.name?.replace(/_/g, " ")}</span>
              </div>
              <span className="font-mono text-[10px] text-amber-400">${s.profit_usd?.toFixed(2)}</span>
            </div>
          )) : (
            <div className="text-[10px] text-gray-600">No scenarios computed yet</div>
          )}
        </div>
      </div>

      {/* Combo Layers + Trap Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* 3-Layer Combo System */}
        <div className="card">
          <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">Strategy Layers (Macro / Mini / Micro)</div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-[8px] text-gray-500 w-12">MACRO</span>
              <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                combo.macro === "BULL" ? "bg-green-400/10 text-green-400 border border-green-400/20" :
                combo.macro === "BEAR" ? "bg-red-400/10 text-red-400 border border-red-400/20" :
                "bg-gray-400/10 text-gray-400 border border-gray-400/20"
              }`}>{combo.macro || "NEUTRAL"}</span>
              <span className="text-[8px] text-gray-600">1H + 4H trend direction</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[8px] text-gray-500 w-12">MINI</span>
              <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                (combo.mini || "").includes("UP") ? "bg-green-400/10 text-green-400 border border-green-400/20" :
                (combo.mini || "").includes("DOWN") ? "bg-red-400/10 text-red-400 border border-red-400/20" :
                "bg-amber-400/10 text-amber-400 border border-amber-400/20"
              }`}>{combo.mini || "RANGING"}</span>
              <span className="text-[8px] text-gray-600">15m structure</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[8px] text-gray-500 w-12">MICRO</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-blue-400/10 text-blue-400 border border-blue-400/20 font-bold">
                {combo.entry_tf ? combo.entry_tf.replace(/_/g, " ").toUpperCase() : "SCANNING"}
              </span>
              <span className="text-[8px] text-gray-600">1m entry pattern</span>
            </div>
          </div>
        </div>

        {/* Trap Analysis */}
        <div className="card">
          <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">Trap / Squeeze Detection</div>
          {trap.trap_detected ? (
            <div>
              <div className={`flex items-center gap-2 mb-2 px-2 py-1.5 rounded ${
                trap.action === "ride_squeeze" ? "bg-green-400/5 border border-green-400/20" :
                trap.action === "avoid" ? "bg-red-400/5 border border-red-400/20" :
                "bg-gray-400/5 border border-gray-400/20"
              }`}>
                <span className={`text-[10px] font-bold ${
                  trap.action === "ride_squeeze" ? "text-green-400" :
                  trap.action === "avoid" ? "text-red-400" : "text-gray-400"
                }`}>
                  {trap.action === "ride_squeeze" ? "RIDE THE SQUEEZE" :
                   trap.action === "avoid" ? "TRAP - STAY OUT" :
                   trap.action === "wait_for_trigger" ? "WAIT FOR TRIGGER" : "NEUTRAL"}
                </span>
              </div>
              <div className="text-[10px] text-gray-300 mb-1">{trap.reason}</div>
              <div className="grid grid-cols-2 gap-2 text-[9px]">
                <div>
                  <span className="text-gray-500">Trapped side: </span>
                  <span className={trap.trap_side?.includes("short") ? "text-red-400" : "text-green-400"}>{trap.trap_side?.replace(/_/g, " ")}</span>
                </div>
                <div>
                  <span className="text-gray-500">Distance: </span>
                  <span className="text-amber-400">${trap.trap_distance_usd?.toFixed(2)}</span>
                </div>
                {trap.squeeze_profit_usd > 0 && (
                  <div>
                    <span className="text-gray-500">Squeeze profit: </span>
                    <span className="text-green-400">${trap.squeeze_profit_usd?.toFixed(2)}</span>
                  </div>
                )}
                <div>
                  <span className="text-gray-500">Score mod: </span>
                  <span className={`font-bold ${trap.score_modifier > 0 ? "text-green-400" : trap.score_modifier < 0 ? "text-red-400" : "text-gray-400"}`}>
                    {trap.score_modifier > 0 ? "+" : ""}{trap.score_modifier}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-[10px] text-gray-600 py-2">No liquidation zones detected near current price</div>
          )}
        </div>
      </div>

      {/* Thought Process */}
      {thoughts.length > 0 && (
        <div className="card">
          <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">Bot's Thought Process</div>
          {thoughts.map((t, i) => (
            <ThoughtBubble key={i} type={t.type} thought={t.thought} ts={t.ts} />
          ))}
        </div>
      )}
    </div>
  )
}
