import React, { useState, useMemo } from "react"
import { useApi, timeAgo } from "../hooks"

export default function HiveSessions() {
  const { data, error } = useApi("/api/django/sessions", 30000)
  const [expandedId, setExpandedId] = useState(null)
  const [filter, setFilter] = useState("all")

  const sessions = data?.sessions || data || []
  const sessionList = Array.isArray(sessions) ? sessions : []
  const totalSessions = data?.total ?? sessionList.length
  const todaySessions = data?.today ?? sessionList.filter(s => {
    if (!s.timestamp && !s.created_at) return false
    const d = new Date(s.timestamp || s.created_at)
    const now = new Date()
    return d.toDateString() === now.toDateString()
  }).length
  const avgDuration = data?.avg_duration ?? "--"

  const filtered = useMemo(() => {
    if (filter === "all") return sessionList
    return sessionList.filter(s => (s.status || "").toLowerCase() === filter)
  }, [sessionList, filter])

  if (!data && !error) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="grid grid-cols-3 gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="card"><div className="h-2 w-12 bg-white/[0.05] rounded mb-2" /><div className="h-6 w-16 bg-white/[0.08] rounded" /></div>
          ))}
        </div>
        <div className="card h-48 flex items-center justify-center"><div className="text-[10px] text-gray-600 tracking-widest">Loading Sessions...</div></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-amber-400 tracking-wider">HIVE SESSIONS</h1>
          <p className="text-xs text-gray-500 mt-1">Agent Session History and Analytics</p>
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

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Total Sessions</div>
          <div className="font-mono text-2xl font-bold text-amber-400">{totalSessions}</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Today</div>
          <div className="font-mono text-2xl font-bold text-green-400">{todaySessions}</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Avg Duration</div>
          <div className="font-mono text-2xl font-bold text-blue-400">{avgDuration}</div>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-1.5">
        {["all", "completed", "running", "failed"].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-full text-[11px] font-medium transition-all ${
              filter === f
                ? "bg-amber-400/20 text-amber-400 border border-amber-400/30"
                : "bg-white/[0.05] text-gray-500 hover:text-gray-300 hover:bg-white/[0.08]"
            }`}
          >
            {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Session List */}
      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="card text-center py-8 text-gray-600 text-xs">No sessions found</div>
        ) : (
          filtered.map((session, i) => {
            const id = session.session_id || session.id || i
            const isExpanded = expandedId === id
            const statusColor = (session.status || "completed") === "completed" ? "bg-green-400/10 text-green-300" :
              session.status === "running" ? "bg-blue-400/10 text-blue-300" :
              session.status === "failed" ? "bg-red-400/10 text-red-300" : "bg-gray-400/10 text-gray-300"

            return (
              <div
                key={id}
                className="card hover:border-white/[0.08] transition-colors cursor-pointer"
                onClick={() => setExpandedId(isExpanded ? null : id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${statusColor}`}>
                      {session.status || "completed"}
                    </span>
                    <div>
                      <div className="text-[11px] text-gray-200 font-medium">{session.query || session.title || "Session"}</div>
                      <div className="text-[9px] text-gray-500 mt-0.5">
                        {session.agents ? (Array.isArray(session.agents) ? session.agents.join(", ") : session.agents) : "No agents listed"}
                      </div>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-[9px] text-gray-500 font-mono">{session.timestamp || session.created_at ? timeAgo(session.timestamp || session.created_at) : "--"}</div>
                    <div className="text-[9px] text-gray-600">{session.duration || "--"}</div>
                  </div>
                </div>

                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-white/[0.04]">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[10px]">
                      <div>
                        <div className="text-gray-500 uppercase tracking-wider mb-1">Query</div>
                        <div className="text-gray-300">{session.query || "--"}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 uppercase tracking-wider mb-1">Outcome</div>
                        <div className="text-gray-300">{session.outcome || session.result || "--"}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 uppercase tracking-wider mb-1">Agents Involved</div>
                        <div className="text-gray-300">{session.agents ? (Array.isArray(session.agents) ? session.agents.join(", ") : session.agents) : "--"}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 uppercase tracking-wider mb-1">Session ID</div>
                        <div className="text-gray-400 font-mono">{session.session_id || session.id || "--"}</div>
                      </div>
                    </div>
                    {session.details && (
                      <div className="mt-3 p-2 rounded-lg bg-white/[0.02] text-[10px] text-gray-400 whitespace-pre-wrap">{session.details}</div>
                    )}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
