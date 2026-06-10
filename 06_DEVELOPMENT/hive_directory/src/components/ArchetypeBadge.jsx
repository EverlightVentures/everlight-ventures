import React from 'react'

// Zodiac element palettes
const ZODIAC_ELEMENT = {
  aries: 'fire', leo: 'fire', sagittarius: 'fire',
  taurus: 'earth', virgo: 'earth', capricorn: 'earth',
  gemini: 'air', libra: 'air', aquarius: 'air',
  cancer: 'water', scorpio: 'water', pisces: 'water',
}

const ELEMENT_STYLE = {
  fire: 'bg-orange-500/15 text-orange-300 border-orange-500/30',
  earth: 'bg-emerald-600/15 text-emerald-300 border-emerald-600/30',
  air: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
  water: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
  unknown: 'bg-gray-500/15 text-gray-300 border-gray-500/30',
}

const ZODIAC_GLYPH = {
  aries: 'Aries', taurus: 'Taurus', gemini: 'Gemini', cancer: 'Cancer',
  leo: 'Leo', virgo: 'Virgo', libra: 'Libra', scorpio: 'Scorpio',
  sagittarius: 'Sagittarius', capricorn: 'Capricorn',
  aquarius: 'Aquarius', pisces: 'Pisces',
}

// MBTI temperament buckets
const MBTI_TEMPERAMENT = {
  INTJ: 'analyst', INTP: 'analyst', ENTJ: 'analyst', ENTP: 'analyst',
  INFJ: 'diplomat', INFP: 'diplomat', ENFJ: 'diplomat', ENFP: 'diplomat',
  ISTJ: 'sentinel', ISFJ: 'sentinel', ESTJ: 'sentinel', ESFJ: 'sentinel',
  ISTP: 'explorer', ISFP: 'explorer', ESTP: 'explorer', ESFP: 'explorer',
}

const TEMPERAMENT_STYLE = {
  analyst: 'bg-violet-500/15 text-violet-300 border-violet-500/30',
  diplomat: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  sentinel: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  explorer: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  unknown: 'bg-gray-500/15 text-gray-300 border-gray-500/30',
}

export function ZodiacBadge({ zodiac, summary = '' }) {
  const z = (zodiac || '').toLowerCase()
  const elem = ZODIAC_ELEMENT[z] || 'unknown'
  const style = ELEMENT_STYLE[elem]
  const label = ZODIAC_GLYPH[z] || (z ? z[0].toUpperCase() + z.slice(1) : '??')
  return (
    <span
      title={summary || `${label} (${elem})`}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-medium uppercase tracking-wider ${style}`}
    >
      <span className="opacity-70">{elem[0].toUpperCase()}</span>
      <span>{label}</span>
    </span>
  )
}

export function MbtiBadge({ mbti, summary = '' }) {
  const m = (mbti || '').toUpperCase()
  const t = MBTI_TEMPERAMENT[m] || 'unknown'
  const style = TEMPERAMENT_STYLE[t]
  return (
    <span
      title={summary || `${m} (${t})`}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-mono font-semibold ${style}`}
    >
      {m || 'XXXX'}
    </span>
  )
}

export default { ZodiacBadge, MbtiBadge }
