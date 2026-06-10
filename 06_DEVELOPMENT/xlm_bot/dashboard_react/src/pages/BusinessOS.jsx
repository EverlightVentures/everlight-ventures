import React, { useState } from "react"
import { useApi } from "../hooks"

// ── Tab Navigation ──
function TabNav({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1.5 mb-4 flex-wrap">
      {tabs.map(t => (
        <button key={t.id} onClick={() => onChange(t.id)}
          className={`px-3 py-1.5 rounded-full text-[11px] font-medium transition-all ${
            active === t.id
              ? "bg-amber-400/20 text-amber-400 border border-amber-400/30"
              : "bg-white/5 text-gray-500 hover:text-gray-300"
          }`}>{t.label}</button>
      ))}
    </div>
  )
}

// ── KPI Card ──
function Kpi({ label, value, sub, accent }) {
  return (
    <div className="card">
      <div className="text-[8px] uppercase tracking-widest text-gray-500">{label}</div>
      <div className={`font-mono text-2xl font-bold ${accent || "text-white"}`}>{value}</div>
      {sub && <div className="text-[10px] text-gray-600 mt-1">{sub}</div>}
    </div>
  )
}

// ── Overview Tab ──
function OverviewTab() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="Revenue Streams" value="9" sub="Active ventures" accent="text-amber-400" />
        <Kpi label="Oracle Services" value="11" sub="2 core, 16GB RAM" accent="text-green-400" />
        <Kpi label="Hive Agents" value="63" sub="12 fire teams" accent="text-purple-400" />
        <Kpi label="Slack Channels" value="26" sub="All bot token" accent="text-blue-400" />
      </div>

      <div className="card">
        <div className="text-sm font-medium mb-3">Venture Status</div>
        <div className="space-y-2">
          {[
            { name: "XLM Trading Bot", status: "live", revenue: "Variable", color: "green" },
            { name: "Broker OS", status: "live", revenue: "$5k-25k/deal", color: "green" },
            { name: "Polymarket Agent", status: "live", revenue: "Paper trading", color: "amber" },
            { name: "Onyx POS", status: "ready", revenue: "$49/mo SaaS", color: "blue" },
            { name: "AI Consulting", status: "pipeline", revenue: "$2k-5k/build", color: "purple" },
            { name: "Publishing (KDP)", status: "passive", revenue: "$50-200/mo", color: "gray" },
            { name: "Wholesale RE", status: "live", revenue: "$5k-25k/deal", color: "green" },
            { name: "Field Ops", status: "ready", revenue: "$11k/mo M4", color: "blue" },
            { name: "Computer Use", status: "live", revenue: "Infra", color: "green" },
          ].map((v, i) => (
            <div key={i} className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] transition-all">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full bg-${v.color}-400`} />
                <span className="text-sm">{v.name}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-[10px] px-2 py-0.5 rounded-full bg-${v.color}-400/10 text-${v.color}-400 font-medium uppercase`}>{v.status}</span>
                <span className="text-[11px] text-gray-500 font-mono">{v.revenue}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Onboarding Tab (iframe to Django) ──
function OnboardTab() {
  return (
    <div className="space-y-4">
      <div className="card">
        <div className="text-sm font-medium mb-2">Client Onboarding Portal</div>
        <div className="text-[11px] text-gray-500 mb-4">
          Self-service deployment for new Hive Mind customers. Connect Slack, pick agents, connect tools.
        </div>
        <div className="rounded-xl overflow-hidden border border-gray-800" style={{ height: "70vh" }}>
          <iframe
            src="/api/onboard"
            className="w-full h-full border-0"
            title="Client Onboarding"
            style={{ background: "#0a0a0a" }}
          />
        </div>
      </div>
    </div>
  )
}

// ── Analytics Tab ──
function AnalyticsTab() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <Kpi label="Blinko Notes" value="458+" sub="RAG knowledge base" />
        <Kpi label="Supabase Tables" value="11" sub="15 edge functions" />
        <Kpi label="Oracle Crons" value="62" sub="Active automations" />
      </div>

      <div className="card">
        <div className="text-sm font-medium mb-3">System Analytics</div>
        <div className="space-y-2">
          {[
            { name: "Blinko RAG", url: "http://e5-mother:1111", status: "Healthy", notes: "458+ notes" },
            { name: "n8n Workflows", url: "http://129.159.38.250:5678", status: "Active", notes: "400+ integrations" },
            { name: "Langfuse Traces", url: "http://129.159.38.250:3100", status: "Tracking", notes: "AI observability" },
            { name: "Metabase BI", url: "http://129.159.38.250:3200", status: "Ready", notes: "Custom dashboards" },
            { name: "Netdata Monitor", url: "http://129.159.38.250:19999", status: "Live", notes: "Real-time metrics" },
            { name: "Supabase", url: "https://supabase.com/dashboard", status: "Production", notes: "East US" },
          ].map((s, i) => (
            <a key={i} href={s.url} target="_blank" rel="noopener noreferrer"
              className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] transition-all cursor-pointer">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-400" />
                <span className="text-sm">{s.name}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[10px] text-green-400">{s.status}</span>
                <span className="text-[11px] text-gray-500">{s.notes}</span>
              </div>
            </a>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="text-sm font-medium mb-3">Deliverable Generators</div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { icon: "PDF", desc: "Branded reports, deal packets", color: "red" },
            { icon: "XLSX", desc: "Spreadsheets, lead exports, P&L", color: "green" },
            { icon: "PPTX", desc: "Investor decks, presentations", color: "amber" },
          ].map((d, i) => (
            <div key={i} className="rounded-xl border border-gray-800 p-4 text-center hover:border-amber-400/30 transition-all">
              <div className={`text-2xl font-black text-${d.color}-400 mb-1`}>{d.icon}</div>
              <div className="text-[10px] text-gray-500">{d.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Agents Tab ──
function AgentsTab() {
  const squads = [
    { name: "Claude Corp", leader: "Marcus Cole", count: 16, color: "amber", role: "Strategy & Quality" },
    { name: "Gemini Ops", leader: "Major Dex", count: 16, color: "blue", role: "Execution & Distribution" },
    { name: "Codex Labs", leader: "Franklin Steele", count: 16, color: "green", role: "Engineering & Profit" },
    { name: "Perplexity Intel", leader: "Cipher Wolfe", count: 15, color: "purple", role: "Research & Intelligence" },
  ]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {squads.map((s, i) => (
          <div key={i} className={`card border-l-4 border-l-${s.color}-400`}>
            <div className={`text-xs font-bold text-${s.color}-400`}>{s.name}</div>
            <div className="text-[10px] text-gray-500">{s.role}</div>
            <div className="text-xl font-mono font-bold mt-2">{s.count}</div>
            <div className="text-[10px] text-gray-600">Led by {s.leader}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="text-sm font-medium mb-2">Fire Team Doctrine v2</div>
        <div className="text-[11px] text-gray-500">
          63 agents | 12 fire teams | 4 squads | 26 buddy pairs.
          Every critical function has redundancy. If any agent fails, their buddy takes over.
          Minimum 3 agents per task across 2+ departments.
        </div>
      </div>
    </div>
  )
}

// ── Main BusinessOS Page ──
export default function BusinessOS() {
  const [tab, setTab] = useState("overview")

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "analytics", label: "Analytics" },
    { id: "agents", label: "Agents (63)" },
    { id: "onboard", label: "Client Onboarding" },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-amber-300 to-amber-500 bg-clip-text text-transparent">
            Business OS
          </h1>
          <div className="text-[10px] text-gray-600">Everlight Ventures Command Center</div>
        </div>
      </div>

      <TabNav tabs={tabs} active={tab} onChange={setTab} />

      {tab === "overview" && <OverviewTab />}
      {tab === "analytics" && <AnalyticsTab />}
      {tab === "agents" && <AgentsTab />}
      {tab === "onboard" && <OnboardTab />}
    </div>
  )
}
