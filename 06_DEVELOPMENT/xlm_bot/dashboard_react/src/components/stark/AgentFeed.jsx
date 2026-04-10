import React, { useState, useEffect } from "react"

/**
 * AgentFeed -- Live agent activity sidebar.
 * Shows which agents are active and their recent actions.
 */

const AGENTS = [
  { name: "Marcus Cole",   role: "Chief Operator",     squad: "Claude Corp",      color: "amber",  icon: "M" },
  { name: "Rex Thornton",  role: "Trading Risk",       squad: "Claude Corp",      color: "green",  icon: "R" },
  { name: "Penny Vance",   role: "Profit Maximizer",   squad: "Claude Corp",      color: "emerald",icon: "P" },
  { name: "Rex Blackwell", role: "Wholesale Hunter",    squad: "Claude Corp",      color: "orange", icon: "X" },
  { name: "Piper Reeves",  role: "Outreach Agent",     squad: "Claude Corp",      color: "pink",   icon: "P" },
  { name: "Filter Banks",  role: "Lead Qualifier",      squad: "Claude Corp",      color: "cyan",   icon: "F" },
  { name: "Harrison Knox", role: "Deal Closer",         squad: "Claude Corp",      color: "yellow", icon: "H" },
  { name: "Cipher Wolfe",  role: "Crypto Intel",        squad: "Perplexity Intel", color: "purple", icon: "C" },
  { name: "Forge Steele",  role: "Engineering Lead",    squad: "Codex Labs",       color: "lime",   icon: "F" },
  { name: "Major Dex",     role: "Logistics Commander", squad: "Gemini Ops",       color: "blue",   icon: "D" },
  { name: "Ace Morgan",    role: "Deal Marketer",       squad: "Claude Corp",      color: "rose",   icon: "A" },
  { name: "Scout Navarro", role: "Deal Scout",          squad: "Claude Corp",      color: "teal",   icon: "S" },
  { name: "Justine Park",  role: "Compliance Gate",     squad: "Claude Corp",      color: "indigo", icon: "J" },
]

const COLOR_MAP = {
  amber:   { dot: "bg-amber-400",   text: "text-amber-400",   bg: "bg-amber-400/5" },
  green:   { dot: "bg-green-400",   text: "text-green-400",   bg: "bg-green-400/5" },
  emerald: { dot: "bg-emerald-400", text: "text-emerald-400", bg: "bg-emerald-400/5" },
  orange:  { dot: "bg-orange-400",  text: "text-orange-400",  bg: "bg-orange-400/5" },
  pink:    { dot: "bg-pink-400",    text: "text-pink-400",    bg: "bg-pink-400/5" },
  cyan:    { dot: "bg-cyan-400",    text: "text-cyan-400",    bg: "bg-cyan-400/5" },
  yellow:  { dot: "bg-yellow-400",  text: "text-yellow-400",  bg: "bg-yellow-400/5" },
  purple:  { dot: "bg-purple-400",  text: "text-purple-400",  bg: "bg-purple-400/5" },
  lime:    { dot: "bg-lime-400",    text: "text-lime-400",    bg: "bg-lime-400/5" },
  blue:    { dot: "bg-blue-400",    text: "text-blue-400",    bg: "bg-blue-400/5" },
  rose:    { dot: "bg-rose-400",    text: "text-rose-400",    bg: "bg-rose-400/5" },
  teal:    { dot: "bg-teal-400",    text: "text-teal-400",    bg: "bg-teal-400/5" },
  indigo:  { dot: "bg-indigo-400",  text: "text-indigo-400",  bg: "bg-indigo-400/5" },
}

export default function AgentFeed({ activeAgents = [], recentActivity = [] }) {
  const activeSet = new Set(activeAgents)

  return (
    <div className="bg-[#08080d]/80 rounded-xl border border-white/[0.04] backdrop-blur-sm overflow-hidden h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.04]">
        <div className="flex items-center gap-2">
          <span className="text-[10px] tracking-[0.2em] text-gray-400 font-medium">HIVE AGENTS</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          <span className="text-[9px] text-gray-500 font-mono">{AGENTS.length} online</span>
        </div>
      </div>

      {/* Agent list */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
        {AGENTS.map((agent) => {
          const c = COLOR_MAP[agent.color] || COLOR_MAP.amber
          const isActive = activeSet.has(agent.name)
          return (
            <div
              key={agent.name}
              className={`flex items-center gap-2 px-2 py-1.5 rounded-lg transition-all duration-300 ${
                isActive ? `${c.bg} border border-white/[0.04]` : "opacity-50 hover:opacity-70"
              }`}
            >
              {/* Status dot */}
              <div className="relative flex-shrink-0">
                <div className={`w-1.5 h-1.5 rounded-full ${isActive ? c.dot : "bg-gray-600"} ${isActive ? "animate-pulse" : ""}`} />
              </div>

              {/* Avatar */}
              <div className={`w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 text-[9px] font-bold ${
                isActive ? `${c.bg} ${c.text} border border-white/[0.06]` : "bg-white/[0.03] text-gray-600"
              }`}>
                {agent.icon}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className={`text-[10px] font-medium truncate ${isActive ? c.text : "text-gray-500"}`}>
                  {agent.name}
                </div>
                <div className="text-[8px] text-gray-600 truncate">{agent.role}</div>
              </div>

              {/* Active indicator */}
              {isActive && (
                <div className="flex-shrink-0">
                  <span className="text-[7px] px-1 py-0.5 rounded bg-white/[0.06] text-gray-400 uppercase tracking-wider">active</span>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Recent activity log */}
      {recentActivity.length > 0 && (
        <div className="border-t border-white/[0.04] px-3 py-2 max-h-32 overflow-y-auto">
          <div className="text-[8px] tracking-[0.15em] text-gray-600 mb-1.5">RECENT ACTIVITY</div>
          {recentActivity.slice(-5).map((act, i) => (
            <div key={i} className="flex items-center gap-1.5 py-0.5">
              <span className="text-[8px] text-gray-600 font-mono w-12 flex-shrink-0">{act.time}</span>
              <span className="text-[8px] text-amber-400/60">{act.agent}</span>
              <span className="text-[8px] text-gray-500 truncate">{act.action}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
