'use client'

import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { useBlackjackStore } from '@/lib/blackjack-store'
import { CasinoChip, CHIP_CONFIGS } from './CasinoChip'
import type { SeatPosition } from './BotPlayers'

/**
 * BettingLayout -- Real casino table betting experience
 *
 * Shows at each active seat during betting phase:
 * - Main bet circle (large, center)
 * - Lucky Lucky circle (small, top-left "Mickey ear")
 * - Buster circle (small, top-right "Mickey ear")
 *
 * Chips dragged from tray LAND on circles and stay as visual stacks.
 * Tap a circle to add the selected chip value.
 * Tap a placed chip stack to remove last chip.
 */

interface BetCircleProps {
  label: string
  amount: number
  color: string
  size: number
  onClick: () => void
  onRightClick?: () => void
}

function BetCircle({ label, amount, color, size, onClick, onRightClick }: BetCircleProps) {
  // Show stacked chips based on amount
  const chipStack = getChipStack(amount)

  return (
    <button
      onClick={onClick}
      onContextMenu={(e) => { e.preventDefault(); onRightClick?.() }}
      className="relative rounded-full flex flex-col items-center justify-center"
      style={{
        width: size,
        height: size,
        background: amount > 0 ? `${color}25` : `${color}08`,
        border: `2px solid ${amount > 0 ? color : `${color}30`}`,
        boxShadow: amount > 0 ? `0 0 12px ${color}20, inset 0 0 8px ${color}08` : 'none',
        transition: 'all 0.2s',
      }}
    >
      {amount > 0 ? (
        <div className="flex flex-col items-center">
          {/* Mini chip stack visualization */}
          <div className="relative" style={{ height: Math.min(chipStack.length * 3 + 12, 24) }}>
            {chipStack.slice(0, 5).map((chip, i) => (
              <div key={i} className="absolute left-1/2 -translate-x-1/2 rounded-full"
                style={{
                  width: size * 0.4,
                  height: size * 0.4,
                  bottom: i * 3,
                  background: chip.color,
                  border: '1px solid rgba(255,255,255,0.2)',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
                }} />
            ))}
          </div>
          <span className="text-[8px] font-mono font-bold mt-0.5" style={{ color }}>{amount}</span>
        </div>
      ) : (
        <span className="text-[6px] uppercase tracking-wider font-bold" style={{ color: `${color}60` }}>
          {label}
        </span>
      )}
    </button>
  )
}

function getChipStack(amount: number): { value: number; color: string }[] {
  const chips: { value: number; color: string }[] = []
  const denominations = [
    { value: 5000, color: '#111' },
    { value: 1000, color: '#c9a84c' },
    { value: 500, color: '#8e44ad' },
    { value: 100, color: '#2980b9' },
    { value: 25, color: '#27ae60' },
    { value: 10, color: '#c0392b' },
  ]
  let remaining = amount
  for (const d of denominations) {
    while (remaining >= d.value) {
      chips.push(d)
      remaining -= d.value
    }
  }
  return chips
}

export function BettingLayout({ seatPositions }: { seatPositions: SeatPosition[] }) {
  const store = useBlackjackStore()
  const phase = store.phase
  const selectedChip = store.selectedChip
  const player = store.player
  const gameMode = store.gameMode

  if (phase !== 'betting') return null

  const currency = gameMode === 'sc' ? 'SC' : 'GC'
  const balance = gameMode === 'sc' ? player.sweepsCoins : player.chips

  return (
    <div className="absolute inset-0 z-12 pointer-events-none" style={{ zIndex: 12 }}>
      {seatPositions.map((pos, seatIdx) => {
        if (!pos.visible) return null
        const isActive = store.activeSeatIndices.includes(seatIdx)
        const botSeats = store.bots.filter(b => !b.sittingOut).map(b => b.seat)
        const isBot = botSeats.includes(seatIdx)

        if (isBot && !isActive) return null // don't show circles on bot seats

        return (
          <div key={seatIdx} className="absolute pointer-events-auto"
            style={{
              left: `${pos.x}px`,
              top: `${pos.y}px`,
              transform: 'translate(-50%, -50%)',
            }}>

            {!isActive ? (
              // Empty seat: tap to sit
              <button onClick={() => {
                store.toggleSeat(seatIdx)
              }}
                className="w-14 h-14 rounded-full flex items-center justify-center"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '2px dashed rgba(255,255,255,0.12)',
                }}>
                <span className="text-[7px] uppercase text-center leading-tight" style={{ color: 'rgba(255,255,255,0.25)' }}>
                  TAP{'\n'}TO SIT
                </span>
              </button>
            ) : (
              // Active seat: Mickey Mouse ear layout
              <div className="relative">
                {/* Lucky Lucky ear (top-left) -- Perfect Pairs */}
                <div className="absolute" style={{ top: -22, left: -16 }}>
                  <BetCircle
                    label="LUCKY"
                    amount={store.sideBets.perfectPairs.active ? store.sideBets.perfectPairs.bet : 0}
                    color="#2196f3"
                    size={28}
                    onClick={() => {
                      if (store.sideBets.perfectPairs.active) {
                        store.toggleSideBet('perfectPairs', 0)
                      } else {
                        store.toggleSideBet('perfectPairs', selectedChip || 25)
                      }
                    }}
                  />
                </div>

                {/* Lucky Ladies ear (top-right) -- Hand totals 20 */}
                <div className="absolute" style={{ top: -22, right: -16 }}>
                  <BetCircle
                    label="LADIES"
                    amount={store.sideBets.luckyLadies.active ? store.sideBets.luckyLadies.bet : 0}
                    color="#e91e63"
                    size={28}
                    onClick={() => {
                      if (store.sideBets.luckyLadies.active) {
                        store.toggleSideBet('luckyLadies', 0)
                      } else {
                        store.toggleSideBet('luckyLadies', selectedChip || 10)
                      }
                    }}
                  />
                </div>

                {/* Main bet circle (center, large) */}
                <BetCircle
                  label={`SEAT ${seatIdx + 1}`}
                  amount={store.betAmount}
                  color="#c9a84c"
                  size={56}
                  onClick={() => {
                    // Add selected chip to bet
                    const newBet = Math.min(store.betAmount + (selectedChip || 10), balance, store.config.maxBet)
                    store.setBet(newBet)
                  }}
                  onRightClick={() => {
                    // Remove last chip (undo)
                    const newBet = Math.max(0, store.betAmount - (selectedChip || 10))
                    store.setBet(newBet)
                  }}
                />

                {/* Seat label */}
                <p className="text-center text-[7px] mt-1 uppercase tracking-wider"
                  style={{ color: 'rgba(201,168,76,0.4)' }}>
                  Seat {seatIdx + 1}
                </p>
              </div>
            )}
          </div>
        )
      })}

      {/* Chip tray -- positioned above the DEAL bar */}
      <div className="absolute bottom-[80px] left-1/2 -translate-x-1/2 pointer-events-auto">
        <div className="flex gap-1.5 items-end p-2 rounded-xl"
          style={{ background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(201,168,76,0.2)' }}>
          {[10, 25, 100, 500, 1000, 5000].filter(v => v <= balance).map(v => (
            <CasinoChip key={v} value={v} selected={selectedChip === v}
              onClick={() => useBlackjackStore.setState({ selectedChip: v })}
              size={selectedChip === v ? 48 : 38} />
          ))}
        </div>
        <p className="text-center text-[8px] mt-1" style={{ color: 'rgba(255,255,255,0.3)' }}>
          Tap chip then tap a circle on the table
        </p>
      </div>
    </div>
  )
}
