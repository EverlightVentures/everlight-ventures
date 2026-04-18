'use client'

import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMultiplayerStore } from '@/lib/multiplayer-store'
import SeatRenderer from './SeatRenderer'
import type { GameSeatRow } from '@/lib/multiplayer-types'
import type { Card } from '@/lib/blackjack-engine'
import { dealerAddress, detectGender, getPersonaByName } from '@/lib/bot-personas'

/**
 * MultiplayerTable v2 -- Full rewrite
 *
 * Fixes:
 * - All 5 seats visible on mobile (horizontal row, not absolute positioned)
 * - Seat-by-seat zoom when it's that seat's turn
 * - Dealer speech bubble with proper queuing (no overlap)
 * - Bot emoji only on appropriate outcomes
 * - Google profile pic at the seat
 */

const SUIT_SYMBOL: Record<string, string> = {
  spades: '\u2660', hearts: '\u2665', diamonds: '\u2666', clubs: '\u2663',
}

// Dealer lines per action
const DEALER_LINES: Record<string, string[]> = {
  turn_start: ["What'll it be?", "Your move.", "Hit or stay?", "Cards are waiting."],
  hit: ["Another card.", "Coming your way.", "Here you go."],
  stand: ["Standing pat.", "Holding.", "Wise choice."],
  bust: ["Bust.", "Over 21.", "Too many."],
  blackjack: ["Blackjack! Beautiful.", "Natural 21!", "That's the one."],
  bot_play: ["Let's see what you've got.", "Your turn.", "Show me something."],
  dealing: ["Cards in the air.", "Here we go.", "New hand."],
  settling: ["Let's settle up.", "Moment of truth.", "And the result is..."],
}

function pickDealerLine(key: string): string {
  const lines = DEALER_LINES[key] || DEALER_LINES.turn_start
  return lines[Math.floor(Math.random() * lines.length)]
}

function DealerCard({ card, index }: { card: Card; index: number }) {
  const isHidden = card.faceDown || card.rank === '?'
  const isRed = card.suit === 'hearts' || card.suit === 'diamonds'

  return (
    <motion.div
      initial={{ opacity: 0, y: -20, rotateY: 180 }}
      animate={{ opacity: 1, y: 0, rotateY: 0 }}
      transition={{ delay: index * 0.2, duration: 0.4 }}
      className="rounded-lg shadow-xl flex-shrink-0"
      style={{
        width: 44,
        height: 62,
        marginLeft: index > 0 ? -14 : 0,
        background: isHidden ? 'linear-gradient(135deg, #1a1a3e, #0a0a2e)' : '#fefefe',
        border: isHidden ? '2px solid rgba(201,168,76,0.3)' : '1px solid rgba(0,0,0,0.1)',
        zIndex: index,
      }}
    >
      {isHidden ? (
        <div className="w-full h-full flex items-center justify-center">
          <span className="text-xs font-bold" style={{ color: 'rgba(201,168,76,0.4)' }}>V</span>
        </div>
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center p-0.5">
          <span className="text-xs font-bold" style={{ color: isRed ? '#e74c3c' : '#1a1a2e' }}>{card.rank}</span>
          <span className="text-[10px]" style={{ color: isRed ? '#e74c3c' : '#1a1a2e' }}>{SUIT_SYMBOL[card.suit] || '?'}</span>
        </div>
      )}
    </motion.div>
  )
}

function BetControls({ onBet, minBet }: { onBet: (amount: number) => void; minBet: number }) {
  const [betAmount, setBetAmount] = useState(minBet)
  const chips = [25, 50, 100, 250, 500, 1000, 5000].filter(c => c >= minBet)

  useEffect(() => { setBetAmount(minBet) }, [minBet])

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center gap-2">
      <p className="text-[10px] uppercase tracking-widest opacity-40">Place Your Bet (min {minBet.toLocaleString()})</p>
      <div className="flex gap-1.5 flex-wrap justify-center">
        {chips.map((chip) => (
          <motion.button
            key={chip}
            onClick={() => setBetAmount(chip)}
            className="w-10 h-10 rounded-full flex items-center justify-center text-[9px] font-bold"
            style={{
              background: betAmount === chip ? 'linear-gradient(135deg, #c9a84c, #e8c55a)' : 'rgba(255,255,255,0.05)',
              color: betAmount === chip ? '#000' : '#fff',
              border: `2px solid ${betAmount === chip ? '#c9a84c' : 'rgba(255,255,255,0.1)'}`,
            }}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            {chip >= 1000 ? `${chip / 1000}K` : chip}
          </motion.button>
        ))}
      </div>
      <motion.button
        onClick={() => onBet(betAmount)}
        className="px-6 py-2 rounded-xl text-xs font-bold tracking-wider"
        style={{ background: 'linear-gradient(135deg, #c9a84c, #e8c55a)', color: '#000' }}
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
      >
        BET {betAmount.toLocaleString()} GC
      </motion.button>
    </motion.div>
  )
}

function ActionButtons() {
  const { playerHit, playerStand, playerDouble, playerSplit, playerSurrender, table, seats, mySeatIndices } = useMultiplayerStore()

  // Find the seat that's currently acting (could be any of my seats)
  const currentSeat = seats.find((s) => s.seat_index === table?.current_seat && (mySeatIndices || []).includes(s.seat_index))
  if (!currentSeat) return null

  const cardCount = (currentSeat.cards || []).length
  const canDouble = cardCount === 2 && currentSeat.chips >= currentSeat.bet
  const canSplit = cardCount === 2 && currentSeat.cards?.[0] && currentSeat.cards?.[1] &&
    (currentSeat.cards[0] as Card).rank === (currentSeat.cards[1] as Card).rank &&
    currentSeat.chips >= currentSeat.bet && !currentSeat.is_split
  const canSurrender = cardCount === 2 && table?.surrender_allowed

  const actions = [
    { label: 'HIT', action: playerHit, color: '#27ae60', show: true },
    { label: 'STAND', action: playerStand, color: '#e74c3c', show: true },
    { label: 'DOUBLE', action: playerDouble, color: '#f39c12', show: canDouble },
    { label: 'SPLIT', action: playerSplit, color: '#9b59b6', show: canSplit },
    { label: 'SURRENDER', action: playerSurrender, color: '#95a5a6', show: canSurrender },
  ]

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex gap-2 flex-wrap justify-center">
      {actions.filter(a => a.show).map((a) => (
        <motion.button
          key={a.label}
          onClick={a.action}
          className="px-5 py-2.5 rounded-xl text-xs font-bold tracking-wider"
          style={{ background: `${a.color}20`, color: a.color, border: `1px solid ${a.color}40` }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {a.label}
        </motion.button>
      ))}
    </motion.div>
  )
}

// ============================================================
// MAIN COMPONENT
// ============================================================

export default function MultiplayerTable({ tableId }: { tableId: string }) {
  const {
    connect, disconnect, connected, table, seats, mySeatIndex,
    mySeatIndices, myUserId, turnTimeLeft, error, chatMessages,
    joinSeat, placeBetOnSeat, createInvite, getFriends, sendChat,
  } = useMultiplayerStore()

  const [dealerSpeech, setDealerSpeech] = useState('')
  const [inviteModal, setInviteModal] = useState<{ seatIndex: number; code?: string; url?: string } | null>(null)
  const [friends, setFriends] = useState<any[]>([])
  const speechTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastPhase = useRef<string>('')

  // Connect on mount
  useEffect(() => {
    connect(tableId)
    return () => disconnect()
  }, [tableId])

  // Dealer speech queue -- no overlapping
  const dealerSay = (line: string) => {
    if (speechTimer.current) clearTimeout(speechTimer.current)
    setDealerSpeech(line)
    speechTimer.current = setTimeout(() => setDealerSpeech(''), 3000)
  }

  // React to phase changes with dealer lines
  useEffect(() => {
    if (!table) return
    const phase = `${table.phase}:${table.current_seat}`
    if (phase === lastPhase.current) return
    lastPhase.current = phase

    if (table.phase === 'dealing') {
      dealerSay(pickDealerLine('dealing'))
    } else if (table.phase === 'player_turn') {
      const seat = seats.find(s => s.seat_index === table.current_seat)
      const name = seat?.display_name || `Seat ${table.current_seat + 1}`
      const gender = seat ? detectGender(name) : 'neutral'
      const isBotSeat = seat?.player_id === 'BOT' && !seat?.user_id
      const address = dealerAddress(name, gender)
      if (isBotSeat) {
        dealerSay(`${address}, ${pickDealerLine('bot_play')}`)
      } else {
        dealerSay(`${address}, ${pickDealerLine('turn_start')}`)
      }
    } else if (table.phase === 'settled') {
      dealerSay(pickDealerLine('settling'))
    }
  }, [table?.phase, table?.current_seat])

  if (!connected || !table) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#050510' }}>
        <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.5, repeat: Infinity }}
          className="text-sm" style={{ color: '#c9a84c' }}>
          Connecting...
        </motion.div>
      </div>
    )
  }

  const isMyTurn = table.phase === 'player_turn' && (mySeatIndices || []).includes(table.current_seat)
  const isBettingPhase = table.phase === 'betting'
  const isSettled = table.phase === 'settled'
  const isPlayerTurn = table.phase === 'player_turn'
  const mySeats = (mySeatIndices || [])
  const allMySeatsHaveBets = mySeats.length > 0 && seats.filter(s => mySeats.includes(s.seat_index) && s.bet > 0).length === mySeats.length
  const mySeatCount = mySeats.length
  const effectiveMinBet = table.min_bet * Math.pow(2, Math.max(0, mySeatCount - 1))
  const dealerCards = (table.dealer_hand || []) as Card[]
  const dealerTotal = table.dealer_total || 0
  const activeSeatIndex = table.current_seat

  return (
    <div className="h-screen flex flex-col relative overflow-hidden" style={{ background: '#050510' }}>
      {/* Table felt gradient */}
      <div className="absolute inset-0 opacity-20 pointer-events-none"
        style={{ background: `radial-gradient(ellipse at 50% 35%, ${table.felt_color}60 0%, transparent 70%)` }} />

      {/* Error banner */}
      <AnimatePresence>
        {error && (
          <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="absolute top-2 left-1/2 -translate-x-1/2 z-50 px-3 py-1.5 rounded-lg text-[10px]"
            style={{ background: 'rgba(231,76,60,0.2)', color: '#e74c3c', border: '1px solid rgba(231,76,60,0.3)' }}>
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ===== TOP: Header + Dealer ===== */}
      <div className="relative z-10 flex-shrink-0 px-4 pt-3">
        {/* Header row */}
        <div className="flex items-center justify-between mb-2">
          <div>
            <h2 className="text-sm font-bold" style={{ fontFamily: "'Cinzel', serif", color: '#c9a84c' }}>
              {table.name}
            </h2>
            <p className="text-[8px] uppercase tracking-widest opacity-30">
              {table.variant} | Round #{table.round_number}
            </p>
          </div>
          <div className="text-right">
            <p className="text-[9px] opacity-40">{table.min_bet}-{table.max_bet.toLocaleString()}</p>
            <p className="text-[8px] uppercase tracking-widest"
              style={{ color: isPlayerTurn ? '#27ae60' : 'rgba(255,255,255,0.3)' }}>
              {table.phase.replace('_', ' ')}
            </p>
          </div>
        </div>

        {/* Dealer area */}
        <div className="flex flex-col items-center mb-2">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-900/30 to-amber-700/10 border border-amber-600/20 flex items-center justify-center">
              <span className="text-base">&#9813;</span>
            </div>
            <div>
              <p className="text-[10px] font-medium opacity-50">{table.dealer_name}</p>
              {/* Dealer speech bubble */}
              <AnimatePresence>
                {dealerSpeech && (
                  <motion.p
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    className="text-[10px] italic max-w-[200px]"
                    style={{ color: '#c9a84c' }}
                  >
                    "{dealerSpeech}"
                  </motion.p>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Dealer cards */}
          {dealerCards.length > 0 && (
            <div className="flex items-center">
              {dealerCards.map((card, i) => <DealerCard key={i} card={card} index={i} />)}
              {dealerTotal > 0 && (
                <span className="ml-2 text-xs font-bold px-2 py-0.5 rounded-full" style={{ background: 'rgba(255,255,255,0.08)' }}>
                  {dealerTotal}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ===== MIDDLE: Seats (horizontal row, all visible, no overflow) ===== */}
      <div className="relative z-10 flex-1 flex items-center justify-center px-1 min-h-0 overflow-visible">
        <div className="flex items-end justify-between w-full max-w-[420px] px-1">
          {seats.slice(0, table.max_seats).map((seat, i) => {
            const isCurrent = isPlayerTurn && activeSeatIndex === seat.seat_index
            const isMe = seat.user_id === myUserId
            const isEmpty = seat.status === 'empty' && !seat.user_id && seat.player_id !== 'BOT'

            return (
              <motion.div
                key={seat.id || i}
                className="flex-1 flex justify-center"
                animate={{
                  scale: isCurrent ? 1.12 : 1,
                  y: isCurrent ? -8 : 0,
                  zIndex: isCurrent ? 10 : 1,
                }}
                transition={{ duration: 0.4, ease: 'easeOut' }}
                style={{ position: 'relative' }}
              >
                {/* Active turn glow */}
                {isCurrent && (
                  <motion.div
                    className="absolute inset-0 rounded-2xl pointer-events-none"
                    animate={{ opacity: [0.1, 0.3, 0.1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    style={{ background: 'radial-gradient(circle, rgba(39,174,96,0.15) 0%, transparent 70%)' }}
                  />
                )}
                <SeatRenderer
                  seat={seat}
                  isMyTurn={isMe && isCurrent}
                  isMe={isMe}
                  isCurrent={isCurrent}
                  turnTimeLeft={isCurrent ? turnTimeLeft : undefined}
                  onSitDown={() => joinSeat(seat.seat_index)}
                  onInvite={mySeatIndex !== null && isEmpty ? async () => {
                    const result = await createInvite(seat.seat_index)
                    if (result) {
                      setInviteModal({ seatIndex: seat.seat_index, code: result.code, url: result.invite_url })
                      const f = await getFriends()
                      setFriends(f)
                    }
                  } : undefined}
                  showInviteOption={mySeatIndex !== null && isEmpty}
                />
              </motion.div>
            )
          })}
        </div>
      </div>

      {/* ===== BOTTOM: Controls ===== */}
      <div className="relative z-10 flex-shrink-0 px-4 pb-4 pt-2">
        {isBettingPhase && mySeatIndex !== null && !allMySeatsHaveBets && (
          <div>
            {mySeatCount > 1 && (
              <p className="text-center text-[9px] mb-1" style={{ color: '#c9a84c' }}>
                {mySeatCount} seats -- min {effectiveMinBet.toLocaleString()} GC/seat
              </p>
            )}
            <BetControls minBet={effectiveMinBet} onBet={(amount) => {
              for (const idx of mySeats) { placeBetOnSeat(idx, amount) }
            }} />
          </div>
        )}

        {isBettingPhase && mySeatIndex !== null && allMySeatsHaveBets && (
          <motion.p animate={{ opacity: [0.3, 0.7, 0.3] }} transition={{ duration: 2, repeat: Infinity }}
            className="text-center text-xs opacity-50">
            Waiting for others...
          </motion.p>
        )}

        {mySeatIndex === null && (
          <p className="text-center text-xs opacity-40">Tap an empty seat to join</p>
        )}

        {isMyTurn && <ActionButtons />}

        {isPlayerTurn && !isMyTurn && mySeatIndex !== null && (
          <p className="text-center text-[10px] opacity-30">
            {seats.find(s => s.seat_index === activeSeatIndex)?.display_name || `Seat ${activeSeatIndex + 1}`} is playing...
          </p>
        )}

        {isSettled && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="text-center text-[10px] opacity-30">
            Next hand starting soon...
          </motion.p>
        )}
      </div>

      {/* ===== CHAT FEED (floating messages) ===== */}
      <div className="fixed bottom-20 left-3 z-30 max-w-[260px] pointer-events-none">
        <AnimatePresence>
          {chatMessages.slice(-4).map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, x: -20, y: 10 }}
              animate={{ opacity: 1, x: 0, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              className="mb-1 px-2.5 py-1.5 rounded-lg backdrop-blur-sm"
              style={{ background: 'rgba(0,0,0,0.6)', border: '1px solid rgba(255,255,255,0.06)' }}
            >
              <span className="text-[9px] font-bold" style={{
                color: msg.seat_index >= 0
                  ? `hsl(${(msg.seat_index * 72 + 120) % 360}, 60%, 65%)`
                  : '#c9a84c'
              }}>
                {msg.display_name}
              </span>
              <span className="text-[10px] ml-1.5" style={{ color: 'rgba(255,255,255,0.75)' }}>
                {msg.text}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* ===== INVITE MODAL ===== */}
      <AnimatePresence>
        {inviteModal && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center"
            style={{ background: 'rgba(0,0,0,0.8)' }}
            onClick={() => setInviteModal(null)}
          >
            <motion.div
              initial={{ scale: 0.9 }} animate={{ scale: 1 }} exit={{ scale: 0.9 }}
              className="rounded-2xl p-5 max-w-xs w-full mx-4"
              style={{ background: '#0a0a15', border: '1px solid rgba(201,168,76,0.2)' }}
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-sm font-bold mb-3" style={{ color: '#c9a84c' }}>
                Invite to Seat {(inviteModal.seatIndex || 0) + 1}
              </h3>

              <div className="mb-3 p-3 rounded-lg text-center" style={{ background: 'rgba(255,255,255,0.03)' }}>
                <p className="text-[9px] uppercase tracking-widest opacity-30 mb-1">Invite Code</p>
                <p className="text-xl font-mono font-bold tracking-[0.3em]" style={{ color: '#c9a84c' }}>
                  {inviteModal.code}
                </p>
                <button
                  onClick={() => navigator.clipboard?.writeText(inviteModal.url || inviteModal.code || '')}
                  className="mt-1.5 text-[9px] px-3 py-1 rounded-full"
                  style={{ background: 'rgba(201,168,76,0.1)', color: '#c9a84c' }}
                >
                  COPY LINK
                </button>
              </div>

              {friends.length > 0 && (
                <div className="mb-3">
                  <p className="text-[9px] uppercase tracking-widest opacity-30 mb-1.5">Invite a friend</p>
                  <div className="space-y-1.5 max-h-[150px] overflow-y-auto">
                    {friends.map((f: any) => (
                      <div key={f.auth_user_id} className="flex items-center justify-between p-1.5 rounded-lg"
                        style={{ background: 'rgba(255,255,255,0.03)' }}>
                        <div className="flex items-center gap-2">
                          {f.avatar_url ? (
                            <img src={f.avatar_url} className="w-6 h-6 rounded-full" referrerPolicy="no-referrer" />
                          ) : (
                            <div className="w-6 h-6 rounded-full bg-gray-700 flex items-center justify-center text-[9px]">
                              {(f.display_name || 'P')[0]}
                            </div>
                          )}
                          <p className="text-[10px]">{f.display_name}</p>
                        </div>
                        <button className="text-[8px] px-2 py-0.5 rounded-full"
                          style={{ background: 'rgba(39,174,96,0.15)', color: '#27ae60' }}
                          onClick={async () => {
                            const result = await createInvite(inviteModal.seatIndex, f.auth_user_id)
                            if (result) setInviteModal({ ...inviteModal, code: result.code, url: result.invite_url })
                          }}>
                          INVITE
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <a href={`sms:?body=Join%20me%20at%20Vantaris!%20Code:%20${inviteModal.code}%20${encodeURIComponent(inviteModal.url || '')}`}
                className="block text-center text-[10px] px-3 py-2 rounded-lg mb-2"
                style={{ background: 'rgba(100,100,255,0.1)', color: 'rgba(100,150,255,1)', border: '1px solid rgba(100,100,255,0.15)' }}>
                SEND VIA TEXT
              </a>

              <button onClick={() => setInviteModal(null)}
                className="w-full text-[10px] py-1.5 rounded-lg opacity-30 hover:opacity-60">
                Close
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
