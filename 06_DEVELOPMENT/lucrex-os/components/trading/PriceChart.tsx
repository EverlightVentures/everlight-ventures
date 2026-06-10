"use client";
import { useEffect, useRef, useState } from "react";
import { createChart, CrosshairMode, type IChartApi, type ISeriesApi } from "lightweight-charts";

type Candle = { t: number; o: number; h: number; l: number; c: number; v: number };

const COLORS = {
  bg:         "#0A0A0A",
  grid:       "rgba(255,255,255,0.03)",
  text:       "#666",
  crosshair:  "#888",
  bull:       "#22C55E",
  bear:       "#EF4444",
  ema8:       "#06B6D4",
  ema21:      "#D4A843",
  volBull:    "rgba(34,197,94,0.25)",
  volBear:    "rgba(239,68,68,0.25)",
};

function calcEMA(data: Candle[], period: number): Array<{ time: number; value: number }> {
  const k = 2 / (period + 1);
  let prev: number | null = null;
  const out: Array<{ time: number; value: number }> = [];
  for (const c of data) {
    if (prev == null) prev = c.c;
    else prev = c.c * k + prev * (1 - k);
    out.push({ time: c.t, value: prev });
  }
  return out;
}

type Props = {
  basePath?: string;
  height?: number;
};

export function PriceChart({ basePath = "", height = 420 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const ema8Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const ema21Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const volRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { color: COLORS.bg },
        textColor: COLORS.text,
        fontFamily: "JetBrains Mono, ui-monospace, monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: COLORS.grid },
        horzLines: { color: COLORS.grid },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: COLORS.crosshair, width: 1, style: 2 },
        horzLine: { color: COLORS.crosshair, width: 1, style: 2 },
      },
      rightPriceScale: { borderColor: "#222" },
      timeScale: { borderColor: "#222", timeVisible: true, secondsVisible: false },
    });

    const candle = chart.addCandlestickSeries({
      upColor: COLORS.bull, downColor: COLORS.bear,
      borderUpColor: COLORS.bull, borderDownColor: COLORS.bear,
      wickUpColor: COLORS.bull, wickDownColor: COLORS.bear,
    });
    const ema8 = chart.addLineSeries({ color: COLORS.ema8, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
    const ema21 = chart.addLineSeries({ color: COLORS.ema21, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
    const vol = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
      color: COLORS.volBull,
    });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });

    chartRef.current = chart;
    candleRef.current = candle;
    ema8Ref.current = ema8;
    ema21Ref.current = ema21;
    volRef.current = vol;

    const onResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", onResize);

    let stop = false;
    async function loadCandles() {
      try {
        const r = await fetch(`${basePath}/api/trading/proxy/candles?limit=200`, { cache: "no-store" });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data: Candle[] = await r.json();
        if (stop || !candleRef.current) return;

        const sorted = [...data].sort((a, b) => a.t - b.t);
        candleRef.current.setData(sorted.map((c) => ({
          time: c.t as never, open: c.o, high: c.h, low: c.l, close: c.c,
        })));
        ema8Ref.current?.setData(calcEMA(sorted, 8).map((p) => ({ time: p.time as never, value: p.value })));
        ema21Ref.current?.setData(calcEMA(sorted, 21).map((p) => ({ time: p.time as never, value: p.value })));
        volRef.current?.setData(sorted.map((c) => ({
          time: c.t as never,
          value: c.v,
          color: c.c >= c.o ? COLORS.volBull : COLORS.volBear,
        })));
        chartRef.current?.timeScale().fitContent();
        setError(null);
        setLastUpdate(new Date().toLocaleTimeString());
      } catch (e) {
        setError(e instanceof Error ? e.message : "fetch failed");
      }
    }

    loadCandles();
    const id = setInterval(loadCandles, 15000);

    return () => {
      stop = true;
      clearInterval(id);
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [height, basePath]);

  return (
    <div className="relative">
      <div className="flex items-center justify-between px-1 mb-2">
        <div className="flex items-center gap-3 text-[11px] font-mono">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-3 rounded-sm" style={{ background: COLORS.ema8 }} /> EMA 8
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-3 rounded-sm" style={{ background: COLORS.ema21 }} /> EMA 21
          </span>
        </div>
        <div className="text-[10px] text-[var(--color-muted)] font-mono">
          {error ? <span className="text-[var(--color-alert)]">{error}</span> : lastUpdate ? `updated ${lastUpdate}` : "loading..."}
        </div>
      </div>
      <div ref={containerRef} style={{ height }} className="rounded-md overflow-hidden border border-[var(--color-border)]" />
    </div>
  );
}
