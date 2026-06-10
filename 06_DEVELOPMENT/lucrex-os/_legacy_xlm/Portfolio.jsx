import React, { useState, useMemo } from "react"
import { useApi, formatUSD, formatTime } from "./hooks"
import TradeReasonBanner from "./components/TradeReasonBanner"
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  ComposedChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, CartesianGrid, ReferenceLine, ReferenceArea, Legend, PieChart, Pie
} from "recharts"

function StatCard({ label, value, color = "text-white", sub }) {
  return (
    <div className="bg-white/[0.03] rounded-xl p-4 text-center relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent pointer-events-none" />
      <div className="relative">
        <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">{label}</div>
        <div className={`font-mono text-xl font-bold ${color}`}>{value}</div>
        {sub && <div className="text-[10px] text-gray-600 mt-0.5">{sub}</div>}
      </div>
    </div>
  )
}

function EquityTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d) return null
  return (
    <div className="chart-tooltip">
      <div className="text-[10px] text-gray-400 mb-1">{d.label || d.ts?.slice(5, 16)}</div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs font-mono">
        <span className="text-gray-500">Equity</span>
        <span className={d.equity >= d.startEquity ? "text-green-400" : "text-red-400"}>${d.equity?.toFixed(2)}</span>
        {d.pnl != null && <><span className="text-gray-500">Trade</span><span className={d.pnl >= 0 ? "text-green-400" : "text-red-400"}>{formatUSD(d.pnl)}</span></>}
        {d.rsi != null && <><span className="text-gray-500">RSI</span><span>{d.rsi?.toFixed(1)}</span></>}
        {d.ema8 != null && <><span className="text-gray-500">EMA8</span><span>${d.ema8?.toFixed(2)}</span></>}
        {d.ema21 != null && <><span className="text-gray-500">EMA21</span><span>${d.ema21?.toFixed(2)}</span></>}
        {d.type && <><span className="text-gray-500">Event</span><span className="text-amber-400">{d.type}</span></>}
      </div>
    </div>
  )
}

function DailyTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="chart-tooltip">
      <div className="text-[10px] text-gray-400">{d.date}</div>
      <div className="font-mono text-sm">
        P&L: <span className={d.pnl >= 0 ? "text-green-400" : "text-red-400"}>{formatUSD(d.pnl)}</span>
      </div>
      <div className="text-[10px] text-gray-500">{d.trades} trades ({d.wins}W/{d.losses}L)</div>
    </div>
  )
}

// Calculate EMA
function calcEMA(data, key, period) {
  const k = 2 / (period + 1)
  let ema = data[0]?.[key] || 0
  return data.map((d, i) => {
    if (i === 0) return ema
    ema = d[key] * k + ema * (1 - k)
    return ema
  })
}

// Calculate RSI on equity curve
function calcRSI(data, key, period = 14) {
  const result = []
  let avgGain = 0, avgLoss = 0
  for (let i = 0; i < data.length; i++) {
    if (i === 0) { result.push(50); continue }
    const change = (data[i][key] || 0) - (data[i - 1][key] || 0)
    const gain = change > 0 ? change : 0
    const loss = change < 0 ? -change : 0
    if (i <= period) {
      avgGain = (avgGain * (i - 1) + gain) / i
      avgLoss = (avgLoss * (i - 1) + loss) / i
    } else {
      avgGain = (avgGain * (period - 1) + gain) / period
      avgLoss = (avgLoss * (period - 1) + loss) / period
    }
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
    result.push(100 - (100 / (1 + rs)))
  }
  return result
}

export default function Portfolio() {
  const { data } = useApi("/history", 30000)
  const [view, setView] = useState("overview")

  // Build equity curve with indicators
  const equityData = useMemo(() => {
    if (!data?.pnl_curve?.length) return []
    const startEquity = 485 // approximate starting balance
    let equity = startEquity
    const points = data.pnl_curve.map((p, i) => {
      equity += p.pnl
      return {
        ts: p.ts,
        label: p.ts?.slice(5, 16),
        equity: Math.round(equity * 100) / 100,
        cumulative: p.cumulative,
        pnl: p.pnl,
        startEquity,
        type: p.pnl > 0 ? "WIN" : p.pnl < 0 ? "LOSS" : "FLAT",
        isWin: p.pnl > 0,
        isLoss: p.pnl < 0,
      }
    })

    // Add EMAs
    const ema8 = calcEMA(points, "equity", Math.min(8, points.length))
    const ema21 = calcEMA(points, "equity", Math.min(21, points.length))
    const rsi = calcRSI(points, "equity", Math.min(14, points.length))

    return points.map((p, i) => ({
      ...p,
      ema8: Math.round(ema8[i] * 100) / 100,
      ema21: Math.round(ema21[i] * 100) / 100,
      rsi: Math.round(rsi[i] * 10) / 10,
      // Markers for entries/exits
      winMarker: p.pnl > 0 ? p.equity : null,
      lossMarker: p.pnl < 0 ? p.equity : null,
    }))
  }, [data])

  if (!data) return <div className="text-center py-12 text-gray-600">Loading portfolio data...</div>

  const { trades, daily, by_strategy, pnl_curve, summary } = data
  const s = summary || {}

  // Win/Loss distribution for pie chart
  const pieData = [
    { name: "Wins", value: s.wins || 0, fill: "#00e676" },
    { name: "Losses", value: s.losses || 0, fill: "#ff1744" },
  ]

  // Strategy breakdown for pie chart
  const stratPie = Object.entries(by_strategy || {}).map(([name, stats]) => ({
    name: name.replace(/_/g, " "),
    value: stats.trades,
    fill: ["#448aff", "#b388ff", "#ffd740", "#00e676", "#ff1744", "#00bcd4"][
      Object.keys(by_strategy).indexOf(name) % 6
    ],
  }))

  const views = [
    { id: "overview", label: "Overview" },
    { id: "equity", label: "Equity Deep Dive" },
    { id: "trades", label: "All Trades" },
    { id: "strategies", label: "By Strategy" },
  ]

  const eqMin = equityData.length ? Math.min(...equityData.map(d => Math.min(d.equity, d.ema21 || d.equity))) * 0.998 : 0
  const eqMax = equityData.length ? Math.max(...equityData.map(d => Math.max(d.equity, d.ema8 || d.equity))) * 1.002 : 500

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-700 flex items-center justify-center text-lg font-bold shadow-lg shadow-green-500/20">$</div>
          <div>
            <div className="text-lg font-semibold">Portfolio Analytics</div>
            <div className="text-xs text-gray-500">
              {s.first_trade || "?"} to {s.last_trade || "?"} -- {s.trading_days || 0} trading days, {s.total_trades || 0} trades
            </div>
          </div>
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {views.map(v => (
            <button key={v.id} onClick={() => setView(v.id)}
              className={`px-3 py-1.5 rounded-full text-[11px] font-medium transition-all ${
                view === v.id ? "bg-amber-400/20 text-amber-400 border border-amber-400/30 shadow-sm shadow-amber-400/10"
                  : "bg-white/5 text-gray-500 border border-transparent hover:text-gray-300"
              }`}>{v.label}</button>
          ))}
        </div>
      </div>

      {/* Live Trade Status */}
      <TradeReasonBanner />

      {/* Summary Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        <StatCard label="Total P&L" value={formatUSD(s.total_pnl)} color={s.total_pnl >= 0 ? "text-green-400" : "text-red-400"} />
        <StatCard label="Win Rate" value={`${s.win_rate || 0}%`} color={s.win_rate >= 50 ? "text-green-400" : "text-amber-400"} />
        <StatCard label="Total Trades" value={s.total_trades || 0} sub={`${s.wins || 0}W / ${s.losses || 0}L`} />
        <StatCard label="Avg Win" value={formatUSD(s.avg_win)} color="text-green-400" />
        <StatCard label="Avg Loss" value={formatUSD(s.avg_loss)} color="text-red-400" />
        <StatCard label="Best Trade" value={formatUSD(s.best_trade)} color="text-green-400" />
        <StatCard label="Worst Trade" value={formatUSD(s.worst_trade)} color="text-red-400" />
        <StatCard label="Best Day" value={formatUSD(s.best_day)} color="text-green-400" />
      </div>

      {(view === "overview" || view === "equity") && (
        <>
          {/* Main Equity Chart with Indicators */}
          <div className="card relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-blue-500/[0.03] to-transparent rounded-bl-full" />
            <div className="flex justify-between items-center mb-3">
              <div>
                <span className="text-sm font-medium">Portfolio Equity</span>
                <span className="text-[10px] text-gray-500 ml-2">with EMA(8), EMA(21), entries & exits</span>
              </div>
              <div className="flex gap-3 text-[10px]">
                <span className="text-blue-400">-- Equity</span>
                <span className="text-amber-400">-- EMA8</span>
                <span className="text-purple-400">-- EMA21</span>
                <span className="text-green-400">* Win</span>
                <span className="text-red-400">* Loss</span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={equityData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#448aff" stopOpacity={0.25} />
                    <stop offset="50%" stopColor="#448aff" stopOpacity={0.05} />
                    <stop offset="95%" stopColor="#448aff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 6" stroke="#1a1a2e" />
                <XAxis dataKey="label" tick={{ fontSize: 9, fill: "#444" }} tickLine={false} axisLine={{ stroke: "#1e1e2e" }} />
                <YAxis domain={[eqMin, eqMax]} tick={{ fontSize: 10, fill: "#555" }} tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} width={55} />
                <Tooltip content={<EquityTooltip />} />
                {/* EMA bands */}
                <Line type="monotone" dataKey="ema21" stroke="#b388ff" strokeWidth={1} dot={false} strokeDasharray="4 2" opacity={0.6} />
                <Line type="monotone" dataKey="ema8" stroke="#ffd740" strokeWidth={1} dot={false} opacity={0.7} />
                {/* Main equity line */}
                <Area type="monotone" dataKey="equity" stroke="#448aff" strokeWidth={2.5} fill="url(#eqGrad)" dot={false}
                  activeDot={{ r: 4, fill: "#448aff", stroke: "#0a0a0f", strokeWidth: 2 }} />
                {/* Win markers */}
                <Scatter dataKey="winMarker" fill="#00e676" shape={(props) => {
                  if (!props.cy || !props.payload?.winMarker) return null
                  return <circle cx={props.cx} cy={props.cy} r={5} fill="#00e676" stroke="#0a0a0f" strokeWidth={2} opacity={0.9} />
                }} />
                {/* Loss markers */}
                <Scatter dataKey="lossMarker" fill="#ff1744" shape={(props) => {
                  if (!props.cy || !props.payload?.lossMarker) return null
                  return <circle cx={props.cx} cy={props.cy} r={5} fill="#ff1744" stroke="#0a0a0f" strokeWidth={2} opacity={0.9} />
                }} />
                {/* Starting equity reference */}
                <ReferenceLine y={equityData[0]?.startEquity} stroke="#333" strokeDasharray="6 3" label={{ value: "Start", fill: "#555", fontSize: 9, position: "right" }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* RSI Chart for Equity */}
          {view === "equity" && equityData.length > 5 && (
            <div className="card">
              <div className="text-sm font-medium mb-2">Portfolio RSI (14-period)</div>
              <ResponsiveContainer width="100%" height={120}>
                <AreaChart data={equityData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="rsiGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#b388ff" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#b388ff" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="2 6" stroke="#1a1a2e" />
                  <XAxis dataKey="label" tick={{ fontSize: 8, fill: "#444" }} tickLine={false} />
                  <YAxis domain={[0, 100]} ticks={[20, 50, 80]} tick={{ fontSize: 9, fill: "#555" }} tickLine={false} axisLine={false} width={30} />
                  <ReferenceArea y1={70} y2={100} fill="#ff1744" fillOpacity={0.05} />
                  <ReferenceArea y1={0} y2={30} fill="#00e676" fillOpacity={0.05} />
                  <ReferenceLine y={70} stroke="#ff1744" strokeDasharray="3 3" strokeOpacity={0.4} />
                  <ReferenceLine y={30} stroke="#00e676" strokeDasharray="3 3" strokeOpacity={0.4} />
                  <Area type="monotone" dataKey="rsi" stroke="#b388ff" strokeWidth={1.5} fill="url(#rsiGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Daily P&L */}
            <div className="card">
              <div className="text-sm font-medium mb-3">Daily P&L</div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={daily} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="2 6" stroke="#1a1a2e" />
                  <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#444" }} tickFormatter={v => v?.slice(5)} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: "#555" }} tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} />
                  <Tooltip content={<DailyTooltip />} />
                  <Bar dataKey="pnl" radius={[6, 6, 0, 0]}>
                    {daily.map((d, i) => (
                      <Cell key={i} fill={d.pnl >= 0 ? "#00e676" : "#ff1744"} opacity={0.85} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Win/Loss Pie + Strategy Pie */}
            <div className="card">
              <div className="text-sm font-medium mb-3">Distribution</div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-[10px] text-gray-500 text-center mb-1">Win/Loss</div>
                  <ResponsiveContainer width="100%" height={160}>
                    <PieChart>
                      <Pie data={pieData} cx="50%" cy="50%" innerRadius={35} outerRadius={60} paddingAngle={4} dataKey="value" stroke="none">
                        {pieData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                      </Pie>
                      <Tooltip formatter={(v, name) => [`${v} trades`, name]} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="text-center text-xs font-mono text-gray-400">{s.wins}W / {s.losses}L</div>
                </div>
                <div>
                  <div className="text-[10px] text-gray-500 text-center mb-1">By Strategy</div>
                  <ResponsiveContainer width="100%" height={160}>
                    <PieChart>
                      <Pie data={stratPie} cx="50%" cy="50%" innerRadius={35} outerRadius={60} paddingAngle={2} dataKey="value" stroke="none">
                        {stratPie.map((e, i) => <Cell key={i} fill={e.fill} />)}
                      </Pie>
                      <Tooltip formatter={(v, name) => [`${v} trades`, name]} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {view === "trades" && (
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800">
            <span className="text-sm font-medium">All Trades ({trades.length})</span>
          </div>
          <div className="max-h-[500px] overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-[#12121a]">
                <tr className="text-gray-500 uppercase text-[10px] border-b border-gray-800">
                  <th className="px-3 py-2 text-left">Date</th>
                  <th className="px-3 py-2 text-left">Dir</th>
                  <th className="px-3 py-2 text-left">Strategy</th>
                  <th className="px-3 py-2 text-left">Exit Reason</th>
                  <th className="px-3 py-2 text-right">P&L</th>
                  <th className="px-3 py-2 text-right">Cumulative</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t, i) => {
                  const cum = pnl_curve[i]?.cumulative || 0
                  return (
                    <tr key={i} className="border-b border-gray-800/30 hover:bg-white/[0.02] transition-colors">
                      <td className="px-3 py-2 font-mono text-gray-400">{t.exit_ts?.slice(5, 16)}</td>
                      <td className="px-3 py-2">
                        <span className={`font-bold uppercase text-[10px] px-1.5 py-0.5 rounded ${t.direction === "long" ? "bg-green-400/10 text-green-400" : "bg-red-400/10 text-red-400"}`}>{t.direction}</span>
                      </td>
                      <td className="px-3 py-2 text-gray-300">{t.strategy?.replace(/_/g, " ")}</td>
                      <td className="px-3 py-2 text-gray-500">{t.exit_reason?.replace(/_/g, " ")}</td>
                      <td className={`px-3 py-2 text-right font-mono font-medium ${t.pnl_usd >= 0 ? "text-green-400" : "text-red-400"}`}>
                        {formatUSD(t.pnl_usd)}
                      </td>
                      <td className={`px-3 py-2 text-right font-mono ${cum >= 0 ? "text-blue-400" : "text-orange-400"}`}>
                        {formatUSD(cum)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {view === "strategies" && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(by_strategy).sort((a, b) => b[1].trades - a[1].trades).map(([name, stats]) => {
            const wr = stats.trades > 0 ? Math.round(stats.wins / stats.trades * 100) : 0
            return (
              <div key={name} className="card relative overflow-hidden">
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-bl from-white/[0.02] to-transparent rounded-bl-full" />
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="text-sm font-semibold">{name.replace(/_/g, " ")}</div>
                    <div className="text-[10px] text-gray-500">{stats.trades} trades</div>
                  </div>
                  <span className={`font-mono text-lg font-bold ${stats.pnl >= 0 ? "text-green-400 glow-green" : "text-red-400 glow-red"}`}>
                    {formatUSD(stats.pnl)}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="bg-white/[0.03] rounded-lg py-1.5">
                    <div className="font-mono text-sm text-green-400">{stats.wins}</div>
                    <div className="text-[9px] text-gray-500">WINS</div>
                  </div>
                  <div className="bg-white/[0.03] rounded-lg py-1.5">
                    <div className="font-mono text-sm text-red-400">{stats.losses}</div>
                    <div className="text-[9px] text-gray-500">LOSSES</div>
                  </div>
                  <div className="bg-white/[0.03] rounded-lg py-1.5">
                    <div className={`font-mono text-sm ${wr >= 50 ? "text-green-400" : "text-amber-400"}`}>{wr}%</div>
                    <div className="text-[9px] text-gray-500">WIN RATE</div>
                  </div>
                </div>
                <div className="mt-3 h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-500" style={{
                    width: `${wr}%`,
                    background: `linear-gradient(90deg, ${wr >= 50 ? "#00e676" : "#ffd740"}, ${wr >= 60 ? "#00c853" : "#ff9100"})`,
                  }} />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
