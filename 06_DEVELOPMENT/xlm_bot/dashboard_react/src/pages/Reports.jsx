import React, { useState, useMemo } from "react"
import { useApi, timeAgo } from "../hooks"

const CATEGORIES = ["all", "pipeline", "deals", "outreach", "operations", "trading"]

const FALLBACK_REPORTS = [
  { title: "Wholesale Pipeline Report", category: "pipeline", filename: "wholesale_pipeline_report.html", date: "2026-04-07", size: "24 KB" },
  { title: "Buyer Database Export", category: "deals", filename: "buyer_database_export.html", date: "2026-04-06", size: "18 KB" },
  { title: "Weekly Outreach Summary", category: "outreach", filename: "weekly_outreach_summary.html", date: "2026-04-05", size: "12 KB" },
  { title: "Broker Revenue Report", category: "deals", filename: "broker_revenue_report.html", date: "2026-04-04", size: "15 KB" },
  { title: "Hive Operations Log", category: "operations", filename: "hive_operations_log.html", date: "2026-04-03", size: "31 KB" },
  { title: "XLM Trading Summary", category: "trading", filename: "xlm_trading_summary.html", date: "2026-04-02", size: "22 KB" },
  { title: "Lead Scoring Analysis", category: "pipeline", filename: "lead_scoring_analysis.html", date: "2026-04-01", size: "9 KB" },
  { title: "Deal Prep Package", category: "deals", filename: "deal_prep_package.html", date: "2026-03-31", size: "45 KB" },
  { title: "Agent Performance Review", category: "operations", filename: "agent_performance_review.html", date: "2026-03-30", size: "14 KB" },
  { title: "Daily P&L Report", category: "trading", filename: "daily_pnl_report.html", date: "2026-03-29", size: "8 KB" },
]

const CATEGORY_COLORS = {
  pipeline: "bg-blue-400/10 text-blue-300 border-blue-400/30",
  deals: "bg-green-400/10 text-green-300 border-green-400/30",
  outreach: "bg-purple-400/10 text-purple-300 border-purple-400/30",
  operations: "bg-amber-400/10 text-amber-300 border-amber-400/30",
  trading: "bg-cyan-400/10 text-cyan-300 border-cyan-400/30",
}

const REPORT_BASE_URL = "http://129.159.38.250:8504/reports"

export default function Reports() {
  const { data, error } = useApi("/api/django/reports", 60000)
  const [activeCategory, setActiveCategory] = useState("all")
  const [viewingReport, setViewingReport] = useState(null)

  const reports = useMemo(() => {
    const raw = data?.reports || data
    if (Array.isArray(raw) && raw.length > 0) return raw
    return FALLBACK_REPORTS
  }, [data])

  const filtered = useMemo(() => {
    if (activeCategory === "all") return reports
    return reports.filter(r => r.category === activeCategory)
  }, [reports, activeCategory])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-amber-400 tracking-wider">REPORTS</h1>
          <p className="text-xs text-gray-500 mt-1">Styled HTML Reports Hub</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${error ? "bg-yellow-400" : "bg-green-400"} animate-pulse`} />
          <span className="text-[9px] text-gray-500 font-mono">{error ? "using cached" : "60s refresh"}</span>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex gap-1.5 flex-wrap">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-4 py-2 rounded-full text-[11px] font-medium transition-all ${
              activeCategory === cat
                ? "bg-amber-400/20 text-amber-400 border border-amber-400/30"
                : "bg-white/[0.05] text-gray-500 hover:text-gray-300 hover:bg-white/[0.08]"
            }`}
          >
            {cat === "all" ? "All" : cat.charAt(0).toUpperCase() + cat.slice(1)}
            {cat !== "all" && (
              <span className="ml-1.5 text-[9px] opacity-60">
                {reports.filter(r => r.category === cat).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Report Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.length === 0 ? (
          <div className="col-span-full card text-center py-8 text-gray-600 text-xs">No reports in this category</div>
        ) : (
          filtered.map((report, i) => {
            const catColor = CATEGORY_COLORS[report.category] || CATEGORY_COLORS.operations
            return (
              <div
                key={report.filename || i}
                className="card hover:border-amber-400/20 transition-all cursor-pointer group"
                onClick={() => setViewingReport(report)}
              >
                <div className="flex items-start justify-between mb-3">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide border ${catColor}`}>
                    {report.category}
                  </span>
                  <span className="text-[9px] text-gray-600 font-mono">{report.size || "--"}</span>
                </div>
                <div className="text-sm text-gray-200 font-medium group-hover:text-amber-400 transition-colors mb-2">
                  {report.title || report.filename}
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[9px] text-gray-500">{report.date || "--"}</span>
                  <span className="text-[9px] text-amber-400/60 opacity-0 group-hover:opacity-100 transition-opacity">View Report --&gt;</span>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Report Viewer Modal */}
      {viewingReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={() => setViewingReport(null)}>
          <div className="w-[95vw] h-[90vh] bg-[#0a0a0f] border border-[#222] rounded-xl overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#222]">
              <div className="flex items-center gap-3">
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide border ${CATEGORY_COLORS[viewingReport.category] || ""}`}>
                  {viewingReport.category}
                </span>
                <span className="text-sm text-gray-200 font-medium">{viewingReport.title}</span>
              </div>
              <div className="flex items-center gap-3">
                <a
                  href={`${REPORT_BASE_URL}/${viewingReport.filename}?raw=1`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[10px] text-amber-400 hover:text-amber-300 transition-colors"
                >
                  Open in New Tab
                </a>
                <button onClick={() => setViewingReport(null)} className="text-gray-500 hover:text-white transition-colors text-lg font-bold px-2">x</button>
              </div>
            </div>
            {/* iFrame */}
            <iframe
              src={`${REPORT_BASE_URL}/${viewingReport.filename}?raw=1`}
              className="flex-1 w-full border-0 bg-white"
              title={viewingReport.title}
            />
          </div>
        </div>
      )}
    </div>
  )
}
