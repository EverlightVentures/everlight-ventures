'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useBlackjackStore } from '@/lib/blackjack-store'

/**
 * BotPlayers -- Visual bot overlay system
 *
 * Renders 4 AI bot players at their 3D-projected seat positions.
 * Each bot has: name, chip count, seat label, sitting out state.
 * Bots play simulated hands each round with basic strategy.
 * Outcome flashes (WIN/BUST/LOSS/PUSH) display for 1.2s.
 *
 * Positions come from seatPositions prop (projected by CasinoScene3D).
 */

// ============================================================
// CONSTANTS
// ============================================================

const BOT_SEATS = [0, 1, 3, 4]
const SEAT_LABELS = ['Seat 1', 'Seat 2', 'Seat 3', 'Seat 4', 'Seat 5']

function botDecision(handVal: number, dealerUp: number): 'hit' | 'stand' {
  if (Math.random() < 0.2) return Math.random() < 0.5 ? 'hit' : 'stand'
  if (handVal >= 17) return 'stand'
  if (handVal <= 11) return 'hit'
  if (handVal === 12) return dealerUp >= 4 && dealerUp <= 6 ? 'stand' : 'hit'
  if (handVal >= 13 && handVal <= 16) return dealerUp >= 2 && dealerUp <= 6 ? 'stand' : 'hit'
  return 'stand'
}

function randomRank(): string {
  const ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
  const weights = [1,1,1,1,1,1,1,1,1,4,4,4,1]
  const total = weights.reduce((a,b) => a+b, 0)
  let r = Math.random() * total
  for (let i = 0; i < ranks.length; i++) {
    r -= weights[i]
    if (r <= 0) return ranks[i]
  }
  return '10'
}

function cardVal(rank: string): number {
  if (['J','Q','K'].includes(rank)) return 10
  if (rank === 'A') return 11
  return Math.min(parseInt(rank) || 10, 10)
}

function handTotal(hand: string[]): number {
  let total = 0, aces = 0
  for (const r of hand) {
    total += cardVal(r)
    if (r === 'A') aces++
  }
  while (total > 21 && aces > 0) { total -= 10; aces-- }
  return total
}

// ============================================================
// TYPES
// ============================================================

export interface SeatPosition {
  x: number
  y: number
  visible: boolean
}

interface BotOutcome {
  text: string
  color: string
}

interface BotCardData {
  rank: string
  suit: string
  faceDown: boolean
}

// Bot thought bubble phrases
const BOT_WIN_THOUGHTS = ['Nice hand!', 'Let\'s go!', 'Easy money', 'On fire!', 'Yes!']
const BOT_LOSS_THOUGHTS = ['Ouch...', 'Tough break', 'Next one', 'Ugh', 'Cold deck']
const BOT_BJ_THOUGHTS = ['WOW!', 'Incredible!', 'No way!', 'Legend!', 'GOAT move']
const BOT_IDLE_THOUGHTS = ['Hmm...', 'Hit or stand?', 'Feeling lucky', 'Let me think...', 'Risky...']

const SUIT_SYMBOLS: Record<string, string> = {
  s: '\u2660', h: '\u2665', d: '\u2666', c: '\u2663',
}
const SUIT_POOL = ['s', 'h', 'd', 'c']

function randomSuit(): string {
  return SUIT_POOL[Math.floor(Math.random() * 4)]
}

// ============================================================
// MINI CARD (40x56px for bot hands)
// ============================================================

function MiniCard({ card, index }: { card: BotCardData; index: number }) {
  const isRed = card.suit === 'h' || card.suit === 'd'
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0, rotateY: 180 }}
      animate={{ opacity: 1, scale: 1, rotateY: 0 }}
      transition={{ duration: 0.3, delay: index * 0.15, type: 'spring', stiffness: 200, damping: 18 }}
      className="rounded"
      style={{
        width: '28px', height: '40px',
        marginLeft: index > 0 ? '-12px' : '0',
        background: card.faceDown
          ? 'linear-gradient(135deg, #1a3a6b, #0d1f3c)'
          : '#fff',
        border: card.faceDown ? '1px solid #c9a84c' : '1px solid #ddd',
        boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
        display: 'flex', flexDirection: 'column' as const,
        alignItems: 'center', justifyContent: 'center',
        fontSize: '0.5rem', fontWeight: 700,
        color: card.faceDown ? '#c9a84c' : isRed ? '#c0392b' : '#111',
        zIndex: index,
        position: 'relative' as const,
      }}
    >
      {card.faceDown ? (
        <span style={{ fontSize: '0.7rem' }}>{'\u2666'}</span>
      ) : (
        <>
          <span style={{ fontSize: '0.55rem', lineHeight: 1 }}>{card.rank}</span>
          <span style={{ fontSize: '0.45rem', lineHeight: 1 }}>{SUIT_SYMBOLS[card.suit]}</span>
        </>
      )}
    </motion.div>
  )
}

// ============================================================
// BOT LABEL (with cards)
// ============================================================

function BotLabel({ bot, position, outcome, cards, thought }: {
  bot: { name: string; chips: number; seat: number; sittingOut: boolean; color: string }
  position: SeatPosition
  outcome: BotOutcome | null
  cards: BotCardData[]
  thought: string | null
}) {
  if (!position.visible) return null

  return (
    <div
      className="absolute pointer-events-none text-center"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        transform: 'translate(-50%, -50%)',
        fontFamily: "'Cinzel', serif",
        transition: 'left 0.1s linear, top 0.1s linear',
        opacity: bot.sittingOut ? 0.35 : 1,
        filter: bot.sittingOut ? 'grayscale(0.7)' : 'none',
      }}
    >
      {/* Thought bubble */}
      <AnimatePresence>
        {thought && (
          <motion.div
            initial={{ opacity: 0, y: 6, scale: 0.8 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.9 }}
            className="mb-1 px-2 py-0.5 rounded-lg text-[0.5rem]"
            style={{
              background: 'rgba(0,0,0,0.75)',
              border: '1px solid rgba(255,255,255,0.15)',
              color: 'rgba(255,255,255,0.7)',
              backdropFilter: 'blur(4px)',
              maxWidth: '80px',
            }}
          >
            {thought}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bot cards (mini hand) */}
      {cards.length > 0 && (
        <div className="flex justify-center mb-1" style={{ minHeight: '42px' }}>
          {cards.map((c, i) => <MiniCard key={i} card={c} index={i} />)}
        </div>
      )}

      <div className="text-[0.62rem] font-semibold" style={{
        color: bot.sittingOut ? '#666' : '#aaeeff',
        textShadow: '0 1px 3px rgba(0,0,0,0.9)',
      }}>
        {bot.name}
      </div>

      {bot.sittingOut ? (
        <div className="text-[0.5rem] tracking-wider mt-0.5"
          style={{ color: 'rgba(255,255,255,0.25)', letterSpacing: '1px' }}>
          SITTING OUT
        </div>
      ) : (
        <div className="text-[0.55rem]" style={{
          color: 'rgba(201,168,76,0.8)',
          textShadow: '0 1px 3px rgba(0,0,0,0.9)',
        }}>
          {bot.chips.toLocaleString()} chips
        </div>
      )}

      <AnimatePresence>
        {outcome && (
          <motion.div
            initial={{ opacity: 0, scale: 0.5, y: 4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: -4 }}
            transition={{ type: 'spring', stiffness: 400, damping: 20 }}
            className="text-[0.65rem] font-bold mt-0.5"
            style={{ color: outcome.color, textShadow: `0 0 8px ${outcome.color}40` }}
          >
            {outcome.text}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="text-[0.48rem] tracking-wider mt-0.5" style={{
        color: 'rgba(201,168,76,0.4)',
        letterSpacing: '1px',
        textShadow: '0 1px 3px rgba(0,0,0,0.9)',
      }}>
        {SEAT_LABELS[bot.seat]}
      </div>
    </div>
  )
}

// ============================================================
// PLAYER SEAT LABEL
// ============================================================

function PlayerSeatLabel({ position }: { position: SeatPosition }) {
  if (!position.visible) return null

  const playerName = typeof window !== 'undefined'
    ? localStorage.getItem('vantaris_player_name') || 'Player'
    : 'Player'
  const initial = playerName.charAt(0).toUpperCase()

  return (
    <div
      className="absolute pointer-events-none text-center"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        transform: 'translate(-50%, -50%)',
        fontFamily: "'Cinzel', serif",
        transition: 'left 0.1s linear, top 0.1s linear',
      }}
    >
      {/* Player avatar circle */}
      <div className="mx-auto mb-1 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
        style={{
          background: 'linear-gradient(135deg, #c9a84c, #e8c55a)',
          color: '#000',
          boxShadow: '0 0 12px rgba(201,168,76,0.4), 0 2px 8px rgba(0,0,0,0.5)',
          border: '2px solid rgba(201,168,76,0.6)',
        }}>
        {initial}
      </div>
      <div className="text-[0.55rem] font-semibold" style={{
        color: '#c9a84c',
        textShadow: '0 1px 3px rgba(0,0,0,0.9)',
      }}>
        {playerName}
      </div>
      <div className="text-[0.45rem] tracking-wider" style={{
        color: 'rgba(201,168,76,0.4)',
        letterSpacing: '1px',
        textShadow: '0 1px 3px rgba(0,0,0,0.9)',
      }}>
        {SEAT_LABELS[2]}
      </div>
    </div>
  )
}

// ============================================================
// MAIN COMPONENT
// ============================================================

export function BotPlayers({ seatPositions }: { seatPositions: SeatPosition[] }) {
  const bots = useBlackjackStore(s => s.bots)
  const phase = useBlackjackStore(s => s.phase)
  const [outcomes, setOutcomes] = useState<Record<number, BotOutcome | null>>({})
  const [thoughts, setThoughts] = useState<Record<number, string | null>>({})
  const [botCards, setBotCards] = useState<Record<number, BotCardData[]>>({})

  // Deal face-down cards to bots when player's hand is dealt
  useEffect(() => {
    if (phase === 'dealing') {
      const cards: Record<number, BotCardData[]> = {}
      bots.forEach(bot => {
        if (!bot.sittingOut) {
          cards[bot.seat] = [
            { rank: randomRank(), suit: randomSuit(), faceDown: true },
            { rank: randomRank(), suit: randomSuit(), faceDown: true },
          ]
        }
      })
      setBotCards(cards)
    } else if (phase === 'betting') {
      setBotCards({})
    }
  }, [phase])

  const runBotRound = useCallback(async () => {
    const store = useBlackjackStore.getState()
    const updatedBots = [...store.bots]

    for (let i = 0; i < updatedBots.length; i++) {
      const bot = { ...updatedBots[i] }

      if (Math.random() < 0.1) {
        bot.sittingOut = !bot.sittingOut
        updatedBots[i] = bot
        continue
      }
      if (bot.sittingOut) { updatedBots[i] = bot; continue }

      const bet = Math.min(Math.floor(50 + Math.random() * 150) * 10, bot.chips)
      if (bet <= 0) { updatedBots[i] = bot; continue }

      // Use the pre-dealt cards or generate new ones
      const existingCards = botCards[bot.seat] || []
      const hand = existingCards.length >= 2
        ? existingCards.map(c => c.rank)
        : [randomRank(), randomRank()]
      let total = handTotal(hand)
      const dealerUp = Math.floor(Math.random() * 9) + 2

      // Build visible card data (reveal face-down cards)
      const visibleCards: BotCardData[] = hand.map((r, idx) => ({
        rank: r,
        suit: existingCards[idx]?.suit || randomSuit(),
        faceDown: false,
      }))

      // Bot plays (hit more cards)
      let iterations = 0
      while (total < 21 && iterations < 5) {
        if (botDecision(total, dealerUp) === 'stand') break
        const newRank = randomRank()
        hand.push(newRank)
        visibleCards.push({ rank: newRank, suit: randomSuit(), faceDown: false })
        total = handTotal(hand)
        iterations++
      }

      // Reveal cards at this bot's seat
      setBotCards(prev => ({ ...prev, [bot.seat]: visibleCards }))

      // Outcome
      const bust = total > 21
      const dealerTotal = 17 + Math.floor(Math.random() * 7)
      const win = !bust && (dealerTotal > 21 || total > dealerTotal)
      const push = !bust && total === dealerTotal

      if (win) bot.chips += bet
      else if (!push) bot.chips = Math.max(0, bot.chips - bet)
      if (bot.chips < 200) bot.chips = 800

      updatedBots[i] = bot

      const outcomeText = bust ? 'BUST' : win ? `WIN +${bet}` : push ? 'PUSH' : `LOSS -${bet}`
      const outcomeColor = win ? '#27ae60' : (bust || !push) ? '#e74c3c' : '#aaa'

      setOutcomes(prev => ({ ...prev, [bot.seat]: { text: outcomeText, color: outcomeColor } }))
      setTimeout(() => {
        setOutcomes(prev => ({ ...prev, [bot.seat]: null }))
      }, 1800)

      // Show outcome thought bubble
      const thoughtPool = bust ? BOT_LOSS_THOUGHTS : win ? BOT_WIN_THOUGHTS : BOT_IDLE_THOUGHTS
      setThoughts(prev => ({ ...prev, [bot.seat]: thoughtPool[Math.floor(Math.random() * thoughtPool.length)] }))
      setTimeout(() => setThoughts(prev => ({ ...prev, [bot.seat]: null })), 2500)

      // Think delay: 1.5-4s per bot (well spaced, simulates real player thinking)
      await new Promise(r => setTimeout(r, 1500 + Math.random() * 2500))
    }

    useBlackjackStore.setState({ bots: updatedBots })
  }, [botCards])

  // Trigger bot round when player hand settles
  useEffect(() => {
    if (phase === 'settled') {
      const timer = setTimeout(runBotRound, 400)
      return () => clearTimeout(timer)
    }
  }, [phase, runBotRound])

  const botSeatMap = BOT_SEATS.map((seatIdx, i) => ({
    bot: bots[i],
    position: seatPositions[seatIdx] || { x: 0, y: 0, visible: false },
  }))

  return (
    <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 15 }}>
      {botSeatMap.map(({ bot, position }) => (
        <BotLabel
          key={bot.seat}
          bot={bot}
          position={position}
          outcome={outcomes[bot.seat] || null}
          cards={botCards[bot.seat] || []}
          thought={thoughts[bot.seat] || null}
        />
      ))}
      <PlayerSeatLabel position={seatPositions[2] || { x: 0, y: 0, visible: false }} />
    </div>
  )
}
