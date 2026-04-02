import React, { useMemo } from "react"
import {
  ComposedChart, Bar, Line, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell, Rectangle
} from "recharts"

/* ── Indicator math ─────────────────────────────────────────────── */
function calcEMA(data, period, key = "c") {
  const k = 2 / (period + 1)
  const out = []
  let prev = null
  for (const d of data) {
    const val = d[key]
    if (val == null) { out.push(null); continue }
    if (prev == null) { prev = val; out.push(val); continue }
    prev = val * k + prev * (1 - k)
    out.push(prev)
  }
  return out
}

function calcRSI(data, period = 14) {
  const out = new Array(data.length).fill(null)
  if (data.length < period + 1) return out
  let avgGain = 0, avgLoss = 0
  for (let i = 1; i <= period; i++) {
    const diff = (data[i].c ?? 0) - (data[i - 1].c ?? 0)
    if (diff > 0) avgGain += diff; else avgLoss -= diff
  }
  avgGain /= period; avgLoss /= period
  out[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
  for (let i = period + 1; i < data.length; i++) {
    const diff = (data[i].c ?? 0) - (data[i - 1].c ?? 0)
    const gain = diff > 0 ? diff : 0
    const loss = diff < 0 ? -diff : 0
    avgGain = (avgGain * (period - 1) + gain) / period
    avgLoss = (avgLoss * (period - 1) + loss) / period
    out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
  }
  return out
}

function calcBollinger(data, period = 20, mult = 2) {
  const upper = [], lower = [], mid = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) { upper.push(null); lower.push(null); mid.push(null); continue }
    let sum = 0
    for (let j = i - period + 1; j <= i; j++) sum += data[j].c
    const mean = sum / period
    let sqSum = 0
    for (let j = i - period + 1; j <= i; j++) sqSum += (data[j].c - mean) ** 2
    const std = Math.sqrt(sqSum / period)
    mid.push(mean)
    upper.push(mean + mult * std)
    lower.push(mean - mult * std)
  }
  return { upper, lower, mid }
}

/* ── Custom candlestick shape ───────────────────────────────────── */
function CandlestickBar(props) {
  const { x, y, width, height, payload } = props
  if (!payload) return null
  const { o, c, h, l, yScale } = payload
  if (o == null || c == null || h == null || l == null || !yScale) return null

  const bull = c >= o
  const fill = bull ? "#00e676" : "#ff1744"
  const fillBody = bull ? "rgba(0,230,118,0.85)" : "rgba(255,23,68,0.85)"

  const bodyTop = yScale(Math.max(o, c))
  const bodyBot = yScale(Math.min(o, c))
  const bodyH = Math.max(bodyBot - bodyTop, 1)
  const wickTop = yScale(h)
  const wickBot = yScale(l)
  const cx = x + width / 2

  return (
    <g>
      {/* Wick */}
      <line x1={cx} y1={wickTop} x2={cx} y2={wickBot} stroke={fill} strokeWidth={1} />
      {/* Body */}
      <rect
        x={x + width * 0.15}
        y={bodyTop}
        width={width * 0.7}
        height={bodyH}
        fill={fillBody}
        stroke={fill}
        strokeWidth={0.5}
        rx={1}
      />
    </g>
  )
}

/* ── Custom tooltip ─────────────────────────────────────────────── */
function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d) return null
  const bull = d.c >= d.o
  return (
    <div className="chart-tooltip" style={{ minWidth: 180 }}>
      <div className="text-[10px] text-gray-400 mb-1.5 border-b border-gray-700 pb-1">{d.time}</div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs font-mono">
        <span className="text-gray-500">Open</span><span>{d.o?.toFixed(5)}</span>
        <span className="text-gray-500">High</span><span className="text-green-400">{d.h?.toFixed(5)}</span>
        <span className="text-gray-500">Low</span><span className="text-red-400">{d.l?.toFixed(5)}</span>
        <span className="text-gray-500">Close</span>
        <span className={bull ? "text-green-400" : "text-red-400"}>{d.c?.toFixed(5)}</span>
        <span className="text-gray-500">Vol</span><span className="text-blue-300">{d.v?.toLocaleString()}</span>
      </div>
      {(d.ema8 != null || d.ema21 != null) && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs font-mono mt-1 pt-1 border-t border-gray-700">
          {d.ema8 != null && <><span className="text-cyan-500">EMA 8</span><span>{d.ema8.toFixed(5)}</span></>}
          {d.ema21 != null && <><span className="text-amber-500">EMA 21</span><span>{d.ema21.toFixed(5)}</span></>}
        </div>
      )}
      {d.rsi != null && (
        <div className="text-xs font-mono mt-1 pt-1 border-t border-gray-700">
          <span className="text-purple-400">RSI </span>
          <span className={d.rsi > 70 ? "text-red-400" : d.rsi < 30 ? "text-green-400" : "text-gray-300"}>
            {d.rsi.toFixed(1)}
          </span>
        </div>
      )}
    </div>
  )
}

/* ── RSI Tooltip ────────────────────────────────────────────────── */
function RSITooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d || d.rsi == null) return null
  return (
    <div className="chart-tooltip" style={{ padding: "4px 8px" }}>
      <span className="text-[10px] text-gray-400">{d.time} </span>
      <span className="text-xs font-mono text-purple-400">RSI {d.rsi?.toFixed(1)}</span>
    </div>
  )
}

/* ── Entry/Exit markers ─────────────────────────────────────────── */
function EntryMarker({ cx, cy }) {
  return (
    <g>
      <polygon points={`${cx},${cy - 14} ${cx - 6},${cy - 4} ${cx + 6},${cy - 4}`} fill="#00e676" stroke="#00e676" opacity={0.9} />
      <circle cx={cx} cy={cy} r={3} fill="#00e676" />
    </g>
  )
}

function ExitMarker({ cx, cy }) {
  return (
    <g>
      <polygon points={`${cx},${cy + 14} ${cx - 6},${cy + 4} ${cx + 6},${cy + 4}`} fill="#ff1744" stroke="#ff1744" opacity={0.9} />
      <circle cx={cx} cy={cy} r={3} fill="#ff1744" />
    </g>
  )
}

/* ── Pulsing price dot ──────────────────────────────────────────── */
function PulseDot(props) {
  const { cx, cy, index, dataLength } = props
  if (index !== dataLength - 1) return null
  return (
    <g>
      <circle cx={cx} cy={cy} r={6} fill="none" stroke="#ffd740" strokeWidth={1.5} opacity={0.4}>
        <animate attributeName="r" from="4" to="14" dur="2s" repeatCount="indefinite" />
        <animate attributeName="opacity" from="0.6" to="0" dur="2s" repeatCount="indefinite" />
      </circle>
      <circle cx={cx} cy={cy} r={4} fill="#ffd740" stroke="#ffd740" strokeWidth={1} />
    </g>
  )
}

/* ══════════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════════════════════ */
export default function PriceChart({ candles, height = 400, position }) {
  const data = useMemo(() => {
    if (!candles?.length) return []
    const ema8 = calcEMA(candles, 8)
    const ema21 = calcEMA(candles, 21)
    const rsi = calcRSI(candles, 14)
    const bb = calcBollinger(candles, 20, 2)

    return candles.map((c, i) => ({
      time: new Date(c.t * 1000).toLocaleTimeString("en-US", {
        hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "America/Los_Angeles"
      }),
      ts: c.t,
      o: c.o, h: c.h, l: c.l, c: c.c, v: c.v,
      ema8: ema8[i], ema21: ema21[i],
      rsi: rsi[i],
      bbUpper: bb.upper[i], bbLower: bb.lower[i], bbMid: bb.mid[i],
      // Bollinger band fill range
      bbRange: bb.upper[i] != null ? [bb.lower[i], bb.upper[i]] : undefined,
      // For candlestick coloring
      bull: c.c >= c.o,
      // Volume color
      volColor: c.c >= c.o ? "rgba(0,230,118,0.35)" : "rgba(255,23,68,0.35)",
    }))
  }, [candles])

  // Attach yScale to data after computing domain
  const { priceMin, priceMax, volMax } = useMemo(() => {
    if (!data.length) return { priceMin: 0, priceMax: 1, volMax: 1 }
    let pMin = Infinity, pMax = -Infinity, vMax = 0
    for (const d of data) {
      const lo = Math.min(d.l, d.bbLower ?? d.l)
      const hi = Math.max(d.h, d.bbUpper ?? d.h)
      if (lo < pMin) pMin = lo
      if (hi > pMax) pMax = hi
      if (d.v > vMax) vMax = d.v
    }
    const pad = (pMax - pMin) * 0.02
    return { priceMin: pMin - pad, priceMax: pMax + pad, volMax }
  }, [data])

  // Entry/exit timestamps from position
  const entryTs = position?.entry_ts
  const exitTs = position?.exit_ts

  if (!data.length) {
    return (
      <div className="flex items-center justify-center text-gray-600 text-sm" style={{ height }}>
        <div className="flex items-center gap-2">
          <div className="live-indicator" style={{ background: "#555" }} />
          Loading chart data...
        </div>
      </div>
    )
  }

  const mainH = Math.round(height * 0.75)
  const rsiH = 80

  return (
    <div className="chart-container">
      {/* ── Main price chart ──────────────────────────────────────── */}
      <ResponsiveContainer width="100%" height={mainH}>
        <ComposedChart data={data} margin={{ top: 8, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="bbFillGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#b388ff" stopOpacity={0.08} />
              <stop offset="50%" stopColor="#b388ff" stopOpacity={0.04} />
              <stop offset="100%" stopColor="#b388ff" stopOpacity={0.08} />
            </linearGradient>
            <linearGradient id="volGreenGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00e676" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#00e676" stopOpacity={0.1} />
            </linearGradient>
            <linearGradient id="volRedGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ff1744" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#ff1744" stopOpacity={0.1} />
            </linearGradient>
          </defs>

          <XAxis
            dataKey="time"
            tick={{ fontSize: 9, fill: "#444" }}
            tickLine={false}
            axisLine={{ stroke: "#1a1a2e" }}
            interval={Math.max(1, Math.floor(data.length / 8))}
          />

          {/* Price axis */}
          <YAxis
            yAxisId="price"
            domain={[priceMin, priceMax]}
            tick={{ fontSize: 9, fill: "#555" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={v => v.toFixed(4)}
            width={62}
            orientation="right"
          />

          {/* Volume axis (hidden, scaled to 30% of chart) */}
          <YAxis
            yAxisId="vol"
            domain={[0, volMax * 3.3]}
            hide
          />

          <Tooltip content={<ChartTooltip />} />

          {/* Bollinger Band fill */}
          <Area
            yAxisId="price"
            dataKey="bbUpper"
            stroke="none"
            fill="none"
            dot={false}
            activeDot={false}
          />
          <Area
            yAxisId="price"
            dataKey="bbLower"
            stroke="none"
            fill="url(#bbFillGradient)"
            dot={false}
            activeDot={false}
            baseValue="dataMax"
          />

          {/* Bollinger lines */}
          <Line
            yAxisId="price"
            dataKey="bbUpper"
            stroke="rgba(179,136,255,0.25)"
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
            activeDot={false}
          />
          <Line
            yAxisId="price"
            dataKey="bbLower"
            stroke="rgba(179,136,255,0.25)"
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
            activeDot={false}
          />

          {/* Volume bars */}
          <Bar yAxisId="vol" dataKey="v" barSize={4} radius={[1, 1, 0, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.bull ? "url(#volGreenGrad)" : "url(#volRedGrad)"} />
            ))}
          </Bar>

          {/* Candlestick bodies rendered as custom bars on close price */}
          <Bar
            yAxisId="price"
            dataKey="c"
            barSize={8}
            shape={(props) => {
              const { payload, x, width } = props
              if (!payload?.o || !payload?.c) return null
              const bull = payload.c >= payload.o
              const bodyTop = Math.max(payload.o, payload.c)
              const bodyBot = Math.min(payload.o, payload.c)
              // We need to convert prices to pixels using the y axis
              // The YAxis domain and chart area give us the mapping
              return null // placeholder, we use the custom rendering below
            }}
            hide
          />

          {/* EMA 8 */}
          <Line
            yAxisId="price"
            dataKey="ema8"
            stroke="#00bcd4"
            strokeWidth={1.2}
            dot={false}
            activeDot={false}
            connectNulls
          />

          {/* EMA 21 */}
          <Line
            yAxisId="price"
            dataKey="ema21"
            stroke="#ff9100"
            strokeWidth={1.2}
            dot={false}
            activeDot={false}
            connectNulls
          />

          {/* Price close line (thin, for structure) */}
          <Line
            yAxisId="price"
            dataKey="c"
            stroke="rgba(255,215,64,0.6)"
            strokeWidth={1.5}
            dot={(dotProps) => (
              <PulseDot {...dotProps} dataLength={data.length} />
            )}
            activeDot={{ r: 3, fill: "#ffd740", stroke: "#ffd740" }}
            connectNulls
          />

          {/* High/Low range as thin candle wicks */}
          <Line
            yAxisId="price"
            dataKey="h"
            stroke="none"
            dot={false}
            activeDot={false}
          />

          {/* Entry marker */}
          {entryTs && (
            <ReferenceLine
              yAxisId="price"
              x={data.find(d => d.ts >= entryTs)?.time}
              stroke="#00e676"
              strokeDasharray="3 3"
              strokeWidth={1}
              label={{ value: "ENTRY", position: "top", fill: "#00e676", fontSize: 9 }}
            />
          )}

          {/* Exit marker */}
          {exitTs && (
            <ReferenceLine
              yAxisId="price"
              x={data.find(d => d.ts >= exitTs)?.time}
              stroke="#ff1744"
              strokeDasharray="3 3"
              strokeWidth={1}
              label={{ value: "EXIT", position: "top", fill: "#ff1744", fontSize: 9 }}
            />
          )}

          {/* Entry price horizontal */}
          {position?.entry_price && (
            <ReferenceLine
              yAxisId="price"
              y={position.entry_price}
              stroke="rgba(0,230,118,0.3)"
              strokeDasharray="6 4"
              strokeWidth={1}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* ── RSI sub-chart ─────────────────────────────────────────── */}
      <div style={{ marginTop: -1 }}>
        <ResponsiveContainer width="100%" height={rsiH}>
          <ComposedChart data={data} margin={{ top: 4, right: 10, left: 0, bottom: 0 }}>
            <XAxis dataKey="time" hide />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 8, fill: "#444" }}
              tickLine={false}
              axisLine={false}
              ticks={[30, 50, 70]}
              width={62}
              orientation="right"
            />
            <Tooltip content={<RSITooltip />} />

            {/* Overbought/oversold zones */}
            <ReferenceLine y={70} stroke="rgba(255,23,68,0.25)" strokeDasharray="3 3" />
            <ReferenceLine y={30} stroke="rgba(0,230,118,0.25)" strokeDasharray="3 3" />
            <ReferenceLine y={50} stroke="rgba(100,100,130,0.15)" strokeDasharray="2 4" />

            {/* RSI fill above 70 */}
            <Area
              dataKey="rsi"
              stroke="none"
              fill="rgba(179,136,255,0.08)"
              baseValue={50}
              dot={false}
              activeDot={false}
              connectNulls
            />

            <Line
              dataKey="rsi"
              stroke="#b388ff"
              strokeWidth={1.2}
              dot={false}
              activeDot={{ r: 2, fill: "#b388ff" }}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
