import React from "react"
import { useApi, formatUSD } from "../hooks"

const MODE_CONFIG = {
  GRIND: {
    gradient: "from-red-500/20 via-orange-500/10 to-red-900/5",
    border: "border-red-400/30",
    glow: "shadow-red-500/10",
    text: "text-red-400",
    icon: "!",
    ethicBar: "from-red-400 to-orange-500",
  },
  STEADY: {
    gradient: "from-blue-500/15 via-cyan-500/5 to-blue-900/5",
    border: "border-blue-400/20",
    glow: "shadow-blue-500/10",
    text: "text-blue-400",
    icon: "~",
    ethicBar: "from-blue-400 to-cyan-500",
  },
  CRUISE: {
    gradient: "from-green-500/15 via-emerald-500/5 to-green-900/5",
    border: "border-green-400/20",
    glow: "shadow-green-500/10",
    text: "text-green-400",
    icon: "^",
    ethicBar: "from-green-400 to-emerald-500",
  },
  BEAST: {
    gradient: "from-amber-500/20 via-yellow-500/10 to-orange-900/5",
    border: "border-amber-400/30",
    glow: "shadow-amber-500/20",
    text: "text-amber-400",
    icon: "*",
    ethicBar: "from-amber-400 to-orange-500",
  },
}

export default function MindsetPanel() {
  const { data } = useApi("/mindset", 8000)
  const { data: brain } = useApi("/brain/status", 30000)
  if (!data) return null
  const m = data.mindset || {}
  const g = data.goals || {}
  const brainReady = !!brain?.available
  const topTopics = brainReady ? (brain.top_topics || []).slice(0, 4) : []
  const traits = brainReady ? (brain.cognitive_profile || {}) : {}
  const highlights = brainReady ? (brain.highlights || []).slice(0, 2) : []
  const repoStack = brainReady ? (brain.repo_stack || {}) : {}
  const repoNext = brainReady ? (repoStack.recommended_next || []).slice(0, 3) : []
  const agentRoster = brainReady ? ((brain.slack_routing || {}).agent_names || []).slice(0, 4) : []
  const mode = m.mode || "STEADY"
  const mc = MODE_CONFIG[mode] || MODE_CONFIG.STEADY
  const ethic = m.work_ethic || 50
  const thought = m.thought || ""
  const pnl = g.daily_pnl || 0
  const minGoal = g.daily_min_goal || 25
  const idealGoal = g.daily_ideal_goal || 100
  const lossDebt = g.loss_debt_today || 0
  const weeklyPnl = g.weekly_pnl || 0
  const weeklyGoal = g.weekly_min_goal || 175
  const monthlyPnl = g.monthly_pnl || 0
  const monthlyGoal = g.monthly_min_goal || 750

  const dailyPct = minGoal > 0 ? Math.max(-100, Math.min(100, pnl / minGoal * 100)) : 0
  const weeklyPct = weeklyGoal > 0 ? Math.max(-100, Math.min(100, weeklyPnl / weeklyGoal * 100)) : 0
  const monthlyPct = monthlyGoal > 0 ? Math.max(-100, Math.min(100, monthlyPnl / monthlyGoal * 100)) : 0
  const idealPct = idealGoal > 0 ? Math.max(-100, Math.min(100, pnl / idealGoal * 100)) : 0

  return (
    <div className={`card border ${mc.border} bg-gradient-to-br ${mc.gradient} relative overflow-hidden shadow-lg ${mc.glow}`}>
      {/* Top accent */}
      <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${mc.ethicBar}`} />
      {/* Ambient glow orb */}
      <div className={`absolute -top-10 -right-10 w-32 h-32 rounded-full bg-gradient-to-br ${mc.gradient} opacity-30 blur-2xl`} />

      <div className="relative">
        {/* Header: Mode + Work Ethic */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${mc.ethicBar} flex items-center justify-center text-xl font-black text-black shadow-lg ${mc.glow}`}>
              {mc.icon}
            </div>
            <div>
              <div className={`text-lg font-black tracking-wider ${mc.text}`}>{mode} MODE</div>
              <div className="text-[10px] text-gray-500">Bot Mindset</div>
            </div>
          </div>
          {/* Work ethic gauge */}
          <div className="text-right">
            <div className="text-[9px] text-gray-500 uppercase tracking-wider">Work Ethic</div>
            <div className="flex items-center gap-2">
              <div className="w-20 h-2 bg-gray-800/50 rounded-full overflow-hidden">
                <div className={`h-full rounded-full bg-gradient-to-r ${mc.ethicBar} transition-all`} style={{width: `${ethic}%`}} />
              </div>
              <span className={`font-mono text-sm font-bold ${mc.text}`}>{ethic}</span>
            </div>
          </div>
        </div>

        {/* Bot's thought */}
        <div className="bg-black/20 rounded-lg px-3 py-2 mb-3 border border-white/5">
          <div className="text-[9px] text-gray-600 uppercase tracking-wider mb-0.5">Bot is thinking</div>
          <div className={`text-xs ${mc.text} font-medium leading-relaxed`}>{thought}</div>
        </div>

        {/* Adjustments */}
        <div className="grid grid-cols-3 gap-2 mb-3">
          <div className="bg-black/20 rounded-lg p-2 text-center">
            <div className="text-[8px] text-gray-600">Threshold</div>
            <div className={`font-mono text-sm font-bold ${m.threshold_adj > 0 ? "text-red-400" : m.threshold_adj < 0 ? "text-green-400" : "text-gray-400"}`}>
              {m.threshold_adj > 0 ? "+" : ""}{m.threshold_adj || 0}
            </div>
          </div>
          <div className="bg-black/20 rounded-lg p-2 text-center">
            <div className="text-[8px] text-gray-600">Size</div>
            <div className={`font-mono text-sm font-bold ${(m.size_mult || 1) < 1 ? "text-red-400" : (m.size_mult || 1) > 1 ? "text-green-400" : "text-gray-400"}`}>
              {(m.size_mult || 1).toFixed(2)}x
            </div>
          </div>
          <div className="bg-black/20 rounded-lg p-2 text-center">
            <div className="text-[8px] text-gray-600">Daily P&L</div>
            <div className={`font-mono text-sm font-bold ${pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
              {formatUSD(pnl)}
            </div>
          </div>
        </div>

        {/* Goal progress bars */}
        <div className="space-y-2">
          {[
            {label: "Daily", current: pnl, goal: minGoal, pct: dailyPct, color: "amber", debt: lossDebt},
            {label: "Weekly", current: weeklyPnl, goal: weeklyGoal, pct: weeklyPct, color: "green"},
            {label: "Monthly", current: monthlyPnl, goal: monthlyGoal, pct: monthlyPct, color: "blue"},
          ].map(({label, current, goal, pct, color, debt}) => (
            <div key={label}>
              <div className="flex justify-between items-center mb-0.5">
                <div className="flex items-center gap-1.5">
                  <span className="text-[9px] text-gray-500 uppercase">{label}</span>
                  {debt > 0 && <span className="text-[8px] px-1.5 py-0 rounded bg-red-400/10 text-red-400">+${debt.toFixed(0)} debt</span>}
                </div>
                <span className={`text-[9px] font-mono ${current >= goal ? "text-green-400" : current >= 0 ? "text-gray-400" : "text-red-400"}`}>
                  {formatUSD(current)} / {formatUSD(goal)}
                </span>
              </div>
              <div className="h-2 bg-gray-800/50 rounded-full overflow-hidden">
                {current < 0 ? (
                  <div className="h-full bg-red-500/40 rounded-full" style={{width: `${Math.min(100, Math.abs(pct))}%`}} />
                ) : (
                  <div className={`h-full rounded-full transition-all bg-gradient-to-r ${
                    color === "amber" ? "from-amber-400 to-orange-500" : 
                    color === "green" ? "from-green-400 to-emerald-500" : 
                    "from-blue-400 to-cyan-500"
                  } ${pct >= 100 ? "animate-pulse" : ""}`} style={{width: `${Math.max(0, pct)}%`}} />
                )}
              </div>
            </div>
          ))}
          {/* Daily ideal */}
          <div>
            <div className="flex justify-between items-center mb-0.5">
              <span className="text-[9px] text-gray-500 uppercase">Daily Ideal ($100+)</span>
              <span className={`text-[9px] font-mono ${pnl >= idealGoal ? "text-green-400" : "text-gray-400"}`}>
                {formatUSD(pnl)} / {formatUSD(idealGoal)}
              </span>
            </div>
            <div className="h-2 bg-gray-800/50 rounded-full overflow-hidden">
              {pnl < 0 ? (
                <div className="h-full bg-red-500/40 rounded-full" style={{width: `${Math.min(100, Math.abs(idealPct))}%`}} />
              ) : (
                <div className="h-full rounded-full bg-gradient-to-r from-amber-400 via-orange-500 to-red-500 transition-all" style={{width: `${Math.max(0, idealPct)}%`}} />
              )}
            </div>
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-white/5">
          <div className="flex items-start justify-between gap-3 mb-2">
            <div>
              <div className="text-[9px] text-gray-500 uppercase tracking-wider">AI Brain Sync</div>
              <div className={`text-[11px] font-semibold ${brainReady ? "text-cyan-300" : "text-gray-500"}`}>
                {brainReady ? (brain.knowledge_mode || "knowledge online") : "syncing transcript corpus"}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[9px] font-mono text-gray-400">
                {brainReady ? `${brain.documents || 0} docs` : "--"}
              </div>
              <div className="text-[8px] text-gray-600">
                {brainReady ? `${brain.chunks || 0} memory chunks` : "waiting"}
              </div>
            </div>
          </div>

          {brainReady ? (
            <>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {topTopics.map((topic) => (
                  <span key={topic.topic} className="text-[8px] px-1.5 py-0.5 rounded bg-cyan-400/10 text-cyan-300 border border-cyan-400/15">
                    {topic.topic.replace(/_/g, " ")} {topic.count}
                  </span>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-2 mb-2">
                {[
                  ["Self-Healing", traits.self_healing],
                  ["Emotional", traits.emotional_regulation],
                  ["Decisive", traits.decisiveness],
                  ["Logical", traits.logical_rigor],
                ].map(([label, value]) => (
                  <div key={label} className="bg-black/20 rounded-lg p-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[8px] text-gray-500 uppercase">{label}</span>
                      <span className="text-[9px] font-mono text-cyan-300">{value || 0}</span>
                    </div>
                    <div className="h-1.5 bg-gray-800/50 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-blue-500" style={{ width: `${Math.max(0, Math.min(100, value || 0))}%` }} />
                    </div>
                  </div>
                ))}
              </div>

              {highlights.length > 0 && (
                <div className="space-y-1.5">
                  {highlights.map((item) => (
                    <div key={item.path} className="bg-black/20 rounded-lg px-2.5 py-2 border border-white/5">
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-[10px] text-gray-200 truncate">{item.title}</div>
                        <div className="text-[8px] uppercase text-gray-500">{item.kind}</div>
                      </div>
                      <div className="text-[8px] text-gray-600 mt-0.5">
                        {(item.topics || []).join(" • ") || "neuromorphic reference"}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-2 grid grid-cols-2 gap-2">
                <div className="bg-black/20 rounded-lg p-2 border border-white/5">
                  <div className="text-[8px] text-gray-500 uppercase mb-1">Open Source Stack</div>
                  <div className="text-[10px] text-gray-200">
                    {repoStack.repos_total || 0} curated repos
                  </div>
                  <div className="text-[8px] text-gray-500 mt-0.5">
                    {repoStack.installed_total || 0} installed / {repoStack.missing_total || 0} pending
                  </div>
                </div>
                <div className="bg-black/20 rounded-lg p-2 border border-white/5">
                  <div className="text-[8px] text-gray-500 uppercase mb-1">Formal Agent Roster</div>
                  <div className="text-[10px] text-gray-200 truncate">
                    {agentRoster.join(" • ") || "syncing"}
                  </div>
                </div>
              </div>

              {repoNext.length > 0 && (
                <div className="mt-2 space-y-1.5">
                  {repoNext.map((item) => (
                    <div key={item.id} className="bg-black/20 rounded-lg px-2.5 py-2 border border-white/5">
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-[10px] text-cyan-200">{item.id}</div>
                        <div className="text-[8px] uppercase text-gray-500">{item.owner_agent}</div>
                      </div>
                      <div className="text-[8px] text-gray-500 mt-0.5">
                        {item.category}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="text-[10px] text-gray-600 bg-black/20 rounded-lg px-3 py-2 border border-white/5">
              Building local transcript-backed brain memory from the Ai_Brain corpus.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
