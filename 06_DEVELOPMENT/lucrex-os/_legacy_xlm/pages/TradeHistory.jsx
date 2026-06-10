import React, { useState, useEffect } from "react"
import { useApi, formatUSD } from "../hooks"

function WinLossBadge({ result }) {
  const isWin = result === "win"
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${isWin ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
      {isWin ? "W" : "L"}
    </span>
  )
}

function DayCard({ day }) {
  const [expanded, setExpanded] = useState(false)
  const pnlColor = day.pnl >= 0 ? "text-green-400" : "text-red-400"
  const pnlBg = day.pnl >= 0 ? "border-green-500/20" : "border-red-500/20"

  return (
    <div className={`bg-white/[0.03] rounded-lg border ${pnlBg} overflow-hidden`}>
      {/* Day header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-white">{day.date}</span>
          <span className="text-xs text-gray-500">{day.trade_count} trades</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-gray-400">{day.wins}W / {day.losses}L</span>
          <span className="text-xs text-gray-500">{day.win_rate}%</span>
          <span className={`text-sm font-mono font-bold ${pnlColor}`}>
            {day.pnl >= 0 ? "+" : ""}{formatUSD(day.pnl)}
          </span>
          <span className="text-gray-600 text-xs">{expanded ? "^" : "v"}</span>
        </div>
      </button>

      {/* Expanded trade list */}
      {expanded && (
        <div className="border-t border-white/[0.04]">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-600 border-b border-white/[0.04]">
                <th className="px-3 py-1.5 text-left">Time</th>
                <th className="px-3 py-1.5 text-left">Side</th>
                <th className="px-3 py-1.5 text-right">Entry</th>
                <th className="px-3 py-1.5 text-right">Exit</th>
                <th className="px-3 py-1.5 text-center">Result</th>
                <th className="px-3 py-1.5 text-right">P&L</th>
                <th className="px-3 py-1.5 text-right">Fees</th>
                <th className="px-3 py-1.5 text-right">Duration</th>
                <th className="px-3 py-1.5 text-left">Exit Reason</th>
              </tr>
            </thead>
            <tbody>
              {day.trades.map((t, i) => (
                <tr key={i} className="border-b border-white/[0.02] hover:bg-white/[0.02]">
                  <td className="px-3 py-1.5 text-gray-300 font-mono">{t.time}</td>
                  <td className="px-3 py-1.5">
                    <span className={t.side === "long" ? "text-green-400" : "text-red-400"}>
                      {t.side}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-right text-gray-300 font-mono">${t.entry_price}</td>
                  <td className="px-3 py-1.5 text-right text-gray-300 font-mono">${t.exit_price}</td>
                  <td className="px-3 py-1.5 text-center"><WinLossBadge result={t.result} /></td>
                  <td className={`px-3 py-1.5 text-right font-mono font-bold ${t.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {t.pnl >= 0 ? "+" : ""}{formatUSD(t.pnl)}
                  </td>
                  <td className="px-3 py-1.5 text-right text-gray-500 font-mono">{formatUSD(t.fees)}</td>
                  <td className="px-3 py-1.5 text-right text-gray-500">{t.duration_min ? `${t.duration_min}m` : "-"}</td>
                  <td className="px-3 py-1.5 text-gray-500 truncate max-w-[120px]">{t.exit_reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default function TradeHistory() {
  const [month, setMonth] = useState("")
  const url = month ? `/api/trades/history?month=${month}` : "/api/trades/history"
  const data = useApi(url, 30000)

  if (!data) return <div className="text-gray-500 p-8">Loading trade history...</div>

  const { days = [], paper_trades = [], summary = {}, months = [] } = data

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">Trade History</h2>
          <p className="text-xs text-gray-500">Midnight-to-midnight PT. Real trades only.</p>
        </div>
        {/* Month filter */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setMonth("")}
            className={`px-3 py-1 rounded text-xs ${!month ? "bg-amber-400/20 text-amber-400" : "bg-white/5 text-gray-400 hover:text-white"}`}
          >
            All
          </button>
          {months.map(m => (
            <button
              key={m}
              onClick={() => setMonth(m)}
              className={`px-3 py-1 rounded text-xs ${month === m ? "bg-amber-400/20 text-amber-400" : "bg-white/5 text-gray-400 hover:text-white"}`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: "Trades", value: summary.total_trades },
          { label: "Win Rate", value: `${summary.win_rate}%` },
          { label: "Wins", value: summary.total_wins },
          { label: "Losses", value: summary.total_losses },
          { label: "Net P&L", value: formatUSD(summary.total_pnl), color: summary.total_pnl >= 0 ? "text-green-400" : "text-red-400" },
        ].map(s => (
          <div key={s.label} className="bg-white/[0.03] rounded-lg p-3 text-center">
            <div className="text-[10px] text-gray-500 uppercase tracking-wider">{s.label}</div>
            <div className={`text-lg font-bold ${s.color || "text-white"}`}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Day cards */}
      <div className="space-y-2">
        {days.slice().reverse().map(day => (
          <DayCard key={day.date} day={day} />
        ))}
      </div>

      {/* Paper trades section */}
      {paper_trades.length > 0 && (
        <div className="mt-6 pt-4 border-t border-white/[0.06]">
          <h3 className="text-sm font-bold text-gray-400 mb-2">Paper / Ghost Trades (NOT included in P&L)</h3>
          <div className="text-xs text-gray-600 space-y-1">
            {paper_trades.map(pd => (
              <div key={pd.date}>{pd.date}: {pd.count} paper trades</div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
