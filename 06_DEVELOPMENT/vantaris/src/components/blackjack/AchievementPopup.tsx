'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState } from 'react'

/**
 * Achievement Unlock Popup
 *
 * Slides in from the top-right when an achievement unlocks.
 * Gold border glow. Auto-dismisses after 4 seconds.
 * Stacks if multiple unlock simultaneously.
 */

export interface Achievement {
  id: string
  name: string
  desc: string
  reward: number
}

const ACHIEVEMENT_ICONS: Record<string, string> = {
  first_win: '\uD83C\uDFC6',
  first_blackjack: '\uD83C\uDCCF',
  hot_streak_5: '\uD83D\uDD25',
  hot_streak_10: '\u26A1',
  centurion: '\uD83D\uDEE1',
  big_winner: '\uD83D\uDCB0',
  gold_rank: '\uD83E\uDD47',
  diamond_rank: '\uD83D\uDC8E',
  lucky_seven: '\uD83C\uDFB0',
}

export function AchievementPopup({
  achievements,
  onDismiss,
}: {
  achievements: Achievement[]
  onDismiss: (id: string) => void
}) {
  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {achievements.map((ach) => (
          <AchievementToast key={ach.id} achievement={ach} onDismiss={() => onDismiss(ach.id)} />
        ))}
      </AnimatePresence>
    </div>
  )
}

function AchievementToast({ achievement, onDismiss }: { achievement: Achievement; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 4000)
    return () => clearTimeout(timer)
  }, [onDismiss])

  return (
    <motion.div
      initial={{ opacity: 0, x: 100, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 200, damping: 20 }}
      className="glass-elevated px-4 py-3 rounded-xl flex items-center gap-3 min-w-[260px] pointer-events-auto cursor-pointer"
      style={{
        border: '1px solid rgba(201,168,76,0.3)',
        boxShadow: '0 0 20px rgba(201,168,76,0.15)',
      }}
      onClick={onDismiss}
    >
      <div className="text-2xl">{ACHIEVEMENT_ICONS[achievement.id] || '\uD83C\uDFC6'}</div>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] uppercase tracking-widest" style={{ color: 'var(--gold)' }}>
          Achievement Unlocked
        </p>
        <p className="text-sm font-semibold truncate">{achievement.name}</p>
        <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{achievement.desc}</p>
      </div>
      {achievement.reward > 0 && (
        <div className="text-right">
          <p className="font-mono text-sm font-bold" style={{ color: 'var(--gold)' }}>
            +{achievement.reward.toLocaleString()}
          </p>
          <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>GC</p>
        </div>
      )}
    </motion.div>
  )
}
