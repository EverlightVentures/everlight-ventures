import React, { useState, useMemo } from "react"
import { useApi, formatUSD } from "../hooks"

// ── Status color map ──
const STATUS_CONFIG = {
  new:            { color: "bg-gray-400",   text: "text-gray-300",   border: "border-gray-400/30",  bg: "bg-gray-400/10" },
  contacted:      { color: "bg-blue-400",   text: "text-blue-300",   border: "border-blue-400/30",  bg: "bg-blue-400/10" },
  negotiating:    { color: "bg-amber-400",  text: "text-amber-300",  border: "border-amber-400/30", bg: "bg-amber-400/10" },
  under_contract: { color: "bg-green-400",  text: "text-green-300",  border: "border-green-400/30", bg: "bg-green-400/10" },
  assigned:       { color: "bg-purple-400", text: "text-purple-300", border: "border-purple-400/30",bg: "bg-purple-400/10" },
  closed:         { color: "bg-amber-300",  text: "text-amber-200",  border: "border-amber-300/30", bg: "bg-amber-300/10" },
  cold:           { color: "bg-red-400",    text: "text-red-300",    border: "border-red-400/30",   bg: "bg-red-400/10" },
}

const OUTREACH_STATUS = {
  sent:    { color: "bg-blue-400",  text: "text-blue-300" },
  replied: { color: "bg-green-400", text: "text-green-300" },
  bounced: { color: "bg-red-400",   text: "text-red-300" },
  pending: { color: "bg-gray-400",  text: "text-gray-300" },
}

const FUNNEL_STAGES = ["scouted", "contacted", "negotiating", "under_contract", "assigned", "closed"]
const FUNNEL_COLORS = ["bg-gray-500", "bg-blue-500", "bg-amber-500", "bg-green-500", "bg-purple-500", "bg-amber-300"]

function StatusPill({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.new
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${cfg.bg} ${cfg.text} ${cfg.border} border`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.color}`} />
      {(status || "new").replace(/_/g, " ")}
    </span>
  )
}

// ── KPI Card ──
function KpiCard({ label, value, sub, accent }) {
  return (
    <div className="card">
      <div className="text-[8px] uppercase tracking-widest text-gray-500">{label}</div>
      <div className={`font-mono text-2xl font-bold ${accent || "text-white"}`}>{value}</div>
      {sub && <div className="text-[9px] text-gray-600 mt-0.5">{sub}</div>}
    </div>
  )
}

// ── Deal Funnel ──
function DealFunnel({ sellers }) {
  const counts = useMemo(() => {
    const c = {}
    FUNNEL_STAGES.forEach(s => c[s] = 0)
    ;(sellers || []).forEach(s => {
      const st = (s.status || "new").toLowerCase()
      if (st === "new") c.scouted = (c.scouted || 0) + 1
      else if (c[st] !== undefined) c[st]++
    })
    return c
  }, [sellers])

  const max = Math.max(...Object.values(counts), 1)

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm font-medium">Deal Funnel</div>
        <div className="text-[9px] text-gray-500">{(sellers || []).length} total leads</div>
      </div>
      <div className="space-y-2">
        {FUNNEL_STAGES.map((stage, i) => {
          const count = counts[stage] || 0
          const pct = max > 0 ? (count / max) * 100 : 0
          const prev = i > 0 ? (counts[FUNNEL_STAGES[i - 1]] || 0) : 0
          const convRate = prev > 0 ? Math.round((count / prev) * 100) : null
          return (
            <div key={stage} className="flex items-center gap-3">
              <div className="w-24 text-[10px] text-gray-400 uppercase tracking-wider text-right">
                {stage.replace(/_/g, " ")}
              </div>
              <div className="flex-1 h-7 bg-white/[0.03] rounded-lg overflow-hidden relative">
                <div
                  className={`h-full ${FUNNEL_COLORS[i]} opacity-70 rounded-lg transition-all duration-700`}
                  style={{ width: `${Math.max(pct, 2)}%` }}
                />
                <div className="absolute inset-0 flex items-center px-3 justify-between">
                  <span className="font-mono text-[11px] font-bold text-white drop-shadow-lg">{count}</span>
                  {convRate !== null && (
                    <span className="text-[9px] text-gray-400">{convRate}% conv</span>
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

// ── Pipeline Table ──
function PipelineTable({ sellers }) {
  const [sortKey, setSortKey] = useState("priority_score")
  const [sortDir, setSortDir] = useState("desc")
  const [filterStatus, setFilterStatus] = useState("all")
  const [filterState, setFilterState] = useState("all")

  const states = useMemo(() => {
    const s = new Set()
    ;(sellers || []).forEach(r => r.state && s.add(r.state))
    return ["all", ...Array.from(s).sort()]
  }, [sellers])

  const statuses = useMemo(() => {
    const s = new Set()
    ;(sellers || []).forEach(r => r.status && s.add(r.status))
    return ["all", ...Array.from(s).sort()]
  }, [sellers])

  const sorted = useMemo(() => {
    let rows = [...(sellers || [])]
    if (filterStatus !== "all") rows = rows.filter(r => r.status === filterStatus)
    if (filterState !== "all") rows = rows.filter(r => r.state === filterState)
    rows.sort((a, b) => {
      const av = a[sortKey] ?? 0
      const bv = b[sortKey] ?? 0
      if (typeof av === "number" && typeof bv === "number") return sortDir === "asc" ? av - bv : bv - av
      return sortDir === "asc" ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av))
    })
    return rows
  }, [sellers, sortKey, sortDir, filterStatus, filterState])

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc")
    else { setSortKey(key); setSortDir("desc") }
  }

  const SortIcon = ({ col }) => (
    <span className="text-[8px] ml-0.5 opacity-50">
      {sortKey === col ? (sortDir === "asc" ? "^" : "v") : "-"}
    </span>
  )

  return (
    <div className="card p-0 overflow-hidden">
      {/* Filters */}
      <div className="px-4 py-3 border-b border-white/[0.04] flex items-center justify-between flex-wrap gap-2">
        <div className="text-sm font-medium">Wholesale Pipeline</div>
        <div className="flex items-center gap-2">
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="bg-white/[0.05] border border-white/[0.08] rounded-lg px-2 py-1 text-[10px] text-gray-300 outline-none"
          >
            {statuses.map(s => (
              <option key={s} value={s} className="bg-[#0d0d14]">{s === "all" ? "All Status" : s.replace(/_/g, " ")}</option>
            ))}
          </select>
          <select
            value={filterState}
            onChange={e => setFilterState(e.target.value)}
            className="bg-white/[0.05] border border-white/[0.08] rounded-lg px-2 py-1 text-[10px] text-gray-300 outline-none"
          >
            {states.map(s => (
              <option key={s} value={s} className="bg-[#0d0d14]">{s === "all" ? "All States" : s}</option>
            ))}
          </select>
          <span className="text-[9px] text-gray-500">{sorted.length} results</span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-white/[0.04]">
              {[
                { key: "status", label: "Status" },
                { key: "city", label: "City/State" },
                { key: "property_type", label: "Type" },
                { key: "estimated_arv", label: "ARV" },
                { key: "asking_price", label: "Asking" },
                { key: "mao", label: "MAO" },
                { key: "motivation_level", label: "Motivation" },
                { key: "lead_source", label: "Source" },
                { key: "last_contact", label: "Last Contact" },
                { key: "priority_score", label: "Priority" },
              ].map(col => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="px-3 py-2.5 text-left text-[9px] uppercase tracking-wider text-gray-500 cursor-pointer hover:text-gray-300 transition-colors whitespace-nowrap"
                >
                  {col.label}<SortIcon col={col.key} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr><td colSpan={10} className="text-center py-8 text-gray-600">No sellers match filters</td></tr>
            ) : (
              sorted.map((row, i) => (
                <tr key={row.id || i} className="border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors">
                  <td className="px-3 py-2"><StatusPill status={row.status} /></td>
                  <td className="px-3 py-2 text-gray-300 whitespace-nowrap">{row.city || "--"}{row.state ? `, ${row.state}` : ""}</td>
                  <td className="px-3 py-2 text-gray-400">{row.property_type || "--"}</td>
                  <td className="px-3 py-2 font-mono text-green-400">{row.estimated_arv ? formatUSD(row.estimated_arv) : "--"}</td>
                  <td className="px-3 py-2 font-mono text-gray-300">{row.asking_price ? formatUSD(row.asking_price) : "--"}</td>
                  <td className="px-3 py-2 font-mono text-amber-400">{row.mao ? formatUSD(row.mao) : "--"}</td>
                  <td className="px-3 py-2">
                    <MotivationBar level={row.motivation_level} />
                  </td>
                  <td className="px-3 py-2 text-gray-500 text-[10px]">{row.lead_source || "--"}</td>
                  <td className="px-3 py-2 text-gray-500 text-[10px] whitespace-nowrap">{row.last_contact ? new Date(row.last_contact).toLocaleDateString() : "--"}</td>
                  <td className="px-3 py-2">
                    <PriorityBadge score={row.priority_score} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function MotivationBar({ level }) {
  const n = Number(level) || 0
  const color = n >= 8 ? "bg-green-400" : n >= 5 ? "bg-amber-400" : "bg-red-400"
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-12 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${Math.min(n * 10, 100)}%` }} />
      </div>
      <span className="font-mono text-[10px] text-gray-400">{n}</span>
    </div>
  )
}

function PriorityBadge({ score }) {
  const n = Number(score) || 0
  const color = n >= 80 ? "text-green-400 bg-green-400/10" : n >= 50 ? "text-amber-400 bg-amber-400/10" : "text-gray-400 bg-white/[0.05]"
  return (
    <span className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded ${color}`}>{n}</span>
  )
}

// ── Active Deals ──
function ActiveDeals({ deals }) {
  if (!deals || deals.length === 0) {
    return (
      <div className="card text-center py-8">
        <div className="text-xl opacity-10 mb-2">--</div>
        <div className="text-xs text-gray-500">No active deals</div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="text-sm font-medium">Active Deals</div>
      {deals.map((deal, i) => (
        <div key={deal.id || i} className="card border-l-4 border-l-amber-400 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-amber-400/[0.03] rounded-full blur-3xl" />
          <div className="relative">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-xs font-medium text-white">{deal.seller_name || deal.property_address || "Deal"}</div>
                <div className="text-[10px] text-gray-500">{deal.city}{deal.state ? `, ${deal.state}` : ""}</div>
              </div>
              <StatusPill status={deal.status} />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <div className="text-[8px] uppercase text-gray-500 tracking-wider">Assignment Fee</div>
                <div className="font-mono text-sm font-bold text-amber-400">{deal.assignment_fee ? formatUSD(deal.assignment_fee) : "--"}</div>
              </div>
              <div>
                <div className="text-[8px] uppercase text-gray-500 tracking-wider">Buyer</div>
                <div className="text-[11px] text-gray-300">{deal.buyer_name || "Unassigned"}</div>
              </div>
              <div>
                <div className="text-[8px] uppercase text-gray-500 tracking-wider">Agent</div>
                <div className="text-[11px] text-gray-300">{deal.agent_assigned || "Unassigned"}</div>
              </div>
              <div>
                <div className="text-[8px] uppercase text-gray-500 tracking-wider">Contract</div>
                <div className="text-[11px] text-gray-300">{deal.contract_price ? formatUSD(deal.contract_price) : "--"}</div>
              </div>
            </div>
            {/* Timeline */}
            {deal.timeline && deal.timeline.length > 0 && (
              <div className="mt-3 pt-3 border-t border-white/[0.04]">
                <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-2">Timeline</div>
                <div className="space-y-1.5">
                  {deal.timeline.slice(0, 5).map((ev, j) => (
                    <div key={j} className="flex items-center gap-2 text-[10px]">
                      <div className="w-1.5 h-1.5 rounded-full bg-amber-400/50 flex-shrink-0" />
                      <span className="text-gray-500 font-mono w-16 flex-shrink-0">{ev.date ? new Date(ev.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "--"}</span>
                      <span className="text-gray-400">{ev.action || ev.note}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Buyer Table ──
function BuyerTable({ buyers }) {
  const [sortKey, setSortKey] = useState("deals_closed")
  const [sortDir, setSortDir] = useState("desc")

  const sorted = useMemo(() => {
    const rows = [...(buyers || [])]
    rows.sort((a, b) => {
      const av = a[sortKey] ?? 0
      const bv = b[sortKey] ?? 0
      if (typeof av === "number" && typeof bv === "number") return sortDir === "asc" ? av - bv : bv - av
      return sortDir === "asc" ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av))
    })
    return rows
  }, [buyers, sortKey, sortDir])

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc")
    else { setSortKey(key); setSortDir("desc") }
  }

  const relColors = {
    hot:  "text-green-400 bg-green-400/10",
    warm: "text-amber-400 bg-amber-400/10",
    cold: "text-gray-400 bg-white/[0.05]",
    new:  "text-blue-400 bg-blue-400/10",
  }

  return (
    <div className="card p-0 overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[0.04] flex items-center justify-between">
        <div className="text-sm font-medium">Buyer Database</div>
        <span className="text-[9px] text-gray-500">{(buyers || []).length} buyers</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-white/[0.04]">
              {[
                { key: "company", label: "Company" },
                { key: "contact_name", label: "Contact" },
                { key: "state", label: "State" },
                { key: "buyer_type", label: "Type" },
                { key: "relationship_status", label: "Relationship" },
                { key: "deals_closed", label: "Deals Closed" },
                { key: "avg_deal_size", label: "Avg Deal" },
                { key: "last_contact", label: "Last Contact" },
              ].map(col => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="px-3 py-2.5 text-left text-[9px] uppercase tracking-wider text-gray-500 cursor-pointer hover:text-gray-300 transition-colors whitespace-nowrap"
                >
                  {col.label}
                  <span className="text-[8px] ml-0.5 opacity-50">{sortKey === col.key ? (sortDir === "asc" ? "^" : "v") : "-"}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-8 text-gray-600">No buyers in database</td></tr>
            ) : (
              sorted.map((row, i) => (
                <tr key={row.id || i} className="border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors">
                  <td className="px-3 py-2 text-gray-200 font-medium">{row.company || "--"}</td>
                  <td className="px-3 py-2 text-gray-400">{row.contact_name || "--"}</td>
                  <td className="px-3 py-2 text-gray-400">{row.state || "--"}</td>
                  <td className="px-3 py-2 text-gray-400 text-[10px]">{row.buyer_type || "--"}</td>
                  <td className="px-3 py-2">
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${relColors[row.relationship_status] || relColors.new}`}>
                      {(row.relationship_status || "new").toUpperCase()}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-center text-gray-300">{row.deals_closed ?? 0}</td>
                  <td className="px-3 py-2 font-mono text-amber-400">{row.avg_deal_size ? formatUSD(row.avg_deal_size) : "--"}</td>
                  <td className="px-3 py-2 text-gray-500 text-[10px] whitespace-nowrap">{row.last_contact ? new Date(row.last_contact).toLocaleDateString() : "--"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Outreach Feed ──
function OutreachFeed({ outreach }) {
  if (!outreach || outreach.length === 0) {
    return (
      <div className="card text-center py-8">
        <div className="text-xl opacity-10 mb-2">--</div>
        <div className="text-xs text-gray-500">No outreach activity yet</div>
      </div>
    )
  }

  return (
    <div className="card p-0 overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[0.04] flex items-center justify-between">
        <div className="text-sm font-medium">Outreach Activity</div>
        <span className="text-[9px] text-gray-500">{outreach.length} messages</span>
      </div>
      <div className="max-h-[400px] overflow-y-auto">
        {outreach.map((msg, i) => {
          const cfg = OUTREACH_STATUS[msg.status] || OUTREACH_STATUS.pending
          return (
            <div key={msg.id || i} className="px-4 py-3 border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full ${cfg.color}`} />
                  <span className={`text-[10px] font-semibold uppercase ${cfg.text}`}>{msg.status || "pending"}</span>
                  <span className="text-[10px] text-gray-400">{msg.type || "email"}</span>
                </div>
                <span className="text-[9px] text-gray-600 font-mono">
                  {msg.sent_at ? new Date(msg.sent_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "--"}
                </span>
              </div>
              <div className="text-[11px] text-gray-300 mb-0.5">{msg.subject || msg.template || "Outreach"}</div>
              <div className="text-[10px] text-gray-500">
                To: {msg.recipient_name || msg.recipient_email || "--"}
                {msg.seller_city && <span className="ml-2">({msg.seller_city}{msg.seller_state ? `, ${msg.seller_state}` : ""})</span>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Revenue Summary ──
function RevenueSummary({ deals, stats }) {
  const closedDeals = useMemo(() => (deals || []).filter(d => d.status === "closed"), [deals])
  const totalFees = useMemo(() => closedDeals.reduce((sum, d) => sum + (Number(d.assignment_fee) || 0), 0), [closedDeals])
  const avgDeal = closedDeals.length > 0 ? totalFees / closedDeals.length : 0

  // Group by month for chart
  const monthly = useMemo(() => {
    const months = {}
    closedDeals.forEach(d => {
      const date = d.closed_at || d.updated_at
      if (!date) return
      const key = new Date(date).toLocaleString("en-US", { month: "short", year: "2-digit" })
      months[key] = (months[key] || 0) + (Number(d.assignment_fee) || 0)
    })
    return Object.entries(months).slice(-6)
  }, [closedDeals])

  const maxMonthly = Math.max(...monthly.map(([, v]) => v), 1)

  return (
    <div className="space-y-4">
      {/* Revenue KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="card bg-gradient-to-br from-amber-500/10 to-amber-900/5 border border-amber-400/10">
          <div className="text-[8px] uppercase tracking-widest text-amber-400/60">Total Revenue</div>
          <div className="font-mono text-3xl font-black bg-gradient-to-r from-amber-300 to-amber-500 bg-clip-text text-transparent">{formatUSD(totalFees)}</div>
          <div className="text-[9px] text-gray-500 mt-1">{closedDeals.length} closed deals</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Avg Deal Size</div>
          <div className="font-mono text-2xl font-bold text-white">{formatUSD(avgDeal)}</div>
          <div className="text-[9px] text-gray-500 mt-1">assignment fee avg</div>
        </div>
        <div className="card">
          <div className="text-[8px] uppercase tracking-widest text-gray-500">Pipeline Value</div>
          <div className="font-mono text-2xl font-bold text-green-400">{formatUSD(stats?.pipeline_value || 0)}</div>
          <div className="text-[9px] text-gray-500 mt-1">active + under contract</div>
        </div>
      </div>

      {/* Monthly Chart */}
      {monthly.length > 0 && (
        <div className="card">
          <div className="text-sm font-medium mb-4">Monthly Revenue</div>
          <div className="flex items-end gap-2 h-32">
            {monthly.map(([month, val]) => (
              <div key={month} className="flex-1 flex flex-col items-center gap-1">
                <div className="font-mono text-[9px] text-amber-400">{formatUSD(val)}</div>
                <div className="w-full bg-white/[0.03] rounded-t-lg overflow-hidden" style={{ height: "100px" }}>
                  <div
                    className="w-full bg-gradient-to-t from-amber-500 to-amber-400 rounded-t-lg transition-all duration-700 mt-auto"
                    style={{ height: `${(val / maxMonthly) * 100}%`, marginTop: `${100 - (val / maxMonthly) * 100}%` }}
                  />
                </div>
                <div className="text-[9px] text-gray-500">{month}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Closed deals list */}
      {closedDeals.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b border-white/[0.04]">
            <div className="text-sm font-medium">Closed Deals</div>
          </div>
          <div className="max-h-[300px] overflow-y-auto">
            {closedDeals.map((d, i) => (
              <div key={d.id || i} className="px-4 py-3 border-b border-white/[0.02] flex items-center justify-between">
                <div>
                  <div className="text-[11px] text-gray-300">{d.property_address || d.seller_name || "Deal"}</div>
                  <div className="text-[9px] text-gray-500">{d.city}{d.state ? `, ${d.state}` : ""} {d.buyer_name ? `- ${d.buyer_name}` : ""}</div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-sm font-bold text-amber-400">{d.assignment_fee ? formatUSD(d.assignment_fee) : "--"}</div>
                  <div className="text-[9px] text-gray-500">{d.closed_at ? new Date(d.closed_at).toLocaleDateString() : "--"}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Loading Skeleton ──
function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="card">
            <div className="h-2 w-12 bg-white/[0.05] rounded mb-2" />
            <div className="h-6 w-16 bg-white/[0.08] rounded" />
          </div>
        ))}
      </div>
      <div className="card h-48 flex items-center justify-center">
        <div className="text-[10px] text-gray-600 tracking-widest">Loading Broker OS...</div>
      </div>
    </div>
  )
}

// ── Main BrokerOS Page ──
export default function BrokerOS() {
  const [tab, setTab] = useState("pipeline")
  const { data: stats, error: statsErr } = useApi("/api/broker/stats", 10000)
  const { data: sellers, error: sellersErr } = useApi("/api/broker/sellers", 10000)
  const { data: buyers, error: buyersErr } = useApi("/api/broker/buyers", 10000)
  const { data: deals, error: dealsErr } = useApi("/api/broker/deals", 10000)
  const { data: outreach, error: outreachErr } = useApi("/api/broker/outreach", 10000)

  const isLoading = !stats && !statsErr
  const hasError = statsErr || sellersErr

  const tabs = [
    { id: "pipeline", label: "Pipeline" },
    { id: "buyers", label: "Buyers" },
    { id: "outreach", label: "Outreach" },
    { id: "revenue", label: "Revenue" },
  ]

  if (isLoading) return <LoadingSkeleton />

  return (
    <div className="space-y-4">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-bold tracking-wide">Broker OS</div>
          <div className="text-[10px] text-gray-500 tracking-wider">Wholesale Pipeline Command Center</div>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${hasError ? "bg-red-400" : "bg-green-400"} animate-pulse`} />
          <span className="text-[9px] text-gray-500 font-mono">Auto-refresh 10s</span>
        </div>
      </div>

      {/* KPI Bar */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <KpiCard label="Total Sellers" value={stats?.total_sellers ?? 0} accent="text-white" />
        <KpiCard label="Contacted" value={stats?.contacted ?? 0} accent="text-blue-400" />
        <KpiCard label="Under Contract" value={stats?.under_contract ?? 0} accent="text-green-400" />
        <KpiCard label="Active Deals" value={stats?.active_deals ?? 0} accent="text-amber-400" />
        <KpiCard label="Total Buyers" value={stats?.total_buyers ?? 0} accent="text-purple-400" />
        <KpiCard label="Pipeline Value" value={stats?.pipeline_value ? formatUSD(stats.pipeline_value) : "$0"} accent="text-amber-300" sub="active pipeline" />
      </div>

      {/* Deal Funnel */}
      <DealFunnel sellers={sellers} />

      {/* Tab Navigation */}
      <div className="flex gap-1.5">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-full text-[11px] font-medium transition-all ${
              tab === t.id
                ? "bg-amber-400/20 text-amber-400 border border-amber-400/30"
                : "bg-white/[0.05] text-gray-500 hover:text-gray-300 hover:bg-white/[0.08]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Error Banner */}
      {hasError && (
        <div className="card border border-red-400/20 bg-red-400/[0.03]">
          <div className="text-[10px] text-red-400">API connection issue -- data may be stale</div>
          <div className="text-[9px] text-gray-600 mt-0.5">{String(statsErr || sellersErr)}</div>
        </div>
      )}

      {/* Tab Content */}
      {tab === "pipeline" && (
        <div className="space-y-4">
          <PipelineTable sellers={sellers} />
          <ActiveDeals deals={deals} />
        </div>
      )}

      {tab === "buyers" && <BuyerTable buyers={buyers} />}

      {tab === "outreach" && <OutreachFeed outreach={outreach} />}

      {tab === "revenue" && <RevenueSummary deals={deals} stats={stats} />}
    </div>
  )
}
