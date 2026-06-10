import React from 'react'
import { useSearchParams } from 'react-router-dom'

const MBTI_TYPES = [
  'INTJ', 'INTP', 'ENTJ', 'ENTP',
  'INFJ', 'INFP', 'ENFJ', 'ENFP',
  'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ',
  'ISTP', 'ISFP', 'ESTP', 'ESFP',
]

const ZODIACS = [
  'aries', 'taurus', 'gemini', 'cancer',
  'leo', 'virgo', 'libra', 'scorpio',
  'sagittarius', 'capricorn', 'aquarius', 'pisces',
]

const DEFAULT_DEPTS = [
  'Claude Corp',
  'Gemini Ops',
  'Codex Labs',
  'Perplexity Intel',
  'SaaS Factory',
  'Beat Collectives',
]

export default function SearchFilters({ departments = [] }) {
  const [params, setParams] = useSearchParams()

  const set = (k, v) => {
    const next = new URLSearchParams(params)
    if (!v) next.delete(k)
    else next.set(k, v)
    setParams(next, { replace: true })
  }
  const toggle = (k, v) => {
    if (params.get(k) === v) set(k, '')
    else set(k, v)
  }

  const current = {
    q: params.get('q') || '',
    mbti: params.get('mbti') || '',
    zodiac: params.get('zodiac') || '',
    dept: params.get('dept') || '',
    has_photo: params.get('has_photo') || '',
  }

  const deptList = departments.length ? departments : DEFAULT_DEPTS

  const chip = (active, label, onClick, extra = '') => (
    <button
      key={label + extra}
      onClick={onClick}
      className={`px-3 py-1 rounded-full text-[11px] font-medium transition-all whitespace-nowrap ${
        active
          ? 'bg-amber-400/20 text-amber-300 border border-amber-400/40'
          : 'bg-white/5 text-gray-400 border border-transparent hover:text-gray-100 hover:bg-white/10'
      }`}
    >
      {label}
    </button>
  )

  const hasAny =
    current.q || current.mbti || current.zodiac || current.dept || current.has_photo

  return (
    <div className="flex flex-col gap-3">
      <div className="relative">
        <input
          type="text"
          value={current.q}
          onChange={(e) => set('q', e.target.value)}
          placeholder="Search name, title, backstory, hobbies, catchphrase..."
          className="w-full bg-[#12121a] border border-[#1e1e2e] rounded-xl px-4 py-3 pr-10 text-sm placeholder:text-gray-600 focus:outline-none focus:border-amber-400/40"
        />
        {current.q && (
          <button
            onClick={() => set('q', '')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-amber-400"
            title="Clear search"
          >
            x
          </button>
        )}
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-wider text-gray-600 mb-1">Department</div>
        <div className="flex gap-2 flex-wrap">
          {deptList.map((d) =>
            chip(current.dept === d, d, () => toggle('dept', d), 'dept')
          )}
        </div>
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-wider text-gray-600 mb-1">MBTI</div>
        <div className="flex gap-2 flex-wrap">
          {MBTI_TYPES.map((m) =>
            chip(current.mbti === m, m, () => toggle('mbti', m), 'mbti')
          )}
        </div>
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-wider text-gray-600 mb-1">Zodiac</div>
        <div className="flex gap-2 flex-wrap">
          {ZODIACS.map((z) =>
            chip(
              current.zodiac === z,
              z[0].toUpperCase() + z.slice(1),
              () => toggle('zodiac', z),
              'zod'
            )
          )}
        </div>
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-wider text-gray-600 mb-1">Other</div>
        <div className="flex gap-2 flex-wrap">
          {chip(
            current.has_photo === 'true',
            'Has photo',
            () => toggle('has_photo', 'true'),
            'photo'
          )}
          {hasAny && (
            <button
              onClick={() => setParams(new URLSearchParams(), { replace: true })}
              className="px-3 py-1 rounded-full text-[11px] font-medium border border-red-400/30 text-red-300 hover:bg-red-400/10"
            >
              Clear all
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
