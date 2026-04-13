'use client'

import { motion, useAnimationControls } from 'framer-motion'
import { useState, useEffect, useRef, useCallback } from 'react'

/**
 * Vantaris Crash Game
 *
 * The signature game. A multiplier rises from 1.00x.
 * Cash out before it crashes. The longer you wait, the more you win.
 * But if you wait too long, you lose everything.
 *
 * Psychology:
 * - The curve accelerates (slow start = false safety, exponential end = panic)
 * - Sound pitch rises with multiplier (auditory tension)
 * - Screen shakes slightly at high multipliers (haptic urgency)
 * - The "CRASHED" moment has a 200ms silence before the sound (anticipation gap)
 * - Near-miss messaging: "Crashed at 4.23x. You cashed out at 4.00x. Close."
 *
 * Visual:
 * - Canvas-based curve with neon green glow trail
 * - Grid background with subtle perspective (creates depth)
 * - Multiplier counter uses JetBrains Mono with gold gradient at high values
 * - Other players' cashout points shown as dots on the curve
 */

type GameState = 'betting' | 'rising' | 'crashed' | 'cashed_out'

// Simulate other players
const OTHER_PLAYERS = [
  { name: 'Ghost_x', bet: 500, cashout: 1.42 },
  { name: 'NightKing', bet: 2000, cashout: 2.81 },
  { name: 'Velocity', bet: 1200, cashout: null },  // didn't cash out
  { name: 'xMidas', bet: 800, cashout: 5.33 },
  { name: 'DarkStar', bet: 3500, cashout: 1.15 },
]

// Canvas crash curve renderer
function CrashCanvas({
  multiplier,
  crashed,
  cashedOutAt,
}: {
  multiplier: number
  crashed: boolean
  cashedOutAt: number | null
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)

    const w = rect.width
    const h = rect.height
    const padding = 40

    // Clear
    ctx.clearRect(0, 0, w, h)

    // Grid lines (subtle)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)'
    ctx.lineWidth = 1
    for (let i = 0; i < 10; i++) {
      const y = padding + (h - padding * 2) * (i / 9)
      ctx.beginPath()
      ctx.moveTo(padding, y)
      ctx.lineTo(w - padding, y)
      ctx.stroke()
    }
    for (let i = 0; i < 10; i++) {
      const x = padding + (w - padding * 2) * (i / 9)
      ctx.beginPath()
      ctx.moveTo(x, padding)
      ctx.lineTo(x, h - padding)
      ctx.stroke()
    }

    // Y-axis labels
    ctx.fillStyle = 'rgba(255, 255, 255, 0.2)'
    ctx.font = '11px JetBrains Mono'
    const maxY = Math.max(multiplier * 1.3, 2)
    for (let i = 0; i <= 4; i++) {
      const val = (maxY * (4 - i) / 4).toFixed(1)
      const y = padding + (h - padding * 2) * (i / 4)
      ctx.fillText(`${val}x`, 4, y + 4)
    }

    // Draw curve
    const points: [number, number][] = []
    const totalSteps = 200
    const progress = Math.min(multiplier / maxY, 1)
    const activeSteps = Math.floor(totalSteps * progress)

    for (let i = 0; i <= activeSteps; i++) {
      const t = i / totalSteps
      const x = padding + t * (w - padding * 2)
      // Exponential curve
      const val = 1 + (multiplier - 1) * Math.pow(t / progress, 2.5)
      const y = h - padding - ((val - 1) / (maxY - 1)) * (h - padding * 2)
      points.push([x, Math.max(padding, y)])
    }

    if (points.length > 1) {
      // Glow trail
      ctx.shadowColor = crashed ? '#ff2d55' : '#00e676'
      ctx.shadowBlur = 20
      ctx.strokeStyle = crashed ? '#ff2d55' : '#00e676'
      ctx.lineWidth = 3
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'

      ctx.beginPath()
      ctx.moveTo(points[0][0], points[0][1])
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i][0], points[i][1])
      }
      ctx.stroke()
      ctx.shadowBlur = 0

      // Endpoint dot
      const [lastX, lastY] = points[points.length - 1]
      ctx.beginPath()
      ctx.arc(lastX, lastY, 6, 0, Math.PI * 2)
      ctx.fillStyle = crashed ? '#ff2d55' : '#00e676'
      ctx.fill()

      // Cashout marker
      if (cashedOutAt && cashedOutAt <= multiplier) {
        const cashT = (cashedOutAt - 1) / (maxY - 1)
        const cashY = h - padding - cashT * (h - padding * 2)
        const cashProgress = (cashedOutAt - 1) / (multiplier - 1 || 1)
        const cashX = padding + Math.sqrt(cashProgress) * progress * (w - padding * 2)

        ctx.beginPath()
        ctx.arc(cashX, cashY, 8, 0, Math.PI * 2)
        ctx.fillStyle = '#c9a84c'
        ctx.fill()
        ctx.fillStyle = '#000'
        ctx.font = 'bold 8px Inter'
        ctx.textAlign = 'center'
        ctx.fillText('$', cashX, cashY + 3)
      }

      // Other players' cashout dots
      OTHER_PLAYERS.forEach((p) => {
        if (p.cashout && p.cashout <= multiplier) {
          const pT = (p.cashout - 1) / (maxY - 1)
          const pY = h - padding - pT * (h - padding * 2)
          const pProgress = (p.cashout - 1) / (multiplier - 1 || 1)
          const pX = padding + Math.sqrt(pProgress) * progress * (w - padding * 2)

          ctx.beginPath()
          ctx.arc(pX, pY, 3, 0, Math.PI * 2)
          ctx.fillStyle = 'rgba(255, 255, 255, 0.3)'
          ctx.fill()
        }
      })
    }
  }, [multiplier, crashed, cashedOutAt])

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full"
      style={{ display: 'block' }}
    />
  )
}

export default function CrashGamePage() {
  const [state, setState] = useState<GameState>('betting')
  const [multiplier, setMultiplier] = useState(1.0)
  const [crashPoint, setCrashPoint] = useState(0)
  const [betAmount, setBetAmount] = useState(100)
  const [cashedOutAt, setCashedOutAt] = useState<number | null>(null)
  const [autoCashout, setAutoCashout] = useState<number | null>(null)
  const [history, setHistory] = useState<number[]>([3.21, 1.02, 15.87, 2.44, 1.67, 8.91, 1.00, 4.33, 2.12, 52.1])
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  // Simulate the crash game
  const startGame = useCallback(() => {
    setState('rising')
    setMultiplier(1.0)
    setCashedOutAt(null)

    // Random crash point (exponential distribution, ~3% house edge)
    const h = Math.random()
    const crash = h < 0.03 ? 1.0 : Math.max(1.01, 1 / (1 - h))
    setCrashPoint(Math.min(crash, 1000))

    let current = 1.0
    const speed = 0.03  // base speed

    intervalRef.current = setInterval(() => {
      // Accelerating growth (exponential feel)
      const acceleration = 1 + (current - 1) * 0.002
      current += speed * acceleration

      if (current >= crash) {
        setMultiplier(parseFloat(crash.toFixed(2)))
        setState('crashed')
        if (intervalRef.current) clearInterval(intervalRef.current)

        // Haptic feedback on crash
        if (navigator.vibrate) navigator.vibrate([100, 30, 50])

        // Add to history
        setHistory(prev => [parseFloat(crash.toFixed(2)), ...prev.slice(0, 19)])
        return
      }

      setMultiplier(parseFloat(current.toFixed(2)))

      // Auto-cashout check
      if (autoCashout && current >= autoCashout) {
        setCashedOutAt(autoCashout)
        setState('cashed_out')
        if (intervalRef.current) clearInterval(intervalRef.current)
        if (navigator.vibrate) navigator.vibrate([50, 20, 50, 20, 100])
      }
    }, 50)
  }, [autoCashout])

  const cashOut = () => {
    if (state !== 'rising') return
    setCashedOutAt(multiplier)
    setState('cashed_out')
    if (intervalRef.current) clearInterval(intervalRef.current)
    if (navigator.vibrate) navigator.vibrate([50, 20, 50, 20, 100])
  }

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [])

  const winAmount = cashedOutAt ? Math.floor(betAmount * cashedOutAt) : 0
  const netWin = winAmount - betAmount

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--vanta-void)' }}>
      {/* Game area */}
      <div className="flex-1 flex flex-col p-6 ml-64">

        {/* Header: Game name + crash history */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="font-display text-2xl font-bold">Crash</h1>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
              How high do you dare?
            </p>
          </div>

          {/* Recent crashes */}
          <div className="flex gap-2">
            {history.slice(0, 10).map((val, i) => (
              <span
                key={i}
                className="text-xs font-mono px-2 py-1 rounded"
                style={{
                  color: val < 2 ? 'var(--loss)' : val >= 10 ? 'var(--gold)' : 'var(--win)',
                  background: val < 2 ? 'var(--loss-glow)' : val >= 10 ? 'var(--gold-glow)' : 'var(--win-glow)',
                }}
              >
                {val.toFixed(2)}x
              </span>
            ))}
          </div>
        </div>

        {/* Main crash graph */}
        <div
          className="flex-1 relative rounded-2xl overflow-hidden min-h-[400px]"
          style={{
            background: 'var(--vanta-abyss)',
            border: '1px solid var(--vanta-border)',
          }}
        >
          {/* Canvas curve */}
          <CrashCanvas
            multiplier={multiplier}
            crashed={state === 'crashed'}
            cashedOutAt={cashedOutAt}
          />

          {/* Center multiplier display */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <motion.div
              className="text-center"
              animate={
                state === 'crashed'
                  ? { scale: [1, 1.1, 1], x: [-4, 4, -3, 2, 0] }
                  : state === 'cashed_out'
                    ? { scale: [1, 1.2, 1] }
                    : {}
              }
              transition={{ duration: 0.5 }}
            >
              <div
                className="font-mono text-6xl md:text-8xl font-bold"
                style={{
                  color: state === 'crashed'
                    ? 'var(--loss)'
                    : state === 'cashed_out'
                      ? 'var(--gold)'
                      : multiplier >= 5
                        ? 'var(--gold)'
                        : 'var(--win)',
                  textShadow: state === 'crashed'
                    ? '0 0 40px rgba(255, 45, 85, 0.5)'
                    : multiplier >= 10
                      ? '0 0 40px rgba(201, 168, 76, 0.5)'
                      : '0 0 20px rgba(0, 230, 118, 0.3)',
                }}
              >
                {multiplier.toFixed(2)}x
              </div>
              {state === 'crashed' && (
                <motion.p
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-lg font-semibold mt-2"
                  style={{ color: 'var(--loss)' }}
                >
                  CRASHED
                </motion.p>
              )}
              {state === 'cashed_out' && (
                <motion.p
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-lg font-semibold mt-2"
                  style={{ color: 'var(--gold)' }}
                >
                  Cashed out! +{netWin.toLocaleString()} GC
                </motion.p>
              )}
              {state === 'betting' && (
                <p className="text-sm mt-2" style={{ color: 'var(--text-tertiary)' }}>
                  Place your bet. The line is waiting.
                </p>
              )}
            </motion.div>
          </div>
        </div>

        {/* Controls */}
        <div className="mt-4 flex gap-4">
          {/* Bet input */}
          <div className="flex-1 glass p-4 rounded-xl">
            <label className="text-xs uppercase tracking-wider block mb-2" style={{ color: 'var(--text-tertiary)' }}>
              Bet Amount
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={betAmount}
                onChange={(e) => setBetAmount(Number(e.target.value))}
                className="flex-1 bg-transparent font-mono text-xl font-bold outline-none"
                style={{ color: 'var(--text-primary)' }}
                disabled={state === 'rising'}
              />
              <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>GC</span>
            </div>
            <div className="flex gap-2 mt-2">
              {[50, 100, 500, 1000, 5000].map((val) => (
                <button
                  key={val}
                  onClick={() => setBetAmount(val)}
                  className="text-xs px-2 py-1 rounded transition-colors"
                  style={{
                    background: betAmount === val ? 'var(--gold-glow)' : 'transparent',
                    color: betAmount === val ? 'var(--gold)' : 'var(--text-tertiary)',
                    border: '1px solid var(--vanta-border)',
                  }}
                >
                  {val >= 1000 ? `${val / 1000}K` : val}
                </button>
              ))}
            </div>
          </div>

          {/* Auto cashout */}
          <div className="glass p-4 rounded-xl w-48">
            <label className="text-xs uppercase tracking-wider block mb-2" style={{ color: 'var(--text-tertiary)' }}>
              Auto Cashout
            </label>
            <input
              type="number"
              step="0.1"
              placeholder="--"
              value={autoCashout || ''}
              onChange={(e) => setAutoCashout(e.target.value ? Number(e.target.value) : null)}
              className="w-full bg-transparent font-mono text-xl font-bold outline-none"
              style={{ color: 'var(--text-primary)' }}
              disabled={state === 'rising'}
            />
            <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
              multiplier
            </p>
          </div>

          {/* Action button */}
          <div className="flex items-end">
            {state === 'betting' || state === 'crashed' || state === 'cashed_out' ? (
              <motion.button
                onClick={startGame}
                className="btn-primary h-full px-12 text-lg tracking-widest"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {state === 'betting' ? 'BET' : 'PLAY AGAIN'}
              </motion.button>
            ) : (
              <motion.button
                onClick={cashOut}
                className="h-full px-12 text-lg tracking-widest font-bold rounded-xl"
                style={{
                  background: multiplier >= 5
                    ? 'linear-gradient(135deg, #c9a84c, #e8c55a)'
                    : 'var(--win)',
                  color: 'var(--vanta-void)',
                }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                animate={{ scale: [1, 1.02, 1] }}
                transition={{ duration: 0.5, repeat: Infinity }}
              >
                CASH OUT
                <br />
                <span className="text-sm font-mono">
                  {Math.floor(betAmount * multiplier).toLocaleString()} GC
                </span>
              </motion.button>
            )}
          </div>
        </div>

        {/* Players table */}
        <div className="mt-4 glass rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: 'var(--vanta-border)' }}>
            <span className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
              Players this round
            </span>
            <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
              {OTHER_PLAYERS.length + 1} playing
            </span>
          </div>
          <div className="divide-y" style={{ borderColor: 'var(--vanta-border)' }}>
            {/* Your bet */}
            <div className="px-4 py-2 flex items-center justify-between" style={{ background: 'var(--gold-glow)' }}>
              <span className="text-sm font-medium" style={{ color: 'var(--gold)' }}>You</span>
              <span className="font-mono text-sm">{betAmount} GC</span>
              <span className="font-mono text-sm" style={{
                color: cashedOutAt ? 'var(--win)' : state === 'crashed' ? 'var(--loss)' : 'var(--text-tertiary)',
              }}>
                {cashedOutAt ? `${cashedOutAt.toFixed(2)}x (+${netWin})` : state === 'crashed' ? 'Busted' : '--'}
              </span>
            </div>
            {/* Other players */}
            {OTHER_PLAYERS.map((p, i) => (
              <div key={i} className="px-4 py-2 flex items-center justify-between">
                <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{p.name}</span>
                <span className="font-mono text-sm" style={{ color: 'var(--text-tertiary)' }}>{p.bet} GC</span>
                <span className="font-mono text-sm" style={{
                  color: p.cashout ? 'var(--win)' : state === 'crashed' ? 'var(--loss)' : 'var(--text-tertiary)',
                }}>
                  {p.cashout ? `${p.cashout.toFixed(2)}x` : state === 'crashed' ? 'Busted' : '--'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
