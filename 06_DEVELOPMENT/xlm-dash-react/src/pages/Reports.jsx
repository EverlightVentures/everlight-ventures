import React, { useState } from "react"
import { useApi, formatUSD } from "../hooks"

const SUBJECT_COLORS = {
  "Legal / Compliance": { bg: "bg-purple-400/10", text: "text-purple-400", border: "border-purple-400/20" },
  "Deal Packages": { bg: "bg-amber-400/10", text: "text-amber-400", border: "border-amber-400/20" },
  "Operations Reports": { bg: "bg-blue-400/10", text: "text-blue-400", border: "border-blue-400/20" },
  "Wholesale": { bg: "bg-green-400/10", text: "text-green-400", border: "border-green-400/20" },
  "Contracts": { bg: "bg-red-400/10", text: "text-red-400", border: "border-red-400/20" },
  "Email Drafts": { bg: "bg-pink-400/10", text: "text-pink-400", border: "border-pink-400/20" },
  "General": { bg: "bg-gray-400/10", text: "text-gray-400", border: "border-gray-400/20" },
}

const STATUS_STYLE = {
  active: { color: "text-green-400", bg: "bg-green-400/10", border: "border-green-400/20", label: "ACTIVE" },
  under_contract: { color: "text-amber-400", bg: "bg-amber-400/10", border: "border-amber-400/20", label: "CONTRACT" },
  closing: { color: "text-blue-400", bg: "bg-blue-400/10", border: "border-blue-400/20", label: "CLOSING" },
  closed: { color: "text-purple-400", bg: "bg-purple-400/10", border: "border-purple-400/20", label: "CLOSED" },
  dead: { color: "text-gray-500", bg: "bg-gray-500/10", border: "border-gray-500/20", label: "DEAD" },
}

const DOC_TYPE_META = {
  seller_outreach: { emoji: "✉", label: "Seller Outreach" },
  deal_sheet: { emoji: "📄", label: "Deal Sheet" },
  assignment_contract: { emoji: "📝", label: "Assignment Contract" },
  buyer_pitch: { emoji: "🎯", label: "Buyer Pitch" },
  title_engagement: { emoji: "🏛", label: "Title Engagement" },
  signed_contract: { emoji: "✅", label: "Signed Contract" },
  closing_statement: { emoji: "💰", label: "Closing Statement" },
  payment_receipt: { emoji: "💸", label: "Payment Receipt" },
  addendum: { emoji: "📌", label: "Addendum" },
  note: { emoji: "📓", label: "Note" },
  other: { emoji: "📃", label: "Other" },
}

const DOC_STATUS_COLOR = {
  draft: "text-gray-500",
  sent: "text-blue-400",
  signed: "text-green-400",
  final: "text-green-400",
  voided: "text-red-400",
}

// ── Client Files Sub-Page ──
function ClientFiles() {
  const { data: stats } = useApi("/client-files/stats", 30000)
  const { data: files } = useApi("/client-files", 15000)
  const [statusFilter, setStatusFilter] = useState("all")
  const [expandedFile, setExpandedFile] = useState(null)
  const [previewDoc, setPreviewDoc] = useState(null)

  const filtered = statusFilter === "all"
    ? (files || [])
    : (files || []).filter(f => f.status === statusFilter)

  if (previewDoc) {
    return (
      <div className="flex flex-col gap-4">
        <button onClick={() => setPreviewDoc(null)}
          className="self-start px-4 py-2 rounded-lg bg-white/5 text-xs text-gray-400 hover:text-amber-400 hover:bg-amber-400/10 transition-all flex items-center gap-2">
          <span>&larr;</span> Back to Client Files
        </button>
        <div className="card p-0 overflow-hidden rounded-xl" style={{ height: "calc(100vh - 160px)" }}>
          <iframe src={`/client-file-doc/${previewDoc.id}`} className="w-full h-full border-0" title={previewDoc.title} />
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5">
      {/* KPIs */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
        {[
          { label: "Total", value: stats?.total || 0, color: "text-white" },
          { label: "Active", value: stats?.active || 0, color: "text-green-400" },
          { label: "Contract", value: stats?.under_contract || 0, color: "text-amber-400" },
          { label: "Closing", value: stats?.closing || 0, color: "text-blue-400" },
          { label: "Closed", value: stats?.closed || 0, color: "text-purple-400" },
          { label: "Pipeline $", value: `$${(stats?.pipeline_fees || 0).toLocaleString()}`, color: "text-green-400" },
        ].map(kpi => (
          <div key={kpi.label} className="card text-center py-3">
            <div className={`text-xl font-bold font-mono ${kpi.color}`}>{kpi.value}</div>
            <div className="text-[10px] text-gray-500 tracking-wider uppercase">{kpi.label}</div>
          </div>
        ))}
      </div>

      {stats?.closed_revenue > 0 && (
        <div className="card text-center py-3 border border-green-400/20 bg-green-400/5">
          <span className="text-green-400 font-bold text-lg font-mono">
            Closed Revenue: ${(stats.closed_revenue).toLocaleString()}
          </span>
        </div>
      )}

      {/* Status filter chips */}
      <div className="flex gap-2 flex-wrap">
        {["all", "active", "under_contract", "closing", "closed", "dead"].map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-full text-[11px] font-medium transition-all ${
              statusFilter === s
                ? "bg-amber-400/20 text-amber-400 border border-amber-400/30"
                : "bg-white/5 text-gray-500 hover:text-gray-300"
            }`}>
            {s === "all" ? "All" : (STATUS_STYLE[s]?.label || s)}
          </button>
        ))}
      </div>

      {/* Client File Cards */}
      {filtered.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl opacity-10 mb-3">📁</div>
          <div className="text-sm text-gray-500">No client files yet</div>
          <div className="text-xs text-gray-600 mt-1">Files appear when deals enter the wholesale pipeline</div>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map(cf => {
            const ss = STATUS_STYLE[cf.status] || STATUS_STYLE.dead
            const isExpanded = expandedFile === cf.id
            return (
              <div key={cf.id} className="card overflow-hidden">
                {/* Card header */}
                <div className="flex justify-between items-start cursor-pointer" onClick={() => setExpandedFile(isExpanded ? null : cf.id)}>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <div className={`w-1 h-8 rounded-full ${ss.bg.replace("/10", "")}`} />
                      <div>
                        <div className="text-sm font-semibold">{cf.property_address}</div>
                        <div className="text-[11px] text-gray-500">{cf.city}, {cf.state} · {cf.client_name}</div>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full border ${ss.bg} ${ss.color} ${ss.border}`}>
                      {ss.label}
                    </span>
                    <span className="text-gray-600 text-xs">{isExpanded ? "▲" : "▼"}</span>
                  </div>
                </div>

                {/* Financial row */}
                <div className="grid grid-cols-4 gap-4 mt-3 px-3">
                  {[
                    { label: "Contract", value: cf.contract_price, color: "text-white" },
                    { label: "Fee", value: cf.assignment_fee, color: "text-green-400" },
                    { label: "ARV", value: cf.estimated_arv, color: "text-amber-400" },
                    { label: "Buyer $", value: cf.buyer_price, color: "text-white" },
                  ].map(f => (
                    <div key={f.label} className="text-center">
                      <div className="text-[9px] text-gray-600 uppercase">{f.label}</div>
                      <div className={`text-xs font-bold font-mono ${f.color}`}>
                        ${Number(f.value || 0).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>

                {cf.buyer_name && (
                  <div className="mt-2 px-3">
                    <span className="text-[10px] bg-amber-400/10 text-amber-400 px-2 py-0.5 rounded-full border border-amber-400/20">
                      Buyer: {cf.buyer_name}
                    </span>
                  </div>
                )}

                {/* Expanded: Document Timeline */}
                {isExpanded && <ClientDocTimeline fileId={cf.id} onPreview={setPreviewDoc} />}

                <div className="text-[9px] text-gray-700 mt-3 px-3">
                  Updated {cf.updated_at?.slice(0, 10)} · {cf.id?.slice(0, 8)}...
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── Document Timeline (loaded on expand) ──
function ClientDocTimeline({ fileId, onPreview }) {
  const { data: docs } = useApi(`/client-files/${fileId}/documents`, 30000)

  const allSteps = [
    "seller_outreach", "deal_sheet", "assignment_contract", "buyer_pitch",
    "title_engagement", "signed_contract", "closing_statement", "payment_receipt",
  ]
  const existingTypes = new Set((docs || []).map(d => d.doc_type))

  return (
    <div className="mt-4 pt-4 border-t border-white/[0.04]">
      <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-3 px-3">
        Document Timeline · {(docs || []).length} docs
      </div>
      <div className="relative pl-8 space-y-3">
        {/* Vertical line */}
        <div className="absolute left-[14px] top-0 bottom-0 w-px bg-white/[0.06]" />

        {allSteps.map((step, i) => {
          const doc = (docs || []).find(d => d.doc_type === step)
          const meta = DOC_TYPE_META[step] || DOC_TYPE_META.other
          const completed = existingTypes.has(step)

          return (
            <div key={step} className="relative flex items-start gap-3">
              {/* Step circle */}
              <div className={`absolute -left-8 w-7 h-7 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${
                completed ? "bg-green-400/20 text-green-400" : "bg-white/[0.04] text-gray-600"
              }`}>
                {completed ? "✓" : i + 1}
              </div>

              {doc ? (
                <div className="flex-1 bg-white/[0.02] rounded-lg px-3 py-2.5 border border-white/[0.04] hover:border-amber-400/20 transition-all">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-xs font-medium flex items-center gap-1.5">
                        <span>{meta.emoji}</span> {meta.label}
                      </div>
                      <div className="text-[10px] text-gray-500 mt-0.5">{doc.title}</div>
                      <div className="flex gap-2 items-center mt-1">
                        <span className={`text-[9px] font-bold uppercase ${DOC_STATUS_COLOR[doc.status] || "text-gray-500"}`}>
                          {doc.status}
                        </span>
                        {doc.generated_by && <span className="text-[9px] text-gray-600">by {doc.generated_by}</span>}
                        <span className="text-[9px] text-gray-700">{doc.created_at?.slice(0, 16).replace("T", " ")}</span>
                      </div>
                    </div>
                    {doc.html_content && (
                      <button onClick={() => onPreview(doc)}
                        className="px-2.5 py-1 rounded-lg bg-amber-400/10 text-amber-400 text-[10px] font-medium hover:bg-amber-400/20 transition-all">
                        Preview
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex-1 bg-white/[0.01] rounded-lg px-3 py-2 border border-dashed border-white/[0.04]">
                  <div className="text-[11px] text-gray-600 flex items-center gap-1.5">
                    <span className="opacity-30">{meta.emoji}</span> {meta.label}
                    <span className="text-[9px] text-gray-700 ml-1">Pending</span>
                  </div>
                </div>
              )}
            </div>
          )
        })}

        {/* Extra docs (addenda, notes) */}
        {(docs || []).filter(d => !allSteps.includes(d.doc_type)).map(doc => {
          const meta = DOC_TYPE_META[doc.doc_type] || DOC_TYPE_META.other
          return (
            <div key={doc.id} className="relative flex items-start gap-3">
              <div className="absolute -left-8 w-7 h-7 rounded-full flex items-center justify-center text-xs bg-gray-500/20 text-gray-500">+</div>
              <div className="flex-1 bg-white/[0.02] rounded-lg px-3 py-2.5 border border-white/[0.04]">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="text-xs font-medium">{meta.emoji} {meta.label}</div>
                    <div className="text-[10px] text-gray-500">{doc.title}</div>
                  </div>
                  {doc.html_content && (
                    <button onClick={() => onPreview(doc)}
                      className="px-2.5 py-1 rounded-lg bg-amber-400/10 text-amber-400 text-[10px] font-medium hover:bg-amber-400/20 transition-all">
                      Preview
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Reports List (existing) ──
function ReportsList() {
  const { data: reports } = useApi("/reports", 30000)
  const [filter, setFilter] = useState("all")
  const [viewing, setViewing] = useState(null)

  const subjects = ["all", ...new Set((reports || []).map(r => r.subject))]
  const filtered = filter === "all" ? (reports || []) : (reports || []).filter(r => r.subject === filter)

  if (viewing) {
    return (
      <div className="flex flex-col gap-4">
        <button onClick={() => setViewing(null)}
          className="self-start px-4 py-2 rounded-lg bg-white/5 text-xs text-gray-400 hover:text-amber-400 hover:bg-amber-400/10 transition-all flex items-center gap-2">
          <span>&larr;</span> Back to Reports
        </button>
        <div className="card p-0 overflow-hidden rounded-xl" style={{ height: "calc(100vh - 160px)" }}>
          <iframe src={viewing.url} className="w-full h-full border-0" title={viewing.title} />
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Filter chips */}
      <div className="flex gap-2 flex-wrap">
        {subjects.map(s => {
          const count = s === "all" ? (reports || []).length : (reports || []).filter(r => r.subject === s).length
          return (
            <button key={s} onClick={() => setFilter(s)}
              className={`px-3 py-1.5 rounded-full text-[11px] font-medium transition-all ${
                filter === s
                  ? "bg-amber-400/20 text-amber-400 border border-amber-400/30"
                  : "bg-white/5 text-gray-500 hover:text-gray-300"
              }`}>
              {s === "all" ? "All" : s} ({count})
            </button>
          )
        })}
      </div>

      {/* Reports grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.map((r, i) => {
          const sc = SUBJECT_COLORS[r.subject] || SUBJECT_COLORS.General
          const dateStr = r.date || new Date(r.modified * 1000).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
          return (
            <div key={i}
              className="card cursor-pointer relative overflow-hidden group hover:border-amber-400/20 transition-all"
              onClick={() => setViewing(r)}>
              <div className={`absolute top-0 left-0 right-0 h-0.5 ${sc.bg.replace("/10", "")}`} />
              <div className="relative pt-1">
                <div className="flex justify-between items-start mb-2">
                  <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full border ${sc.bg} ${sc.text} ${sc.border}`}>
                    {r.subject}
                  </span>
                  <span className="text-[10px] text-gray-600">{dateStr}</span>
                </div>
                <div className="text-sm font-medium mb-1 group-hover:text-amber-400 transition-colors">{r.title}</div>
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-gray-600 font-mono">{r.filename?.slice(0, 30)}</span>
                  <span className="text-[10px] text-gray-600">{r.size_kb} KB</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-gray-600 text-sm">No reports match this filter.</div>
      )}
    </div>
  )
}

// ── Main Reports Page with Tabs ──
export default function Reports() {
  const [tab, setTab] = useState("client-files")

  const tabs = [
    { id: "client-files", label: "Client Files", icon: "📁" },
    { id: "reports", label: "Reports", icon: "R" },
  ]

  return (
    <div className="flex flex-col gap-5">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-700 flex items-center justify-center text-lg font-bold shadow-lg shadow-blue-500/20">R</div>
        <div>
          <div className="text-lg font-semibold">Reports Hub</div>
          <div className="text-xs text-gray-500">Client files, deal documents, and operational reports</div>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1.5 border-b border-white/[0.04] pb-0">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2.5 text-[12px] font-medium transition-all border-b-2 -mb-px ${
              tab === t.id
                ? "border-amber-400 text-amber-400"
                : "border-transparent text-gray-500 hover:text-gray-300"
            }`}>
            <span className="mr-1.5">{t.icon}</span>{t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "client-files" && <ClientFiles />}
      {tab === "reports" && <ReportsList />}
    </div>
  )
}
