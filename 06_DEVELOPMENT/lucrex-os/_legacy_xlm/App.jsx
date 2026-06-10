import React, { useState, useEffect } from "react"
import { useApi, formatUSD, formatPrice, timeAgo } from "./hooks"
import Sidebar from "./components/Sidebar"
import PriceChart from "./PriceChart"
import DecisionFeed from "./DecisionFeed"
import StrategyIQ from "./StrategyIQ"
import Portfolio from "./Portfolio"
import ControlPanel from "./ControlPanel"
import Revenue from "./pages/Revenue"
import BrokerOS from "./pages/BrokerOS"
import BusinessOS from "./pages/BusinessOS"
import HiveSessions from "./pages/HiveSessions"
import Taskboard from "./pages/Taskboard"
import Funnel from "./pages/Funnel"
import HiveMind from "./pages/HiveMind"
import Reports from "./pages/Reports"
import Settings from "./pages/Settings"
import MarketIntel from "./pages/MarketIntel"
import TradeHistory from "./pages/TradeHistory"
import Changelog from "./pages/Changelog"
import TradingChat from "./components/TradingChat"
import MindsetPanel from "./components/MindsetPanel"
import TradeReportCard from "./components/TradeReportCard"
import AIAdvisor from "./components/AIAdvisor"
import MarketContextBar from "./components/MarketContextBar"
import TradingCharts from "./components/TradingCharts"

// -- Loading / Welcome Screen --
function SplashScreen({ onDone }) {
  const [phase, setPhase] = useState(0)
  useEffect(() => {
    const t1 = setTimeout(() => setPhase(1), 400)
    const t2 = setTimeout(() => setPhase(2), 1200)
    const t3 = setTimeout(() => setPhase(3), 2000)
    const t4 = setTimeout(() => onDone(), 2800)
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4) }
  }, [onDone])

  return (
    <div className="fixed inset-0 bg-[#0a0a0f] z-[100] flex items-center justify-center">
      <div className="absolute w-[400px] h-[400px] rounded-full bg-amber-500/[0.04] blur-[100px] animate-pulse" />
      <div className="absolute w-[300px] h-[300px] rounded-full bg-purple-500/[0.03] blur-[80px] animate-pulse" style={{ animationDelay: "1s" }} />

      <div className="relative text-center">
        {/* Logo mp4 icon */}
        <div className={`transition-all duration-700 ${phase >= 0 ? "opacity-100 scale-100" : "opacity-0 scale-50"}`}>
          <div className="w-20 h-20 mx-auto rounded-2xl overflow-hidden shadow-2xl shadow-amber-500/30 mb-6">
            <video autoPlay muted playsInline loop className="w-full h-full object-cover">
              <source src="/lucrex_logo.mp4" type="video/mp4" />
            </video>
          </div>
        </div>

        {/* Brand */}
        <div className={`transition-all duration-700 delay-200 ${phase >= 1 ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
          <div className="text-2xl font-bold tracking-[0.3em] bg-gradient-to-r from-amber-300 via-orange-400 to-amber-300 bg-clip-text text-transparent mb-0.5">
            LUCREX
          </div>
          <div className="text-[10px] tracking-[0.4em] text-gray-600">COMMAND CENTER</div>
          <div className="text-[9px] tracking-[0.15em] text-gray-700 italic mt-0.5">By Everlight Ventures</div>
        </div>

        {/* Tagline */}
        <div className={`mt-6 transition-all duration-700 delay-500 ${phase >= 2 ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
          <div className="text-xs text-gray-500 italic">The Mind Behind the Money</div>
          <div className="text-[10px] text-gray-700 mt-1">Everlight Ventures</div>
        </div>

        {/* Loading bar */}
        <div className={`mt-8 w-48 mx-auto transition-all duration-500 ${phase >= 1 ? "opacity-100" : "opacity-0"}`}>
          <div className="h-0.5 bg-gray-800 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-amber-400 to-orange-500 rounded-full transition-all duration-[1800ms] ease-out"
              style={{ width: phase >= 3 ? "100%" : phase >= 2 ? "70%" : "30%" }} />
          </div>
          <div className="text-[9px] text-gray-600 mt-2 font-mono">
            {phase < 2 ? "Connecting to Oracle..." : phase < 3 ? "Loading systems..." : "Ready"}
          </div>
        </div>
      </div>
    </div>
  )
}

// -- Header Bar --
function Header({ price, pnlToday, pnlClosed, pnlUnrealized, winRate, wins, losses, alive, position }) {
  return (
    <header className="h-14 bg-[#0a0a0f]/80 backdrop-blur-xl border-b border-white/[0.04] flex items-center justify-between px-5 flex-shrink-0">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${alive ? "bg-green-400 pulse-live" : "bg-red-500"}`} />
          <span className={`text-[10px] font-mono tracking-wider ${alive ? "text-green-400/80" : "text-red-400"}`}>{alive ? "ONLINE" : "OFFLINE"}</span>
        </div>
        {/* Position status */}
        {position ? (
          <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full border ${position.direction === "long" ? "border-green-400/30 bg-green-400/5" : "border-red-400/30 bg-red-400/5"}`}>
            <span className={`text-[10px] font-bold uppercase ${position.direction === "long" ? "text-green-400" : "text-red-400"}`}>{position.direction}</span>
            <span className={`font-mono text-[11px] font-bold ${pnlUnrealized >= 0 ? "text-green-400" : "text-red-400"}`}>{pnlUnrealized >= 0 ? "+" : ""}{formatUSD(pnlUnrealized)}</span>
            <span className="text-[8px] text-gray-500">{(position.entry_type || "").replace(/_/g, " ")}</span>
          </div>
        ) : (
          <span className="text-[10px] text-gray-500 px-2">SCANNING</span>
        )}
      </div>
      <div className="flex items-center gap-6">
        <div className="text-right">
          <div className="text-[8px] text-gray-600 tracking-widest">XLM</div>
          <div className="font-mono text-lg font-bold bg-gradient-to-r from-amber-300 to-amber-500 bg-clip-text text-transparent">{formatPrice(price)}</div>
        </div>
        <div className="text-right">
          <div className="text-[8px] text-gray-600 tracking-widest">DAY P&L</div>
          <div className={`font-mono text-xl font-black ${pnlToday >= 0 ? "text-green-400" : "text-red-400"}`}>{pnlToday >= 0 ? "+" : ""}{formatUSD(pnlToday)}</div>
          <div className="text-[8px] text-gray-600">closed {formatUSD(pnlClosed)} {pnlUnrealized !== 0 ? `+ open ${formatUSD(pnlUnrealized)}` : ""}</div>
        </div>
        <div className="text-right hidden md:block">
          <div className="text-[8px] text-gray-600 tracking-widest">RECORD</div>
          <div className="font-mono text-sm font-bold"><span className="text-green-400">{wins}W</span><span className="text-gray-600">/</span><span className="text-red-400">{losses}L</span> <span className="text-gray-500 text-xs">{winRate}%</span></div>
        </div>
      </div>
    </header>
  )
}

// ── Position Card ──
const STRATEGY_COLORS = {
  micro_sweep: { bg: "from-purple-500/20 to-purple-900/10", border: "border-purple-400", text: "text-purple-400" },
  breakout_retest: { bg: "from-blue-500/20 to-blue-900/10", border: "border-blue-400", text: "text-blue-400" },
  fib_retrace: { bg: "from-amber-500/20 to-amber-900/10", border: "border-amber-400", text: "text-amber-400" },
  pullback: { bg: "from-cyan-500/20 to-cyan-900/10", border: "border-cyan-400", text: "text-cyan-400" },
  default: { bg: "from-gray-500/20 to-gray-900/10", border: "border-gray-400", text: "text-gray-400" },
}

function PositionCard({ position, price, activeStrategy }) {
  const watching = activeStrategy?.watching
  if (!position) {
    return (
      <div className="card border-dashed border-gray-700/50">
        <div className="text-center py-3">
          <div className="text-xl opacity-15 mb-1">---</div>
          <div className="text-xs text-gray-500">No Position</div>
          {watching && (
            <div className="mt-2 px-2 py-1.5 rounded-lg bg-white/[0.03] text-left">
              <div className="text-[9px] uppercase text-amber-400/60 tracking-wider">Scanning</div>
              <div className="text-[11px] text-gray-400 mt-0.5">{watching.signal?.slice(0, 70)}</div>
            </div>
          )}
        </div>
      </div>
    )
  }
  const dir = position.direction || "?"
  const entry = Number(position.entry_price || 0)
  const size = position.size || 1
  const isLong = dir === "long"
  const pnlPct = entry > 0 && price > 0 ? (isLong ? (price - entry) / entry : (entry - price) / entry) * 100 : 0
  const pnlUsd = pnlPct / 100 * entry * size * 5000
  const strategy = activeStrategy?.strategy || "unknown"
  const sc = STRATEGY_COLORS[strategy] || STRATEGY_COLORS.default

  return (
    <div className={`card border-l-4 ${isLong ? "border-l-green-400" : "border-l-red-400"} relative overflow-hidden`}>
      <div className={`absolute top-0 right-0 left-0 h-7 bg-gradient-to-r ${sc.bg} opacity-50`} />
      <div className="relative">
        <div className="flex justify-between items-center mb-2">
          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${isLong ? "bg-green-400/10 text-green-400" : "bg-red-400/10 text-red-400"}`}>{dir} {size}x</span>
          <span className="text-[10px] text-gray-500">{timeAgo(position.entry_time)}</span>
        </div>
        <div className={`mb-2 px-2 py-1.5 rounded-lg bg-gradient-to-r ${sc.bg} border ${sc.border}/20`}>
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Strategy</div>
          <div className={`text-xs font-bold ${sc.text}`}>{strategy.replace(/_/g, " ").toUpperCase()}</div>
        </div>
        <div className="grid grid-cols-3 gap-3 text-center">
          <div><div className="text-[9px] text-gray-500">Entry</div><div className="font-mono text-xs">{formatPrice(entry)}</div></div>
          <div><div className="text-[9px] text-gray-500">Mark</div><div className="font-mono text-xs">{formatPrice(price)}</div></div>
          <div><div className="text-[9px] text-gray-500">uPnL</div><div className={`font-mono text-xs font-bold ${pnlUsd >= 0 ? "text-green-400" : "text-red-400"}`}>{formatUSD(pnlUsd)}</div></div>
        </div>
      </div>
    </div>
  )
}

// -- Error boundary for components that might crash --
class SafeRender extends React.Component {
  constructor(props) { super(props); this.state = { error: null } }
  static getDerivedStateFromError(error) { return { error: error.message } }
  render() {
    if (this.state.error) return (
      <div className="card border border-red-400/20 text-center py-4">
        <div className="text-[10px] text-red-400">Component error</div>
        <div className="text-[9px] text-gray-600 mt-1">{this.state.error}</div>
      </div>
    )
    return this.props.children
  }
}

// -- Trading Page --
function TradingPage({ status, candles, chartTf, chartPosition, events, stratIq, activeStrat, decisions, daily }) {
  const [subTab, setSubTab] = useState("chart")
  const price = status?.price || 0
  const pos = status?.position
  const last = status?.last_decision || {}

  let pnlToday = 0, wins = 0, losses = 0
  ;(events || []).forEach(e => {
    const p = e.payload || {}
    if (p.pnl_usd != null && ["exit_position", "exit_position_pnl", "exchange_side_close_detected"].includes(e.type)) {
      pnlToday += Number(p.pnl_usd)
      if (Number(p.pnl_usd) > 0) wins++; else if (Number(p.pnl_usd) < 0) losses++
    }
  })

  const subTabs = [
    { id: "chart", label: "Chart" },
    { id: "report", label: "Report Card" },
    { id: "advisor", label: "AI Advisor" },
    { id: "iq", label: "Strategy IQ" },
    { id: "feed", label: "Decisions" },
  ]

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-1.5 mb-1">
        {subTabs.map(t => (
          <button key={t.id} onClick={() => setSubTab(t.id)}
            className={`px-3 py-1.5 rounded-full text-[11px] font-medium transition-all ${
              subTab === t.id ? "bg-amber-400/20 text-amber-400 border border-amber-400/30" : "bg-white/5 text-gray-500 hover:text-gray-300"
            }`}>{t.label}</button>
        ))}
      </div>

      {subTab === "chart" && (
        <div className="flex flex-col gap-3">
          {/* Market Context + Stats Row */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <SafeRender><MarketContextBar /></SafeRender>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03]">
                <span className="text-[8px] text-gray-500">Trades</span>
                <span className="font-mono text-[10px] font-bold text-white">{wins + losses}</span>
                <span className="text-[8px] text-gray-500">{wins}W/{losses}L</span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03]">
                <span className="text-[8px] text-gray-500">Margin</span>
                <span className="font-mono text-[10px] font-bold text-white">{status?.margin?.tier || "--"}</span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03]">
                <span className="text-[8px] text-gray-500">Signal</span>
                <span className={`font-mono text-[10px] font-bold ${last.direction === "long" ? "text-green-400" : last.direction === "short" ? "text-red-400" : "text-gray-400"}`}>{last.direction || "--"}</span>
              </div>
            </div>
          </div>

          {/* Mindset + Position row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <div className="lg:col-span-2"><MindsetPanel /></div>
            <PositionCard position={pos} price={price} activeStrategy={activeStrat} />
          </div>

          {/* Multi-chart grid */}
          <SafeRender><TradingCharts /></SafeRender>

          {/* P&L Summary Bar */}
          {daily && (
            <div className="card p-3 grid grid-cols-5 gap-2 text-center">
              <div>
                <div className="text-[9px] text-gray-500 uppercase">Gross P&L</div>
                <div className={`font-mono text-sm font-bold ${(daily.gross_pnl||0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {(daily.gross_pnl||0) >= 0 ? "+" : ""}{formatUSD(daily.gross_pnl||0)}
                </div>
              </div>
              <div>
                <div className="text-[9px] text-gray-500 uppercase">Fees Paid</div>
                <div className="font-mono text-sm font-bold text-amber-400">-{formatUSD(daily.total_fees||0)}</div>
              </div>
              <div>
                <div className="text-[9px] text-gray-500 uppercase">Net P&L</div>
                <div className={`font-mono text-sm font-bold ${(daily.net_pnl||0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {(daily.net_pnl||0) >= 0 ? "+" : ""}{formatUSD(daily.net_pnl||0)}
                </div>
              </div>
              <div>
                <div className="text-[9px] text-gray-500 uppercase">Avg Fee</div>
                <div className="font-mono text-sm text-amber-400">{formatUSD(daily.avg_fee_per_trade||0)}</div>
              </div>
              <div>
                <div className="text-[9px] text-gray-500 uppercase">BE Move</div>
                <div className="font-mono text-sm text-gray-400">${(daily.breakeven_move||0).toFixed(5)}</div>
              </div>
            </div>
          )}

          {/* Today's Trades - full P&L breakdown */}
          <div className="card p-0 overflow-hidden">
            <div className="px-3 py-2 border-b border-gray-800 flex justify-between items-center">
              <span className="text-xs font-medium">Today's Trades (PT)</span>
              <span className="text-[10px] text-gray-500">{(daily?.trades || []).length} trades</span>
            </div>
            <div className="overflow-x-auto">
              {(daily?.trades || []).length === 0 ? (
                <div className="text-center py-4 text-[11px] text-gray-600">No trades today yet</div>
              ) : (
                <table className="w-full text-[10px]">
                  <thead>
                    <tr className="text-gray-500 border-b border-gray-800/50">
                      <th className="px-2 py-1.5 text-left">Time</th>
                      <th className="px-2 py-1.5 text-left">Side</th>
                      <th className="px-2 py-1.5 text-left">Type</th>
                      <th className="px-2 py-1.5 text-right">Entry</th>
                      <th className="px-2 py-1.5 text-right">Exit</th>
                      <th className="px-2 py-1.5 text-right">Move</th>
                      <th className="px-2 py-1.5 text-right">Gross</th>
                      <th className="px-2 py-1.5 text-right">Fees</th>
                      <th className="px-2 py-1.5 text-right font-bold">Net</th>
                      <th className="px-2 py-1.5 text-center">W/L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(daily?.trades || []).map((t, i) => {
                      const net = t.net_pnl != null ? t.net_pnl : t.pnl || 0
                      return (
                      <tr key={i} className={`border-b border-gray-800/20 ${net >= 0 ? "bg-green-400/[0.02]" : "bg-red-400/[0.02]"}`}>
                        <td className="px-2 py-1.5 text-gray-400 font-mono">{t.time}</td>
                        <td className={`px-2 py-1.5 font-bold uppercase ${t.side === "long" ? "text-green-400" : "text-red-400"}`}>{t.side || "?"}</td>
                        <td className="px-2 py-1.5 text-gray-500">{(t.type || "").replace(/_/g, " ") || "..."}</td>
                        <td className="px-2 py-1.5 text-right font-mono text-gray-300">{t.entry_price ? "$" + t.entry_price.toFixed(5) : "..."}</td>
                        <td className="px-2 py-1.5 text-right font-mono text-gray-300">{t.exit_price ? "$" + t.exit_price.toFixed(5) : "..."}</td>
                        <td className={`px-2 py-1.5 text-right font-mono ${(t.price_move_pct||0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                          {t.price_move_pct ? (t.price_move_pct >= 0 ? "+" : "") + t.price_move_pct.toFixed(3) + "%" : "..."}
                        </td>
                        <td className={`px-2 py-1.5 text-right font-mono ${(t.gross_pnl||0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                          {t.gross_pnl != null ? (t.gross_pnl >= 0 ? "+" : "") + formatUSD(t.gross_pnl) : "..."}
                        </td>
                        <td className="px-2 py-1.5 text-right font-mono text-amber-400">
                          {t.total_fees ? "-" + formatUSD(t.total_fees) : "..."}
                        </td>
                        <td className={`px-2 py-1.5 text-right font-mono font-bold ${net >= 0 ? "text-green-400" : "text-red-400"}`}>
                          {net >= 0 ? "+" : ""}{formatUSD(net)}
                        </td>
                        <td className="px-2 py-1.5 text-center">
                          <span className={`font-bold uppercase px-1.5 py-0.5 rounded text-[9px] ${t.result === "win" ? "bg-green-400/10 text-green-400" : "bg-red-400/10 text-red-400"}`}>
                            {t.result === "win" ? "W" : "L"}
                          </span>
                        </td>
                      </tr>
                      )
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
      {subTab === "report" && <SafeRender><TradeReportCard /></SafeRender>}
      {subTab === "advisor" && <SafeRender><AIAdvisor /></SafeRender>}
      {subTab === "iq" && <StrategyIQ data={stratIq} />}
      {subTab === "feed" && <DecisionFeed decisions={decisions || []} />}
    </div>
  )
}

// ── Placeholder pages ──
function Placeholder({ title, desc }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="text-4xl opacity-10 mb-4">--</div>
      <div className="text-lg font-medium text-gray-400">{title}</div>
      <div className="text-xs text-gray-600 mt-1">{desc}</div>
    </div>
  )
}

// ── Main App ──
export default function App() {
  const [page, setPage] = useState("hivemind")
  const [showSplash, setShowSplash] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const { data: status } = useApi("/status", 3000)
  const { data: decisions } = useApi("/decisions?limit=100", 5000)
  const { data: events } = useApi("/events?limit=200", 10000)
  const { data: candleResp } = useApi("/candles", 15000)
  const candles = Array.isArray(candleResp?.candles) ? candleResp.candles : Array.isArray(candleResp) ? candleResp : []
  const chartTf = candleResp?.timeframe || "15m"
  const chartPosition = candleResp?.position || null
  const { data: stratIq } = useApi("/strategy-iq", 8000)
  const { data: activeStrat } = useApi("/active-strategy", 3000)
  const { data: daily } = useApi("/daily-summary", 5000)

  const price = status?.price || 0
  const alive = status?.bot_alive

  const pnlClosed = daily?.real_pnl || daily?.closed_pnl || 0
  const pnlUnrealized = daily?.unrealized || 0
  const pnlToday = (daily?.real_pnl || daily?.closed_pnl || 0) + (daily?.unrealized || 0)
  const wins = daily?.wins || 0
  const losses = daily?.losses || 0
  const churnCount = daily?.churn_count || 0
  const churnPnl = daily?.churn_pnl || 0
  const winRate = (wins + losses) > 0 ? Math.round(wins / (wins + losses) * 100) : 0
  const dailyPos = daily?.position || null

  if (showSplash) return <SplashScreen onDone={() => setShowSplash(false)} />

  return (
    <div className="h-screen flex bg-[#0a0a0f] overflow-hidden">
      {/* Ambient effects */}
      <div className="fixed top-0 left-1/3 w-[500px] h-[300px] bg-amber-500/[0.02] rounded-full blur-[120px] pointer-events-none breathing" />
      <div className="fixed bottom-0 right-1/4 w-[400px] h-[400px] bg-purple-500/[0.015] rounded-full blur-[100px] pointer-events-none breathing-slow" />

      <Sidebar active={page} onNav={setPage} collapsed={sidebarCollapsed} />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header price={price} pnlToday={pnlToday} pnlClosed={pnlClosed} pnlUnrealized={pnlUnrealized} winRate={winRate} wins={wins} losses={losses} alive={alive} position={dailyPos} />

        <main className="flex-1 overflow-y-auto px-5 py-4">
          <div className="max-w-[1400px] mx-auto page-enter">
            {page === "hivemind" && <HiveMind />}
            {page === "trading" && <TradingPage status={status} candles={candles} chartTf={chartTf} chartPosition={chartPosition} events={events} stratIq={stratIq} activeStrat={activeStrat} decisions={decisions} daily={daily} />}
            {page === "portfolio" && <Portfolio />}
            {page === "control" && <ControlPanel />}
            {page === "revenue" && <Revenue />}
            {page === "broker" && <BrokerOS />}
            {page === "business" && <BusinessOS />}
            {page === "taskboard" && <Taskboard />}
            {page === "sessions" && <HiveSessions />}
            {page === "reports" && <Reports />}
            {page === "funnel" && <Funnel />}
            {page === "settings" && <Settings />}
            {page === "intel" && <MarketIntel />}
            {page === "trade-history" && <TradeHistory />}
            {page === "changelog" && <Changelog />}
          </div>
        </main>
      </div>

      {/* Floating Trading Chat -- available on every page */}
      <TradingChat />
    </div>
  )
}
