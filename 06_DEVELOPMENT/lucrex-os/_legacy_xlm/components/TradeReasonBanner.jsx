import React from "react"
import { useApi } from "../hooks"

export default function TradeReasonBanner() {
  const { data } = useApi("/trade-reason", 10000)

  if (!data) return null

  const inTrade = data.status === "in_trade"
  const dir = data.direction || ""

  return (
    <div className={`rounded-xl px-5 py-3 border relative overflow-hidden ${
      inTrade
        ? dir === "long"
          ? "bg-green-400/[0.04] border-green-400/20"
          : "bg-red-400/[0.04] border-red-400/20"
        : "bg-white/[0.02] border-white/[0.06]"
    }`}>
      {/* Subtle glow */}
      <div className={`absolute -top-10 -right-10 w-32 h-32 rounded-full blur-[60px] pointer-events-none ${
        inTrade
          ? dir === "long" ? "bg-green-400/10" : "bg-red-400/10"
          : "bg-amber-400/[0.03]"
      }`} />

      <div className="relative flex items-center gap-3">
        {/* Status indicator */}
        <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
          inTrade ? "bg-green-400 pulse-live" : "bg-amber-400/60"
        }`} />

        {/* Headline */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className={`text-[10px] font-bold uppercase tracking-wider ${
              inTrade ? "text-green-400" : "text-amber-400/70"
            }`}>
              {inTrade ? "IN POSITION" : "SCANNING"}
            </span>
            <span className="text-[9px] text-gray-600 font-mono">
              live
            </span>
          </div>
          <div className={`text-sm font-medium leading-snug ${
            inTrade
              ? dir === "long" ? "text-green-300" : "text-red-300"
              : "text-gray-300"
          }`}>
            {data.headline}
          </div>
        </div>
      </div>
    </div>
  )
}
