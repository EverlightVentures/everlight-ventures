'use client'

import { motion, AnimatePresence } from 'framer-motion'
import type { GameSeatRow } from '@/lib/multiplayer-types'
import type { Card } from '@/lib/blackjack-engine'

/**
 * SeatRenderer -- Renders a single seat at the multiplayer table.
 *
 * Shows: avatar (Google profile pic), display name, cards, bet,
 * hand total, status, outcome, VIP border, turn indicator.
 *
 * Layout is a semi-circular arrangement around the dealer.
 */

interface SeatRendererProps {
  seat: GameSeatRow
  isMyTurn: boolean
  isMe: boolean
  isCurrent: boolean // this seat has the active turn
  turnTimeLeft?: number
  onSitDown?: () => void
  onInvite?: () => void
  showInviteOption?: boolean
}

// Card display component
function MiniCard({ card, index }: { card: Card; index: number }) {
  const isHidden = card.faceDown || card.rank === '?'
  const isRed = card.suit === 'hearts' || card.suit === 'diamonds'

  const suitSymbol: Record<string, string> = {
    spades: '\u2660', hearts: '\u2665', diamonds: '\u2666', clubs: '\u2663',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -20, rotateY: 180 }}
      animate={{ opacity: 1, y: 0, rotateY: 0 }}
      transition={{ delay: index * 0.15, duration: 0.3 }}
      className="relative rounded-md shadow-lg"
      style={{
        width: 36,
        height: 50,
        marginLeft: index > 0 ? -12 : 0,
        background: isHidden
          ? 'linear-gradient(135deg, #1a1a3e, #0a0a2e)'
          : '#fff',
        border: isHidden
          ? '1px solid rgba(201,168,76,0.3)'
          : '1px solid rgba(0,0,0,0.15)',
        zIndex: index,
      }}
    >
      {isHidden ? (
        <div className="w-full h-full flex items-center justify-center">
          <span className="text-[8px]" style={{ color: 'rgba(201,168,76,0.5)' }}>V</span>
        </div>
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center p-0.5">
          <span
            className="text-[10px] font-bold leading-none"
            style={{ color: isRed ? '#e74c3c' : '#1a1a2e' }}
          >
            {card.rank}
          </span>
          <span
            className="text-[8px] leading-none"
            style={{ color: isRed ? '#e74c3c' : '#1a1a2e' }}
          >
            {suitSymbol[card.suit] || '?'}
          </span>
        </div>
      )}
    </motion.div>
  )
}

// Outcome badge
function OutcomeBadge({ outcome, payout }: { outcome: string; payout: number }) {
  const colors: Record<string, { bg: string; text: string }> = {
    win: { bg: 'rgba(39,174,96,0.2)', text: '#27ae60' },
    blackjack: { bg: 'rgba(201,168,76,0.2)', text: '#c9a84c' },
    charlie: { bg: 'rgba(142,68,173,0.2)', text: '#8e44ad' },
    push: { bg: 'rgba(149,165,166,0.2)', text: '#95a5a6' },
    loss: { bg: 'rgba(231,76,60,0.15)', text: '#e74c3c' },
    bust: { bg: 'rgba(231,76,60,0.15)', text: '#e74c3c' },
    surrender: { bg: 'rgba(243,156,18,0.15)', text: '#f39c12' },
  }
  const style = colors[outcome] || colors.loss

  return (
    <motion.div
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className="absolute -top-3 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider whitespace-nowrap"
      style={{ background: style.bg, color: style.text, border: `1px solid ${style.text}30` }}
    >
      {outcome === 'blackjack' ? 'BJ!' : outcome.toUpperCase()}
      {payout > 0 && ` +${payout.toLocaleString()}`}
    </motion.div>
  )
}

export default function SeatRenderer({
  seat, isMyTurn, isMe, isCurrent, turnTimeLeft, onSitDown, onInvite, showInviteOption,
}: SeatRendererProps) {
  const isOccupied = seat.status !== 'empty' && (seat.user_id || seat.player_id === 'BOT')
  const isEmpty = !isOccupied
  const isBotSeat = seat.player_id === 'BOT' && !seat.user_id
  const hasCards = (seat.cards || []).length > 0
  const isSettled = seat.status === 'settled'

  // VIP gold border
  const borderColor = seat.is_vip
    ? 'rgba(201,168,76,0.5)'
    : isCurrent
      ? 'rgba(39,174,96,0.5)'
      : isMe
        ? 'rgba(100,100,255,0.3)'
        : 'rgba(255,255,255,0.08)'

  // Empty seat -- show "Sit Down" and "Invite Friend"
  if (isEmpty) {
    return (
      <div className="flex flex-col items-center gap-1 w-[68px]">
        <motion.div
          className="w-10 h-10 rounded-full flex items-center justify-center cursor-pointer transition-colors"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '2px dashed rgba(255,255,255,0.12)',
          }}
          whileHover={{ scale: 1.1, borderColor: 'rgba(201,168,76,0.4)' }}
          whileTap={{ scale: 0.9 }}
          onClick={onSitDown}
        >
          <span className="text-sm opacity-40">+</span>
        </motion.div>
        <motion.button
          onClick={onSitDown}
          className="text-[8px] font-bold tracking-wider px-2 py-1 rounded-md w-full"
          style={{ background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.5)' }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          SIT
        </motion.button>
        {showInviteOption && onInvite && (
          <motion.button
            onClick={(e) => { e.stopPropagation(); onInvite(); }}
            className="text-[8px] font-bold tracking-wider px-2 py-1 rounded-md w-full"
            style={{
              background: 'linear-gradient(135deg, rgba(100,100,255,0.15), rgba(150,100,255,0.1))',
              color: 'rgba(130,160,255,1)',
              border: '1px solid rgba(100,100,255,0.25)',
            }}
            whileHover={{ scale: 1.05, boxShadow: '0 0 8px rgba(100,100,255,0.2)' }}
            whileTap={{ scale: 0.95 }}
          >
            INVITE
          </motion.button>
        )}
      </div>
    )
  }

  return (
    <motion.div
      className="flex flex-col items-center gap-1 relative w-[68px]"
      animate={{ scale: isCurrent ? 1.08 : 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Turn timer ring */}
      {isCurrent && turnTimeLeft !== undefined && (
        <svg className="absolute -inset-1 w-[calc(100%+8px)] h-[calc(100%+8px)]" viewBox="0 0 100 100">
          <circle
            cx="50" cy="20" r="18"
            fill="none"
            stroke={turnTimeLeft <= 5 ? '#e74c3c' : turnTimeLeft <= 15 ? '#f39c12' : '#27ae60'}
            strokeWidth="2"
            strokeDasharray={`${(turnTimeLeft / 30) * 113} 113`}
            strokeLinecap="round"
            transform="rotate(-90 50 20)"
            opacity={0.6}
          />
        </svg>
      )}

      {/* Outcome badge */}
      {isSettled && seat.outcome && (
        <OutcomeBadge outcome={seat.outcome} payout={seat.payout} />
      )}

      {/* Avatar */}
      <div
        className="w-10 h-10 rounded-full overflow-hidden flex items-center justify-center relative"
        style={{
          border: `2px solid ${borderColor}`,
          boxShadow: isCurrent ? `0 0 12px ${borderColor}` : 'none',
        }}
      >
        {seat.avatar_url ? (
          <img
            src={seat.avatar_url}
            alt={seat.display_name || 'Player'}
            className="w-full h-full object-cover"
            referrerPolicy="no-referrer"
          />
        ) : (
          <div
            className="w-full h-full flex items-center justify-center text-sm font-bold"
            style={{
              background: isBotSeat
                ? `hsl(${(seat.seat_index * 72 + 120) % 360}, 40%, 25%)`
                : `hsl(${(seat.seat_index * 72) % 360}, 50%, 30%)`,
            }}
          >
            {(seat.display_name || 'P')[0].toUpperCase()}
          </div>
        )}

        {/* Bot indicator */}
        {isBotSeat && (
          <div className="absolute -bottom-0.5 right--0.5 w-3 h-3 rounded-full flex items-center justify-center"
            style={{ background: 'rgba(100,100,100,0.8)', fontSize: 6 }}>
            AI
          </div>
        )}

        {/* VIP crown */}
        {seat.is_vip && (
          <div className="absolute -top-1 left-1/2 -translate-x-1/2 text-[10px]">
            <span style={{ filter: 'drop-shadow(0 0 3px rgba(201,168,76,0.5))' }}>&#9813;</span>
          </div>
        )}
      </div>

      {/* Name + chips */}
      <div className="text-center">
        <p className="text-[10px] font-medium truncate max-w-[80px]" style={{
          color: isMe ? 'rgba(100,150,255,1)' : 'rgba(255,255,255,0.7)',
        }}>
          {isMe ? 'YOU' : isBotSeat ? `${seat.display_name}` : seat.display_name || 'Player'}
        </p>
        <p className="text-[9px] font-mono" style={{ color: 'rgba(201,168,76,0.6)' }}>
          {seat.chips.toLocaleString()} GC
        </p>
      </div>

      {/* Cards */}
      {hasCards && (
        <div className="flex items-center mt-0.5">
          {(seat.cards as Card[]).map((card, i) => (
            <MiniCard key={i} card={card} index={i} />
          ))}
        </div>
      )}

      {/* Hand total */}
      {hasCards && seat.hand_total > 0 && (
        <div
          className="px-2 py-0.5 rounded-full text-[10px] font-bold"
          style={{
            background: seat.status === 'busted' ? 'rgba(231,76,60,0.2)' : 'rgba(255,255,255,0.08)',
            color: seat.status === 'busted' ? '#e74c3c' : '#fff',
          }}
        >
          {seat.hand_total}
        </div>
      )}

      {/* Bet */}
      {seat.bet > 0 && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="flex items-center gap-1 px-2 py-0.5 rounded-full"
          style={{ background: 'rgba(201,168,76,0.15)', border: '1px solid rgba(201,168,76,0.2)' }}
        >
          <span className="text-[9px]" style={{ color: 'var(--gold, #c9a84c)' }}>
            {seat.bet.toLocaleString()}
          </span>
        </motion.div>
      )}

      {/* Status indicator */}
      {!isSettled && seat.status !== 'empty' && seat.status !== 'waiting' && (
        <span className="text-[8px] uppercase tracking-widest opacity-40">
          {seat.status === 'acting' && isCurrent ? 'THINKING...' :
           seat.status === 'standing' ? 'STAND' :
           seat.status === 'betting' ? 'BET PLACED' :
           seat.status}
        </span>
      )}

      {/* Turn timer text */}
      {isCurrent && isMe && turnTimeLeft !== undefined && (
        <span
          className="text-[10px] font-mono font-bold"
          style={{ color: turnTimeLeft <= 5 ? '#e74c3c' : turnTimeLeft <= 15 ? '#f39c12' : '#27ae60' }}
        >
          {turnTimeLeft}s
        </span>
      )}
    </motion.div>
  )
}
