'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useBlackjackStore } from '@/lib/blackjack-store'
import type { SeatPosition } from './BotPlayers'

/**
 * EmojiReactions -- Social emoji system
 *
 * Player can tap quick-reaction emojis that float up from their seat.
 * Bots randomly react to outcomes with their own emojis.
 * Creates the feeling of a live social table.
 */

const QUICK_EMOJIS = [
  { emoji: '\uD83D\uDC4D', label: 'Nice' },
  { emoji: '\uD83D\uDD25', label: 'Fire' },
  { emoji: '\uD83D\uDC4F', label: 'Clap' },
  { emoji: '\uD83D\uDE02', label: 'Laugh' },
  { emoji: '\uD83D\uDE2D', label: 'Cry' },
  { emoji: '\uD83E\uDD2F', label: 'Whoa' },
]

// Emojis bots use to react
const BOT_WIN_EMOJIS = ['\uD83D\uDC4D', '\uD83D\uDD25', '\uD83D\uDC4F', '\uD83D\uDE0E', '\uD83D\uDCAA']
const BOT_LOSS_EMOJIS = ['\uD83D\uDE2C', '\uD83D\uDE13', '\uD83D\uDCA8', '\uD83E\uDD37']
const BOT_BJ_EMOJIS = ['\uD83E\uDD2F', '\uD83D\uDE31', '\uD83D\uDD25', '\uD83C\uDF89', '\uD83D\uDC51']

interface FloatingEmoji {
  id: number
  emoji: string
  x: number
  y: number
  seatIndex: number
}

let emojiId = 0

export function EmojiReactions({ seatPositions }: { seatPositions: SeatPosition[] }) {
  const phase = useBlackjackStore(s => s.phase)
  const outcome = useBlackjackStore(s => s.outcome)
  const [floating, setFloating] = useState<FloatingEmoji[]>([])
  const [showBar, setShowBar] = useState(false)

  // Spawn a floating emoji at a seat position
  const spawnEmoji = useCallback((emoji: string, seatIndex: number) => {
    const pos = seatPositions[seatIndex]
    if (!pos?.visible) return
    const id = emojiId++
    setFloating(prev => [...prev, { id, emoji, x: pos.x, y: pos.y, seatIndex }])
    // Auto-remove after animation
    setTimeout(() => {
      setFloating(prev => prev.filter(e => e.id !== id))
    }, 2000)
  }, [seatPositions])

  // Player sends emoji (seat 2 = player)
  const handlePlayerEmoji = useCallback((emoji: string) => {
    spawnEmoji(emoji, 2)
    setShowBar(false)
  }, [spawnEmoji])

  // Bots react to player outcomes
  useEffect(() => {
    if (!outcome) return
    const botSeats = [0, 1, 3, 4]

    // Stagger bot reactions 500-1500ms after outcome
    botSeats.forEach((seat, i) => {
      // 40% chance each bot reacts
      if (Math.random() > 0.4) return
      const delay = 500 + Math.random() * 1000 + i * 200

      setTimeout(() => {
        let pool: string[]
        if (outcome === 'blackjack') pool = BOT_BJ_EMOJIS
        else if (outcome === 'win' || outcome === 'charlie') pool = BOT_WIN_EMOJIS
        else pool = BOT_LOSS_EMOJIS
        spawnEmoji(pool[Math.floor(Math.random() * pool.length)], seat)
      }, delay)
    })
  }, [outcome, spawnEmoji])

  return (
    <>
      {/* Floating emojis */}
      <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 25 }}>
        <AnimatePresence>
          {floating.map(f => (
            <motion.div
              key={f.id}
              initial={{ opacity: 1, x: f.x, y: f.y, scale: 0.5 }}
              animate={{ opacity: 0, y: f.y - 80, scale: 1.2 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 1.8, ease: 'easeOut' }}
              className="absolute text-2xl"
              style={{ transform: 'translate(-50%, -50%)' }}
            >
              {f.emoji}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Quick emoji bar (bottom-left, toggleable) */}
      <div className="absolute bottom-[100px] left-2 md:left-4 z-20">
        <AnimatePresence>
          {showBar && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.8, y: 10 }}
              className="flex gap-1.5 mb-2 glass rounded-xl p-2"
            >
              {QUICK_EMOJIS.map(e => (
                <motion.button
                  key={e.label}
                  onClick={() => handlePlayerEmoji(e.emoji)}
                  className="w-9 h-9 md:w-10 md:h-10 rounded-lg flex items-center justify-center text-lg md:text-xl hover:bg-white/10 transition-colors"
                  whileTap={{ scale: 0.85 }}
                >
                  {e.emoji}
                </motion.button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <motion.button
          onClick={() => setShowBar(!showBar)}
          className="w-10 h-10 rounded-full flex items-center justify-center text-lg glass"
          style={{
            border: showBar ? '1px solid rgba(201,168,76,0.4)' : '1px solid rgba(255,255,255,0.1)',
            boxShadow: showBar ? '0 0 12px rgba(201,168,76,0.2)' : 'none',
          }}
          whileTap={{ scale: 0.9 }}
        >
          {'\uD83D\uDE00'}
        </motion.button>
      </div>
    </>
  )
}
