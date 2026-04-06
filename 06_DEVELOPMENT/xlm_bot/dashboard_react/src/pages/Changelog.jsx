import React, { useState } from "react"
import { useApi } from "../hooks"

const CATEGORY_COLORS = {
  deploy: "bg-blue-500/20 text-blue-400",
  bot: "bg-green-500/20 text-green-400",
  pipeline: "bg-purple-500/20 text-purple-400",
  credentials: "bg-yellow-500/20 text-yellow-400",
  dashboard: "bg-cyan-500/20 text-cyan-400",
  fix: "bg-red-500/20 text-red-400",
  update: "bg-gray-500/20 text-gray-400",
}

function UpdateEntry({ update }) {
  const colorClass = CATEGORY_COLORS[update.category] || CATEGORY_COLORS.update
  return (
    <div className="flex gap-3 py-2 border-b border-white/[0.03] last:border-0">
      <div className="text-xs text-gray-500 font-mono w-20 flex-shrink-0 pt-0.5">{update.time}</div>
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${colorClass}`}>
            {update.category}
          </span>
          <span className="text-sm text-white">{update.summary}</span>
        </div>
        {update.details && (
          <p className="text-xs text-gray-500 mt-1">{update.details}</p>
        )}
        {update.files && update.files.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {update.files.map((f, i) => (
              <span key={i} className="text-[10px] px-1.5 py-0.5 bg-white/[0.04] rounded text-gray-500 font-mono">
                {typeof f === "string" ? f : JSON.stringify(f)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function Changelog() {
  const [view, setView] = useState("week") // today | week | month
  const endpoints = {
    today: "/api/changelog/today",
    week: "/api/changelog",
    month: `/api/changelog?month=${new Date().toISOString().slice(0, 7)}`,
  }
  const data = useApi(endpoints[view], 30000)

  if (!data) return <div className="text-gray-500 p-8">Loading changelog...</div>

  const { days = [], total_updates = 0 } = data

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">Changelog</h2>
          <p className="text-xs text-gray-500">{total_updates} updates logged</p>
        </div>
        <div className="flex items-center gap-2">
          {["today", "week", "month"].map(v => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-1 rounded text-xs capitalize ${view === v ? "bg-amber-400/20 text-amber-400" : "bg-white/5 text-gray-400 hover:text-white"}`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {/* Day groups */}
      {days.length === 0 ? (
        <div className="text-center text-gray-600 py-12">No updates for this period.</div>
      ) : (
        <div className="space-y-4">
          {days.slice().reverse().map(day => (
            <div key={day.date} className="bg-white/[0.03] rounded-lg border border-white/[0.06] overflow-hidden">
              <div className="px-4 py-2 bg-white/[0.02] border-b border-white/[0.04] flex items-center justify-between">
                <span className="text-sm font-medium text-white">{day.date}</span>
                <span className="text-[10px] text-gray-500">{day.updates.length} updates</span>
              </div>
              <div className="px-4 py-2">
                {day.updates.map((u, i) => (
                  <UpdateEntry key={i} update={u} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
