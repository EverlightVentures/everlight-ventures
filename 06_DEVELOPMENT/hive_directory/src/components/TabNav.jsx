import React from 'react'

export default function TabNav({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1 border-b border-white/5 overflow-x-auto no-scrollbar">
      {tabs.map((t) => {
        const isActive = t.key === active
        return (
          <button
            key={t.key}
            onClick={() => onChange(t.key)}
            className={`px-4 py-2 text-xs font-medium uppercase tracking-wider transition-all whitespace-nowrap border-b-2 ${
              isActive
                ? 'text-amber-400 border-amber-400'
                : 'text-gray-500 border-transparent hover:text-gray-200'
            }`}
          >
            {t.label}
          </button>
        )
      })}
    </div>
  )
}
