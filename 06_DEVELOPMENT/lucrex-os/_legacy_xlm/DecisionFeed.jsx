import React, { useState } from "react"
import { formatTime } from "./hooks"

const REASON_COLORS = {
  "entry_blocked": "text-yellow-500",
  "idle_sweep": "text-gray-500",
  "circuit_breaker": "text-orange-400",
  "htf_short_blocked": "text-red-400",
  "htf_long_blocked": "text-red-400",
  "profit_manager": "text-green-400",
  "hedge_flip": "text-amber-400",
  "divergence": "text-purple-400",
  "fib_confluence": "text-cyan-400",
  "entry_blocked_sl": "text-yellow-600",
  "entry_blocked_sentiment": "text-orange-300",
  "entry_blocked_margin": "text-red-300",
}

function getReasonColor(reason) {
  for (const [key, color] of Object.entries(REASON_COLORS)) {
    if (reason.includes(key)) return color
  }
  return "text-gray-400"
}

export default function DecisionFeed({ decisions }) {
  const [filter, setFilter] = useState("all")

  const filters = [
    { id: "all", label: "All" },
    { id: "entry", label: "Entry Signals" },
    { id: "blocked", label: "Blocked" },
    { id: "iq", label: "Strategy IQ" },
    { id: "exit", label: "Exits" },
  ]

  const filtered = decisions.filter(d => {
    const r = String(d.reason || "")
    if (filter === "all") return !r.includes("idle_sweep")  // skip noise
    if (filter === "entry") return d.direction && !r.includes("blocked")
    if (filter === "blocked") return r.includes("blocked") || r.includes("circuit_breaker")
    if (filter === "iq") return r.includes("profit_manager") || r.includes("hedge_flip") || r.includes("divergence") || r.includes("fib_confluence") || (r.includes("htf") && r.includes("blocked"))
    if (filter === "exit") return r.includes("exit") || r.includes("tp1") || r.includes("stop")
    return true
  }).reverse()

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <div className="text-lg font-semibold">Decision Feed</div>
        <span className="text-xs text-gray-500">Last 24h -- {filtered.length} decisions</span>
      </div>

      {/* Filter Chips */}
      <div className="flex gap-2 flex-wrap">
        {filters.map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              filter === f.id
                ? "bg-amber-400/20 text-amber-400 border border-amber-400/30"
                : "bg-white/5 text-gray-500 border border-transparent hover:text-gray-300"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Feed */}
      <div className="card p-0 overflow-hidden">
        <div className="max-h-[600px] overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="text-center py-8 text-gray-600 text-sm">No decisions match this filter.</div>
          ) : (
            filtered.slice(0, 100).map((d, i) => {
              const reason = String(d.reason || "?")
              const thought = String(d.thought || "")
              const dir = d.direction
              const ts = d.timestamp
              const score = d.v4_score

              return (
                <div key={i} className="px-4 py-2.5 border-b border-gray-800/30 hover:bg-white/[0.02] transition-colors">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-[11px] font-mono font-medium ${getReasonColor(reason)}`}>
                        {reason.slice(0, 35)}
                      </span>
                      {dir && (
                        <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                          dir === "long" ? "bg-green-400/10 text-green-400" : "bg-red-400/10 text-red-400"
                        }`}>{dir}</span>
                      )}
                      {score && <span className="text-[10px] text-gray-500 font-mono">score:{score}</span>}
                    </div>
                    <span className="text-[10px] text-gray-600 font-mono whitespace-nowrap ml-2">{formatTime(ts)}</span>
                  </div>
                  {thought && <div className="text-[11px] text-gray-500 mt-1 leading-relaxed">{thought.slice(0, 180)}</div>}
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
