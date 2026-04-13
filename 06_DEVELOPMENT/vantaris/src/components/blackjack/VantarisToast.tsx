'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

/**
 * VantarisToast -- Luxury casino notification system
 *
 * Slide-in toasts from top-right with gold/green/red/blue variants.
 * Auto-dismiss with progress bar. Stacks up to 5 visible.
 * Used for: achievements, rank-ups, low chips, deck reshuffle,
 * purchase confirmations, dealer mood shifts, XP gains.
 */

// ============================================================
// TYPES
// ============================================================

export type ToastType = 'achievement' | 'win' | 'loss' | 'info' | 'warning' | 'xp' | 'rank' | 'dealer'

interface Toast {
  id: string
  type: ToastType
  title: string
  message?: string
  icon?: string
  reward?: number
  duration: number
  createdAt: number
}

// ============================================================
// TOAST STORE (global singleton)
// ============================================================

type ToastListener = (toasts: Toast[]) => void

let toasts: Toast[] = []
let listeners: ToastListener[] = []
let nextId = 0

function notify() {
  listeners.forEach(fn => fn([...toasts]))
}

export function toast(opts: {
  type?: ToastType
  title: string
  message?: string
  icon?: string
  reward?: number
  duration?: number
}) {
  const t: Toast = {
    id: `toast-${nextId++}`,
    type: opts.type || 'info',
    title: opts.title,
    message: opts.message,
    icon: opts.icon,
    reward: opts.reward,
    duration: opts.duration || 4000,
    createdAt: Date.now(),
  }
  toasts = [...toasts, t].slice(-5) // max 5 visible
  notify()

  // Auto-dismiss
  setTimeout(() => {
    toasts = toasts.filter(x => x.id !== t.id)
    notify()
  }, t.duration)

  return t.id
}

// Convenience helpers
export const toastAchievement = (title: string, message: string, reward?: number) =>
  toast({ type: 'achievement', title, message, icon: '\uD83C\uDFC6', reward, duration: 5000 })

export const toastWin = (title: string, message?: string) =>
  toast({ type: 'win', title, message, icon: '\u2728', duration: 3000 })

export const toastLoss = (title: string, message?: string) =>
  toast({ type: 'loss', title, message, icon: '\uD83D\uDCA8', duration: 3000 })

export const toastInfo = (title: string, message?: string) =>
  toast({ type: 'info', title, message, icon: '\u2139\uFE0F', duration: 3500 })

export const toastWarning = (title: string, message?: string) =>
  toast({ type: 'warning', title, message, icon: '\u26A0\uFE0F', duration: 4000 })

export const toastXP = (amount: number) =>
  toast({ type: 'xp', title: `+${amount} XP`, icon: '\u2B50', duration: 2500 })

export const toastRankUp = (rank: string) =>
  toast({ type: 'rank', title: 'RANK UP', message: `You've reached ${rank}!`, icon: '\uD83D\uDC51', duration: 6000 })

export const toastDealer = (dealerName: string, message: string) =>
  toast({ type: 'dealer', title: dealerName, message, duration: 3000 })

// ============================================================
// TOAST STYLES
// ============================================================

const TOAST_STYLES: Record<ToastType, { bg: string; border: string; glow: string; titleColor: string }> = {
  achievement: {
    bg: 'rgba(201,168,76,0.12)',
    border: 'rgba(201,168,76,0.5)',
    glow: '0 0 20px rgba(201,168,76,0.2)',
    titleColor: '#c9a84c',
  },
  win: {
    bg: 'rgba(0,230,118,0.08)',
    border: 'rgba(0,230,118,0.4)',
    glow: '0 0 15px rgba(0,230,118,0.15)',
    titleColor: '#00e676',
  },
  loss: {
    bg: 'rgba(255,45,85,0.08)',
    border: 'rgba(255,45,85,0.3)',
    glow: '0 0 10px rgba(255,45,85,0.1)',
    titleColor: '#ff2d55',
  },
  info: {
    bg: 'rgba(88,166,255,0.08)',
    border: 'rgba(88,166,255,0.3)',
    glow: '0 0 10px rgba(88,166,255,0.1)',
    titleColor: '#58a6ff',
  },
  warning: {
    bg: 'rgba(255,179,0,0.1)',
    border: 'rgba(255,179,0,0.4)',
    glow: '0 0 12px rgba(255,179,0,0.15)',
    titleColor: '#ffb300',
  },
  xp: {
    bg: 'rgba(201,168,76,0.1)',
    border: 'rgba(201,168,76,0.35)',
    glow: '0 0 10px rgba(201,168,76,0.12)',
    titleColor: '#e8c55a',
  },
  rank: {
    bg: 'rgba(201,168,76,0.15)',
    border: 'rgba(201,168,76,0.6)',
    glow: '0 0 25px rgba(201,168,76,0.3)',
    titleColor: '#c9a84c',
  },
  dealer: {
    bg: 'rgba(255,255,255,0.06)',
    border: 'rgba(255,255,255,0.15)',
    glow: 'none',
    titleColor: 'rgba(255,255,255,0.7)',
  },
}

// ============================================================
// TOAST COMPONENT
// ============================================================

function ToastItem({ t, onDismiss }: { t: Toast; onDismiss: () => void }) {
  const style = TOAST_STYLES[t.type]
  const elapsed = Date.now() - t.createdAt
  const remaining = Math.max(0, t.duration - elapsed)

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 80, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 60, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 350, damping: 28 }}
      onClick={onDismiss}
      className="relative cursor-pointer overflow-hidden rounded-xl px-4 py-3 backdrop-blur-md max-w-[300px]"
      style={{
        background: style.bg,
        border: `1px solid ${style.border}`,
        boxShadow: style.glow,
      }}
    >
      <div className="flex items-start gap-3">
        {t.icon && (
          <span className="text-lg flex-shrink-0 mt-0.5">{t.icon}</span>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold tracking-wider" style={{
            color: style.titleColor,
            fontFamily: "'Cinzel', serif",
            letterSpacing: '1px',
          }}>
            {t.title}
          </p>
          {t.message && (
            <p className="text-[10px] mt-0.5 leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)' }}>
              {t.message}
            </p>
          )}
          {t.reward && t.reward > 0 && (
            <p className="text-[10px] font-mono font-bold mt-1" style={{ color: '#c9a84c' }}>
              +{t.reward.toLocaleString()} GC
            </p>
          )}
        </div>
      </div>

      {/* Progress bar (auto-dismiss timer) */}
      <motion.div
        className="absolute bottom-0 left-0 h-[2px]"
        style={{ background: style.border }}
        initial={{ width: '100%' }}
        animate={{ width: '0%' }}
        transition={{ duration: remaining / 1000, ease: 'linear' }}
      />
    </motion.div>
  )
}

// ============================================================
// TOAST CONTAINER (mount once in layout)
// ============================================================

export function ToastContainer() {
  const [visible, setVisible] = useState<Toast[]>([])

  useEffect(() => {
    const listener = (t: Toast[]) => setVisible(t)
    listeners.push(listener)
    return () => { listeners = listeners.filter(l => l !== listener) }
  }, [])

  const dismiss = useCallback((id: string) => {
    toasts = toasts.filter(t => t.id !== id)
    notify()
  }, [])

  return (
    <div className="fixed top-[70px] right-4 z-50 flex flex-col gap-2 pointer-events-auto">
      <AnimatePresence mode="popLayout">
        {visible.map(t => (
          <ToastItem key={t.id} t={t} onDismiss={() => dismiss(t.id)} />
        ))}
      </AnimatePresence>
    </div>
  )
}
