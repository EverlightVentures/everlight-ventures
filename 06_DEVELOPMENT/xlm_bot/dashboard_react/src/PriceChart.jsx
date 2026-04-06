import React, { useRef, useEffect, useMemo } from "react"
import { createChart, CrosshairMode } from "lightweight-charts"

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

/* -- Chart colors -- */
const COLORS = {
  bg: "#0a0a0f",
  grid: "rgba(255,255,255,0.03)",
  text: "#555",
  crosshair: "#666",
  bullCandle: "#00e676",
  bearCandle: "#ff1744",
  bullWick: "#00e676",
  bearWick: "#ff1744",
  ema8: "#00bcd4",
  ema21: "#ff9100",
  bbUpper: "rgba(179,136,255,0.35)",
  bbLower: "rgba(179,136,255,0.35)",
  volBull: "rgba(0,230,118,0.25)",
  volBear: "rgba(255,23,68,0.25)",
  rsiLine: "#b388ff",
  rsiOver: "rgba(255,23,68,0.25)",
  rsiUnder: "rgba(0,230,118,0.25)",
}

export default function PriceChart({ candles, height = 400, position }) {
  const mainRef = useRef(null)
  const rsiRef = useRef(null)
  const chartRef = useRef(null)
  const rsiChartRef = useRef(null)

  // Convert candle data
  const { ohlc, vol, ema8Data, ema21Data, bbUp, bbLo, rsiData } = useMemo(() => {
    if (!candles?.length) return { ohlc: [], vol: [], ema8Data: [], ema21Data: [], bbUp: [], bbLo: [], rsiData: [] }
    const ema8 = calcEMA(candles, 8)
    const ema21 = calcEMA(candles, 21)
    const rsi = calcRSI(candles, 14)
    const bb = calcBollinger(candles, 20, 2)

    const ohlc = []
    const vol = []
    const ema8Data = []
    const ema21Data = []
    const bbUp = []
    const bbLo = []
    const rsiData = []

    for (let i = 0; i < candles.length; i++) {
      const c = candles[i]
      const time = c.t
      ohlc.push({ time, open: c.o, high: c.h, low: c.l, close: c.c })
      vol.push({ time, value: c.v, color: c.c >= c.o ? COLORS.volBull : COLORS.volBear })
      if (ema8[i] != null) ema8Data.push({ time, value: ema8[i] })
      if (ema21[i] != null) ema21Data.push({ time, value: ema21[i] })
      if (bb.upper[i] != null) bbUp.push({ time, value: bb.upper[i] })
      if (bb.lower[i] != null) bbLo.push({ time, value: bb.lower[i] })
      if (rsi[i] != null) rsiData.push({ time, value: rsi[i] })
    }

    return { ohlc, vol, ema8Data, ema21Data, bbUp, bbLo, rsiData }
  }, [candles])

  const mainH = Math.round(height * 0.75)
  const rsiH = Math.round(height * 0.22)

  // Main chart
  useEffect(() => {
    if (!mainRef.current || !ohlc.length) return

    // Clean up previous chart
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
    }

    const chart = createChart(mainRef.current, {
      width: mainRef.current.clientWidth,
      height: mainH,
      layout: {
        background: { color: "transparent" },
        textColor: COLORS.text,
        fontSize: 10,
      },
      grid: {
        vertLines: { color: COLORS.grid },
        horzLines: { color: COLORS.grid },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: COLORS.crosshair, width: 1, style: 3, labelBackgroundColor: "#1a1a2e" },
        horzLine: { color: COLORS.crosshair, width: 1, style: 3, labelBackgroundColor: "#1a1a2e" },
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.05)",
        scaleMargins: { top: 0.05, bottom: 0.2 },
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.05)",
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { mouseWheel: true, pinch: true },
    })

    // Candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: COLORS.bullCandle,
      downColor: COLORS.bearCandle,
      wickUpColor: COLORS.bullWick,
      wickDownColor: COLORS.bearWick,
      borderUpColor: COLORS.bullCandle,
      borderDownColor: COLORS.bearCandle,
    })
    candleSeries.setData(ohlc)

    // Volume as histogram on same pane
    const volSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
      scaleMargins: { top: 0.85, bottom: 0 },
    })
    chart.priceScale("vol").applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    })
    volSeries.setData(vol)

    // EMA 8
    const ema8Series = chart.addLineSeries({
      color: COLORS.ema8,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })
    ema8Series.setData(ema8Data)

    // EMA 21
    const ema21Series = chart.addLineSeries({
      color: COLORS.ema21,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })
    ema21Series.setData(ema21Data)

    // Bollinger upper
    const bbUpSeries = chart.addLineSeries({
      color: COLORS.bbUpper,
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })
    bbUpSeries.setData(bbUp)

    // Bollinger lower
    const bbLoSeries = chart.addLineSeries({
      color: COLORS.bbLower,
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })
    bbLoSeries.setData(bbLo)

    // Position markers: entry, stop loss, TP levels
    if (position?.entry_price) {
      const isLong = position.direction === "long"
      // Entry line
      candleSeries.createPriceLine({
        price: position.entry_price,
        color: isLong ? "#00e676" : "#ff1744",
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: "ENTRY " + (position.entry_type || "").replace(/_/g, " ").toUpperCase(),
      })
      // Stop loss
      if (position.stop_loss) {
        candleSeries.createPriceLine({
          price: position.stop_loss,
          color: "rgba(255,23,68,0.6)",
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: "SL",
        })
      }
      // TP1
      if (position.tp1) {
        candleSeries.createPriceLine({
          price: position.tp1,
          color: "rgba(0,230,118,0.5)",
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: "TP1",
        })
      }
      // TP2
      if (position.tp2) {
        candleSeries.createPriceLine({
          price: position.tp2,
          color: "rgba(0,230,118,0.35)",
          lineWidth: 1,
          lineStyle: 3,
          axisLabelVisible: true,
          title: "TP2",
        })
      }
      // TP3
      if (position.tp3) {
        candleSeries.createPriceLine({
          price: position.tp3,
          color: "rgba(0,230,118,0.2)",
          lineWidth: 1,
          lineStyle: 3,
          axisLabelVisible: true,
          title: "TP3",
        })
      }
      // Entry time marker
      if (position.entry_time) {
        try {
          const entryTs = Math.floor(new Date(position.entry_time).getTime() / 1000)
          candleSeries.setMarkers([{
            time: entryTs,
            position: isLong ? "belowBar" : "aboveBar",
            color: isLong ? "#00e676" : "#ff1744",
            shape: isLong ? "arrowUp" : "arrowDown",
            text: (position.quality_tier || "") + " " + (position.direction || "").toUpperCase(),
          }])
        } catch (e) {}
      }
    }

    // Fit content
    chart.timeScale().fitContent()

    // Resize handler
    const resize = () => {
      if (mainRef.current) chart.applyOptions({ width: mainRef.current.clientWidth })
    }
    window.addEventListener("resize", resize)
    chartRef.current = chart

    return () => {
      window.removeEventListener("resize", resize)
      chart.remove()
      chartRef.current = null
    }
  }, [ohlc, vol, ema8Data, ema21Data, bbUp, bbLo, mainH, position])

  // RSI chart
  useEffect(() => {
    if (!rsiRef.current || !rsiData.length) return

    if (rsiChartRef.current) {
      rsiChartRef.current.remove()
      rsiChartRef.current = null
    }

    const chart = createChart(rsiRef.current, {
      width: rsiRef.current.clientWidth,
      height: rsiH,
      layout: {
        background: { color: "transparent" },
        textColor: COLORS.text,
        fontSize: 9,
      },
      grid: {
        vertLines: { color: COLORS.grid },
        horzLines: { color: COLORS.grid },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { visible: false },
        horzLine: { color: COLORS.crosshair, width: 1, style: 3 },
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.05)",
        scaleMargins: { top: 0.05, bottom: 0.05 },
      },
      timeScale: { visible: false },
      handleScroll: false,
      handleScale: false,
    })

    const rsiSeries = chart.addLineSeries({
      color: COLORS.rsiLine,
      lineWidth: 1.5,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: true,
    })
    rsiSeries.setData(rsiData)

    // Overbought/oversold lines
    rsiSeries.createPriceLine({ price: 70, color: COLORS.rsiOver, lineWidth: 1, lineStyle: 2, axisLabelVisible: false })
    rsiSeries.createPriceLine({ price: 30, color: COLORS.rsiUnder, lineWidth: 1, lineStyle: 2, axisLabelVisible: false })
    rsiSeries.createPriceLine({ price: 50, color: "rgba(100,100,130,0.15)", lineWidth: 1, lineStyle: 3, axisLabelVisible: false })

    chart.timeScale().fitContent()

    const resize = () => {
      if (rsiRef.current) chart.applyOptions({ width: rsiRef.current.clientWidth })
    }
    window.addEventListener("resize", resize)
    rsiChartRef.current = chart

    return () => {
      window.removeEventListener("resize", resize)
      chart.remove()
      rsiChartRef.current = null
    }
  }, [rsiData, rsiH])

  if (!candles?.length) {
    return (
      <div className="flex items-center justify-center text-gray-600 text-sm" style={{ height }}>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-gray-600 animate-pulse" />
          Loading chart data...
        </div>
      </div>
    )
  }

  return (
    <div className="chart-container">
      {/* Legend */}
      <div className="flex items-center gap-3 mb-1 px-1">
        <span className="text-[9px] text-gray-500">XLM-USD 15m</span>
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 rounded" style={{ background: COLORS.ema8 }} /><span className="text-[8px] text-gray-500">EMA 8</span></span>
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 rounded" style={{ background: COLORS.ema21 }} /><span className="text-[8px] text-gray-500">EMA 21</span></span>
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 rounded" style={{ background: COLORS.bbUpper, borderTop: "1px dashed rgba(179,136,255,0.5)" }} /><span className="text-[8px] text-gray-500">BB</span></span>
      </div>
      {/* Main candlestick chart */}
      <div ref={mainRef} style={{ width: "100%" }} />
      {/* RSI label */}
      <div className="flex items-center gap-2 mt-1 mb-0.5 px-1">
        <span className="text-[8px] text-gray-500">RSI 14</span>
        <span className="text-[8px] text-gray-600">70 / 30</span>
      </div>
      {/* RSI sub-chart */}
      <div ref={rsiRef} style={{ width: "100%" }} />
    </div>
  )
}
