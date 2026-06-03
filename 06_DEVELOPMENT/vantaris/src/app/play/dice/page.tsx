'use client'

import { motion } from 'framer-motion'
import { useState, useEffect, useRef, useCallback } from 'react'
import {
  rollDice,
  diceWinChance,
  diceMultiplier,
  diceIsWin,
  loadChips,
  persistRound,
  type ChipState,
} from '@/lib/casino-engine'

/**
 * Vantaris Dice
 *
 * Pick a target (1-98) and bet the roll lands OVER or UNDER it.
 * Lower win-chance pays more. The first Vantaris game that BANKS to
 * Supabase (casino_players.gold_coins + casino_game_rounds via
 * casino-engine.persistRound), so the leaderboard finally has real data.
 * Guests play on a local-chip fallback.
 *
 * Matches /play/crash: vanta tokens, Cinzel header, glass panels, GC
 * currency, vibrate haptics, recent-roll history strip.
 */

const CHIP_PRESETS = [50, 100, 500, 1000, 5000]
const SUSPENSE_MS = 600
const MIN_TARGET = 1
const MAX_TARGET = 98

export default function DiceGamePage() {
  const [chips, setChips] = useState<ChipState>({ balance: 1000, playerId: null, authed: false })
  const [bet, setBet] = useState(100)
  const [target, setTarget] = useState(50)
  const [direction, setDirection] = useState<'over' | 'under'>('over')
  const [roll, setRoll] = useState<number | null>(null)
  const [rolling, setRolling] = useState(false)
  const [lastWin, setLastWin] = useState<boolean | null>(null)
  const [history, setHistory] = useState<{ value: number; win: boolean }[]>([])
  const flick = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    loadChips().then(setChips).catch(() => {})
    return () => { if (flick.current) clearInterval(flick.current) }
  }, [])

  const winChance = diceWinChance(target, direction)
  const multiplier = diceMultiplier(target, direction)
  const payout = Math.floor(bet * multiplier)
  const profitOnWin = payout - bet
  const canRoll = !rolling && bet > 0 && bet <= chips.balance

  const doRoll = useCallback(() => {
    if (rolling || bet <= 0 || bet > chips.balance) return
    setRolling(true)
    setLastWin(null)

    // Suspense: flicker random faces, then settle on the real roll.
    flick.current = setInterval(() => {
      setRoll(Math.floor(Math.random() * 10000) / 100)
    }, 45)

    window.setTimeout(() => {
      if (flick.current) clearInterval(flick.current)

      const result = rollDice()
      const win = diceIsWin(result, target, direction)
      const returned = win ? payout : 0
      const newBalance = chips.balance - bet + returned

      setRoll(result)
      setLastWin(win)
      setRolling(false)
      setChips((prev) => ({ ...prev, balance: newBalance }))
      setHistory((prev) => [{ value: result, win }, ...prev.slice(0, 11)])

      if (navigator.vibrate) navigator.vibrate(win ? [40, 20, 60] : [120])

      void persistRound({
        state: chips,
        game: 'dice',
        bet,
        win: returned,
        multiplier,
        gameData: { target, direction, roll: result, win },
        newBalance,
      })
    }, SUSPENSE_MS)
  }, [rolling, bet, chips, target, direction, payout, multiplier])

  // Win region for the visual bar (percent positions).
  const winFrom = direction === 'over' ? target : 0
  const winTo = direction === 'over' ? 100 : target

  return (
    <div className="min-h-screen flex flex-col p-4 md:p-6" style={{ background: 'var(--vanta-void)' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <a href="/lobby" className="text-sm" style={{ color: 'var(--text-tertiary)' }}>{'←'}</a>
          <h1 className="font-display text-2xl font-bold tracking-widest" style={{
            fontFamily: "'Cinzel', serif",
            background: 'linear-gradient(135deg, #c9a84c, #e8c55a)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>DICE</h1>
          <p className="text-xs hidden sm:block" style={{ color: 'var(--text-tertiary)' }}>
            Over or under. Lower odds, bigger pay.
          </p>
        </div>

        {/* Balance */}
        <div className="text-right">
          <div className="font-mono text-lg font-bold" style={{ color: 'var(--gold)' }}>
            {Math.floor(chips.balance).toLocaleString()} <span className="text-xs">GC</span>
          </div>
          <div className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
            {chips.authed ? 'banked' : 'guest · sign in to save'}
          </div>
        </div>
      </div>

      {/* Recent rolls */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {history.slice(0, 12).map((h, i) => (
          <span key={i} className="text-xs font-mono px-2 py-1 rounded" style={{
            color: h.win ? 'var(--win)' : 'var(--loss)',
            background: h.win ? 'var(--win-glow)' : 'var(--loss-glow)',
          }}>
            {h.value.toFixed(2)}
          </span>
        ))}
      </div>

      {/* Roll display + win-region bar */}
      <div className="flex-1 relative rounded-2xl overflow-hidden min-h-[340px] flex flex-col items-center justify-center p-6"
        style={{ background: 'var(--vanta-abyss)', border: '1px solid var(--vanta-border)' }}>

        <motion.div
          className="text-center mb-10"
          animate={lastWin === false ? { x: [-5, 5, -4, 3, 0] } : lastWin ? { scale: [1, 1.18, 1] } : {}}
          transition={{ duration: 0.5 }}
        >
          <div className="font-mono text-7xl md:text-8xl font-bold" style={{
            color: lastWin === null ? 'var(--text-primary)' : lastWin ? 'var(--gold)' : 'var(--loss)',
            textShadow: lastWin ? '0 0 40px rgba(201,168,76,0.5)' : lastWin === false ? '0 0 40px rgba(255,45,85,0.4)' : 'none',
          }}>
            {roll === null ? '0.00' : roll.toFixed(2)}
          </div>
          {lastWin !== null && !rolling && (
            <motion.p initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              className="text-lg font-semibold mt-2"
              style={{ color: lastWin ? 'var(--gold)' : 'var(--loss)' }}>
              {lastWin ? `+${profitOnWin.toLocaleString()} GC` : 'Bust'}
            </motion.p>
          )}
          {lastWin === null && !rolling && (
            <p className="text-sm mt-2" style={{ color: 'var(--text-tertiary)' }}>Set your roll. Then send it.</p>
          )}
        </motion.div>

        {/* Win-region bar */}
        <div className="w-full max-w-xl">
          <div className="relative h-3 rounded-full" style={{ background: 'var(--vanta-border)' }}>
            {/* win region */}
            <div className="absolute top-0 h-3 rounded-full" style={{
              left: `${winFrom}%`, width: `${winTo - winFrom}%`,
              background: 'linear-gradient(90deg, rgba(0,230,118,0.5), rgba(0,230,118,0.85))',
            }} />
            {/* roll marker */}
            {roll !== null && (
              <motion.div className="absolute -top-1.5 w-1.5 h-6 rounded-full"
                style={{ left: `calc(${roll}% - 3px)`, background: lastWin ? 'var(--gold)' : '#fff' }}
                animate={{ left: `calc(${roll}% - 3px)` }} transition={{ type: 'spring', stiffness: 200, damping: 20 }} />
            )}
          </div>
          <div className="flex justify-between mt-2 text-[10px] font-mono" style={{ color: 'var(--text-tertiary)' }}>
            <span>0</span><span>25</span><span>50</span><span>75</span><span>100</span>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="mt-4 flex flex-col lg:flex-row gap-4">
        {/* Bet */}
        <div className="flex-1 glass p-4 rounded-xl">
          <label className="text-xs uppercase tracking-wider block mb-2" style={{ color: 'var(--text-tertiary)' }}>Bet Amount</label>
          <div className="flex items-center gap-2">
            <input type="number" value={bet} min={1} max={Math.floor(chips.balance)} disabled={rolling}
              onChange={(e) => setBet(Math.max(0, Number(e.target.value)))}
              className="flex-1 bg-transparent font-mono text-xl font-bold outline-none" style={{ color: 'var(--text-primary)' }} />
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>GC</span>
          </div>
          <div className="flex gap-2 mt-2 flex-wrap">
            {CHIP_PRESETS.map((v) => (
              <button key={v} onClick={() => setBet(v)} disabled={rolling}
                className="text-xs px-2 py-1 rounded transition-colors"
                style={{
                  background: bet === v ? 'var(--gold-glow)' : 'transparent',
                  color: bet === v ? 'var(--gold)' : 'var(--text-tertiary)',
                  border: '1px solid var(--vanta-border)',
                }}>
                {v >= 1000 ? `${v / 1000}K` : v}
              </button>
            ))}
            <button onClick={() => setBet(Math.floor(chips.balance / 2))} disabled={rolling}
              className="text-xs px-2 py-1 rounded" style={{ color: 'var(--text-tertiary)', border: '1px solid var(--vanta-border)' }}>
              {'½'}
            </button>
            <button onClick={() => setBet(Math.floor(chips.balance))} disabled={rolling}
              className="text-xs px-2 py-1 rounded" style={{ color: 'var(--text-tertiary)', border: '1px solid var(--vanta-border)' }}>
              MAX
            </button>
          </div>
        </div>

        {/* Target + direction */}
        <div className="flex-1 glass p-4 rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
              Roll {direction === 'over' ? 'Over' : 'Under'} {target}
            </label>
            <button onClick={() => setDirection((d) => (d === 'over' ? 'under' : 'over'))} disabled={rolling}
              className="text-xs px-3 py-1 rounded font-bold tracking-wider"
              style={{ background: 'var(--gold-glow)', color: 'var(--gold)', border: '1px solid var(--vanta-border)' }}>
              {direction === 'over' ? 'OVER' : 'UNDER'}
            </button>
          </div>
          <input type="range" min={MIN_TARGET} max={MAX_TARGET} step={1} value={target} disabled={rolling}
            onChange={(e) => setTarget(Number(e.target.value))}
            className="w-full accent-[#c9a84c]" />
          <div className="grid grid-cols-3 gap-2 mt-3 text-center">
            <div>
              <div className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Win Chance</div>
              <div className="font-mono text-sm font-bold" style={{ color: 'var(--text-primary)' }}>{winChance.toFixed(2)}%</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Payout</div>
              <div className="font-mono text-sm font-bold" style={{ color: 'var(--gold)' }}>{multiplier.toFixed(2)}x</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Profit</div>
              <div className="font-mono text-sm font-bold" style={{ color: 'var(--win)' }}>+{profitOnWin.toLocaleString()}</div>
            </div>
          </div>
        </div>

        {/* Roll button */}
        <div className="flex items-stretch">
          <motion.button onClick={doRoll} disabled={!canRoll}
            className="btn-primary px-12 text-lg tracking-widest w-full lg:w-auto"
            style={{ opacity: canRoll ? 1 : 0.45 }}
            whileHover={canRoll ? { scale: 1.02 } : {}} whileTap={canRoll ? { scale: 0.98 } : {}}>
            {rolling ? '...' : bet > chips.balance ? 'LOW BALANCE' : 'ROLL'}
          </motion.button>
        </div>
      </div>
    </div>
  )
}
