'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'

/**
 * Hall of Legends -- Leaderboard
 *
 * Top players by chips won. Daily / Weekly / All-Time tabs.
 * Gold/silver/bronze styling for top 3.
 */

const MOCK_LEADERS = [
  { rank: 1, name: 'DarkStar', tier: 'Legend', chipsWon: 847200, hands: 2341, winRate: 54.2 },
  { rank: 2, name: 'xMidas', tier: 'Diamond', chipsWon: 623100, hands: 1872, winRate: 52.8 },
  { rank: 3, name: 'Phantom_x', tier: 'Diamond', chipsWon: 518900, hands: 1654, winRate: 51.1 },
  { rank: 4, name: 'NightKing', tier: 'Platinum', chipsWon: 412300, hands: 1420, winRate: 50.3 },
  { rank: 5, name: 'CryptoWolf', tier: 'Platinum', chipsWon: 389700, hands: 1380, winRate: 49.8 },
  { rank: 6, name: 'Velocity', tier: 'Gold', chipsWon: 287400, hands: 1102, winRate: 48.9 },
  { rank: 7, name: 'LuckyAce', tier: 'Gold', chipsWon: 234500, hands: 987, winRate: 50.1 },
  { rank: 8, name: 'ShadowKing', tier: 'Gold', chipsWon: 198200, hands: 876, winRate: 47.2 },
  { rank: 9, name: 'NightOwl22', tier: 'Silver', chipsWon: 156800, hands: 743, winRate: 46.8 },
  { rank: 10, name: 'xVenus', tier: 'Silver', chipsWon: 123400, hands: 654, winRate: 45.9 },
]

const RANK_MEDAL: Record<number, { color: string; bg: string }> = {
  1: { color: '#ffd700', bg: 'rgba(255,215,0,0.1)' },
  2: { color: '#c0c0c0', bg: 'rgba(192,192,192,0.08)' },
  3: { color: '#cd7f32', bg: 'rgba(205,127,50,0.08)' },
}

const TIER_COLORS: Record<string, string> = {
  Bronze: '#cd7f32', Silver: '#c0c0c0', Gold: '#ffd700',
  Platinum: '#e5e4e2', Diamond: '#b9f2ff', Legend: '#ff6b35',
}

export function Leaderboard({
  isOpen,
  onClose,
}: {
  isOpen: boolean
  onClose: () => void
}) {
  const [period, setPeriod] = useState<'daily' | 'weekly' | 'alltime'>('weekly')

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(16px)' }}
          onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
        >
          <motion.div
            initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 20 }}
            className="w-full max-w-lg max-h-[80vh] rounded-2xl overflow-hidden flex flex-col"
            style={{ background: 'var(--vanta-abyss)', border: '1px solid var(--vanta-border)' }}
          >
            {/* Header */}
            <div className="px-6 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--vanta-border)' }}>
              <div>
                <h2 className="font-display text-xl font-bold" style={{ color: 'var(--gold)' }}>
                  Hall of Legends
                </h2>
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Top players by chips won</p>
              </div>
              <button onClick={onClose} className="text-lg" style={{ color: 'var(--text-tertiary)' }}>&times;</button>
            </div>

            {/* Period tabs */}
            <div className="flex border-b" style={{ borderColor: 'var(--vanta-border)' }}>
              {(['daily', 'weekly', 'alltime'] as const).map(p => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className="flex-1 py-2 text-xs uppercase tracking-wider"
                  style={{
                    color: period === p ? 'var(--gold)' : 'var(--text-tertiary)',
                    borderBottom: period === p ? '2px solid var(--gold)' : '2px solid transparent',
                  }}
                >
                  {p === 'alltime' ? 'All Time' : p}
                </button>
              ))}
            </div>

            {/* Rankings */}
            <div className="flex-1 overflow-y-auto">
              {MOCK_LEADERS.map((leader, idx) => {
                const medal = RANK_MEDAL[leader.rank]
                return (
                  <motion.div
                    key={leader.rank}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="flex items-center gap-3 px-5 py-3 border-b"
                    style={{
                      borderColor: 'var(--vanta-border)',
                      background: medal?.bg || 'transparent',
                    }}
                  >
                    {/* Rank number */}
                    <div
                      className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                      style={{
                        color: medal?.color || 'var(--text-tertiary)',
                        background: medal ? `${medal.color}20` : 'var(--vanta-surface)',
                        border: medal ? `1px solid ${medal.color}40` : '1px solid var(--vanta-border)',
                      }}
                    >
                      {leader.rank}
                    </div>

                    {/* Player info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold truncate">{leader.name}</span>
                        <span
                          className="text-[9px] px-1.5 py-0.5 rounded-full font-semibold"
                          style={{ color: TIER_COLORS[leader.tier], background: `${TIER_COLORS[leader.tier]}15` }}
                        >
                          {leader.tier}
                        </span>
                      </div>
                      <div className="flex gap-3 mt-0.5">
                        <span className="text-[10px] font-mono" style={{ color: 'var(--text-tertiary)' }}>
                          {leader.hands} hands
                        </span>
                        <span className="text-[10px] font-mono" style={{ color: leader.winRate >= 50 ? 'var(--win)' : 'var(--text-tertiary)' }}>
                          {leader.winRate}% win rate
                        </span>
                      </div>
                    </div>

                    {/* Chips won */}
                    <div className="text-right">
                      <p className="font-mono text-sm font-bold" style={{ color: medal?.color || 'var(--gold)' }}>
                        {leader.chipsWon.toLocaleString()}
                      </p>
                      <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>GC won</p>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
