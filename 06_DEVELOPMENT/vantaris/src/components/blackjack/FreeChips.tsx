'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'

/**
 * Free Chips Panel (Ad Rewards)
 *
 * Watch a rewarded ad -> get 100 GC. Max 10/day.
 * Also shows daily login bonus status and streak.
 */

export function FreeChips({
  isOpen,
  onClose,
  refillsRemaining,
  currentStreak,
  onWatchAd,
  onClaimDaily,
  dailyClaimed,
}: {
  isOpen: boolean
  onClose: () => void
  refillsRemaining: number
  currentStreak: number
  onWatchAd: () => void
  onClaimDaily: () => void
  dailyClaimed: boolean
}) {
  const [watching, setWatching] = useState(false)

  const handleWatch = async () => {
    setWatching(true)
    // Simulate ad watch (in production: Google AdSense rewarded ad)
    setTimeout(() => {
      onWatchAd()
      setWatching(false)
    }, 2000)
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(12px)' }}
          onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
        >
          <motion.div
            initial={{ scale: 0.95, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, y: 20 }}
            className="w-full max-w-sm rounded-2xl overflow-hidden"
            style={{ background: 'var(--vanta-abyss)', border: '1px solid var(--vanta-border)' }}
          >
            <div className="px-6 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--vanta-border)' }}>
              <h2 className="font-display text-lg font-bold" style={{ color: 'var(--win)' }}>Free Chips</h2>
              <button onClick={onClose} className="text-lg" style={{ color: 'var(--text-tertiary)' }}>&times;</button>
            </div>

            <div className="p-6 space-y-4">
              {/* Daily Login Bonus */}
              <div className="rounded-xl p-4" style={{ background: dailyClaimed ? 'rgba(0,230,118,0.05)' : 'var(--gold-glow)', border: `1px solid ${dailyClaimed ? 'rgba(0,230,118,0.2)' : 'rgba(201,168,76,0.3)'}` }}>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold">Daily Login Bonus</p>
                  {currentStreak > 0 && (
                    <span className="text-xs font-mono" style={{ color: 'var(--gold)' }}>
                      {currentStreak}-day streak
                    </span>
                  )}
                </div>
                <p className="text-xs mb-3" style={{ color: 'var(--text-tertiary)' }}>
                  {dailyClaimed
                    ? 'Already claimed today. Come back tomorrow!'
                    : `Claim 100 GC + ${Math.min(currentStreak * 10, 200)} streak bonus + 0.10 free SC`}
                </p>
                <motion.button
                  onClick={onClaimDaily}
                  className={dailyClaimed ? 'btn-ghost w-full py-2 text-xs opacity-50' : 'btn-primary w-full py-2 text-xs'}
                  disabled={dailyClaimed}
                  whileHover={dailyClaimed ? {} : { scale: 1.02 }}
                  whileTap={dailyClaimed ? {} : { scale: 0.98 }}
                >
                  {dailyClaimed ? 'CLAIMED' : 'CLAIM DAILY BONUS'}
                </motion.button>
              </div>

              {/* Ad Rewards */}
              <div className="rounded-xl p-4" style={{ background: 'var(--vanta-surface)', border: '1px solid var(--vanta-border)' }}>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold">Watch Ad for Chips</p>
                  <span className="text-xs font-mono" style={{ color: refillsRemaining > 0 ? 'var(--win)' : 'var(--loss)' }}>
                    {refillsRemaining}/10 left
                  </span>
                </div>
                <p className="text-xs mb-3" style={{ color: 'var(--text-tertiary)' }}>
                  Watch a short ad and receive 100 Gold Coins. Resets daily.
                </p>

                {/* Refill dots */}
                <div className="flex gap-1 mb-3">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <div
                      key={i}
                      className="w-2 h-2 rounded-full"
                      style={{ background: i < refillsRemaining ? 'var(--win)' : 'var(--vanta-border)' }}
                    />
                  ))}
                </div>

                <motion.button
                  onClick={handleWatch}
                  className={refillsRemaining > 0 ? 'btn-ghost w-full py-2 text-xs' : 'btn-ghost w-full py-2 text-xs opacity-30'}
                  disabled={refillsRemaining <= 0 || watching}
                  whileHover={refillsRemaining > 0 ? { scale: 1.02 } : {}}
                >
                  {watching ? (
                    <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.5, repeat: Infinity }}>
                      Watching...
                    </motion.span>
                  ) : refillsRemaining > 0 ? (
                    'WATCH AD (+100 GC)'
                  ) : (
                    'ALL USED TODAY'
                  )}
                </motion.button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
