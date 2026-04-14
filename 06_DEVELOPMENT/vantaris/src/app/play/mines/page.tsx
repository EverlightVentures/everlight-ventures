'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'

export default function GamePage() {
  const gameName = typeof window !== 'undefined' ? window.location.pathname.split('/').pop() || 'Game' : 'Game'
  
  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--vanta-void)' }}>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center max-w-md px-6">
        <h1 className="text-3xl font-bold tracking-widest mb-4" style={{
          fontFamily: "'Cinzel', serif",
          background: 'linear-gradient(135deg, #c9a84c, #e8c55a)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        }}>
          {gameName.toUpperCase()}
        </h1>
        <div className="glass p-8 rounded-2xl mb-6">
          <p className="text-4xl mb-4">{gameName === 'roulette' ? '\u25CF' : gameName === 'dice' ? '\u2684' : gameName === 'plinko' ? '\u25BD' : '\u2B23'}</p>
          <p className="text-sm mb-2" style={{ color: 'var(--text-secondary)' }}>Coming Soon</p>
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            This game is currently in development. Check back soon for the full Vantaris experience.
          </p>
        </div>
        <Link href="/lobby">
          <motion.button className="px-8 py-3 rounded-xl text-sm font-bold tracking-widest"
            style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif" }}
            whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
            BACK TO LOBBY
          </motion.button>
        </Link>
      </motion.div>
    </div>
  )
}
