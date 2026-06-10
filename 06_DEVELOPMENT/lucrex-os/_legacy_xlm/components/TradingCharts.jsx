import React, { useRef, useEffect, useMemo, useCallback } from "react"
import { createChart, CrosshairMode, LineStyle } from "lightweight-charts"
import { useApi } from "../hooks"

/* -- Indicator math -- */
function calcEMA(data, period) {
  const k = 2 / (period + 1)
  const out = []
  let prev = null
  for (const d of data) {
    const val = d.c
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
  const upper = [], lower = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) { upper.push(null); lower.push(null); continue }
    let sum = 0
    for (let j = i - period + 1; j <= i; j++) sum += data[j].c
    const mean = sum / period
    let sqSum = 0
    for (let j = i - period + 1; j <= i; j++) sqSum += (data[j].c - mean) ** 2
    const std = Math.sqrt(sqSum / period)
    upper.push(mean + mult * std)
    lower.push(mean - mult * std)
  }
  return { upper, lower }
}

/* -- Colors -- */
const C = {
  bg: "transparent",
  grid: "rgba(255,255,255,0.025)",
  text: "#555",
  crosshair: "#555",
  bullCandle: "#00e676",
  bearCandle: "#ff1744",
  ema8: "#00bcd4",
  ema21: "#ff9100",
  ema55: "#7c4dff",
  bbLine: "rgba(179,136,255,0.3)",
  volBull: "rgba(0,230,118,0.2)",
  volBear: "rgba(255,23,68,0.2)",
  rsi: "#b388ff",
  entry: { long: "#00e676", short: "#ff1744" },
  sl: "rgba(255,23,68,0.5)",
  tp1: "rgba(0,230,118,0.5)",
  tp2: "rgba(0,230,118,0.3)",
  tp3: "rgba(0,230,118,0.18)",
  fvg: "rgba(255,193,7,0.08)",
  fib: "rgba(255,193,7,0.25)",
  vwap: "rgba(33,150,243,0.4)",
  structure: "rgba(156,39,176,0.3)",
}

/* -- Single chart builder -- */
function ChartPane({ candles, height, label, position, strategy, showRSI, showOverlays, isPrimary }) {
  const containerRef = useRef(null)
  const chartObjRef = useRef(null)
  const hasInitRef = useRef(false)

  const processed = useMemo(() => {
    if (!candles?.length) return null
    const ema8 = calcEMA(candles, 8)
    const ema21 = calcEMA(candles, 21)
    const rsi = showRSI ? calcRSI(candles, 14) : []
    const bb = calcBollinger(candles, 20, 2)

    const ohlc = [], vol = [], e8 = [], e21 = [], bU = [], bL = [], rsiD = []
    for (let i = 0; i < candles.length; i++) {
      const c = candles[i]
      ohlc.push({ time: c.t, open: c.o, high: c.h, low: c.l, close: c.c })
      vol.push({ time: c.t, value: c.v, color: c.c >= c.o ? C.volBull : C.volBear })
      if (ema8[i] != null) e8.push({ time: c.t, value: ema8[i] })
      if (ema21[i] != null) e21.push({ time: c.t, value: ema21[i] })
      if (bb.upper[i] != null) bU.push({ time: c.t, value: bb.upper[i] })
      if (bb.lower[i] != null) bL.push({ time: c.t, value: bb.lower[i] })
      if (rsi[i] != null) rsiD.push({ time: c.t, value: rsi[i] })
    }
    return { ohlc, vol, e8, e21, bU, bL, rsiD }
  }, [candles, showRSI])

  useEffect(() => {
    if (!containerRef.current || !processed?.ohlc?.length) return

    if (chartObjRef.current) {
      chartObjRef.current.remove()
      chartObjRef.current = null
    }

    const chartH = showRSI ? height - 60 : height
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: chartH,
      layout: { background: { color: C.bg }, textColor: C.text, fontSize: 9 },
      grid: { vertLines: { color: C.grid }, horzLines: { color: C.grid } },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: C.crosshair, width: 1, style: 3, labelBackgroundColor: "#1a1a2e" },
        horzLine: { color: C.crosshair, width: 1, style: 3, labelBackgroundColor: "#1a1a2e" },
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.04)",
        scaleMargins: { top: 0.05, bottom: 0.18 },
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.04)",
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { mouseWheel: true, pinch: true },
    })

    // Candlesticks
    const cs = chart.addCandlestickSeries({
      upColor: C.bullCandle, downColor: C.bearCandle,
      wickUpColor: C.bullCandle, wickDownColor: C.bearCandle,
      borderUpColor: C.bullCandle, borderDownColor: C.bearCandle,
    })
    cs.setData(processed.ohlc)

    // Volume
    const vs = chart.addHistogramSeries({
      priceFormat: { type: "volume" }, priceScaleId: "vol",
    })
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } })
    vs.setData(processed.vol)

    // EMA 8
    const e8s = chart.addLineSeries({ color: C.ema8, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })
    e8s.setData(processed.e8)

    // EMA 21
    const e21s = chart.addLineSeries({ color: C.ema21, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })
    e21s.setData(processed.e21)

    // Bollinger Bands
    const bbUs = chart.addLineSeries({ color: C.bbLine, lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })
    bbUs.setData(processed.bU)
    const bbLs = chart.addLineSeries({ color: C.bbLine, lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })
    bbLs.setData(processed.bL)

    // Strategy overlays (only on primary/trade chart)
    if (showOverlays && strategy) {
      // VWAP
      const vwapPrice = strategy.indicators?.vwap_price
      if (vwapPrice && vwapPrice > 0) {
        cs.createPriceLine({ price: vwapPrice, color: C.vwap, lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: false, title: "VWAP" })
      }

      // FVG zone (drawn as two price lines marking the gap)
      if (strategy.fvg_detail) {
        const fvgHi = strategy.fvg_detail.high
        const fvgLo = strategy.fvg_detail.low
        if (fvgHi && fvgLo) {
          cs.createPriceLine({ price: fvgHi, color: "rgba(255,193,7,0.3)", lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: false, title: "FVG Hi" })
          cs.createPriceLine({ price: fvgLo, color: "rgba(255,193,7,0.3)", lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: false, title: "FVG Lo" })
        }
      }

      // Channel support/resistance
      if (strategy.channel_detail) {
        const chUp = strategy.channel_detail.upper
        const chLo = strategy.channel_detail.lower
        if (chUp) cs.createPriceLine({ price: chUp, color: C.structure, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: "Chan R" })
        if (chLo) cs.createPriceLine({ price: chLo, color: C.structure, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: "Chan S" })
      }
    }

    // Position markers (on ALL charts)
    if (position?.entry_price) {
      const isLong = position.direction === "long"
      const ec = isLong ? C.entry.long : C.entry.short
      const typeLabel = (position.entry_type || "").replace(/_/g, " ").toUpperCase()

      cs.createPriceLine({ price: position.entry_price, color: ec, lineWidth: 2, lineStyle: LineStyle.Solid, axisLabelVisible: true, title: isPrimary ? ("ENTRY " + typeLabel) : "Entry" })
      if (position.stop_loss) cs.createPriceLine({ price: position.stop_loss, color: C.sl, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "SL" })
      if (position.tp1) cs.createPriceLine({ price: position.tp1, color: C.tp1, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "TP1" })
      if (position.tp2 && isPrimary) cs.createPriceLine({ price: position.tp2, color: C.tp2, lineWidth: 1, lineStyle: LineStyle.LargeDashed, axisLabelVisible: true, title: "TP2" })
      if (position.tp3 && isPrimary) cs.createPriceLine({ price: position.tp3, color: C.tp3, lineWidth: 1, lineStyle: LineStyle.LargeDashed, axisLabelVisible: true, title: "TP3" })

      // Entry marker arrow
      if (position.entry_time) {
        try {
          const entryTs = Math.floor(new Date(position.entry_time).getTime() / 1000)
          cs.setMarkers([{
            time: entryTs,
            position: isLong ? "belowBar" : "aboveBar",
            color: ec,
            shape: isLong ? "arrowUp" : "arrowDown",
            text: isPrimary ? ((position.quality_tier || "") + " " + (position.direction || "").toUpperCase()) : (position.direction || "").toUpperCase(),
          }])
        } catch (e) { /* marker timestamp might be outside candle range */ }
      }
    }

    // Only fit content on first load -- preserve user zoom after that
    if (!hasInitRef.current) {
      chart.timeScale().fitContent()
      hasInitRef.current = true
    }

    const resize = () => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth })
    }
    window.addEventListener("resize", resize)
    chartObjRef.current = chart

    return () => {
      window.removeEventListener("resize", resize)
      chart.remove()
      chartObjRef.current = null
    }
  }, [processed, position, strategy, height, showRSI, showOverlays, isPrimary])

  // RSI sub-chart
  const rsiRef = useRef(null)
  const rsiChartRef = useRef(null)

  useEffect(() => {
    if (!showRSI || !rsiRef.current || !processed?.rsiD?.length) return
    if (rsiChartRef.current) { rsiChartRef.current.remove(); rsiChartRef.current = null }

    const chart = createChart(rsiRef.current, {
      width: rsiRef.current.clientWidth,
      height: 55,
      layout: { background: { color: C.bg }, textColor: "#444", fontSize: 8 },
      grid: { vertLines: { color: C.grid }, horzLines: { color: C.grid } },
      crosshair: { mode: CrosshairMode.Normal, vertLine: { visible: false }, horzLine: { color: "#444", width: 1, style: 3 } },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.04)", scaleMargins: { top: 0.05, bottom: 0.05 } },
      timeScale: { visible: false },
      handleScroll: false, handleScale: false,
    })
    const rs = chart.addLineSeries({ color: C.rsi, lineWidth: 1.5, priceLineVisible: false, lastValueVisible: true, crosshairMarkerVisible: true })
    rs.setData(processed.rsiD)
    rs.createPriceLine({ price: 70, color: "rgba(255,23,68,0.2)", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false })
    rs.createPriceLine({ price: 30, color: "rgba(0,230,118,0.2)", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false })
    rs.createPriceLine({ price: 50, color: "rgba(100,100,130,0.1)", lineWidth: 1, lineStyle: LineStyle.LargeDashed, axisLabelVisible: false })
    chart.timeScale().fitContent()

    const resize = () => { if (rsiRef.current) chart.applyOptions({ width: rsiRef.current.clientWidth }) }
    window.addEventListener("resize", resize)
    rsiChartRef.current = chart
    return () => { window.removeEventListener("resize", resize); chart.remove(); rsiChartRef.current = null }
  }, [processed?.rsiD, showRSI])

  if (!candles?.length) {
    return (
      <div className="card flex items-center justify-center text-gray-600 text-[10px]" style={{ height }}>
        <div className="w-2 h-2 rounded-full bg-gray-600 animate-pulse mr-2" />
        Loading {label}...
      </div>
    )
  }

  return (
    <div className="card p-2 relative overflow-hidden">
      {/* Chart label */}
      <div className="flex items-center justify-between mb-1 px-1">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-white">{label}</span>
          {position?.direction && (
            <span className={`text-[8px] px-1.5 py-0.5 rounded font-bold uppercase ${position.direction === "long" ? "bg-green-400/10 text-green-400" : "bg-red-400/10 text-red-400"}`}>
              {position.direction}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-0.5"><span className="w-2 h-0.5 rounded" style={{ background: C.ema8 }} /><span className="text-[7px] text-gray-500">8</span></span>
          <span className="flex items-center gap-0.5"><span className="w-2 h-0.5 rounded" style={{ background: C.ema21 }} /><span className="text-[7px] text-gray-500">21</span></span>
          <span className="flex items-center gap-0.5"><span className="w-2 h-0.5 rounded" style={{ background: C.bbLine }} /><span className="text-[7px] text-gray-500">BB</span></span>
        </div>
      </div>
      {/* Main chart */}
      <div ref={containerRef} style={{ width: "100%" }} />
      {/* RSI */}
      {showRSI && (
        <div className="mt-0.5">
          <div className="text-[7px] text-gray-500 px-1 mb-0.5">RSI 14</div>
          <div ref={rsiRef} style={{ width: "100%" }} />
        </div>
      )}
      {/* Pattern/confirmation tags (primary chart only) */}
      {showOverlays && strategy && (strategy.patterns_detected?.length > 0 || strategy.confirmations?.length > 0) && (
        <div className="flex flex-wrap gap-1 px-1 mt-1.5 pb-0.5">
          {(strategy.patterns_detected || []).map((p, i) => (
            <span key={"p" + i} className="text-[7px] px-1 py-0.5 rounded bg-purple-400/10 text-purple-400 border border-purple-400/20">
              {p.replace(/_/g, " ")}
            </span>
          ))}
          {(strategy.confirmations || []).map((c, i) => (
            <span key={"c" + i} className="text-[7px] px-1 py-0.5 rounded bg-green-400/10 text-green-400 border border-green-400/20">
              {c.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

/* -- Main multi-chart component -- */
export default function TradingCharts() {
  const { data } = useApi("/charts", 15000)

  const pos = data?.position || null
  const strat = data?.strategy || null
  const tradeTf = data?.trade_tf
  const tradeLabel = tradeTf
    ? `${tradeTf.toUpperCase()} -- ${(pos?.entry_type || "").replace(/_/g, " ").toUpperCase() || "Trade TF"}`
    : null

  return (
    <div className="flex flex-col gap-3">
      {/* PRIMARY: Big trade timeframe chart (or daily if no position) */}
      {tradeTf && data?.trade?.length > 0 ? (
        <ChartPane
          candles={data.trade}
          height={400}
          label={tradeLabel}
          position={pos}
          strategy={strat}
          showRSI={true}
          showOverlays={true}
          isPrimary={true}
        />
      ) : (
        <ChartPane
          candles={data?.daily || []}
          height={400}
          label="DAILY -- XLM-USD"
          position={pos}
          strategy={strat}
          showRSI={true}
          showOverlays={true}
          isPrimary={true}
        />
      )}

      {/* SECONDARY: 2x2 grid of context charts */}
      <div className="grid grid-cols-2 gap-3">
        {/* 1-Minute -- live scalp */}
        <ChartPane
          candles={data?.minute || []}
          height={200}
          label="1M -- Live"
          position={pos}
          strategy={null}
          showRSI={false}
          showOverlays={false}
          isPrimary={false}
        />

        {/* Daily -- medium term */}
        <ChartPane
          candles={data?.daily || []}
          height={200}
          label="DAILY -- 90 Days"
          position={pos}
          strategy={null}
          showRSI={false}
          showOverlays={false}
          isPrimary={false}
        />

        {/* Monthly -- macro trend */}
        <ChartPane
          candles={data?.monthly || []}
          height={200}
          label="MONTHLY -- Macro"
          position={pos}
          strategy={null}
          showRSI={false}
          showOverlays={false}
          isPrimary={false}
        />
      </div>

      {/* Strategy context summary */}
      {strat && (strat.vol_phase !== "COMPRESSION" || strat.structure_bias !== "neutral" || strat.atr_expanding || strat.bb_expanding) && (
        <div className="flex items-center gap-2 flex-wrap px-1">
          <span className="text-[8px] uppercase tracking-widest text-gray-600">Context:</span>
          {strat.structure_bias !== "neutral" && (
            <span className={`text-[8px] px-1.5 py-0.5 rounded border ${strat.structure_bias === "bullish" ? "bg-green-400/10 text-green-400 border-green-400/20" : "bg-red-400/10 text-red-400 border-red-400/20"}`}>
              Structure: {strat.structure_bias}
            </span>
          )}
          {strat.htf_trend !== "neutral" && (
            <span className="text-[8px] px-1.5 py-0.5 rounded bg-blue-400/10 text-blue-400 border border-blue-400/20">
              HTF: {strat.htf_trend}
            </span>
          )}
          {strat.vol_phase !== "COMPRESSION" && (
            <span className="text-[8px] px-1.5 py-0.5 rounded bg-amber-400/10 text-amber-400 border border-amber-400/20">
              Vol: {strat.vol_phase}
            </span>
          )}
          {strat.atr_expanding && <span className="text-[8px] px-1.5 py-0.5 rounded bg-amber-400/10 text-amber-400 border border-amber-400/20">ATR Expanding</span>}
          {strat.bb_expanding && <span className="text-[8px] px-1.5 py-0.5 rounded bg-cyan-400/10 text-cyan-400 border border-cyan-400/20">BB Expanding</span>}
        </div>
      )}
    </div>
  )
}
