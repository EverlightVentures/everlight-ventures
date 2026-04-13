'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { DealerAvatar } from './DealerAvatar'

/**
 * WelcomeScreen -- First-time visitor onboarding
 *
 * Shows once for new players (checked via localStorage).
 * Gives 1,000 GC starting chips, lets them pick a name and dealer.
 */

const DEALERS = [
  { id: 'aria', name: 'Aria Sinclair', title: 'Elegant. Composed. Classic Vegas.', color: '#c9a84c' },
  { id: 'marcus', name: 'Marcus Vega', title: 'Intense. Street-smart. No mercy.', color: '#ff6b35' },
  { id: 'kanisha', name: 'Kanisha Thompson', title: 'Warm. Confident. VIP energy.', color: '#e91e63' },
  { id: 'bacardi', name: 'Bacardi Ice', title: 'Cold. Calculated. Elite.', color: '#00bcd4' },
]

export function WelcomeScreen({ onComplete }: {
  onComplete: (name: string, dealerId: string) => void
}) {
  const [step, setStep] = useState(0)
  const [name, setName] = useState('')
  const [selectedDealer, setSelectedDealer] = useState('aria')

  const handleFinish = () => {
    const finalName = name.trim() || 'Player'
    localStorage.setItem('vantaris_welcomed', 'true')
    onComplete(finalName, selectedDealer)
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'radial-gradient(ellipse at center, #0d0815 0%, #000 100%)' }}
    >
      <div className="max-w-md w-full mx-4">
        {/* Step 0: Welcome */}
        {step === 0 && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            className="text-center">
            <motion.h1
              className="text-4xl md:text-5xl font-black tracking-widest mb-4"
              style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #c9a84c, #e8c55a)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}
              animate={{ opacity: [0.7, 1, 0.7] }}
              transition={{ duration: 3, repeat: Infinity }}
            >
              VANTARIS
            </motion.h1>
            <p className="text-xs tracking-widest mb-2" style={{ color: 'rgba(201,168,76,0.6)', letterSpacing: '3px', fontFamily: "'Cinzel', serif" }}>
              THE DARKEST STAR BURNS BRIGHTEST
            </p>
            <p className="text-sm mt-6 mb-8" style={{ color: 'rgba(255,255,255,0.5)' }}>
              Provably fair blackjack with AI dealers, custom card skins, and a presence system that rewards your loyalty.
            </p>

            <div className="glass p-4 rounded-xl mb-6 inline-block">
              <p className="text-xs mb-1" style={{ color: 'var(--text-tertiary)' }}>YOUR STARTING BALANCE</p>
              <p className="font-mono text-3xl font-bold" style={{ color: 'var(--gold)' }}>1,000 GC</p>
              <p className="text-[10px] mt-1" style={{ color: 'rgba(255,255,255,0.3)' }}>+ 10 Gems + 5.00 Sweeps Coins</p>
            </div>

            <div>
              <motion.button
                onClick={() => setStep(1)}
                className="px-12 py-3 text-sm tracking-widest font-bold rounded-xl"
                style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif", letterSpacing: '2px', boxShadow: '0 0 30px rgba(201,168,76,0.4)' }}
                whileHover={{ boxShadow: '0 0 45px rgba(201,168,76,0.7)', y: -2 }}
                whileTap={{ scale: 0.97 }}
              >
                ENTER THE CASINO
              </motion.button>
            </div>
          </motion.div>
        )}

        {/* Step 1: Name + Dealer */}
        {step === 1 && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            className="text-center">
            <h2 className="text-xl font-bold tracking-wider mb-6" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
              WHO SITS AT THE TABLE?
            </h2>

            {/* Name input */}
            <div className="mb-8">
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value.slice(0, 20))}
                placeholder="Enter your name..."
                className="w-full max-w-xs bg-transparent border-b-2 text-center text-lg py-2 outline-none placeholder:text-white/20"
                style={{ borderColor: 'rgba(201,168,76,0.4)', color: '#fff', fontFamily: "'Cinzel', serif" }}
                autoFocus
              />
              <p className="text-[10px] mt-2" style={{ color: 'var(--text-tertiary)' }}>
                {20 - name.length} characters remaining
              </p>
            </div>

            {/* Dealer selection */}
            <p className="text-xs tracking-widest mb-4" style={{ color: 'rgba(255,255,255,0.4)', letterSpacing: '2px', fontFamily: "'Cinzel', serif" }}>
              CHOOSE YOUR DEALER
            </p>
            <div className="grid grid-cols-2 gap-3 mb-8">
              {DEALERS.map(d => (
                <motion.div
                  key={d.id}
                  onClick={() => setSelectedDealer(d.id)}
                  className="glass p-3 rounded-xl cursor-pointer text-center"
                  style={{
                    border: selectedDealer === d.id ? `2px solid ${d.color}` : '2px solid transparent',
                    boxShadow: selectedDealer === d.id ? `0 0 20px ${d.color}30` : 'none',
                  }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="flex justify-center mb-2">
                    <DealerAvatar dealerId={d.id} color={d.color} speaking={false} size={48} />
                  </div>
                  <p className="text-xs font-semibold" style={{ color: d.color, fontFamily: "'Cinzel', serif" }}>{d.name}</p>
                  <p className="text-[9px] mt-0.5" style={{ color: 'var(--text-tertiary)' }}>{d.title}</p>
                </motion.div>
              ))}
            </div>

            <motion.button
              onClick={handleFinish}
              className="px-12 py-3 text-sm tracking-widest font-bold rounded-xl"
              style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif", letterSpacing: '2px', boxShadow: '0 0 30px rgba(201,168,76,0.4)' }}
              whileHover={{ boxShadow: '0 0 45px rgba(201,168,76,0.7)', y: -2 }}
              whileTap={{ scale: 0.97 }}
            >
              DEAL ME IN
            </motion.button>
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}

// NOTE: Do NOT call this during render/SSR. Use in useEffect only.
export function isNewPlayer(): boolean {
  try {
    return !localStorage.getItem('vantaris_welcomed')
  } catch { return false }
}
