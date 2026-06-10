import React, { useState } from "react"

const SERVICES = [
  { name: "xlm-bot", desc: "XLM Trading Bot", port: null },
  { name: "xlm-dash-react", desc: "React Dashboard", port: 8502 },
  { name: "xlm-ws", desc: "WebSocket Price Feed", port: null },
  { name: "hive-django", desc: "Django Ops Dashboard", port: 8504 },
  { name: "n8n", desc: "Automation Engine", port: 5678 },
  { name: "blinko", desc: "RAG Knowledge Base", port: 1111 },
  { name: "hive-voice", desc: "Marcus Voice Handler", port: 8200 },
  { name: "hive-slack-agent", desc: "Slack Bot Agent", port: null },
  { name: "wholesale-pipeline", desc: "Wholesale Pipeline Cycles", port: null },
  { name: "xlm-liqfeed", desc: "Liquidation Feed", port: null },
  { name: "hive-dashboard", desc: "Dashboard Service", port: null },
]

const CRONS = [
  { schedule: "*/10 * * * *", job: "Auto-deploy script", desc: "Push local changes to Oracle" },
  { schedule: "0 7 * * *", job: "CEO Morning Brief", desc: "Daily summary to Slack #ceo-brief" },
  { schedule: "0 * * * *", job: "Hourly Pulse", desc: "System health check + Blinko log" },
  { schedule: "*/2 * * * *", job: "Wholesale Outreach", desc: "Reply to seller messages" },
  { schedule: "0 */2 * * *", job: "Broker Pipeline", desc: "Scout and score new leads" },
  { schedule: "0 */6 * * *", job: "XLM Bot Health", desc: "Check bot service + restart if needed" },
  { schedule: "0 3 * * *", job: "Log Rotation", desc: "Compress and archive old logs" },
  { schedule: "*/5 * * * *", job: "Slack Monitor", desc: "Check for new messages in war room" },
]

const API_KEYS = [
  { name: "Anthropic (Claude)", env: "ANTHROPIC_API_KEY", set: true },
  { name: "OpenAI", env: "OPENAI_API_KEY", set: true },
  { name: "Coinbase", env: "COINBASE_API_KEY", set: true },
  { name: "Stripe", env: "STRIPE_SECRET_KEY", set: true },
  { name: "Resend", env: "RESEND_API_KEY", set: true },
  { name: "Supabase", env: "SUPABASE_ANON_KEY", set: true },
  { name: "ElevenLabs", env: "ELEVENLABS_API_KEY", set: true },
  { name: "Slack Bot", env: "SLACK_BOT_TOKEN", set: true },
]

const QUICK_LINKS = [
  { label: "Django Admin", url: "http://129.159.38.250:8504/admin/", icon: "D" },
  { label: "n8n Workflows", url: "http://129.159.38.250:5678", icon: "N" },
  { label: "Blinko RAG", url: "http://e5-mother:1111", icon: "B" },
  { label: "Supabase", url: "https://supabase.com/dashboard/project/jdqqmsmwmbsnlnstyavl", icon: "S" },
  { label: "Cloudflare Pages", url: "https://dash.cloudflare.com", icon: "C" },
  { label: "GitHub Repo", url: "https://github.com/EverlightVentures", icon: "G" },
]

export default function Settings() {
  const [showKeys, setShowKeys] = useState(false)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-amber-400 tracking-wider">SETTINGS</h1>
          <p className="text-xs text-gray-500 mt-1">System Configuration and Infrastructure Status</p>
        </div>
      </div>

      {/* System Info */}
      <div className="card">
        <div className="text-sm font-semibold text-amber-400/80 uppercase tracking-wider mb-4">System Info</div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {[
            { label: "Oracle E5 VM", value: "129.159.38.250" },
            { label: "Supabase Project", value: "jdqqmsmwmbsnlnstyavl" },
            { label: "Region", value: "East US (N. Virginia)" },
            { label: "Django Dashboard", value: ":8504" },
            { label: "React Dashboard", value: ":8502" },
            { label: "Domain", value: "everlightventures.io" },
          ].map(info => (
            <div key={info.label} className="flex items-center gap-3 p-2 rounded-lg bg-white/[0.02]">
              <div className="text-[10px] text-gray-500 uppercase tracking-wider w-28">{info.label}</div>
              <div className="text-[11px] text-gray-300 font-mono">{info.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Service Status */}
      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-white/[0.04]">
          <div className="text-sm font-semibold text-amber-400/80 uppercase tracking-wider">Service Status</div>
        </div>
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-white/[0.04]">
              <th className="px-4 py-2 text-left text-[9px] uppercase tracking-wider text-gray-500">Service</th>
              <th className="px-4 py-2 text-left text-[9px] uppercase tracking-wider text-gray-500">Description</th>
              <th className="px-4 py-2 text-left text-[9px] uppercase tracking-wider text-gray-500">Port</th>
              <th className="px-4 py-2 text-left text-[9px] uppercase tracking-wider text-gray-500">Status</th>
            </tr>
          </thead>
          <tbody>
            {SERVICES.map(svc => (
              <tr key={svc.name} className="border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors">
                <td className="px-4 py-2 text-gray-200 font-mono font-medium">{svc.name}</td>
                <td className="px-4 py-2 text-gray-400">{svc.desc}</td>
                <td className="px-4 py-2 text-gray-500 font-mono">{svc.port || "--"}</td>
                <td className="px-4 py-2">
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide bg-green-400/10 text-green-300 border border-green-400/30">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                    active
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Cron Schedule */}
      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-white/[0.04]">
          <div className="text-sm font-semibold text-amber-400/80 uppercase tracking-wider">Cron Schedule</div>
        </div>
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-white/[0.04]">
              <th className="px-4 py-2 text-left text-[9px] uppercase tracking-wider text-gray-500">Schedule</th>
              <th className="px-4 py-2 text-left text-[9px] uppercase tracking-wider text-gray-500">Job</th>
              <th className="px-4 py-2 text-left text-[9px] uppercase tracking-wider text-gray-500">Description</th>
            </tr>
          </thead>
          <tbody>
            {CRONS.map((cron, i) => (
              <tr key={i} className="border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors">
                <td className="px-4 py-2 text-amber-400 font-mono">{cron.schedule}</td>
                <td className="px-4 py-2 text-gray-200 font-medium">{cron.job}</td>
                <td className="px-4 py-2 text-gray-500">{cron.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* API Keys */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div className="text-sm font-semibold text-amber-400/80 uppercase tracking-wider">API Keys</div>
          <button
            onClick={() => setShowKeys(!showKeys)}
            className="px-3 py-1 rounded-full text-[10px] font-medium bg-white/[0.05] text-gray-400 hover:text-gray-200 hover:bg-white/[0.08] transition-all"
          >
            {showKeys ? "Hide" : "Show"} Details
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {API_KEYS.map(key => (
            <div key={key.name} className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <div>
                <div className="text-[11px] text-gray-300 font-medium">{key.name}</div>
                {showKeys && <div className="text-[9px] text-gray-600 font-mono mt-0.5">{key.env}</div>}
              </div>
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${
                key.set ? "bg-green-400/10 text-green-300 border border-green-400/30" : "bg-red-400/10 text-red-300 border border-red-400/30"
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${key.set ? "bg-green-400" : "bg-red-400"}`} />
                {key.set ? "set" : "missing"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Links */}
      <div className="card">
        <div className="text-sm font-semibold text-amber-400/80 uppercase tracking-wider mb-4">Quick Links</div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {QUICK_LINKS.map(link => (
            <a
              key={link.label}
              href={link.url}
              target="_blank"
              rel="noreferrer"
              className="flex flex-col items-center gap-2 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:border-amber-400/20 hover:bg-amber-400/[0.03] transition-all group"
            >
              <div className="w-10 h-10 rounded-lg bg-amber-400/10 flex items-center justify-center text-amber-400 font-bold text-sm group-hover:bg-amber-400/20 transition-colors">
                {link.icon}
              </div>
              <span className="text-[10px] text-gray-400 group-hover:text-amber-400 transition-colors text-center">{link.label}</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
