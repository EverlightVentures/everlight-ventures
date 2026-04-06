import React from "react"
import { formatTime } from "./hooks"

function Stat({ label, value, color = "text-white", sub }) {
  return (
    <div className="px-3 py-2.5 rounded-lg bg-white/[0.03] text-center">
      <div className={`font-mono text-xl font-bold ${color}`}>{value}</div>
      <div className="text-[9px] uppercase tracking-wider text-gray-500 mt-0.5">{label}</div>
      {sub && <div className="text-[8px] text-gray-600 mt-0.5">{sub}</div>}
    </div>
  )
}

function EventRow({ event }) {
  const reason = event.reason || ""
  const thought = event.thought || event.narrative || ""
  const ts = event.timestamp || ""
  const score = event.final_score || event.score
  const tier = event.quality_tier || ""
  const dir = event.direction || ""

  let color = "border-l-gray-600"
  let badge = reason.replace(/_/g, " ").toUpperCase()

  if (reason === "unified_score") {
    color = (event.recommendation === "ENTER") ? "border-l-green-400" : "border-l-amber-400"
    badge = score != null ? `SCORE ${score}` : "UNIFIED"
  } else if (reason === "unified_hold") {
    color = "border-l-yellow-400"
    badge = `HOLD ${score || ""}`
  } else if (reason === "unified_hard_block") {
    color = "border-l-red-400"
    badge = "BLOCKED"
  } else if (reason === "position_iq") {
    const action = event.action || ""
    if (action === "CUT") { color = "border-l-red-400"; badge = "IQ: CUT" }
    else if (action === "FLIP") { color = "border-l-orange-400"; badge = "IQ: FLIP" }
    else if (action === "TRAIL") { color = "border-l-green-400"; badge = "IQ: TRAIL" }
    else { color = "border-l-blue-400"; badge = "IQ: HOLD" }
  } else if (reason === "entry_fill_check") {
    color = "border-l-green-400"
    badge = "ENTRY FILLED"
  } else if (reason.includes("exit")) {
    color = "border-l-purple-400"
    badge = "EXIT"
  } else if (reason === "macro_vision") {
    color = "border-l-cyan-400"
    badge = "MACRO"
  } else if (reason === "hindsight_scan") {
    color = "border-l-amber-400"
    badge = "HINDSIGHT"
  } else if (reason === "trading_mindset") {
    color = "border-l-blue-400"
    badge = "MINDSET"
  } else if (reason.includes("block")) {
    color = "border-l-red-400"
  }

  return (
    <div className={`px-4 py-2.5 border-l-2 ${color} border-b border-gray-800/30 hover:bg-white/[0.02] transition-colors`}>
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-white/5 text-gray-300">
            {badge}
          </span>
          {tier && (
            <span className={`text-[8px] font-bold px-1 py-0.5 rounded ${
              tier === "MONSTER" ? "bg-amber-400/10 text-amber-400" :
              tier === "FULL" ? "bg-green-400/10 text-green-400" :
              tier === "REDUCED" ? "bg-yellow-400/10 text-yellow-400" :
              "bg-gray-400/10 text-gray-400"
            }`}>{tier}</span>
          )}
          {dir && (
            <span className={`text-[9px] font-mono ${dir === "long" ? "text-green-400" : "text-red-400"}`}>
              {dir.toUpperCase()}
            </span>
          )}
          {event.entry_type && (
            <span className="text-[8px] text-gray-500">{event.entry_type.replace(/_/g, " ")}</span>
          )}
        </div>
        <span className="text-[9px] text-gray-600 font-mono flex-shrink-0">{formatTime(ts)}</span>
      </div>
      {thought && <div className="text-[11px] text-gray-400 mt-1 leading-relaxed">{thought.slice(0, 200)}</div>}
      {event.modifiers && Object.keys(event.modifiers).some(k => event.modifiers[k] !== 0) && (
        <div className="flex gap-1.5 mt-1 flex-wrap">
          {Object.entries(event.modifiers).filter(([,v]) => v !== 0).sort((a,b) => a[1] - b[1]).map(([k, v]) => (
            <span key={k} className={`text-[7px] px-1 py-0.5 rounded ${v > 0 ? "bg-green-400/10 text-green-400" : "bg-red-400/10 text-red-400"}`}>
              {k.replace(/_/g, " ")} {v > 0 ? "+" : ""}{v}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function StrategyIQ({ data }) {
  const s = data?.summary || {}
  const events = data?.events || []
  const piq = s.position_iq || {}
  const strats = Object.entries(s.strategies_seen || {}).sort((a, b) => b[1] - a[1])
  const regimes = Object.entries(s.regimes_seen || {}).sort((a, b) => b[1] - a[1])

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center text-lg font-bold">IQ</div>
        <div>
          <div className="text-lg font-semibold">Strategy Intelligence</div>
          <div className="text-xs text-gray-500">Unified scoring, position management, trade decisions (24h)</div>
        </div>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
        <Stat label="Avg Score" value={s.avg_score || 0} color="text-amber-400" sub={`${s.min_score || 0}-${s.max_score || 0}`} />
        <Stat label="Enter Signals" value={s.enter_signals || 0} color="text-green-400" />
        <Stat label="Hold Signals" value={s.hold_signals || 0} color="text-yellow-400" />
        <Stat label="Entries" value={s.entries || 0} color="text-cyan-400" />
        <Stat label="Exits" value={s.exits || 0} color="text-purple-400" />
        <Stat label="Blocks" value={s.blocks || 0} color="text-red-400" />
      </div>

      {/* Strategy + Regime + Position IQ panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Strategies seen */}
        <div className="card">
          <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">Strategies Fired</div>
          {strats.length > 0 ? strats.map(([name, count]) => (
            <div key={name} className="flex justify-between items-center py-1 border-b border-gray-800/20">
              <span className="text-[11px] text-gray-300 capitalize">{name.replace(/_/g, " ")}</span>
              <span className="font-mono text-[11px] text-amber-400">{count}x</span>
            </div>
          )) : (
            <div className="text-[10px] text-gray-600">No strategies fired yet</div>
          )}
        </div>

        {/* Regimes */}
        <div className="card">
          <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">Regime Distribution</div>
          {regimes.length > 0 ? regimes.map(([name, count]) => (
            <div key={name} className="flex justify-between items-center py-1 border-b border-gray-800/20">
              <span className="text-[11px] text-gray-300 capitalize">{name.replace(/_/g, " ")}</span>
              <span className="font-mono text-[11px] text-blue-400">{count}x</span>
            </div>
          )) : (
            <div className="text-[10px] text-gray-600">No regime data yet</div>
          )}
        </div>

        {/* Position IQ */}
        <div className="card">
          <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">Position IQ Actions</div>
          {Object.keys(piq).length > 0 ? Object.entries(piq).sort((a, b) => b[1] - a[1]).map(([action, count]) => (
            <div key={action} className="flex justify-between items-center py-1 border-b border-gray-800/20">
              <span className={`text-[11px] font-bold ${
                action === "TRAIL" ? "text-green-400" :
                action === "CUT" ? "text-red-400" :
                action === "FLIP" ? "text-orange-400" :
                "text-gray-300"
              }`}>{action}</span>
              <span className="font-mono text-[11px] text-gray-400">{count}x</span>
            </div>
          )) : (
            <div className="text-[10px] text-gray-600">No position actions yet</div>
          )}
        </div>
      </div>

      {/* Event Feed */}
      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 flex justify-between items-center">
          <span className="text-sm font-medium">Strategy Decision Feed</span>
          <span className="text-xs text-gray-500">{events.length} events (24h)</span>
        </div>
        <div className="max-h-[500px] overflow-y-auto">
          {events.length === 0 ? (
            <div className="text-center py-8 text-gray-600 text-sm">
              No strategy events yet. The bot will log unified scores, position IQ decisions, and trade signals here.
            </div>
          ) : (
            events.slice().reverse().map((e, i) => <EventRow key={i} event={e} />)
          )}
        </div>
      </div>
    </div>
  )
}
