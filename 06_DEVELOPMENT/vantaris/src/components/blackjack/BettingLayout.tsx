'use client'

import { motion } from 'framer-motion'
import { useBlackjackStore } from '@/lib/blackjack-store'
import type { SeatPosition } from './BotPlayers'

/**
 * BettingLayout -- Zynga-style tap-to-bet
 *
 * How it works (like Zynga Poker / real casino apps):
 * 1. Tap a chip at the bottom to SELECT it (highlights)
 * 2. Tap the MAIN BET circle on your seat to place that chip
 * 3. Tap the LUCKY LUCKY circle (left ear) to place a side bet
 * 4. Tap the LUCKY LADIES circle (right ear) to place a side bet
 * 5. Tap an EMPTY seat to sit down and bet there
 *
 * No dragging. Just tap-tap. Simple.
 */

const CHIP_VALUES = [10, 25, 100, 500, 1000, 5000]

const CHIP_COLORS: Record<number, string> = {
  10: '#c0392b', 25: '#27ae60', 100: '#2980b9',
  500: '#8e44ad', 1000: '#c9a84c', 5000: '#111',
}

export function BettingLayout({ seatPositions }: { seatPositions: SeatPosition[] }) {
  const store = useBlackjackStore()
  const { phase, selectedChip, player, gameMode, sideBets, activeSeatIndices, bots, betAmount, config } = store

  if (phase !== 'betting') return null

  const balance = gameMode === 'sc' ? player.sweepsCoins : player.chips
  const currency = gameMode === 'sc' ? 'SC' : 'GC'

  return (
    <div className="absolute inset-0" style={{ zIndex: 12 }}>

      {/* === SEAT BETTING CIRCLES ON THE TABLE === */}
      {seatPositions.map((pos, seatIdx) => {
        if (!pos.visible) return null
        const botSeats = bots.filter(b => !b.sittingOut).map(b => b.seat)
        const isBot = botSeats.includes(seatIdx)
        const isActive = activeSeatIndices.includes(seatIdx)

        if (isBot && !isActive) return null

        return (
          <div key={seatIdx} className="absolute"
            style={{ left: `${pos.x}px`, top: `${pos.y}px`, transform: 'translate(-50%, -50%)' }}>

            {!isActive ? (
              /* Empty seat -- tap to sit */
              <motion.button
                onClick={() => store.toggleSeat(seatIdx)}
                className="w-16 h-16 rounded-full flex items-center justify-center"
                style={{ border: '2px dashed rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.02)' }}
                whileTap={{ scale: 0.9 }}
              >
                <span className="text-[8px] uppercase tracking-wider text-center" style={{ color: 'rgba(255,255,255,0.3)' }}>
                  TAP TO{'\n'}SIT
                </span>
              </motion.button>
            ) : (
              /* Active seat -- betting circles */
              <div className="relative">
                {/* Lucky Lucky side bet (top-left ear) */}
                <motion.button
                  onClick={() => {
                    if (sideBets.perfectPairs.active) {
                      store.toggleSideBet('perfectPairs', 0)
                    } else {
                      store.toggleSideBet('perfectPairs', selectedChip || 25)
                    }
                  }}
                  className="absolute rounded-full flex items-center justify-center"
                  style={{
                    width: 32, height: 32, top: -24, left: -12,
                    background: sideBets.perfectPairs.active ? 'rgba(33,150,243,0.3)' : 'rgba(33,150,243,0.06)',
                    border: `2px solid ${sideBets.perfectPairs.active ? '#2196f3' : 'rgba(33,150,243,0.2)'}`,
                    boxShadow: sideBets.perfectPairs.active ? '0 0 10px rgba(33,150,243,0.3)' : 'none',
                  }}
                  whileTap={{ scale: 0.85 }}
                >
                  {sideBets.perfectPairs.active ? (
                    <span className="text-[7px] font-mono font-bold" style={{ color: '#2196f3' }}>{sideBets.perfectPairs.bet}</span>
                  ) : (
                    <span className="text-[6px] font-bold" style={{ color: 'rgba(33,150,243,0.5)' }}>LL</span>
                  )}
                </motion.button>

                {/* Lucky Ladies side bet (top-right ear) */}
                <motion.button
                  onClick={() => {
                    if (sideBets.luckyLadies.active) {
                      store.toggleSideBet('luckyLadies', 0)
                    } else {
                      store.toggleSideBet('luckyLadies', selectedChip || 10)
                    }
                  }}
                  className="absolute rounded-full flex items-center justify-center"
                  style={{
                    width: 32, height: 32, top: -24, right: -12,
                    background: sideBets.luckyLadies.active ? 'rgba(233,30,99,0.3)' : 'rgba(233,30,99,0.06)',
                    border: `2px solid ${sideBets.luckyLadies.active ? '#e91e63' : 'rgba(233,30,99,0.2)'}`,
                    boxShadow: sideBets.luckyLadies.active ? '0 0 10px rgba(233,30,99,0.3)' : 'none',
                  }}
                  whileTap={{ scale: 0.85 }}
                >
                  {sideBets.luckyLadies.active ? (
                    <span className="text-[7px] font-mono font-bold" style={{ color: '#e91e63' }}>{sideBets.luckyLadies.bet}</span>
                  ) : (
                    <span className="text-[6px] font-bold" style={{ color: 'rgba(233,30,99,0.5)' }}>20</span>
                  )}
                </motion.button>

                {/* MAIN BET circle (center) */}
                <motion.button
                  onClick={() => {
                    const chip = selectedChip || 10
                    const newBet = Math.min(betAmount + chip, balance, config.maxBet)
                    store.setBet(newBet)
                  }}
                  className="w-16 h-16 rounded-full flex flex-col items-center justify-center relative"
                  style={{
                    background: betAmount > 0 ? 'rgba(201,168,76,0.2)' : 'rgba(201,168,76,0.05)',
                    border: `2px solid ${betAmount > 0 ? '#c9a84c' : 'rgba(201,168,76,0.25)'}`,
                    boxShadow: betAmount > 0 ? '0 0 15px rgba(201,168,76,0.2)' : 'none',
                  }}
                  whileTap={{ scale: 0.9 }}
                >
                  {betAmount > 0 ? (
                    <>
                      {/* Stacked chip visual */}
                      <div className="w-8 h-8 rounded-full mb-0.5" style={{
                        background: CHIP_COLORS[selectedChip] || '#c9a84c',
                        border: '2px solid rgba(255,255,255,0.2)',
                        boxShadow: '0 2px 6px rgba(0,0,0,0.5)',
                      }} />
                      <span className="text-[8px] font-mono font-bold" style={{ color: '#c9a84c' }}>{betAmount}</span>
                    </>
                  ) : (
                    <span className="text-[7px] uppercase tracking-wider" style={{ color: 'rgba(201,168,76,0.5)' }}>BET</span>
                  )}
                </motion.button>

                <p className="text-center text-[7px] mt-1" style={{ color: 'rgba(201,168,76,0.3)' }}>Seat {seatIdx + 1}</p>
              </div>
            )}
          </div>
        )
      })}

      {/* === CHIP SELECTOR (bottom of game area) === */}
      <div className="absolute bottom-[75px] left-1/2 -translate-x-1/2">
        <div className="flex gap-2 items-end px-3 py-2 rounded-xl"
          style={{ background: 'rgba(0,0,0,0.75)', border: '1px solid rgba(201,168,76,0.15)' }}>
          {CHIP_VALUES.filter(v => v <= balance).map(v => (
            <motion.button key={v}
              onClick={() => useBlackjackStore.setState({ selectedChip: v })}
              className="rounded-full flex items-center justify-center text-[9px] font-bold"
              style={{
                width: selectedChip === v ? 46 : 38,
                height: selectedChip === v ? 46 : 38,
                background: CHIP_COLORS[v],
                border: selectedChip === v ? '3px solid #fff' : '2px solid rgba(255,255,255,0.15)',
                color: v === 5000 ? '#c9a84c' : '#fff',
                boxShadow: selectedChip === v ? `0 0 12px ${CHIP_COLORS[v]}80` : '0 2px 6px rgba(0,0,0,0.5)',
                transition: 'all 0.15s',
              }}
              whileTap={{ scale: 0.85 }}
            >
              {v >= 1000 ? `${v / 1000}K` : v}
            </motion.button>
          ))}
        </div>
        <p className="text-center text-[7px] mt-1" style={{ color: 'rgba(255,255,255,0.2)' }}>
          Tap chip, then tap a circle
        </p>
      </div>
    </div>
  )
}
