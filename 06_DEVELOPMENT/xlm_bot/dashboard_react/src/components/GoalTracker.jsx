import React from "react"
import { useApi, formatUSD } from "../hooks"

function GoalBar({ label, current, goal, color = "amber" }) {
  const pct = goal > 0 ? Math.min(100, Math.max(-100, (current / goal) * 100)) : 0
  const isNeg = current < 0
  const colors = {
    amber: { bar: "from-amber-400 to-orange-500", glow: "shadow-amber-500/20", text: "text-amber-400" },
    green: { bar: "from-green-400 to-emerald-500", glow: "shadow-green-500/20", text: "text-green-400" },
    blue: { bar: "from-blue-400 to-cyan-500", glow: "shadow-blue-500/20", text: "text-blue-400" },
  }
  const c = colors[color] || colors.amber
  return (
    <div className="flex-1">
      <div className="flex justify-between items-center mb-1">
        <span className="text-[9px] uppercase tracking-wider text-gray-500">{label}</span>
        <span className={`text-[9px] font-mono ${c.text}`}>{formatUSD(current)} / {formatUSD(goal)}</span>
      </div>
      <div className="h-2.5 bg-gray-800/50 rounded-full overflow-hidden relative">
        {isNeg && <div className="absolute inset-y-0 right-0 bg-red-500/30 rounded-full" style={{ width: `${Math.min(100, Math.abs(pct))}%` }} />}
        {!isNeg && <div className={`h-full rounded-full bg-gradient-to-r ${c.bar} shadow-lg ${c.glow} transition-all duration-500`} style={{ width: `${Math.max(0, pct)}%` }} />}
        {pct >= 100 && <div className="absolute inset-0 bg-green-400/10 rounded-full animate-pulse" />}
      </div>
      <div className="text-right mt-0.5">
        <span className={`text-[10px] font-mono font-bold ${pct >= 100 ? "text-green-400" : isNeg ? "text-red-400" : c.text}`}>
          {pct >= 100 ? "GOAL HIT" : `${pct.toFixed(0)}%`}
        </span>
      </div>
    </div>
  )
}

export default function GoalTracker() {
  const { data } = useApi("/goals", 10000)
  if (!data || data.error) return null
  const { daily_min_goal, daily_ideal_goal, daily_pnl, loss_debt_today, weekly_min_goal, weekly_pnl, monthly_min_goal, monthly_pnl } = data
  return (
    <div className="card border border-white/5 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-amber-400/30 to-transparent" />
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-amber-400 to-orange-600 flex items-center justify-center text-[10px] font-black text-black">$</div>
          <span className="text-xs font-medium">P&L Goals</span>
        </div>
        {loss_debt_today > 0 && <span className="text-[9px] px-2 py-0.5 rounded-full bg-red-400/10 text-red-400 border border-red-400/20">+${loss_debt_today.toFixed(2)} loss debt</span>}
      </div>
      <div className="flex gap-4">
        <GoalBar label="Daily Min" current={daily_pnl} goal={daily_min_goal} color="amber" />
        <GoalBar label="Weekly" current={weekly_pnl} goal={weekly_min_goal} color="green" />
        <GoalBar label="Monthly" current={monthly_pnl} goal={monthly_min_goal} color="blue" />
      </div>
      {daily_ideal_goal > 0 && (
        <div className="mt-2 pt-2 border-t border-white/5">
          <GoalBar label="Daily Ideal ($100+)" current={daily_pnl} goal={daily_ideal_goal} color="amber" />
        </div>
      )}
    </div>
  )
}
