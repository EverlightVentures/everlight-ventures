import React from "react"

export default function MetricCard({ label, value, sub, color = "text-white", trend, icon }) {
  return (
    <div className="card relative overflow-hidden group">
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent pointer-events-none" />
      <div className="absolute -top-8 -right-8 w-24 h-24 bg-gradient-to-br from-white/[0.02] to-transparent rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="relative flex items-start justify-between">
        <div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">{label}</span>
          <div className={`font-mono text-xl font-bold ${color} mt-0.5`}>{value}</div>
          {sub && <span className="text-[10px] text-gray-600">{sub}</span>}
        </div>
        {trend != null && (
          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${trend >= 0 ? "bg-green-400/10 text-green-400" : "bg-red-400/10 text-red-400"}`}>
            {trend >= 0 ? "+" : ""}{trend}%
          </span>
        )}
      </div>
    </div>
  )
}
