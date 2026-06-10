import React from "react"
import { useApi } from "../hooks"

function Ticker({ data, icon }) {
  if (!data) return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.03] animate-pulse">
      <span className="text-[10px] text-gray-600">{icon}</span>
      <span className="text-[10px] text-gray-600">--</span>
    </div>
  )
  const up = data.change >= 0
  return (
    <div className={`flex items-center gap-2.5 px-3 py-1.5 rounded-lg border ${up ? "bg-green-400/[0.04] border-green-400/10" : "bg-red-400/[0.04] border-red-400/10"}`}>
      <span className="text-[10px] text-gray-400 font-medium">{data.symbol}</span>
      <span className="font-mono text-[11px] text-white font-bold">
        {data.price >= 1000 ? `$${(data.price / 1000).toFixed(1)}k` : `$${data.price.toLocaleString()}`}
      </span>
      <span className={`font-mono text-[10px] font-medium ${up ? "text-green-400" : "text-red-400"}`}>
        {up ? "+" : ""}{data.change_pct.toFixed(2)}%
      </span>
    </div>
  )
}

export default function MarketContextBar() {
  const { data } = useApi("/market-context", 30000)
  return (
    <div className="flex items-center gap-2 mb-3 flex-wrap">
      <span className="text-[8px] uppercase tracking-widest text-gray-600 mr-1">Markets</span>
      <Ticker data={data?.btc} icon="BTC" />
      <Ticker data={data?.spx} icon="SPX" />
      <Ticker data={data?.ndx} icon="NDX" />
    </div>
  )
}
