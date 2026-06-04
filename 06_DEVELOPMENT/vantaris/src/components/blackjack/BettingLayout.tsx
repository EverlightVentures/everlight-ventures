'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
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

  // Physical chips placed on the main bet -- one entry per chip dropped/tapped,
  // so the visible pile grows by a real chip with every drag. BettingLayout
  // unmounts when betting ends, so this clears itself each new round; we also
  // wipe it the moment the bet is cleared to zero.
  const [chipStack, setChipStack] = useState<number[]>([])
  useEffect(() => { if (betAmount === 0) setChipStack([]) }, [betAmount])
  // Set true the moment a placed-chip MOVE gesture promotes, so the click-to-add
  // that the browser fires after the drag gets swallowed instead of adding a chip.
  const movePromotedRef = useRef(0)

  const balance = gameMode === 'sc' ? player.sweepsCoins : player.chips

  if (phase !== 'betting') return null

  // Map a drop-zone id to its side-bet key (null = main bet, not a side bet).
  const sideBetName = (zone: string): 'perfectPairs' | 'luckyLadies' | 'progressive' | null =>
    zone === ZONE_LL ? 'perfectPairs' : zone === ZONE_LADIES ? 'luckyLadies' : zone === 'progressive' ? 'progressive' : null

  // Take one chip of `value` off a spot (the source half of a MOVE). Frees balance
  // first so the matching add on the target passes the store's balance check.
  const removeFromSpot = (zone: string, value: number) => {
    const S = useBlackjackStore.getState()
    if (zone === ZONE_MAIN) {
      S.setBet(Math.max(0, S.betAmount - value))
      setChipStack(s => { const i = s.lastIndexOf(value); if (i < 0) return s.slice(0, -1); const c = [...s]; c.splice(i, 1); return c })
    } else {
      const name = sideBetName(zone); if (!name) return
      const cur = S.sideBets[name].bet
      S.toggleSideBet(name, 0)
      if (cur - value > 0) S.toggleSideBet(name, cur - value)
    }
  }

  // Add `value` to a spot (a tray drop OR the landing half of a move).
  const addToSpot = (zone: string, seatIdx: number, value: number) => {
    const S = useBlackjackStore.getState()
    if (zone === ZONE_MAIN) {
      if (!S.activeSeatIndices.includes(seatIdx)) S.toggleSeat(seatIdx)
      const nb = Math.min(S.betAmount + value, balance, S.config.maxBet)
      if (nb > S.betAmount) setChipStack(s => [...s, value])
      S.setBet(nb)
    } else {
      const name = sideBetName(zone); if (!name) return
      const sb = S.sideBets[name]
      if (!sb.active) S.toggleSideBet(name, value)
      else { S.toggleSideBet(name, 0); S.toggleSideBet(name, sb.bet + value) }
    }
  }

  // Start dragging a chip -- from the tray (source null) OR moving a placed chip (source set).
  const handleDragStart = (value: number, e: { preventDefault?: () => void; clientX: number; clientY: number }, source: { zone: string; seat: number } | null = null) => {
    e.preventDefault?.()
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

      const dropX = ev.clientX, dropY = ev.clientY
      const zones = document.querySelectorAll('[data-drop-zone]')
      let hit: Element | null = null
      let nearest: { el: Element; d: number } | null = null
      for (const zone of zones) {
        const rect = zone.getBoundingClientRect()
        if (dropX >= rect.left && dropX <= rect.right && dropY >= rect.top && dropY <= rect.bottom) { hit = zone; break }
        const cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2
        const d = Math.hypot(dropX - cx, dropY - cy)
        if (!nearest || d < nearest.d) nearest = { el: zone, d }
      }
      // For a MOVE, accept the nearest spot within reach so the small side circles
      // are easy to land on. A tray drop stays strict (must land inside a circle).
      const target = hit || (source && nearest && nearest.d < 70 ? nearest.el : null)
      if (target) {
        const type = target.getAttribute('data-drop-zone') || ''
        const seatIdx = parseInt(target.getAttribute('data-seat') || '2')
        if (source && source.zone === type) return // back on its own spot -- no change
        // A MOVE must never light up a NEW seat (that would force an extra hand) -- snap back.
        if (source && type === ZONE_MAIN && !useBlackjackStore.getState().activeSeatIndices.includes(seatIdx)) return
        if (source) removeFromSpot(source.zone, value) // pull off source first
        addToSpot(type, seatIdx, value)
      }
      // Dropped nowhere reachable: a move snaps the chip back; a tray drag is a no-op.
    }

    document.addEventListener('pointermove', handleMove)
    document.addEventListener('pointerup', handleUp)
  }

  // Pick a chip already sitting on a spot and move it. An 8px threshold tells a
  // real drag from a tap (taps still fall through to the spot's add-on-click).
  const handleSpotPointerDown = (zone: string, seatIdx: number, e: React.PointerEvent) => {
    const S = useBlackjackStore.getState()
    let value = 0
    if (zone === ZONE_MAIN) value = chipStack.length ? chipStack[chipStack.length - 1] : (breakdownChips(S.betAmount)[0] || 0)
    else { const name = sideBetName(zone); if (name) value = breakdownChips(S.sideBets[name].bet)[0] || 0 }
    if (!value) return // empty spot -- nothing to pick up
    const startX = e.clientX, startY = e.clientY
    let promoted = false
    const onMove = (ev: PointerEvent) => {
      if (promoted) return
      if (Math.hypot(ev.clientX - startX, ev.clientY - startY) > 8) {
        promoted = true
        movePromotedRef.current = Date.now()
        document.removeEventListener('pointermove', onMove)
        document.removeEventListener('pointerup', onUp)
        handleDragStart(value, { clientX: ev.clientX, clientY: ev.clientY }, { zone, seat: seatIdx })
      }
    }
    const onUp = () => {
      document.removeEventListener('pointermove', onMove)
      document.removeEventListener('pointerup', onUp)
    }
    document.addEventListener('pointermove', onMove)
    document.addEventListener('pointerup', onUp)
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
                      onPointerDown={(e) => handleSpotPointerDown(ZONE_LL, seatIdx, e)}
                      onClick={() => {
                        if (movePromotedRef.current && Date.now() - movePromotedRef.current < 500) { movePromotedRef.current = 0; return }
                        if (sideBets.perfectPairs.active) store.toggleSideBet('perfectPairs', 0)
                        else store.toggleSideBet('perfectPairs', selectedChip || 25)
                      }}
                      className="rounded-full flex flex-col items-center justify-center"
                      style={{
                        position: 'relative', touchAction: 'none',
                        width: dragging ? 38 : 30, height: dragging ? 38 : 30,
                        transition: 'all 0.2s',
                        background: sideBets.perfectPairs.active ? 'rgba(33,150,243,0.35)' : 'rgba(33,150,243,0.06)',
                        border: `2px solid ${sideBets.perfectPairs.active ? '#2196f3' : 'rgba(33,150,243,0.2)'}`,
                        boxShadow: sideBets.perfectPairs.active ? '0 0 10px rgba(33,150,243,0.3)' : 'none',
                      }}
                      whileTap={{ scale: 0.85 }}
                    >
                      {sideBets.perfectPairs.active ? (
                        <ChipStack chips={[]} size={22} total={sideBets.perfectPairs.bet} max={5} showTotal={false} />
                      ) : (
                        <span className="text-[6px] font-bold" style={{ color: 'rgba(33,150,243,0.5)' }}>LL</span>
                      )}
                    </motion.button>
                  </div>

                  {/* PROGRESSIVE (center, neon) */}
                  <div data-drop-zone="progressive" data-seat={seatIdx}>
                    <motion.button
                      onPointerDown={(e) => handleSpotPointerDown('progressive', seatIdx, e)}
                      onClick={() => {
                        if (movePromotedRef.current && Date.now() - movePromotedRef.current < 500) { movePromotedRef.current = 0; return }
                        if (sideBets.progressive.active) store.toggleSideBet('progressive', 0)
                        else store.toggleSideBet('progressive', selectedChip || 5)
                      }}
                      className="rounded-full flex flex-col items-center justify-center"
                      style={{
                        position: 'relative', touchAction: 'none',
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
                        <ChipStack chips={[]} size={22} total={sideBets.progressive.bet} max={5} showTotal={false} />
                      ) : (
                        <span className="text-[5px] font-bold" style={{ color: 'rgba(201,168,76,0.5)' }}>777</span>
                      )}
                    </motion.button>
                  </div>

                  {/* BB - Bad Buster (right) */}
                  <div data-drop-zone={ZONE_LADIES} data-seat={seatIdx}>
                    <motion.button
                      onPointerDown={(e) => handleSpotPointerDown(ZONE_LADIES, seatIdx, e)}
                      onClick={() => {
                        if (movePromotedRef.current && Date.now() - movePromotedRef.current < 500) { movePromotedRef.current = 0; return }
                        if (sideBets.luckyLadies.active) store.toggleSideBet('luckyLadies', 0)
                        else store.toggleSideBet('luckyLadies', selectedChip || 10)
                      }}
                      className="rounded-full flex flex-col items-center justify-center"
                      style={{
                        position: 'relative', touchAction: 'none',
                        width: dragging ? 38 : 30, height: dragging ? 38 : 30,
                        transition: 'all 0.2s',
                        background: sideBets.luckyLadies.active ? 'rgba(244,67,54,0.35)' : 'rgba(244,67,54,0.06)',
                        border: `2px solid ${sideBets.luckyLadies.active ? '#f44336' : 'rgba(244,67,54,0.2)'}`,
                        boxShadow: sideBets.luckyLadies.active ? '0 0 10px rgba(244,67,54,0.3)' : 'none',
                      }}
                      whileTap={{ scale: 0.85 }}
                    >
                      {sideBets.luckyLadies.active ? (
                        <ChipStack chips={[]} size={22} total={sideBets.luckyLadies.bet} max={5} showTotal={false} />
                      ) : (
                        <span className="text-[6px] font-bold" style={{ color: 'rgba(244,67,54,0.5)' }}>BB</span>
                      )}
                    </motion.button>
                  </div>
                </div>

                {/* MAIN BET circle */}
                <motion.button
                  data-drop-zone={ZONE_MAIN} data-seat={seatIdx}
                  onPointerDown={(e) => handleSpotPointerDown(ZONE_MAIN, seatIdx, e)}
                  onClick={() => {
                    if (movePromotedRef.current && Date.now() - movePromotedRef.current < 500) { movePromotedRef.current = 0; return }
                    const chip = selectedChip || 10
                    const newBet = Math.min(betAmount + chip, balance, config.maxBet)
                    if (newBet > betAmount) setChipStack(s => [...s, chip])
                    store.setBet(newBet)
                  }}
                  className="w-16 h-16 rounded-full flex flex-col items-center justify-center"
                  style={{
                    position: 'relative', touchAction: 'none',
                    background: betAmount > 0 ? 'rgba(201,168,76,0.2)' : dragging ? 'rgba(201,168,76,0.12)' : 'rgba(201,168,76,0.04)',
                    border: `2px solid ${betAmount > 0 ? '#c9a84c' : dragging ? 'rgba(201,168,76,0.5)' : 'rgba(201,168,76,0.2)'}`,
                    boxShadow: betAmount > 0 ? '0 0 15px rgba(201,168,76,0.2)' : dragging ? '0 0 8px rgba(201,168,76,0.1)' : 'none',
                  }}
                  whileTap={{ scale: 0.9 }}
                >
                  {betAmount > 0 ? (
                    <ChipStack chips={chipStack} total={betAmount} size={36} showTotal={false} />
                  ) : (
                    <span className="text-[7px] uppercase tracking-wider" style={{ color: 'rgba(201,168,76,0.4)' }}>
                      {dragging ? 'DROP' : 'BET'}
                    </span>
                  )}
                </motion.button>

                <div className="text-center mt-1 leading-tight">
                  {betAmount > 0 && (
                    <div className="font-mono font-bold" style={{ fontSize: 11, color: '#c9a84c', textShadow: '0 1px 3px rgba(0,0,0,0.9)' }}>
                      {betAmount}
                    </div>
                  )}
                  <div className="text-[7px]" style={{ color: 'rgba(201,168,76,0.3)' }}>Seat {seatIdx + 1}</div>
                </div>
              </div>
            )}
          </div>
        )
      })}

      {/* === CHIP TRAY (luxury SVG chips, draggable) -- at very bottom of game area === */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 pb-1">
        <div className="flex gap-2 items-end px-3 py-2 rounded-xl"
          style={{ background: 'rgba(0,0,0,0.8)', border: '1px solid rgba(201,168,76,0.2)' }}>
          {[10, 25, 100, 500, 1000, 5000].filter(v => v <= balance).map((v, i, arr) => {
            // Curved rail: center chip peaks, ends drop + tilt outward (~16deg).
            const t = arr.length > 1 ? (i / (arr.length - 1)) * 2 - 1 : 0
            const raise = (1 - Math.abs(t)) * 26
            return (
              <div key={v}
                onPointerDown={(e) => handleDragStart(v, e)}
                style={{
                  touchAction: 'none', cursor: 'grab',
                  transform: `translateY(${-raise}px) rotate(${(t * 16).toFixed(1)}deg)`,
                  transformOrigin: 'bottom center',
                  transition: 'transform .25s cubic-bezier(.34,1.56,.64,1)',
                }}
              >
                <CasinoChip value={v} selected={selectedChip === v}
                  onClick={() => useBlackjackStore.setState({ selectedChip: v })}
                  size={44} />
              </div>
            )
          })}
        </div>
        <p className="text-center text-[7px] mt-1" style={{ color: 'rgba(255,255,255,0.25)' }}>
          Drag chip to circle, or tap chip then tap circle
        </p>
      </div>
    </div>
  )
}

// ============================================================
// PHYSICAL CHIP STACK -- real chips that pile up on the bet spot
// ============================================================

// Break a bet total into standard chips (biggest first). Used as a fallback
// when we did not track the individual drags (re-bet, remount with a live bet).
function breakdownChips(total: number): number[] {
  const denoms = [5000, 1000, 500, 100, 25, 10]
  const out: number[] = []
  let r = total
  for (const d of denoms) {
    while (r >= d && out.length < 24) { out.push(d); r -= d }
  }
  if (r > 0 && out.length < 24) out.push(10)
  return out
}

/**
 * ChipStack -- renders the bet as a real, growing pile of casino chips.
 * Lower chips show as slim colored rims; the top chip shows its denomination.
 * The pile grows upward out of the bet circle as more chips land, and each
 * chip is colored by its denomination (matching the tray + CHIP_COLORS).
 * Pointer-events are off so it never blocks dropping more chips on the spot.
 */
function ChipStack({ chips, total, size = 30, max = 16, showTotal = true }: {
  chips: number[]; total: number; size?: number; max?: number; showTotal?: boolean
}) {
  const placed = chips.length ? chips : breakdownChips(total)
  const ordered = [...placed].sort((a, b) => b - a) // biggest at the bottom
  const shown = ordered.slice(Math.max(0, ordered.length - max))
  const SIZE = size
  const STEP = Math.max(3, Math.round(size * 0.2)) // visible rim of each chip below the top
  const stackH = SIZE + (shown.length - 1) * STEP
  const fontPx = Math.max(8, Math.round(size * 0.3))

  return (
    <>
      {/* The pile sits centered IN the circle and grows straight up. These are the
          SAME premium chips as the tray (CasinoChip), just stacked. */}
      <div className="absolute pointer-events-none"
        style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)', width: SIZE, height: stackH }}>
        {shown.map((v, i) => (
          <div key={i} className="absolute left-1/2" style={{ bottom: i * STEP, transform: 'translateX(-50%)' }}>
            <CasinoChip value={v} selected={false} onClick={() => {}} size={SIZE} />
          </div>
        ))}
      </div>
      {showTotal && (
        /* total bet, shown directly underneath the circle */
        <div className="absolute left-1/2 font-mono font-bold whitespace-nowrap"
          style={{ top: '100%', transform: 'translateX(-50%)', marginTop: 3, fontSize: fontPx, color: '#c9a84c', textShadow: '0 1px 3px rgba(0,0,0,0.95)' }}>
          {total}
        </div>
      )}
    </>
  )
}
