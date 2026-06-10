import React, { useMemo } from "react"
import { useApi, timeAgo } from "../hooks"

const FUNNEL_STAGES = [
  { key: "visitors", label: "Visitors", color: "bg-gray-500", text: "text-gray-300" },
  { key: "leads", label: "Leads", color: "bg-blue-500", text: "text-blue-300" },
  { key: "qualified", label: "Qualified", color: "bg-cyan-500", text: "text-cyan-300" },
  { key: "outreach", label: "Outreach", color: "bg-amber-500", text: "text-amber-300" },
  { key: "response", label: "Response", color: "bg-green-500", text: "text-green-300" },
  { key: "deal", label: "Deal", color: "bg-amber-400", text: "text-amber-200" },
]

const SOURCE_COLORS = {
  inbound: "bg-green-400/10 text-green-300",
  product_hunt: "bg-orange-400/10 text-orange-300",
  hacker_news: "bg-amber-400/10 text-amber-300",
  linkedin: "bg-blue-400/10 text-blue-300",
  referral: "bg-purple-400/10 text-purple-300",
  cold_outreach: "bg-gray-400/10 text-gray-300",
  other: "bg-gray-400/10 text-gray-300",
}

export default function Funnel() {
  const { data, error } = useApi("/api/broker/stats", 30000)

  const funnel = data?.funnel || {}
  const stages = FUNNEL_STAGES.map(s => ({ ...s, count: funnel[s.key] ?? (data?.[s.key] ?? 0) }))
  const maxCount = Math.max(...stages.map(s => s.count), 1)

  const sources = data?.lead_sources || data?.sources || {}
  const sourceEntries = Object.entries(sources).sort((a, b) => b[1] - a[1])
  const totalLeads = sourceEntries.reduce((sum, [, v]) => sum + v, 0) || 1

  const recentLeads = data?.recent_leads || data?.recent_activity || []

  if (!data && !error) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="card h-48 flex items-center justify-center"><div className="text-[10px] text-gray-600 tracking-widest">Loading Funnel...</div></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-amber-400 tracking-wider">FUNNEL</h1>
          <p className="text-xs text-gray-500 mt-1">Lead Funnel Analytics and Conversion Tracking</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${error ? "bg-red-400" : "bg-green-400"} animate-pulse`} />
          <span className="text-[9px] text-gray-500 font-mono">30s refresh</span>
        </div>
      </div>

      {error && (
        <div className="card border border-red-400/20 bg-red-400/[0.03]">
          <div className="text-[10px] text-red-400">API connection issue</div>
          <div className="text-[9px] text-gray-600 mt-0.5">{error}</div>
        </div>
      )}

      {/* Visual Funnel */}
      <div className="card">
        <div className="text-sm font-semibold text-amber-400/80 uppercase tracking-wider mb-6">Conversion Funnel</div>
        <div className="space-y-3">
          {stages.map((stage, i) => {
            const pct = maxCount > 0 ? (stage.count / maxCount) * 100 : 0
            const widthPct = Math.max(pct, 5)
            const prev = i > 0 ? stages[i - 1].count : 0
            const convRate = prev > 0 ? ((stage.count / prev) * 100).toFixed(1) : null

            return (
              <div key={stage.key} className="flex items-center gap-3">
                <div className="w-20 text-right">
                  <div className="text-[10px] text-gray-400 uppercase tracking-wider">{stage.label}</div>
                </div>
                <div className="flex-1 relative">
                  <div className="h-10 bg-white/[0.02] rounded-lg overflow-hidden flex items-center" style={{ width: "100%" }}>
                    <div
                      className={`h-full ${stage.color} opacity-60 rounded-lg transition-all duration-700 relative`}
                      style={{ width: `${widthPct}%` }}
                    />
                  </div>
                  <div className="absolute inset-0 flex items-center px-3 justify-between pointer-events-none">
                    <span className="font-mono text-sm font-bold text-white drop-shadow-lg">{stage.count}</span>
                    {convRate !== null && (
                      <span className="text-[9px] text-gray-400 bg-black/40 px-1.5 py-0.5 rounded">{convRate}% from {stages[i - 1].label.toLowerCase()}</span>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Funnel arrows */}
        <div className="flex justify-center mt-4 gap-1">
          {stages.map((s, i) => (
            <React.Fragment key={s.key}>
              <div className={`w-3 h-3 rounded-full ${s.color} opacity-60`} />
              {i < stages.length - 1 && <div className="text-[10px] text-gray-600 self-center">--&gt;</div>}
            </React.Fragment>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Lead Source Breakdown */}
        <div className="card">
          <div className="text-sm font-semibold text-amber-400/80 uppercase tracking-wider mb-4">Lead Sources</div>
          {sourceEntries.length === 0 ? (
            <div className="text-center py-6 text-gray-600 text-xs">No source data available</div>
          ) : (
            <div className="space-y-2">
              {sourceEntries.map(([source, count]) => {
                const pct = ((count / totalLeads) * 100).toFixed(1)
                const color = SOURCE_COLORS[source] || SOURCE_COLORS.other
                return (
                  <div key={source} className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${color} w-28 text-center`}>
                      {source.replace(/_/g, " ")}
                    </span>
                    <div className="flex-1 h-2 bg-white/[0.03] rounded-full overflow-hidden">
                      <div className="h-full bg-amber-400/50 rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="font-mono text-[10px] text-gray-400 w-8 text-right">{count}</span>
                    <span className="text-[9px] text-gray-600 w-10 text-right">{pct}%</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Recent Lead Activity */}
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b border-white/[0.04]">
            <div className="text-sm font-semibold text-amber-400/80 uppercase tracking-wider">Recent Activity</div>
          </div>
          <div className="max-h-[350px] overflow-y-auto">
            {recentLeads.length === 0 ? (
              <div className="text-center py-8 text-gray-600 text-xs">No recent activity</div>
            ) : (
              recentLeads.map((lead, i) => (
                <div key={lead.id || i} className="px-4 py-2.5 border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-amber-400/50" />
                      <span className="text-[11px] text-gray-300 font-medium">{lead.name || lead.company || "Lead"}</span>
                    </div>
                    <span className="text-[9px] text-gray-600 font-mono">{lead.timestamp || lead.created_at ? timeAgo(lead.timestamp || lead.created_at) : "--"}</span>
                  </div>
                  <div className="ml-4 text-[10px] text-gray-500 mt-0.5">
                    {lead.action || lead.stage || "--"}
                    {lead.source && <span className="ml-2 text-gray-600">via {lead.source.replace(/_/g, " ")}</span>}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
