'use client'

import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useBlackjackStore } from '@/lib/blackjack-store'
import type { SeatPosition } from './BotPlayers'

/**
 * SocialBar -- Player social interactions AT the table
 *
 * Positioned near the player's seat (not fixed corner).
 * Features:
 * - Quick emoji reactions (float from player seat)
 * - Gift/troll menu (tap another player to send)
 * - Flying animations between seats
 * - Costs small GC for premium actions
 */

const QUICK_EMOJIS = [
  { emoji: '\uD83D\uDC4D', label: 'Nice' },
  { emoji: '\uD83D\uDD25', label: 'Fire' },
  { emoji: '\uD83D\uDC4F', label: 'GG' },
  { emoji: '\uD83D\uDE02', label: 'LOL' },
  { emoji: '\uD83D\uDE0E', label: 'Cool' },
  { emoji: '\uD83D\uDCAA', label: 'Strong' },
]

const GIFTS = [
  { id: 'drink', emoji: '\uD83C\uDF7A', label: 'Buy a Drink', cost: 10, troll: false },
  { id: 'champagne', emoji: '\uD83C\uDF7E', label: 'Champagne', cost: 50, troll: false },
  { id: 'chips', emoji: '\uD83E\uDE99', label: 'Send Chips', cost: 100, troll: false },
  { id: 'crown', emoji: '\uD83D\uDC51', label: 'Crown', cost: 200, troll: false },
  { id: 'tomato', emoji: '\uD83C\uDF45', label: 'Throw Tomato', cost: 5, troll: true },
  { id: 'ice', emoji: '\uD83E\uDDCA', label: 'Ice Cold', cost: 10, troll: true },
  { id: 'clown', emoji: '\uD83E\uDD21', label: 'Clown', cost: 15, troll: true },
  { id: 'skull', emoji: '\uD83D\uDC80', label: 'RIP', cost: 5, troll: true },
]

interface FlyingItem {
  id: number
  emoji: string
  fromX: number
  fromY: number
  toX: number
  toY: number
}

let flyId = 0

export function SocialBar({ seatPositions }: { seatPositions: SeatPosition[] }) {
  const bots = useBlackjackStore(s => s.bots)
  const player = useBlackjackStore(s => s.player)
  const [showEmojis, setShowEmojis] = useState(false)
  const [showGifts, setShowGifts] = useState(false)
  const [targetSeat, setTargetSeat] = useState<number | null>(null)
  const [flyingItems, setFlyingItems] = useState<FlyingItem[]>([])

  const playerPos = seatPositions[2] // center seat

  // Send a flying item from player to target
  const sendFlying = useCallback((emoji: string, toSeatIdx: number) => {
    const from = seatPositions[2]
    const to = seatPositions[toSeatIdx]
    if (!from?.visible || !to?.visible) return

    const id = flyId++
    setFlyingItems(prev => [...prev, { id, emoji, fromX: from.x, fromY: from.y, toX: to.x, toY: to.y }])
    setTimeout(() => setFlyingItems(prev => prev.filter(f => f.id !== id)), 1500)
  }, [seatPositions])

  // Send quick emoji (floats up from player seat)
  const sendEmoji = useCallback((emoji: string) => {
    const from = seatPositions[2]
    if (!from?.visible) return
    const id = flyId++
    setFlyingItems(prev => [...prev, { id, emoji, fromX: from.x, fromY: from.y, toX: from.x, toY: from.y - 80 }])
    setTimeout(() => setFlyingItems(prev => prev.filter(f => f.id !== id)), 1500)
    setShowEmojis(false)
  }, [seatPositions])

  // Send gift to a bot/player
  const sendGift = useCallback((gift: typeof GIFTS[0], toSeatIdx: number) => {
    if (player.chips < gift.cost) return
    useBlackjackStore.setState({ player: { ...player, chips: player.chips - gift.cost } })
    sendFlying(gift.emoji, toSeatIdx)
    setShowGifts(false)
    setTargetSeat(null)
  }, [player, sendFlying])

  if (!playerPos?.visible) return null

  return (
    <>
      {/* Flying items (emojis/gifts traveling between seats) */}
      <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 30 }}>
        <AnimatePresence>
          {flyingItems.map(f => (
            <motion.div key={f.id}
              initial={{ x: f.fromX, y: f.fromY, scale: 0.5, opacity: 1 }}
              animate={{ x: f.toX, y: f.toY, scale: 1.3, opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
              className="absolute text-3xl"
              style={{ transform: 'translate(-50%, -50%)' }}
            >
              {f.emoji}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Social action bar near player seat */}
      <div className="absolute" style={{
        left: `${playerPos.x}px`,
        top: `${playerPos.y + 90}px`,
        transform: 'translate(-50%, 0)',
        zIndex: 20,
      }}>
        <div className="flex gap-1.5 items-center">
          {/* Quick emoji button */}
          <motion.button
            onClick={() => { setShowEmojis(!showEmojis); setShowGifts(false) }}
            className="w-9 h-9 rounded-full flex items-center justify-center"
            style={{
              background: showEmojis ? 'rgba(201,168,76,0.2)' : 'rgba(0,0,0,0.6)',
              border: `1px solid ${showEmojis ? 'rgba(201,168,76,0.4)' : 'rgba(255,255,255,0.1)'}`,
            }}
            whileTap={{ scale: 0.85 }}
          >
            <span className="text-base">{'\uD83D\uDE00'}</span>
          </motion.button>

          {/* Gift button */}
          <motion.button
            onClick={() => { setShowGifts(!showGifts); setShowEmojis(false) }}
            className="w-9 h-9 rounded-full flex items-center justify-center"
            style={{
              background: showGifts ? 'rgba(201,168,76,0.2)' : 'rgba(0,0,0,0.6)',
              border: `1px solid ${showGifts ? 'rgba(201,168,76,0.4)' : 'rgba(255,255,255,0.1)'}`,
            }}
            whileTap={{ scale: 0.85 }}
          >
            <span className="text-base">{'\uD83C\uDF81'}</span>
          </motion.button>

          {/* Chat button */}
          <motion.button
            onClick={() => {
              // Open the DealerChat panel
              const chatBtn = document.querySelector('[data-chat-toggle]') as HTMLButtonElement
              chatBtn?.click()
            }}
            className="w-9 h-9 rounded-full flex items-center justify-center"
            style={{ background: 'rgba(0,0,0,0.6)', border: '1px solid rgba(255,255,255,0.1)' }}
            whileTap={{ scale: 0.85 }}
          >
            <span className="text-base">{'\uD83D\uDCAC'}</span>
          </motion.button>
        </div>

        {/* Quick emoji picker */}
        <AnimatePresence>
          {showEmojis && (
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.9 }}
              className="flex gap-1 mt-2 px-2 py-1.5 rounded-xl"
              style={{ background: 'rgba(0,0,0,0.85)', border: '1px solid rgba(255,255,255,0.1)' }}
            >
              {QUICK_EMOJIS.map(e => (
                <motion.button key={e.label}
                  onClick={() => sendEmoji(e.emoji)}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-lg hover:bg-white/10"
                  whileTap={{ scale: 0.8 }}
                >
                  {e.emoji}
                </motion.button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Gift/troll picker */}
        <AnimatePresence>
          {showGifts && (
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.9 }}
              className="mt-2 p-2 rounded-xl w-[220px]"
              style={{ background: 'rgba(0,0,0,0.9)', border: '1px solid rgba(201,168,76,0.2)' }}
            >
              {targetSeat === null ? (
                <>
                  <p className="text-[8px] uppercase tracking-wider mb-2 text-center" style={{ color: 'var(--text-tertiary)' }}>
                    TAP A PLAYER TO SEND
                  </p>
                  <div className="flex gap-2 justify-center flex-wrap">
                    {bots.filter(b => !b.sittingOut).map(bot => (
                      <motion.button key={bot.seat}
                        onClick={() => setTargetSeat(bot.seat)}
                        className="px-2 py-1 rounded-lg text-[9px]"
                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: '#aef' }}
                        whileTap={{ scale: 0.9 }}
                      >
                        {bot.name}
                      </motion.button>
                    ))}
                  </div>
                </>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>
                      Send to {bots.find(b => b.seat === targetSeat)?.name}
                    </p>
                    <button onClick={() => setTargetSeat(null)} className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                      {'\u2190'} Back
                    </button>
                  </div>
                  <div className="grid grid-cols-4 gap-1.5">
                    {GIFTS.map(g => (
                      <motion.button key={g.id}
                        onClick={() => sendGift(g, targetSeat)}
                        className="flex flex-col items-center p-1.5 rounded-lg"
                        style={{
                          background: g.troll ? 'rgba(255,45,85,0.08)' : 'rgba(201,168,76,0.08)',
                          border: `1px solid ${g.troll ? 'rgba(255,45,85,0.15)' : 'rgba(201,168,76,0.15)'}`,
                          opacity: player.chips >= g.cost ? 1 : 0.3,
                        }}
                        whileTap={{ scale: 0.85 }}
                        disabled={player.chips < g.cost}
                      >
                        <span className="text-lg">{g.emoji}</span>
                        <span className="text-[6px]" style={{ color: 'var(--text-tertiary)' }}>{g.cost}</span>
                      </motion.button>
                    ))}
                  </div>
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  )
}
