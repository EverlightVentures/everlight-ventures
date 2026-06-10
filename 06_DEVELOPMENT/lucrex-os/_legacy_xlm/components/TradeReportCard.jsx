import React from "react"
import { useApi } from "../hooks"

const TIER_CONFIG = {
  MONSTER: { bg: "from-amber-500/30 to-orange-600/20", border: "border-amber-400", text: "text-amber-400", glow: "shadow-amber-500/20" },
  FULL: { bg: "from-green-500/20 to-emerald-600/10", border: "border-green-400", text: "text-green-400", glow: "shadow-green-500/10" },
  REDUCED: { bg: "from-yellow-500/20 to-amber-600/10", border: "border-yellow-400", text: "text-yellow-400", glow: "shadow-yellow-500/10" },
  SCALP: { bg: "from-orange-500/15 to-red-600/10", border: "border-orange-400", text: "text-orange-400", glow: "" },
  NO_TRADE: { bg: "from-gray-500/10 to-gray-800/10", border: "border-gray-600", text: "text-gray-500", glow: "" },
}

const DIR_COLORS = {
  long: { bg: "bg-green-400/10", text: "text-green-400", border: "border-green-400/30" },
  short: { bg: "bg-red-400/10", text: "text-red-400", border: "border-red-400/30" },
}

function ScoreGauge({ score, threshold }) {
  const pct = Math.max(0, Math.min(100, score))
  const threshPct = Math.max(0, Math.min(100, threshold))
  const isGo = score >= threshold
  const barColor = isGo
    ? "from-green-400 via-emerald-400 to-green-500"
    : score >= threshold - 10
      ? "from-yellow-400 via-amber-400 to-yellow-500"
      : "from-red-400 via-orange-400 to-red-500"

  return (
    <div className="relative">
      <div className="flex justify-between items-center mb-1.5">
        <span className="text-[9px] uppercase tracking-widest text-gray-500">Unified Score</span>
        <span className={`font-mono text-2xl font-black ${isGo ? "text-green-400" : "text-gray-400"}`}>
          {score}<span className="text-sm text-gray-600">/{threshold}</span>
        </span>
      </div>
      <div className="h-3 bg-gray-800/80 rounded-full overflow-hidden relative">
        <div className="absolute top-0 bottom-0 w-0.5 bg-white/30 z-10" style={{ left: `${threshPct}%` }} />
        <div className={`h-full rounded-full bg-gradient-to-r ${barColor} transition-all duration-700 ease-out`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function ModifierBar({ name, value, maxAbs }) {
  const scale = maxAbs > 0 ? Math.abs(value) / maxAbs : 0
  const isPos = value > 0
  const isNeg = value < 0
  const label = name.replace(/_/g, " ")
  return (
    <div className="flex items-center gap-2 py-0.5">
      <span className="text-[10px] text-gray-400 w-28 truncate capitalize">{label}</span>
      <div className="flex-1 h-2.5 bg-gray-800/50 rounded-full relative overflow-hidden">
        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gray-700" />
        {isPos && <div className="absolute top-0 bottom-0 left-1/2 bg-gradient-to-r from-green-500/80 to-green-400 rounded-r-full transition-all duration-500" style={{ width: `${scale * 50}%` }} />}
        {isNeg && <div className="absolute top-0 bottom-0 right-1/2 bg-gradient-to-l from-red-500/80 to-red-400 rounded-l-full transition-all duration-500" style={{ width: `${scale * 50}%` }} />}
      </div>
      <span className={`text-[10px] font-mono w-8 text-right ${isPos ? "text-green-400" : isNeg ? "text-red-400" : "text-gray-600"}`}>
        {value > 0 ? "+" : ""}{value}
      </span>
    </div>
  )
}

function Tag({ children, color = "gray" }) {
  const colors = {
    green: "bg-green-400/10 text-green-400 border-green-400/20",
    red: "bg-red-400/10 text-red-400 border-red-400/20",
    amber: "bg-amber-400/10 text-amber-400 border-amber-400/20",
    blue: "bg-blue-400/10 text-blue-400 border-blue-400/20",
    purple: "bg-purple-400/10 text-purple-400 border-purple-400/20",
    cyan: "bg-cyan-400/10 text-cyan-400 border-cyan-400/20",
    gray: "bg-gray-400/10 text-gray-400 border-gray-400/20",
  }
  return (
    <span className={`inline-block text-[9px] px-1.5 py-0.5 rounded border font-medium ${colors[color] || colors.gray}`}>
      {children}
    </span>
  )
}

function formatPrice(p) {
  if (!p || p === 0) return "--"
  return "$" + Number(p).toFixed(5)
}

export default function TradeReportCard() {
  const { data } = useApi("/report-card", 5000)

  if (!data || !data.active) {
    return (
      <div className="card border-dashed border-gray-700/50">
        <div className="text-center py-8">
          <div className="text-[10px] uppercase tracking-widest text-gray-600 mb-1">Trade Report Card</div>
          <div className="text-xs text-gray-500">Waiting for unified scorer data...</div>
        </div>
      </div>
    )
  }

  const tc = TIER_CONFIG[data.tier] || TIER_CONFIG.NO_TRADE
  const dc = DIR_COLORS[data.direction] || {}
  const entryLabel = (data.entry_type || "").replace(/_/g, " ").toUpperCase()
  const eye = data.eyeball || {}
  const ind = eye.indicators || {}
  const det = eye.entry_details || {}
  const modEntries = Object.entries(data.modifiers || {}).filter(([, v]) => v !== 0)
  const maxAbs = Math.max(1, ...modEntries.map(([, v]) => Math.abs(v)))
  const allMods = Object.entries(data.modifiers || {}).sort((a, b) => a[1] - b[1])

  return (
    <div className="flex flex-col gap-4">
      {/* Row 1: Strategy Header + Score */}
      <div className={`card border ${tc.border}/30 ${tc.glow} relative overflow-hidden`}>
        <div className={`absolute top-0 left-0 right-0 h-16 bg-gradient-to-r ${tc.bg} opacity-60`} />
        <div className="relative">
          <div className="flex justify-between items-start mb-3">
            <div>
              <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-0.5">Play Call</div>
              <div className="text-sm font-bold text-white">{entryLabel || "SCANNING"}</div>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                {data.direction && (
                  <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase ${dc.bg || ""} ${dc.text || "text-gray-400"} ${dc.border || ""} border`}>
                    {data.direction}
                  </span>
                )}
                <Tag color="blue">{eye.primary_timeframe || "15m"}</Tag>
                <Tag color="purple">{(data.regime || "neutral").replace(/_/g, " ")}</Tag>
                {eye.vol_phase && eye.vol_phase !== "COMPRESSION" && <Tag color="amber">{eye.vol_phase}</Tag>}
              </div>
            </div>
            <div className="text-right">
              <span className={`text-xs font-black px-2.5 py-1 rounded-lg bg-gradient-to-r ${tc.bg} ${tc.text} border ${tc.border}/40`}>
                {data.tier}
              </span>
              <div className="text-[8px] text-gray-600 mt-1">
                {data.recommendation === "ENTER" ? "ENTERING" : "HOLDING"}
              </div>
            </div>
          </div>
          <ScoreGauge score={data.score} threshold={data.threshold} />
        </div>
      </div>

      {/* Row 2: What It's Looking At (Eyeball) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Trade Geometry */}
        <div className="card">
          <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">Trade Geometry</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <div>
              <div className="text-[8px] text-gray-500">Entry Price</div>
              <div className="font-mono text-xs text-white">{formatPrice(data.eyeball?.stop_price ? (data.direction === "long" ? data.eyeball.stop_price + (data.eyeball.risk_usd / 5000) : data.eyeball.stop_price - (data.eyeball.risk_usd / 5000)) : 0)}</div>
            </div>
            <div>
              <div className="text-[8px] text-gray-500">Stop Loss</div>
              <div className="font-mono text-xs text-red-400">{formatPrice(eye.stop_price)}</div>
            </div>
            <div>
              <div className="text-[8px] text-gray-500">Target (TP1)</div>
              <div className="font-mono text-xs text-green-400">{formatPrice(eye.tp1_price)}</div>
            </div>
            <div>
              <div className="text-[8px] text-gray-500">R:R Ratio</div>
              <div className="font-mono text-xs text-amber-400">{eye.rr_ratio ? `${eye.rr_ratio}:1` : "--"}</div>
            </div>
            <div>
              <div className="text-[8px] text-gray-500">Risk/Contract</div>
              <div className="font-mono text-xs text-red-400">{eye.risk_usd ? `$${eye.risk_usd.toFixed(2)}` : "--"}</div>
            </div>
            <div>
              <div className="text-[8px] text-gray-500">Reward/Contract</div>
              <div className="font-mono text-xs text-green-400">{eye.reward_usd ? `$${eye.reward_usd.toFixed(2)}` : "--"}</div>
            </div>
          </div>
          {/* Win prob + profit row */}
          <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-gray-800/50">
            <div className="text-center">
              <div className="text-[8px] text-gray-500">Win Prob</div>
              <div className="font-mono text-sm font-bold text-blue-400">{data.p_win > 0 ? `${(data.p_win * 100).toFixed(0)}%` : "--"}</div>
            </div>
            <div className="text-center">
              <div className="text-[8px] text-gray-500">Est. Profit</div>
              <div className={`font-mono text-sm font-bold ${data.profit_est >= 0 ? "text-green-400" : "text-red-400"}`}>
                {data.profit_est ? `$${Math.abs(data.profit_est).toFixed(2)}` : "--"}
              </div>
            </div>
            <div className="text-center">
              <div className="text-[8px] text-gray-500">Primary TF</div>
              <div className="font-mono text-sm font-bold text-purple-400">{eye.primary_timeframe || "15m"}</div>
            </div>
          </div>
        </div>

        {/* Right: Indicators + What's Firing */}
        <div className="card">
          <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">What It Sees</div>

          {/* Key indicators */}
          <div className="grid grid-cols-3 gap-2 mb-3">
            <div className="px-2 py-1.5 rounded-lg bg-white/[0.03]">
              <div className="text-[8px] text-gray-500">RSI 15m</div>
              <div className={`font-mono text-xs font-bold ${ind.rsi_15m <= 30 ? "text-green-400" : ind.rsi_15m >= 70 ? "text-red-400" : "text-gray-300"}`}>
                {ind.rsi_15m || "--"}
              </div>
            </div>
            <div className="px-2 py-1.5 rounded-lg bg-white/[0.03]">
              <div className="text-[8px] text-gray-500">ADX 15m</div>
              <div className={`font-mono text-xs font-bold ${ind.adx_15m >= 25 ? "text-amber-400" : "text-gray-400"}`}>
                {ind.adx_15m || "--"}
              </div>
            </div>
            <div className="px-2 py-1.5 rounded-lg bg-white/[0.03]">
              <div className="text-[8px] text-gray-500">RVOL</div>
              <div className={`font-mono text-xs font-bold ${ind.rvol_15m >= 1.5 ? "text-amber-400" : "text-gray-400"}`}>
                {ind.rvol_15m ? `${ind.rvol_15m.toFixed(1)}x` : "--"}
              </div>
            </div>
          </div>

          {/* VWAP */}
          {ind.vwap_price > 0 && (
            <div className="flex items-center gap-2 mb-2 text-[10px]">
              <span className="text-gray-500">VWAP:</span>
              <span className="font-mono text-gray-300">{formatPrice(ind.vwap_price)}</span>
              <Tag color={ind.vwap_side === "above" ? "green" : "red"}>{ind.vwap_side}</Tag>
            </div>
          )}

          {/* Volume state */}
          <div className="flex items-center gap-2 mb-2 text-[10px]">
            <span className="text-gray-500">Volume:</span>
            <Tag color={eye.vol_phase === "EXPANSION" ? "amber" : eye.vol_phase === "IGNITION" ? "purple" : "gray"}>
              {eye.vol_phase || "COMPRESSION"}
            </Tag>
            {eye.atr_expanding && <Tag color="amber">ATR Expanding</Tag>}
            {eye.bb_expanding && <Tag color="cyan">BB Expanding</Tag>}
          </div>

          {/* Structure */}
          <div className="flex items-center gap-2 mb-3 text-[10px]">
            <span className="text-gray-500">Structure:</span>
            <Tag color={eye.structure_bias === "bullish" ? "green" : eye.structure_bias === "bearish" ? "red" : "gray"}>
              {eye.structure_bias || "neutral"}
            </Tag>
            <Tag color="blue">HTF: {eye.htf_trend || "neutral"}</Tag>
          </div>

          {/* Chart Patterns Detected */}
          {(eye.patterns_detected || []).length > 0 && (
            <div className="mb-2">
              <div className="text-[8px] text-gray-500 uppercase mb-1">Patterns Detected</div>
              <div className="flex flex-wrap gap-1">
                {eye.patterns_detected.map((p, i) => (
                  <Tag key={i} color="purple">{p.replace(/_/g, " ")}</Tag>
                ))}
              </div>
            </div>
          )}

          {/* Confirmations */}
          {(eye.confirmations || []).length > 0 && (
            <div>
              <div className="text-[8px] text-gray-500 uppercase mb-1">Confirmations</div>
              <div className="flex flex-wrap gap-1">
                {eye.confirmations.map((c, i) => (
                  <Tag key={i} color="green">{c.replace(/_/g, " ")}</Tag>
                ))}
              </div>
            </div>
          )}

          {/* Entry-specific details */}
          {(det.near_level || det.fvg_timeframe || det.wick_pct) && (
            <div className="mt-2 pt-2 border-t border-gray-800/50">
              <div className="text-[8px] text-gray-500 uppercase mb-1">Entry Details</div>
              <div className="flex flex-wrap gap-2 text-[10px]">
                {det.near_level && <span className="text-amber-400">Fib: {det.near_level}</span>}
                {det.wick_pct && <span className="text-purple-400">Wick: {(det.wick_pct * 100).toFixed(0)}%</span>}
                {det.fvg_timeframe && <span className="text-blue-400">FVG: {det.fvg_timeframe}</span>}
                {det.risk_reward && <span className="text-green-400">Setup R:R: {det.risk_reward}:1</span>}
                {det.candle_age != null && <span className="text-gray-400">Candle age: {det.candle_age} bars</span>}
                {det.engulfing && <Tag color="amber">Engulfing</Tag>}
              </div>
            </div>
          )}

          {/* FVG detail */}
          {eye.fvg_detail && (
            <div className="mt-1 text-[10px] text-gray-400">
              FVG: {formatPrice(eye.fvg_detail.low)} - {formatPrice(eye.fvg_detail.high)} ({eye.fvg_detail.age} bars ago)
            </div>
          )}
        </div>
      </div>

      {/* Row 3: Narrative */}
      {data.narrative && (
        <div className="card px-4 py-3 border border-white/[0.06]">
          <div className="text-[9px] uppercase tracking-widest text-amber-400/60 mb-1.5">Play-by-Play</div>
          <div className="text-[12px] text-gray-200 leading-relaxed">{data.narrative}</div>
        </div>
      )}

      {/* Row 4: Score Breakdown + Alternatives side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Modifier Breakdown */}
        <div className="card">
          <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">Score Breakdown</div>
          <div className="flex items-center gap-2 py-0.5 mb-1">
            <span className="text-[10px] text-gray-400 w-28">Base (V4)</span>
            <div className="flex-1 h-2.5 bg-gray-800/50 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-blue-500/80 to-blue-400 rounded-full" style={{ width: `${data.base_score}%` }} />
            </div>
            <span className="text-[10px] font-mono text-blue-400 w-8 text-right">{data.base_score}</span>
          </div>
          {allMods.map(([k, v]) => (
            <ModifierBar key={k} name={k} value={v} maxAbs={maxAbs} />
          ))}
        </div>

        {/* Alternatives */}
        <div className="card">
          <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">Strategies Considered</div>
          {(data.alternatives || []).length > 0 ? (
            <div>
              {data.alternatives.map((alt, i) => {
                const adc = DIR_COLORS[alt.direction] || {}
                return (
                  <div key={i} className={`flex items-center gap-2 py-2 ${i > 0 ? "border-t border-gray-800/30" : ""}`}>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        {alt.selected && <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />}
                        <span className={`text-[11px] font-medium truncate ${alt.selected ? "text-white" : "text-gray-400"}`}>
                          {alt.name}
                        </span>
                      </div>
                      {alt.selected && alt.p_win > 0 && (
                        <div className="text-[9px] text-gray-500 mt-0.5 ml-3">
                          {(alt.p_win * 100).toFixed(0)}% win | {alt.rr_ratio}:1 R:R
                        </div>
                      )}
                    </div>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${adc.bg || "bg-gray-500/10"} ${adc.text || "text-gray-400"}`}>
                      {alt.direction}
                    </span>
                    <span className="text-[11px] font-mono text-gray-300 w-8 text-right">{alt.normalized || alt.raw_score}</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-xs text-gray-500 py-2">No alternatives this cycle</div>
          )}
        </div>
      </div>

      {/* Row 5: Foresight + Candle Math */}
      {(data.foresight?.scenarios?.length > 0 || data.candle_math?.avg_range_1h_usd > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Foresight Scenarios */}
          {data.foresight?.scenarios?.length > 0 && (
            <div className="card">
              <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">
                Foresight ({data.foresight.bias} bias, {data.foresight.rsi_state} RSI)
              </div>
              {data.foresight.scenarios.map((s, i) => (
                <div key={i} className={`flex justify-between items-center py-1.5 ${i > 0 ? "border-t border-gray-800/30" : ""}`}>
                  <div className="flex items-center gap-2">
                    <span className={`text-[8px] px-1 py-0.5 rounded font-bold ${
                      s.probability === "high" ? "bg-green-400/10 text-green-400" : "bg-amber-400/10 text-amber-400"
                    }`}>{s.probability}</span>
                    <span className={`text-[9px] font-bold uppercase ${
                      s.direction === "long" ? "text-green-400" : s.direction === "short" ? "text-red-400" : "text-blue-400"
                    }`}>{s.direction}</span>
                    <span className="text-[10px] text-gray-300">{s.name?.replace(/_/g, " ")}</span>
                  </div>
                  <span className="font-mono text-[10px] text-amber-400">${s.profit_usd?.toFixed(2)}</span>
                </div>
              ))}
              <div className="mt-2 pt-2 border-t border-gray-800/30 text-center">
                <span className="text-[9px] text-gray-500">Projected: </span>
                <span className="font-mono text-[10px] text-green-400">
                  {data.foresight.projected_trades} trades, ${data.foresight.projected_profit_conservative?.toFixed(0)}-${data.foresight.projected_profit_best?.toFixed(0)}
                </span>
              </div>
            </div>
          )}

          {/* Candle Math */}
          {data.candle_math?.avg_range_1h_usd > 0 && (
            <div className="card">
              <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-2">Market Movement</div>
              <div className="grid grid-cols-3 gap-2 mb-2">
                <div className="text-center px-2 py-1.5 rounded-lg bg-white/[0.03]">
                  <div className="text-[8px] text-gray-500">15m Candle</div>
                  <div className="font-mono text-xs font-bold text-blue-400">${data.candle_math.avg_range_15m_usd?.toFixed(2)}</div>
                </div>
                <div className="text-center px-2 py-1.5 rounded-lg bg-white/[0.03]">
                  <div className="text-[8px] text-gray-500">1H Candle</div>
                  <div className="font-mono text-xs font-bold text-amber-400">${data.candle_math.avg_range_1h_usd?.toFixed(2)}</div>
                </div>
                <div className="text-center px-2 py-1.5 rounded-lg bg-white/[0.03]">
                  <div className="text-[8px] text-gray-500">4H Candle</div>
                  <div className="font-mono text-xs font-bold text-purple-400">${data.candle_math.avg_range_4h_usd?.toFixed(2)}</div>
                </div>
              </div>
              <div className="text-[10px] text-gray-400">
                TP coverage: <span className={`font-bold ${data.candle_math.tp_coverage_1h >= 1.5 ? "text-green-400" : data.candle_math.tp_coverage_1h >= 1 ? "text-amber-400" : "text-red-400"}`}>
                  {data.candle_math.tp_coverage_1h?.toFixed(1)}x
                </span> (1H avg covers TP {data.candle_math.tp_coverage_1h >= 1.5 ? "easily" : data.candle_math.tp_coverage_1h >= 1 ? "tightly" : "barely"})
              </div>
              {data.candle_math.big_candle_detected && (
                <div className="mt-1.5 px-2 py-1 rounded bg-amber-400/5 border border-amber-400/10">
                  <span className="text-[9px] text-amber-400">Big candle retrace: </span>
                  <span className="text-[9px] text-gray-300">
                    {data.candle_math.retrace_direction} to 50% = ${data.candle_math.retrace_pnl_50_usd?.toFixed(2)}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Timestamp */}
      {data.ts && (
        <div className="text-[8px] text-gray-600 text-right">
          Updated: {new Date(data.ts).toLocaleTimeString()}
        </div>
      )}
    </div>
  )
}
