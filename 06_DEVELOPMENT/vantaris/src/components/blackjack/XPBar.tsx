'use client'

import { motion } from 'framer-motion'

/**
 * XP Progress Bar + Streak Counter
 *
 * Shows current XP, progress to next rank, and active streak.
 * Gold gradient fill. Animates on XP gain.
 */

const RANK_THRESHOLDS = [
  { rank: 'Bronze', xp: 0, color: '#cd7f32' },
  { rank: 'Silver', xp: 1000, color: '#c0c0c0' },
  { rank: 'Gold', xp: 5000, color: '#ffd700' },
  { rank: 'Platinum', xp: 15000, color: '#e5e4e2' },
  { rank: 'Diamond', xp: 40000, color: '#b9f2ff' },
  { rank: 'Legend', xp: 100000, color: '#ff6b35' },
]

function getRankProgress(xp: number) {
  let currentIdx = 0
  for (let i = RANK_THRESHOLDS.length - 1; i >= 0; i--) {
    if (xp >= RANK_THRESHOLDS[i].xp) { currentIdx = i; break }
  }

  const current = RANK_THRESHOLDS[currentIdx]
  const next = RANK_THRESHOLDS[currentIdx + 1]

  if (!next) return { current, next: null, progress: 100, xpNeeded: 0 }

  const range = next.xp - current.xp
  const progress = ((xp - current.xp) / range) * 100

  return { current, next, progress: Math.min(progress, 100), xpNeeded: next.xp - xp }
}

export function XPBar({ xp, streak }: { xp: number; streak: number }) {
  const { current, next, progress, xpNeeded } = getRankProgress(xp)

  return (
    <div className="flex items-center gap-3">
      {/* Streak badge */}
      {streak > 0 && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="flex items-center gap-1 px-2 py-1 rounded-full text-xs font-bold"
          style={{
            background: streak >= 5 ? 'var(--gold-glow)' : 'rgba(255,255,255,0.05)',
            color: streak >= 5 ? 'var(--gold)' : 'var(--win)',
            border: `1px solid ${streak >= 5 ? 'var(--gold)' : 'var(--win)'}30`,
          }}
        >
          <span>{streak >= 5 ? '\uD83D\uDD25' : '\u26A1'}</span>
          <span>{streak}</span>
        </motion.div>
      )}

      {/* XP bar */}
      <div className="flex-1 max-w-[160px]">
        <div className="flex items-center justify-between mb-0.5">
          <span className="text-[9px] uppercase tracking-wider" style={{ color: current.color }}>
            {current.rank}
          </span>
          {next && (
            <span className="text-[9px] font-mono" style={{ color: 'var(--text-tertiary)' }}>
              {xpNeeded.toLocaleString()} XP to {next.rank}
            </span>
          )}
        </div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--vanta-surface)' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: `linear-gradient(90deg, ${current.color}, ${next?.color || current.color})` }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>
      </div>
    </div>
  )
}
