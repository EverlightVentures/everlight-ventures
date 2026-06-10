import React from 'react'
import { Link } from 'react-router-dom'
import { ZodiacBadge, MbtiBadge } from './ArchetypeBadge.jsx'

export const DEPARTMENT_COLORS = {
  'Claude Corp': { stripe: '#f59e0b', text: 'text-amber-400' },
  'Gemini Ops': { stripe: '#10b981', text: 'text-emerald-400' },
  'Codex Labs': { stripe: '#0ea5e9', text: 'text-sky-400' },
  'Perplexity Intel': { stripe: '#8b5cf6', text: 'text-violet-400' },
  'SaaS Factory': { stripe: '#f43f5e', text: 'text-rose-400' },
  'Beat Collectives': { stripe: '#64748b', text: 'text-slate-400' },
}

function deptColor(dept) {
  return DEPARTMENT_COLORS[dept] || { stripe: '#64748b', text: 'text-slate-400' }
}

export default function EmployeeCard({ emp }) {
  const color = deptColor(emp.department)
  const displayName = emp.name || emp.nickname || emp.slug
  return (
    <Link
      to={`/team/${emp.slug}`}
      className="card card-hover flex flex-col overflow-hidden p-0"
    >
      <span className="stripe" style={{ background: color.stripe }} />
      <div className="p-4 flex gap-3">
        <div className="shrink-0 w-16 h-16 rounded-xl overflow-hidden bg-[#1a1a24] ring-1 ring-white/5">
          {emp.photo_url ? (
            <img
              src={emp.photo_url}
              alt={displayName}
              className="w-full h-full object-cover"
            />
          ) : emp.avatar_url ? (
            <img
              src={emp.avatar_url}
              alt={displayName}
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-600 text-xl font-mono">
              {displayName?.[0] || '?'}
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-white truncate">
              {displayName}
            </span>
            {emp.nickname && emp.nickname !== displayName && (
              <span className="text-[11px] text-gray-500">"{emp.nickname}"</span>
            )}
          </div>
          <div className={`text-[11px] uppercase tracking-wider ${color.text} mt-0.5 truncate`}>
            {emp.title || '(no title)'}
          </div>
          <div className="text-[10px] text-gray-600 mt-0.5 truncate">
            {emp.department || 'Unassigned'}
            {emp.fire_team ? ` / ${emp.fire_team}` : ''}
          </div>
          <div className="flex gap-1.5 mt-2 flex-wrap">
            {emp.mbti && <MbtiBadge mbti={emp.mbti} />}
            {emp.zodiac && <ZodiacBadge zodiac={emp.zodiac} />}
            {emp.has_photo && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase">
                photo
              </span>
            )}
            {emp.has_voice && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[9px] bg-sky-500/10 text-sky-400 border border-sky-500/20 uppercase">
                voice
              </span>
            )}
          </div>
        </div>
      </div>
      {emp.catchphrase && (
        <div className="px-4 pb-3 -mt-1">
          <p className="text-[11px] italic text-gray-500 line-clamp-2">
            "{emp.catchphrase}"
          </p>
        </div>
      )}
    </Link>
  )
}
