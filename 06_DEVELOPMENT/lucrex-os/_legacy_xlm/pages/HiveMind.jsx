import React, { useState } from "react"
import { useApi, timeAgo } from "../hooks"

const SQUADS = [
  {
    name: "Claude Corp", leader: "Marcus Cole", color: "amber",
    teams: [
      { name: "Alpha", agents: [{ name: "Marcus Cole", role: "TL" }, { name: "Piper Reeves", role: "S1" }, { name: "Hammer Walsh", role: "S2" }, { name: "Cash Monroe", role: "B" }, { name: "Chart Dawson", role: "A" }] },
      { name: "Bravo", agents: [{ name: "Penny Voss", role: "TL" }, { name: "Justine Zhao", role: "S1" }, { name: "Cupid Vega", role: "S2" }, { name: "Rex Blackwell", role: "B" }, { name: "Filter Banks", role: "A" }] },
      { name: "Charlie", agents: [{ name: "Consult Lead", role: "TL" }, { name: "Scope Analyst", role: "S1" }, { name: "Proposal Writer", role: "S2" }, { name: "QA Reviewer", role: "B" }, { name: "Onboarder", role: "A" }] },
    ]
  },
  {
    name: "Gemini Ops", leader: "Major Dex", color: "blue",
    teams: [
      { name: "Delta", agents: [{ name: "Major Dex", role: "TL" }, { name: "Scout Harmon", role: "S1" }, { name: "Relay Kim", role: "S2" }, { name: "Patch Torres", role: "B" }, { name: "Intel Cross", role: "A" }] },
      { name: "Echo", agents: [{ name: "Surge Patel", role: "TL" }, { name: "Beacon Lee", role: "S1" }, { name: "Drift Okafor", role: "S2" }, { name: "Anchor Wu", role: "B" }, { name: "Pulse Diaz", role: "A" }] },
      { name: "Foxtrot", agents: [{ name: "Vanguard Nash", role: "TL" }, { name: "Recon Avery", role: "S1" }, { name: "Flare Quinn", role: "S2" }, { name: "Shield Ramos", role: "B" }, { name: "Orbit Chen", role: "A" }] },
    ]
  },
  {
    name: "Codex Labs", leader: "Forge", color: "green",
    teams: [
      { name: "Golf", agents: [{ name: "Forge", role: "TL" }, { name: "Syntax Moore", role: "S1" }, { name: "Kernel Ortiz", role: "S2" }, { name: "Stack Rivera", role: "B" }, { name: "Debug Sato", role: "A" }] },
      { name: "Hotel", agents: [{ name: "Pipeline Rex", role: "TL" }, { name: "Deploy Cruz", role: "S1" }, { name: "Schema Hall", role: "S2" }, { name: "Cache Nguyen", role: "B" }, { name: "Query Adams", role: "A" }] },
      { name: "India", agents: [{ name: "Architect Voss", role: "TL" }, { name: "Matrix Lane", role: "S1" }, { name: "Cipher Jr", role: "S2" }, { name: "Vector Blake", role: "B" }, { name: "Node Park", role: "A" }] },
    ]
  },
  {
    name: "Perplexity Intel", leader: "Cipher", color: "purple",
    teams: [
      { name: "Juliet", agents: [{ name: "Cipher", role: "TL" }, { name: "Lens Harper", role: "S1" }, { name: "Prism Young", role: "S2" }, { name: "Nexus Grant", role: "B" }, { name: "Apex Frost", role: "A" }] },
      { name: "Kilo", agents: [{ name: "Spectra Cole", role: "TL" }, { name: "Trace Walker", role: "S1" }, { name: "Signal Dunn", role: "S2" }, { name: "Omega Price", role: "B" }, { name: "Radar Kim", role: "A" }] },
      { name: "Lima", agents: [{ name: "Sentinel Gray", role: "TL" }, { name: "Cortex Bell", role: "S1" }, { name: "Synth Webb", role: "S2" }, { name: "Flux Morales", role: "B" }, { name: "Core Reeves", role: "A" }] },
    ]
  },
]

const COLOR_MAP = {
  amber: { border: "border-amber-400/30", bg: "bg-amber-400/5", text: "text-amber-400", dot: "bg-amber-400" },
  blue: { border: "border-blue-400/30", bg: "bg-blue-400/5", text: "text-blue-400", dot: "bg-blue-400" },
  green: { border: "border-green-400/30", bg: "bg-green-400/5", text: "text-green-400", dot: "bg-green-400" },
  purple: { border: "border-purple-400/30", bg: "bg-purple-400/5", text: "text-purple-400", dot: "bg-purple-400" },
}

const ROLE_LABELS = { TL: "Team Lead", S1: "Specialist", S2: "Specialist", B: "Verifier", A: "Assistant" }

export default function HiveMind() {
  const { data, error } = useApi("/api/django/hub-status", 30000)
  const [expandedSquad, setExpandedSquad] = useState(null)

  const activeAgents = data?.active_agents ?? 63
  const activeTeams = data?.active_teams ?? 12
  const recentActivity = data?.recent_activity || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-amber-400 tracking-wider">HIVE MIND</h1>
          <p className="text-xs text-gray-500 mt-1">Agent Roster and Fire Team Command</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${error ? "bg-red-400" : "bg-green-400"} animate-pulse`} />
          <span className="text-[9px] text-gray-500 font-mono">30s refresh</span>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Agents", value: "63", accent: "text-amber-400" },
          { label: "Fire Teams", value: "12", accent: "text-blue-400" },
          { label: "Squads", value: "4", accent: "text-green-400" },
          { label: "Buddy Pairs", value: "24", accent: "text-purple-400" },
        ].map(k => (
          <div key={k.label} className="card">
            <div className="text-[8px] uppercase tracking-widest text-gray-500">{k.label}</div>
            <div className={`font-mono text-2xl font-bold ${k.accent}`}>{k.value}</div>
          </div>
        ))}
      </div>

      {/* Squad Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {SQUADS.map((squad, si) => {
          const c = COLOR_MAP[squad.color]
          const isExpanded = expandedSquad === si
          return (
            <div key={squad.name} className={`card border ${c.border} ${c.bg} cursor-pointer transition-all`} onClick={() => setExpandedSquad(isExpanded ? null : si)}>
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className={`text-sm font-bold ${c.text} uppercase tracking-wider`}>{squad.name}</div>
                  <div className="text-[10px] text-gray-500">Led by {squad.leader}</div>
                </div>
                <div className="flex items-center gap-1">
                  <div className={`w-2 h-2 rounded-full ${c.dot} animate-pulse`} />
                  <span className="text-[9px] text-gray-500">{squad.teams.length} teams</span>
                  <span className="text-[10px] text-gray-600 ml-2">{isExpanded ? "[-]" : "[+]"}</span>
                </div>
              </div>

              {/* Team summary */}
              <div className="flex gap-2 flex-wrap">
                {squad.teams.map(team => (
                  <span key={team.name} className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${c.bg} ${c.text} border ${c.border}`}>
                    {team.name}
                  </span>
                ))}
              </div>

              {/* Expanded: show all agents */}
              {isExpanded && (
                <div className="mt-4 space-y-3">
                  {squad.teams.map(team => (
                    <div key={team.name} className="border-t border-white/[0.04] pt-3">
                      <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-2">Fire Team {team.name}</div>
                      <div className="space-y-1.5">
                        {team.agents.map(agent => (
                          <div key={agent.name} className="flex items-center gap-2 text-[11px]">
                            <div className={`w-1.5 h-1.5 rounded-full ${c.dot} opacity-70`} />
                            <span className="text-gray-300 font-medium w-32">{agent.name}</span>
                            <span className={`px-1.5 py-0.5 rounded text-[9px] ${c.bg} ${c.text}`}>{agent.role}</span>
                            <span className="text-[9px] text-gray-600">{ROLE_LABELS[agent.role]}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Recent Activity */}
      {recentActivity.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b border-white/[0.04]">
            <div className="text-sm font-semibold text-amber-400/80 uppercase tracking-wider">Recent Agent Activity</div>
          </div>
          <div className="max-h-[300px] overflow-y-auto">
            {recentActivity.map((act, i) => (
              <div key={i} className="px-4 py-2.5 border-b border-white/[0.02] flex items-center gap-3 text-[11px]">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-400/50 flex-shrink-0" />
                <span className="text-gray-300 font-medium">{act.agent || "Agent"}</span>
                <span className="text-gray-500 flex-1">{act.action || act.description || "--"}</span>
                <span className="text-[9px] text-gray-600 font-mono">{act.timestamp ? timeAgo(act.timestamp) : "--"}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
