import React from "react"
import MetricCard from "../components/MetricCard"

const VENTURES = [
  { name: "XLM Trading Bot", status: "live", revenue: "Active P&L", color: "from-amber-500 to-orange-600", stage: "Revenue" },
  { name: "AI Consulting", status: "pipeline", revenue: "$2-5k/build", color: "from-cyan-500 to-blue-600", stage: "Pipeline" },
  { name: "Onyx POS", status: "building", revenue: "$49/mo SaaS", color: "from-green-500 to-emerald-600", stage: "MVP" },
  { name: "Hive Mind SaaS", status: "building", revenue: "$29-149/mo", color: "from-purple-500 to-indigo-600", stage: "MVP" },
  { name: "Publishing", status: "live", revenue: "KDP + Direct", color: "from-pink-500 to-rose-600", stage: "Revenue" },
  { name: "Broker OS", status: "pipeline", revenue: "15-30% fees", color: "from-blue-500 to-indigo-600", stage: "Pipeline" },
  { name: "Alley Kingz", status: "building", revenue: "IAP + VIP $4.99", color: "from-red-500 to-orange-600", stage: "Dev" },
  { name: "Field Ops", status: "concept", revenue: "18% take rate", color: "from-gray-500 to-gray-600", stage: "Concept" },
]

const statusBadge = {
  live: "bg-green-400/10 text-green-400",
  pipeline: "bg-amber-400/10 text-amber-400",
  building: "bg-blue-400/10 text-blue-400",
  concept: "bg-gray-400/10 text-gray-400",
}

export default function BusinessOS() {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-700 flex items-center justify-center text-lg font-bold shadow-lg shadow-purple-500/20">!</div>
        <div>
          <div className="text-lg font-semibold">Business OS</div>
          <div className="text-xs text-gray-500">Everlight Ventures -- empire overview, ventures, milestones</div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <MetricCard label="Active Ventures" value={VENTURES.filter(v => v.status === "live").length} sub={`of ${VENTURES.length}`} color="text-green-400" />
        <MetricCard label="In Pipeline" value={VENTURES.filter(v => v.status === "pipeline").length} color="text-amber-400" />
        <MetricCard label="Building" value={VENTURES.filter(v => v.status === "building").length} color="text-blue-400" />
        <MetricCard label="Revenue Target" value="$10k/mo" color="text-amber-400" sub="across all streams" />
      </div>

      {/* Venture Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {VENTURES.map(v => (
          <div key={v.name} className="card relative overflow-hidden group">
            <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${v.color}`} />
            <div className="absolute -top-12 -right-12 w-32 h-32 bg-gradient-to-bl from-white/[0.02] to-transparent rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative pt-2">
              <div className="flex justify-between items-start mb-2">
                <div className="text-sm font-semibold">{v.name}</div>
                <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full ${statusBadge[v.status]}`}>{v.status}</span>
              </div>
              <div className="text-xs text-gray-500 mb-2">{v.revenue}</div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1 bg-gray-800 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full bg-gradient-to-r ${v.color}`} style={{
                    width: v.status === "live" ? "85%" : v.status === "pipeline" ? "50%" : v.status === "building" ? "30%" : "10%"
                  }} />
                </div>
                <span className="text-[9px] text-gray-600">{v.stage}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Infrastructure */}
      <div className="card">
        <div className="text-sm font-medium mb-3">Infrastructure Stack</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          {[
            { label: "Oracle Cloud", detail: "E5 VM -- 2 cores, 16GB RAM", status: "online" },
            { label: "Cloudflare Pages", detail: "everlightventures.io", status: "online" },
            { label: "Supabase", detail: "Database + Edge Functions", status: "online" },
            { label: "Stripe", detail: "Payments + Subscriptions", status: "ready" },
            { label: "GitHub", detail: "Version control + CI/CD", status: "online" },
            { label: "Slack", detail: "13 channels + bot tokens", status: "online" },
            { label: "Resend", detail: "42 email addresses", status: "ready" },
            { label: "n8n", detail: "Workflow automation", status: "degraded" },
          ].map(i => (
            <div key={i.label} className="bg-white/[0.03] rounded-lg p-2.5 flex justify-between items-start">
              <div>
                <div className="font-medium">{i.label}</div>
                <div className="text-[10px] text-gray-600">{i.detail}</div>
              </div>
              <span className={`w-1.5 h-1.5 rounded-full mt-1 ${i.status === "online" ? "bg-green-400" : i.status === "ready" ? "bg-amber-400" : "bg-orange-400"}`} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
