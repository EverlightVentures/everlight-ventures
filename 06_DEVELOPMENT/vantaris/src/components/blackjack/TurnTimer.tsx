'use client'

import { motion } from 'framer-motion'

/**
 * TurnTimer -- Visual countdown for the current player's turn.
 *
 * Shows a circular progress ring + seconds remaining.
 * Colors: green (30-16s), yellow (15-6s), red (5-0s).
 * At 0s the multiplayer store auto-stands.
 */

interface TurnTimerProps {
  timeLeft: number
  maxTime?: number
  isMyTurn: boolean
}

export default function TurnTimer({ timeLeft, maxTime = 30, isMyTurn }: TurnTimerProps) {
  const pct = timeLeft / maxTime
  const circumference = 2 * Math.PI * 40 // radius 40

  const color = timeLeft <= 5 ? '#e74c3c' : timeLeft <= 15 ? '#f39c12' : '#27ae60'

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      className="relative flex items-center justify-center"
      style={{ width: 64, height: 64 }}
    >
      {/* Background ring */}
      <svg className="absolute inset-0" viewBox="0 0 100 100">
        <circle
          cx="50" cy="50" r="40"
          fill="none"
          stroke="rgba(255,255,255,0.05)"
          strokeWidth="4"
        />
        <circle
          cx="50" cy="50" r="40"
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeDasharray={`${pct * circumference} ${circumference}`}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          style={{ transition: 'stroke-dasharray 0.3s ease, stroke 0.3s ease' }}
        />
      </svg>

      {/* Time text */}
      <motion.span
        className="text-lg font-mono font-bold z-10"
        style={{ color }}
        animate={timeLeft <= 5 ? { scale: [1, 1.2, 1] } : {}}
        transition={{ duration: 0.5, repeat: timeLeft <= 5 ? Infinity : 0 }}
      >
        {timeLeft}
      </motion.span>

      {/* "Your turn" label */}
      {isMyTurn && (
        <motion.span
          className="absolute -bottom-5 text-[9px] uppercase tracking-widest font-bold whitespace-nowrap"
          style={{ color }}
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          YOUR TURN
        </motion.span>
      )}
    </motion.div>
  )
}
