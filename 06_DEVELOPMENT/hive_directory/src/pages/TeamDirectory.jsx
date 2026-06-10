import React, { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import EmployeeCard, { DEPARTMENT_COLORS } from '../components/EmployeeCard.jsx'
import SearchFilters from '../components/SearchFilters.jsx'
import { useApi } from '../hooks.jsx'
import { searchTeam } from '../api/team.js'

export default function TeamDirectory() {
  const [params] = useSearchParams()
  const { data: all } = useApi('/team')
  const { data: depts } = useApi('/departments')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)

  const filter = useMemo(
    () => ({
      q: params.get('q') || '',
      mbti: params.get('mbti') || '',
      zodiac: params.get('zodiac') || '',
      dept: params.get('dept') || '',
      has_photo: params.get('has_photo') || '',
    }),
    [params]
  )

  useEffect(() => {
    let alive = true
    const hasFilter = Object.values(filter).some(Boolean)
    if (!hasFilter) {
      setResults(null)
      return
    }
    setLoading(true)
    searchTeam(filter)
      .then((data) => {
        if (alive) setResults(data)
      })
      .catch(() => {
        if (alive) setResults([])
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [filter])

  const list = results ?? all ?? []
  const departments = (depts || []).map((d) => d.department)

  const stats = useMemo(() => {
    const source = all || []
    return {
      total: source.length,
      withPhoto: source.filter((e) => e.has_photo).length,
      withVoice: source.filter((e) => e.has_voice).length,
    }
  }, [all])

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-white">Hive Directory</h1>
          <p className="text-sm text-gray-500 mt-1">
            78 AI employees. Search, filter, inspect, launch.
          </p>
        </div>
        <div className="flex gap-3 text-xs font-mono">
          <Stat label="Total" value={stats.total} color="text-white" />
          <Stat label="Photo" value={stats.withPhoto} color="text-emerald-400" />
          <Stat label="Voice" value={stats.withVoice} color="text-sky-400" />
        </div>
      </div>

      {depts && depts.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
          {depts.map((d) => {
            const c = DEPARTMENT_COLORS[d.department] || { stripe: '#64748b' }
            return (
              <div
                key={d.department}
                className="card py-2 px-3 flex items-center justify-between gap-2"
              >
                <div>
                  <div
                    className="text-[10px] uppercase tracking-wider"
                    style={{ color: c.stripe }}
                  >
                    {d.department}
                  </div>
                  <div className="text-[10px] text-gray-600">
                    {d.with_photo} photo / {d.with_voice} voice
                  </div>
                </div>
                <div className="font-mono text-lg text-white">{d.count}</div>
              </div>
            )
          })}
        </div>
      )}

      <SearchFilters departments={departments} />

      <div className="flex items-center justify-between text-[11px] text-gray-500">
        <div>
          {loading
            ? 'Searching...'
            : `Showing ${list.length} of ${stats.total} employees`}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {list.map((emp) => (
          <EmployeeCard key={emp.slug} emp={emp} />
        ))}
      </div>

      {list.length === 0 && !loading && (
        <div className="text-center py-20 text-gray-500 text-sm">
          No employees match the current filters.
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, color }) {
  return (
    <div className="card py-2 px-3 text-center min-w-[68px]">
      <div className={`text-base font-bold ${color}`}>{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-gray-600">
        {label}
      </div>
    </div>
  )
}
