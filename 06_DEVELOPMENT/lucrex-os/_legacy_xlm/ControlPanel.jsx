import React from "react"
import { useApi } from "./hooks"

const SERVICES = [
  { name: "XLM Trading Bot", id: "xlm-bot", port: null, type: "core", desc: "Main trading engine -- entry/exit/risk management" },
  { name: "React Dashboard", id: "xlm-dash-react", port: 8502, type: "dashboard", desc: "This dashboard (FastAPI + React)" },
  { name: "WebSocket Feed", id: "xlm-ws", port: null, type: "core", desc: "Live XLM-USD price feed from Coinbase" },
  { name: "Blinko RAG", id: "blinko", port: 1111, type: "intel", desc: "Knowledge base -- 1,060+ notes of trading memory" },
  { name: "n8n Automation", id: "n8n", port: 5678, type: "infra", desc: "Workflow automation -- Google Docs, alerts" },
  { name: "Hive Django", id: "hive-django", port: 8504, type: "dashboard", desc: "Ops dashboard -- sessions, taskboard, analytics" },
  { name: "Voice Handler", id: "hive-voice", port: 8200, type: "infra", desc: "Marcus phone voice actions" },
  { name: "Slack Agent", id: "hive-slack-agent", port: null, type: "infra", desc: "Slack bot -- war room, alerts, channels" },
]

const MCP_TOOLS = [
  { name: "Market Intel", status: "active", desc: "Real-time market intelligence for XLM" },
  { name: "Blinko Memory", status: "active", desc: "RAG knowledge base queries" },
  { name: "Broker OS", status: "standby", desc: "B2B deal matching engine" },
  { name: "Stripe", status: "active", desc: "Payment processing & subscriptions" },
  { name: "Supabase", status: "active", desc: "Database & edge functions" },
  { name: "Gmail", status: "active", desc: "Email integration" },
  { name: "Slack", status: "active", desc: "Team messaging" },
  { name: "Google Calendar", status: "active", desc: "Scheduling" },
  { name: "n8n Webhooks", status: "degraded", desc: "Google Docs workflow (HTTP 500)" },
]

const BOT_FEATURES = [
  { name: "Bidirectional Trading", status: "active", desc: "Long + Short based on HTF trend" },
  { name: "AI Executive Mode", status: "active", desc: "Claude Opus decision engine" },
  { name: "Profit Manager", status: "active", desc: "Partial profits + break-even SL" },
  { name: "Hedge Flip", status: "active", desc: "Auto-reverse on stop loss" },
  { name: "Divergence Scanner", status: "active", desc: "RSI divergence confirmation" },
  { name: "Fib Confluence", status: "active", desc: "Fib + S/R premium setups" },
  { name: "Smart Exit Engine", status: "active", desc: "5-layer structural exit system" },
  { name: "Scalp Engine", status: "standby", desc: "Activates in compression regime" },
  { name: "Moonshot Mode", status: "standby", desc: "Extended runner for big moves" },
  { name: "Market Intel Feed", status: "active", desc: "Intraday market context" },
  { name: "Sentiment Gate", status: "active", desc: "Fear & Greed filtering" },
  { name: "Circuit Breaker", status: "active", desc: "Loss protection + recovery mode" },
]

function StatusBadge({ status }) {
  const styles = {
    active: "bg-green-400/10 text-green-400 border-green-400/20",
    standby: "bg-amber-400/10 text-amber-400 border-amber-400/20",
    degraded: "bg-orange-400/10 text-orange-400 border-orange-400/20",
    offline: "bg-red-400/10 text-red-400 border-red-400/20",
  }
  return (
    <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full border ${styles[status] || styles.offline}`}>
      {status === "active" && <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-400 mr-1 pulse-live" />}
      {status}
    </span>
  )
}

function ServiceCard({ service }) {
  const typeColors = {
    core: "border-l-green-400",
    dashboard: "border-l-blue-400",
    intel: "border-l-purple-400",
    infra: "border-l-amber-400",
  }
  return (
    <div className={`card border-l-2 ${typeColors[service.type] || "border-l-gray-400"} py-3 px-4`}>
      <div className="flex justify-between items-start">
        <div>
          <div className="text-sm font-medium">{service.name}</div>
          <div className="text-[10px] text-gray-500 mt-0.5">{service.desc}</div>
        </div>
        <div className="flex items-center gap-2">
          {service.port && <span className="text-[10px] text-gray-600 font-mono">:{service.port}</span>}
          <StatusBadge status="active" />
        </div>
      </div>
    </div>
  )
}

export default function ControlPanel() {
  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center text-lg font-bold shadow-lg shadow-red-500/20">#</div>
        <div>
          <div className="text-lg font-semibold">Control Panel</div>
          <div className="text-xs text-gray-500">Infrastructure status -- services, MCP tools, bot features</div>
        </div>
      </div>

      {/* Infrastructure Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-white/[0.03] rounded-xl p-4 text-center relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-green-500/[0.05] to-transparent" />
          <div className="relative">
            <div className="font-mono text-3xl font-bold text-green-400">{SERVICES.length}</div>
            <div className="text-[10px] uppercase tracking-wider text-gray-500">Services</div>
          </div>
        </div>
        <div className="bg-white/[0.03] rounded-xl p-4 text-center relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/[0.05] to-transparent" />
          <div className="relative">
            <div className="font-mono text-3xl font-bold text-purple-400">{MCP_TOOLS.length}</div>
            <div className="text-[10px] uppercase tracking-wider text-gray-500">MCP Tools</div>
          </div>
        </div>
        <div className="bg-white/[0.03] rounded-xl p-4 text-center relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-amber-500/[0.05] to-transparent" />
          <div className="relative">
            <div className="font-mono text-3xl font-bold text-amber-400">{BOT_FEATURES.length}</div>
            <div className="text-[10px] uppercase tracking-wider text-gray-500">Bot Features</div>
          </div>
        </div>
        <div className="bg-white/[0.03] rounded-xl p-4 text-center relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/[0.05] to-transparent" />
          <div className="relative">
            <div className="font-mono text-3xl font-bold text-blue-400">2</div>
            <div className="text-[10px] uppercase tracking-wider text-gray-500">Oracle VMs</div>
          </div>
        </div>
      </div>

      {/* Services */}
      <div>
        <div className="text-sm font-medium mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-400 pulse-live" />
          Oracle Services
          <span className="text-[10px] text-gray-500 font-normal">163.192.19.196</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {SERVICES.map(s => <ServiceCard key={s.id} service={s} />)}
        </div>
      </div>

      {/* MCP Tools */}
      <div>
        <div className="text-sm font-medium mb-3">MCP Tool Integrations</div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {MCP_TOOLS.map(t => (
            <div key={t.name} className="card py-2.5 px-3 flex justify-between items-center">
              <div>
                <div className="text-xs font-medium">{t.name}</div>
                <div className="text-[10px] text-gray-600">{t.desc}</div>
              </div>
              <StatusBadge status={t.status} />
            </div>
          ))}
        </div>
      </div>

      {/* Bot Features */}
      <div>
        <div className="text-sm font-medium mb-3">Trading Engine Features</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {BOT_FEATURES.map(f => (
            <div key={f.name} className="card py-2.5 px-3 flex justify-between items-center">
              <div>
                <div className="text-xs font-medium">{f.name}</div>
                <div className="text-[10px] text-gray-600">{f.desc}</div>
              </div>
              <StatusBadge status={f.status} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
