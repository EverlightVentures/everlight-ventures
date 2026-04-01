import React from "react"

const NAV_SECTIONS = [
  {
    label: "COMMAND",
    items: [
      { id: "hivemind", label: "Hive Mind", icon: "L", color: "text-amber-400" },
      { id: "trading", label: "Trading", icon: "~", color: "text-green-400" },
      { id: "intel", label: "Market Intel", icon: "M", color: "text-amber-400" },
      { id: "portfolio", label: "Portfolio", icon: "$", color: "text-emerald-400" },
      { id: "control", label: "Control Panel", icon: "#", color: "text-red-400" },
    ],
  },
  {
    label: "BUSINESS",
    items: [
      { id: "revenue", label: "Revenue", icon: "$", color: "text-emerald-400" },
      { id: "broker", label: "Broker OS", icon: "%", color: "text-blue-400" },
      { id: "business", label: "Business OS", icon: "!", color: "text-purple-400" },
    ],
  },
  {
    label: "OPERATIONS",
    items: [
      { id: "taskboard", label: "Taskboard", icon: ">", color: "text-cyan-400" },
      { id: "sessions", label: "Hive Sessions", icon: "*", color: "text-pink-400" },
      { id: "reports", label: "Reports", icon: "R", color: "text-blue-400" },
      { id: "funnel", label: "Funnel", icon: "+", color: "text-orange-400" },
      { id: "settings", label: "Settings", icon: "S", color: "text-gray-400" },
    ],
  },
]

export default function Sidebar({ active, onNav, collapsed }) {
  return (
    <aside className={`${collapsed ? "w-16" : "w-56"} flex-shrink-0 bg-[#0d0d14] border-r border-white/[0.04] flex flex-col transition-all duration-300 overflow-hidden`}>
      {/* Logo */}
      <div className="px-4 py-4 flex items-center gap-2.5 border-b border-white/[0.04]">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 via-orange-500 to-red-600 flex items-center justify-center text-xs font-black text-black shadow-lg shadow-amber-500/20 flex-shrink-0">L</div>
        {!collapsed && (
          <div>
            <div className="text-xs font-bold tracking-[0.2em] bg-gradient-to-r from-amber-300 to-orange-400 bg-clip-text text-transparent">LUCREX</div>
            <div className="text-[7px] text-gray-600 tracking-[0.15em]">COMMAND CENTER</div>
            <div className="text-[6px] text-gray-700 italic tracking-[0.1em] -mt-0.5">By Everlight Ventures</div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {NAV_SECTIONS.map(section => (
          <div key={section.label} className="mb-3">
            {!collapsed && <div className="px-4 py-1 text-[9px] font-medium tracking-[0.2em] text-gray-600">{section.label}</div>}
            {section.items.map(item => (
              <button
                key={item.id}
                onClick={() => onNav(item.id)}
                className={`w-full flex items-center gap-2.5 px-4 py-2 text-left transition-all ${
                  active === item.id
                    ? "bg-white/[0.06] border-r-2 border-amber-400 text-white"
                    : "text-gray-500 hover:text-gray-300 hover:bg-white/[0.02]"
                }`}
              >
                <span className={`text-sm font-mono ${active === item.id ? item.color : ""} flex-shrink-0 w-5 text-center`}>{item.icon}</span>
                {!collapsed && <span className="text-[12px] font-medium truncate">{item.label}</span>}
              </button>
            ))}
          </div>
        ))}
      </nav>

      {/* Status footer */}
      <div className="px-4 py-3 border-t border-white/[0.04]">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 pulse-live" />
            <span className="text-[10px] text-gray-500 font-mono">ORACLE E5 ONLINE</span>
          </div>
        )}
      </div>
    </aside>
  )
}
