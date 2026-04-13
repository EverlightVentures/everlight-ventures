'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'

/**
 * Player Profile Panel
 *
 * Slide-out from left. Shows full stats, achievements,
 * hand history, and settings.
 * Migrated from the Everlight PlayerProfile.tsx.
 */

const ACHIEVEMENT_DEFS = [
  { id: 'first_win', name: 'First Blood', desc: 'Win your first hand', icon: '\uD83C\uDFC6', reward: 50 },
  { id: 'first_blackjack', name: 'Natural 21', desc: 'Get your first blackjack', icon: '\uD83C\uDCCF', reward: 200 },
  { id: 'hot_streak_5', name: 'On Fire', desc: 'Win 5 hands in a row', icon: '\uD83D\uDD25', reward: 500 },
  { id: 'hot_streak_10', name: 'Unstoppable', desc: 'Win 10 hands in a row', icon: '\u26A1', reward: 2000 },
  { id: 'centurion', name: 'Centurion', desc: 'Play 100 hands', icon: '\uD83D\uDEE1', reward: 1000 },
  { id: 'big_winner', name: 'High Roller', desc: 'Win 10,000+ chips in one hand', icon: '\uD83D\uDCB0', reward: 0 },
  { id: 'gold_rank', name: 'Going for Gold', desc: 'Reach Gold rank', icon: '\uD83E\uDD47', reward: 2500 },
  { id: 'diamond_rank', name: 'Diamond Club', desc: 'Reach Diamond rank', icon: '\uD83D\uDC8E', reward: 10000 },
  { id: 'lucky_seven', name: 'Lucky Seven', desc: '7 blackjacks total', icon: '\uD83C\uDFB0', reward: 777 },
]

interface PlayerStats {
  chips: number
  gems: number
  sweepsCoins: number
  xp: number
  rank: string
  handsPlayed: number
  handsWon: number
  blackjacks: number
  currentStreak: number
  bestStreak: number
  biggestWin: number
  presenceMultiplier: number
}

const RANK_COLORS: Record<string, string> = {
  Bronze: '#cd7f32', Silver: '#c0c0c0', Gold: '#ffd700',
  Platinum: '#e5e4e2', Diamond: '#b9f2ff', Legend: '#ff6b35',
}

export function PlayerProfilePanel({
  isOpen,
  onClose,
  stats,
  unlockedAchievements,
  onOpenAvatar,
  onLogout,
}: {
  isOpen: boolean
  onClose: () => void
  stats: PlayerStats
  unlockedAchievements: string[]
  onOpenAvatar: () => void
  onLogout: () => void
}) {
  const [tab, setTab] = useState<'stats' | 'achievements' | 'settings'>('stats')
  const winRate = stats.handsPlayed > 0 ? ((stats.handsWon / stats.handsPlayed) * 100).toFixed(1) : '0.0'

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(0,0,0,0.6)' }}
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ x: -320 }} animate={{ x: 0 }} exit={{ x: -320 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed left-0 top-0 bottom-0 w-80 z-50 flex flex-col overflow-hidden"
            style={{ background: 'var(--vanta-abyss)', borderRight: '1px solid var(--vanta-border)' }}
          >
            {/* Header with avatar */}
            <div className="p-5 text-center" style={{ background: 'var(--vanta-surface)' }}>
              <div
                className="w-20 h-20 rounded-full mx-auto mb-3 flex items-center justify-center text-2xl font-bold cursor-pointer relative"
                style={{
                  background: `linear-gradient(135deg, ${RANK_COLORS[stats.rank] || '#888'}40, ${RANK_COLORS[stats.rank] || '#888'}10)`,
                  border: `2px solid ${RANK_COLORS[stats.rank] || '#888'}60`,
                }}
                onClick={onOpenAvatar}
              >
                P
                <div className="absolute inset-0 rounded-full flex items-center justify-center bg-black/50 opacity-0 hover:opacity-100 transition-opacity text-xs">
                  EDIT
                </div>
              </div>
              <p className="font-semibold text-sm">Player</p>
              <div className="flex items-center justify-center gap-2 mt-1">
                <span
                  className="text-xs px-2 py-0.5 rounded-full font-semibold"
                  style={{
                    color: RANK_COLORS[stats.rank],
                    background: `${RANK_COLORS[stats.rank]}15`,
                    border: `1px solid ${RANK_COLORS[stats.rank]}30`,
                  }}
                >
                  {stats.rank}
                </span>
                <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
                  {stats.xp.toLocaleString()} XP
                </span>
              </div>

              {/* Balances */}
              <div className="flex justify-center gap-4 mt-3">
                <div className="text-center">
                  <p className="font-mono text-sm font-bold" style={{ color: 'var(--gold)' }}>{stats.chips.toLocaleString()}</p>
                  <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>GC</p>
                </div>
                <div className="text-center">
                  <p className="font-mono text-sm font-bold" style={{ color: '#58a6ff' }}>{stats.gems}</p>
                  <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>Gems</p>
                </div>
                <div className="text-center">
                  <p className="font-mono text-sm font-bold" style={{ color: 'var(--win)' }}>{stats.sweepsCoins.toFixed(2)}</p>
                  <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>SC</p>
                </div>
              </div>

              {/* Presence */}
              <div className="mt-2 inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs" style={{ background: 'var(--gold-glow)', color: 'var(--gold)' }}>
                <span>\u2728</span>
                <span className="font-mono font-bold">{stats.presenceMultiplier.toFixed(2)}x</span>
                <span>presence</span>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b" style={{ borderColor: 'var(--vanta-border)' }}>
              {(['stats', 'achievements', 'settings'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className="flex-1 py-2.5 text-xs uppercase tracking-wider transition-colors"
                  style={{
                    color: tab === t ? 'var(--gold)' : 'var(--text-tertiary)',
                    borderBottom: tab === t ? '2px solid var(--gold)' : '2px solid transparent',
                  }}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {tab === 'stats' && (
                <div className="space-y-3">
                  {[
                    { label: 'Hands Played', value: stats.handsPlayed.toLocaleString() },
                    { label: 'Hands Won', value: stats.handsWon.toLocaleString() },
                    { label: 'Win Rate', value: `${winRate}%`, color: parseFloat(winRate) >= 50 ? 'var(--win)' : 'var(--loss)' },
                    { label: 'Blackjacks', value: stats.blackjacks.toLocaleString(), color: 'var(--gold)' },
                    { label: 'Current Streak', value: stats.currentStreak.toString(), color: stats.currentStreak >= 3 ? 'var(--win)' : undefined },
                    { label: 'Best Streak', value: stats.bestStreak.toString() },
                    { label: 'Biggest Win', value: stats.biggestWin.toLocaleString() + ' GC', color: 'var(--gold)' },
                  ].map(stat => (
                    <div key={stat.label} className="flex justify-between items-center py-1.5 border-b" style={{ borderColor: 'var(--vanta-border)' }}>
                      <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{stat.label}</span>
                      <span className="font-mono text-sm font-semibold" style={{ color: stat.color || 'var(--text-primary)' }}>{stat.value}</span>
                    </div>
                  ))}
                </div>
              )}

              {tab === 'achievements' && (
                <div className="space-y-2">
                  {ACHIEVEMENT_DEFS.map(ach => {
                    const unlocked = unlockedAchievements.includes(ach.id)
                    return (
                      <div
                        key={ach.id}
                        className="flex items-center gap-3 p-3 rounded-xl"
                        style={{
                          background: unlocked ? 'var(--gold-glow)' : 'var(--vanta-surface)',
                          border: `1px solid ${unlocked ? 'rgba(201,168,76,0.2)' : 'var(--vanta-border)'}`,
                          opacity: unlocked ? 1 : 0.5,
                        }}
                      >
                        <span className="text-xl">{ach.icon}</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold">{ach.name}</p>
                          <p className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>{ach.desc}</p>
                        </div>
                        {ach.reward > 0 && (
                          <span className="text-[10px] font-mono" style={{ color: unlocked ? 'var(--gold)' : 'var(--text-tertiary)' }}>
                            {unlocked ? 'Claimed' : `+${ach.reward}`}
                          </span>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}

              {tab === 'settings' && (
                <div className="space-y-4">
                  {[
                    { label: 'Sound Effects', key: 'sound' },
                    { label: 'Music', key: 'music' },
                    { label: 'Dealer Voice', key: 'voice' },
                    { label: 'Auto-Rebet', key: 'autorebet' },
                    { label: 'Haptic Feedback', key: 'haptic' },
                  ].map(setting => (
                    <div key={setting.key} className="flex justify-between items-center">
                      <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{setting.label}</span>
                      <button className="w-10 h-5 rounded-full transition-colors" style={{ background: 'var(--gold)' }}>
                        <div className="w-4 h-4 rounded-full bg-white ml-auto mr-0.5" />
                      </button>
                    </div>
                  ))}

                  <div className="pt-4 border-t" style={{ borderColor: 'var(--vanta-border)' }}>
                    <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--text-tertiary)' }}>Card Speed</p>
                    <div className="flex gap-2">
                      {['Normal', 'Fast'].map(s => (
                        <button key={s} className="text-xs px-3 py-1.5 rounded-lg" style={{ background: s === 'Normal' ? 'var(--gold-glow)' : 'var(--vanta-surface)', color: s === 'Normal' ? 'var(--gold)' : 'var(--text-tertiary)', border: '1px solid var(--vanta-border)' }}>
                          {s}
                        </button>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={onLogout}
                    className="w-full mt-4 py-2 rounded-xl text-xs font-semibold transition-colors"
                    style={{ background: 'var(--loss-glow)', color: 'var(--loss)', border: '1px solid rgba(255,45,85,0.2)' }}
                  >
                    LOG OUT
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
