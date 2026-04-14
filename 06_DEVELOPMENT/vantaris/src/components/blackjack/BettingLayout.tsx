'use client'

import { useState, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useBlackjackStore } from '@/lib/blackjack-store'
import { CasinoChip } from './CasinoChip'
import type { SeatPosition } from './BotPlayers'

/**
 * BettingLayout -- Drag & Drop Casino Chips
 *
 * REAL casino experience:
 * - Luxury SVG chips in the tray
 * - DRAG a chip from the tray with your finger/mouse
 * - A ghost chip follows your finger
 * - DROP it on a betting circle (main bet, Lucky Lucky, Lucky Ladies)
 * - Chip LANDS on the circle and stays (visual stack grows)
 * - Tap also works as fallback (select chip, tap circle)
 */

const CHIP_COLORS: Record<number, string> = {
  10: '#c0392b', 25: '#27ae60', 100: '#2980b9',
  500: '#8e44ad', 1000: '#c9a84c', 5000: '#111',
}

// Drop zone IDs for hit detection
const ZONE_MAIN = 'main'
const ZONE_LL = 'll'
const ZONE_LADIES = 'ladies'

export function BettingLayout({ seatPositions }: { seatPositions: SeatPosition[] }) {
  const store = useBlackjackStore()
  const { phase, selectedChip, player, gameMode, sideBets, activeSeatIndices, bots, betAmount, config } = store

  // Drag state
  const [dragging, setDragging] = useState(false)
  const [dragValue, setDragValue] = useState(0)
  const [dragPos, setDragPos] = useState({ x: 0, y: 0 })
  const dragRef = useRef(false)

  const balance = gameMode === 'sc' ? player.sweepsCoins : player.chips

  if (phase !== 'betting') return null

  // Start dragging a chip
  const handleDragStart = (value: number, e: React.PointerEvent) => {
    e.preventDefault()
    setDragging(true)
    setDragValue(value)
    setDragPos({ x: e.clientX, y: e.clientY })
    dragRef.current = true

    const handleMove = (ev: PointerEvent) => {
      if (!dragRef.current) return
      setDragPos({ x: ev.clientX, y: ev.clientY })
    }

    const handleUp = (ev: PointerEvent) => {
      dragRef.current = false
      setDragging(false)
      document.removeEventListener('pointermove', handleMove)
      document.removeEventListener('pointerup', handleUp)

      // Check what we dropped on
      const dropX = ev.clientX
      const dropY = ev.clientY

      // Find all drop zones and check hit
      const zones = document.querySelectorAll('[data-drop-zone]')
      for (const zone of zones) {
        const rect = zone.getBoundingClientRect()
        if (dropX >= rect.left && dropX <= rect.right && dropY >= rect.top && dropY <= rect.bottom) {
          const type = zone.getAttribute('data-drop-zone')
          const seatIdx = parseInt(zone.getAttribute('data-seat') || '2')

          if (type === ZONE_MAIN) {
            // Activate seat if not active
            if (!activeSeatIndices.includes(seatIdx)) {
              store.toggleSeat(seatIdx)
            }
            const newBet = Math.min(betAmount + value, balance, config.maxBet)
            store.setBet(newBet)
            return
          }
          if (type === ZONE_LL) {
            if (!sideBets.perfectPairs.active) {
              store.toggleSideBet('perfectPairs', value)
            } else {
              // Add more to existing side bet
              store.toggleSideBet('perfectPairs', 0)
              store.toggleSideBet('perfectPairs', sideBets.perfectPairs.bet + value)
            }
            return
          }
          if (type === ZONE_LADIES) {
            if (!sideBets.luckyLadies.active) {
              store.toggleSideBet('luckyLadies', value)
            } else {
              store.toggleSideBet('luckyLadies', 0)
              store.toggleSideBet('luckyLadies', sideBets.luckyLadies.bet + value)
            }
            return
          }
          if (type === 'progressive') {
            if (!sideBets.progressive.active) {
              store.toggleSideBet('progressive', value)
            } else {
              store.toggleSideBet('progressive', 0)
              store.toggleSideBet('progressive', sideBets.progressive.bet + value)
            }
            return
          }
        }
      }
    }

    document.addEventListener('pointermove', handleMove)
    document.addEventListener('pointerup', handleUp)
  }

  return (
    <div className="absolute inset-0" style={{ zIndex: 12 }}>

      {/* === GHOST CHIP (follows finger while dragging) === */}
      {dragging && (
        <div className="fixed pointer-events-none" style={{
          left: dragPos.x - 24, top: dragPos.y - 24,
          zIndex: 100, opacity: 0.9,
          filter: `drop-shadow(0 0 15px ${CHIP_COLORS[dragValue]}80)`,
        }}>
          <CasinoChip value={dragValue} selected={true} onClick={() => {}} size={48} />
        </div>
      )}

      {/* === SEAT CIRCLES ON THE TABLE === */}
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
              /* Empty seat */
              <motion.button
                data-drop-zone={ZONE_MAIN} data-seat={seatIdx}
                onClick={() => store.toggleSeat(seatIdx)}
                className="w-16 h-16 rounded-full flex items-center justify-center"
                style={{
                  border: `2px dashed ${dragging ? 'rgba(201,168,76,0.5)' : 'rgba(255,255,255,0.12)'}`,
                  background: dragging ? 'rgba(201,168,76,0.08)' : 'rgba(255,255,255,0.02)',
                }}
                whileTap={{ scale: 0.9 }}
              >
                <span className="text-[7px] uppercase tracking-wider text-center" style={{ color: 'rgba(255,255,255,0.3)' }}>
                  {dragging ? 'DROP\nHERE' : 'TAP TO\nSIT'}
                </span>
              </motion.button>
            ) : (
              /* Active seat: (LL) (Progressive) (BB) layout */
              <div className="relative">
                {/* Row of 3 side bet circles above main bet */}
                <div className="absolute flex items-center gap-1" style={{ top: -30, left: '50%', transform: 'translateX(-50%)', transition: 'all 0.2s' }}>

                  {/* LL - Lucky Lucky (left) */}
                  <div data-drop-zone={ZONE_LL} data-seat={seatIdx}>
                    <motion.button
                      onClick={() => {
                        if (sideBets.perfectPairs.active) store.toggleSideBet('perfectPairs', 0)
                        else store.toggleSideBet('perfectPairs', selectedChip || 25)
                      }}
                      className="rounded-full flex flex-col items-center justify-center"
                      style={{
                        width: dragging ? 38 : 30, height: dragging ? 38 : 30,
                        transition: 'all 0.2s',
                        background: sideBets.perfectPairs.active ? 'rgba(33,150,243,0.35)' : 'rgba(33,150,243,0.06)',
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
                  </div>

                  {/* PROGRESSIVE (center, neon) */}
                  <div data-drop-zone="progressive" data-seat={seatIdx}>
                    <motion.button
                      onClick={() => {
                        if (sideBets.progressive.active) store.toggleSideBet('progressive', 0)
                        else store.toggleSideBet('progressive', selectedChip || 5)
                      }}
                      className="rounded-full flex flex-col items-center justify-center"
                      style={{
                        width: dragging ? 42 : 34, height: dragging ? 42 : 34,
                        transition: 'all 0.2s',
                        background: sideBets.progressive.active
                          ? 'rgba(201,168,76,0.3)'
                          : 'rgba(201,168,76,0.04)',
                        border: `2px solid ${sideBets.progressive.active ? '#c9a84c' : 'rgba(201,168,76,0.15)'}`,
                        boxShadow: sideBets.progressive.active
                          ? '0 0 15px rgba(201,168,76,0.4), 0 0 30px rgba(201,168,76,0.15)'
                          : dragging ? '0 0 8px rgba(201,168,76,0.2)' : 'none',
                      }}
                      whileTap={{ scale: 0.85 }}
                      animate={sideBets.progressive.active ? {
                        boxShadow: ['0 0 15px rgba(201,168,76,0.4)', '0 0 25px rgba(201,168,76,0.6)', '0 0 15px rgba(201,168,76,0.4)'],
                      } : {}}
                      transition={sideBets.progressive.active ? { duration: 1.5, repeat: Infinity } : {}}
                    >
                      {sideBets.progressive.active ? (
                        <span className="text-[7px] font-mono font-bold" style={{ color: '#c9a84c' }}>{sideBets.progressive.bet}</span>
                      ) : (
                        <span className="text-[5px] font-bold" style={{ color: 'rgba(201,168,76,0.5)' }}>777</span>
                      )}
                    </motion.button>
                  </div>

                  {/* BB - Bad Buster (right) */}
                  <div data-drop-zone={ZONE_LADIES} data-seat={seatIdx}>
                    <motion.button
                      onClick={() => {
                        if (sideBets.luckyLadies.active) store.toggleSideBet('luckyLadies', 0)
                        else store.toggleSideBet('luckyLadies', selectedChip || 10)
                      }}
                      className="rounded-full flex flex-col items-center justify-center"
                      style={{
                        width: dragging ? 38 : 30, height: dragging ? 38 : 30,
                        transition: 'all 0.2s',
                        background: sideBets.luckyLadies.active ? 'rgba(244,67,54,0.35)' : 'rgba(244,67,54,0.06)',
                        border: `2px solid ${sideBets.luckyLadies.active ? '#f44336' : 'rgba(244,67,54,0.2)'}`,
                        boxShadow: sideBets.luckyLadies.active ? '0 0 10px rgba(244,67,54,0.3)' : 'none',
                      }}
                      whileTap={{ scale: 0.85 }}
                    >
                      {sideBets.luckyLadies.active ? (
                        <span className="text-[7px] font-mono font-bold" style={{ color: '#f44336' }}>{sideBets.luckyLadies.bet}</span>
                      ) : (
                        <span className="text-[6px] font-bold" style={{ color: 'rgba(244,67,54,0.5)' }}>BB</span>
                      )}
                    </motion.button>
                  </div>
                </div>

                {/* MAIN BET circle */}
                <motion.button
                  data-drop-zone={ZONE_MAIN} data-seat={seatIdx}
                  onClick={() => {
                    const newBet = Math.min(betAmount + (selectedChip || 10), balance, config.maxBet)
                    store.setBet(newBet)
                  }}
                  className="w-16 h-16 rounded-full flex flex-col items-center justify-center"
                  style={{
                    background: betAmount > 0 ? 'rgba(201,168,76,0.2)' : dragging ? 'rgba(201,168,76,0.12)' : 'rgba(201,168,76,0.04)',
                    border: `2px solid ${betAmount > 0 ? '#c9a84c' : dragging ? 'rgba(201,168,76,0.5)' : 'rgba(201,168,76,0.2)'}`,
                    boxShadow: betAmount > 0 ? '0 0 15px rgba(201,168,76,0.2)' : dragging ? '0 0 8px rgba(201,168,76,0.1)' : 'none',
                  }}
                  whileTap={{ scale: 0.9 }}
                >
                  {betAmount > 0 ? (
                    <>
                      <div className="w-8 h-8 rounded-full" style={{
                        background: CHIP_COLORS[selectedChip] || '#c9a84c',
                        border: '2px solid rgba(255,255,255,0.2)',
                        boxShadow: '0 2px 6px rgba(0,0,0,0.5)',
                      }} />
                      <span className="text-[8px] font-mono font-bold" style={{ color: '#c9a84c' }}>{betAmount}</span>
                    </>
                  ) : (
                    <span className="text-[7px] uppercase tracking-wider" style={{ color: 'rgba(201,168,76,0.4)' }}>
                      {dragging ? 'DROP' : 'BET'}
                    </span>
                  )}
                </motion.button>

                <p className="text-center text-[7px] mt-1" style={{ color: 'rgba(201,168,76,0.3)' }}>
                  Seat {seatIdx + 1}
                </p>
              </div>
            )}
          </div>
        )
      })}

      {/* === CHIP TRAY (luxury SVG chips, draggable) -- at very bottom of game area === */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 pb-1">
        <div className="flex gap-2 items-end px-3 py-2 rounded-xl"
          style={{ background: 'rgba(0,0,0,0.8)', border: '1px solid rgba(201,168,76,0.2)' }}>
          {[10, 25, 100, 500, 1000, 5000].filter(v => v <= balance).map(v => (
            <div key={v}
              onPointerDown={(e) => handleDragStart(v, e)}
              style={{ touchAction: 'none', cursor: 'grab' }}
            >
              <CasinoChip value={v} selected={selectedChip === v}
                onClick={() => useBlackjackStore.setState({ selectedChip: v })}
                size={selectedChip === v ? 50 : 40} />
            </div>
          ))}
        </div>
        <p className="text-center text-[7px] mt-1" style={{ color: 'rgba(255,255,255,0.25)' }}>
          Drag chip to circle, or tap chip then tap circle
        </p>
      </div>
    </div>
  )
}
