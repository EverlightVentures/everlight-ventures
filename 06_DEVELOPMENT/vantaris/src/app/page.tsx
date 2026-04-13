'use client'

import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import Link from 'next/link'

/**
 * Vantaris Landing Page
 *
 * Design: Balenciaga meets Apple keynote.
 * 80% void. One thought per screen. Typography does the talking.
 * The page IS the first hit of dopamine -- anticipation before the game even starts.
 *
 * Scroll sequence:
 * 1. The star (logo pulsing in void)
 * 2. The tagline (serif, massive)
 * 3. The games (floating cards in darkness)
 * 4. The promise (provably fair, one sentence)
 * 5. The enter (single gold button)
 */

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}

const stagger = {
  visible: { transition: { staggerChildren: 0.15 } },
}

// Animated counter that ticks up
function AnimatedNumber({ value, prefix = '' }: { value: number; prefix?: string }) {
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    const duration = 2000
    const steps = 60
    const increment = value / steps
    let current = 0
    const timer = setInterval(() => {
      current += increment
      if (current >= value) {
        setDisplay(value)
        clearInterval(timer)
      } else {
        setDisplay(Math.floor(current))
      }
    }, duration / steps)
    return () => clearInterval(timer)
  }, [value])

  return (
    <span className="font-mono font-bold" style={{ fontVariantNumeric: 'tabular-nums' }}>
      {prefix}{display.toLocaleString()}
    </span>
  )
}

// Pulsing star logo
function VantarisStar() {
  return (
    <motion.div
      className="relative w-24 h-24 mx-auto"
      animate={{
        boxShadow: [
          '0 0 20px rgba(201, 168, 76, 0.1)',
          '0 0 60px rgba(201, 168, 76, 0.3)',
          '0 0 20px rgba(201, 168, 76, 0.1)',
        ],
      }}
      transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
    >
      <svg viewBox="0 0 100 100" className="w-full h-full">
        <defs>
          <linearGradient id="starGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#c9a84c" />
            <stop offset="50%" stopColor="#e8c55a" />
            <stop offset="100%" stopColor="#c9a84c" />
          </linearGradient>
        </defs>
        <polygon
          points="50,5 61,35 95,35 68,55 79,90 50,70 21,90 32,55 5,35 39,35"
          fill="url(#starGrad)"
          opacity="0.9"
        />
      </svg>
    </motion.div>
  )
}

// Game card preview
function GamePreview({ name, color, delay }: { name: string; color: string; delay: number }) {
  return (
    <motion.div
      variants={fadeUp}
      whileHover={{ scale: 1.05, boxShadow: `0 0 40px ${color}30` }}
      className="glass p-6 rounded-2xl cursor-pointer text-center"
      style={{ borderColor: `${color}20` }}
    >
      <div
        className="w-12 h-12 rounded-xl mx-auto mb-4"
        style={{ background: `linear-gradient(135deg, ${color}40, ${color}10)` }}
      />
      <p className="text-sm font-medium tracking-wide uppercase" style={{ color }}>
        {name}
      </p>
    </motion.div>
  )
}

export default function LandingPage() {
  return (
    <main className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>

      {/* === SECTION 1: THE VOID === */}
      <section className="min-h-screen flex flex-col items-center justify-center px-6">
        <motion.div
          initial="hidden"
          animate="visible"
          variants={stagger}
          className="text-center"
        >
          <motion.div variants={fadeUp}>
            <VantarisStar />
          </motion.div>

          <motion.h1
            variants={fadeUp}
            className="mt-12 font-display text-5xl md:text-7xl lg:text-8xl font-bold"
            style={{
              letterSpacing: '0.15em',
              background: 'linear-gradient(135deg, #c9a84c, #e8c55a, #c9a84c)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            VANTARIS
          </motion.h1>

          <motion.p
            variants={fadeUp}
            className="mt-6 text-lg md:text-xl"
            style={{ color: 'var(--text-secondary)', maxWidth: '28ch', margin: '1.5rem auto 0' }}
          >
            The darkest star burns brightest.
          </motion.p>

          <motion.div variants={fadeUp} className="mt-12">
            <motion.div
              animate={{ y: [0, 8, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="text-xs uppercase tracking-widest"
              style={{ color: 'var(--text-tertiary)' }}
            >
              Scroll to enter
            </motion.div>
          </motion.div>
        </motion.div>
      </section>

      {/* === SECTION 2: THE PROMISE === */}
      <section className="min-h-screen flex items-center justify-center px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.5 }}
          variants={stagger}
          className="text-center max-w-3xl"
        >
          <motion.p
            variants={fadeUp}
            className="font-display text-3xl md:text-5xl leading-tight"
            style={{ color: 'var(--text-primary)' }}
          >
            Six games.{' '}
            <span style={{ color: 'var(--gold)' }}>Provably fair.</span>{' '}
            Every outcome verified on-chain.
          </motion.p>

          <motion.p
            variants={fadeUp}
            className="mt-8 text-lg"
            style={{ color: 'var(--text-secondary)' }}
          >
            The house doesn't hide. Every hand, every spin, every crash point
            is cryptographically committed before you play and revealed after.
            Verify it yourself. We dare you.
          </motion.p>
        </motion.div>
      </section>

      {/* === SECTION 3: THE GAMES === */}
      <section className="min-h-screen flex items-center justify-center px-6 py-24">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.3 }}
          variants={stagger}
          className="w-full max-w-5xl"
        >
          <motion.h2
            variants={fadeUp}
            className="font-display text-2xl md:text-4xl text-center mb-16"
          >
            Choose your table.
          </motion.h2>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 md:gap-6">
            <GamePreview name="Blackjack" color="#c9a84c" delay={0} />
            <GamePreview name="Roulette" color="#ff2d55" delay={0.1} />
            <GamePreview name="Crash" color="#00e676" delay={0.2} />
            <GamePreview name="Dice" color="#58a6ff" delay={0.3} />
            <GamePreview name="Plinko" color="#ff6b35" delay={0.4} />
            <GamePreview name="Mines" color="#00ff41" delay={0.5} />
          </div>
        </motion.div>
      </section>

      {/* === SECTION 4: THE NUMBERS === */}
      <section className="py-24 px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={stagger}
          className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center"
        >
          {[
            { value: 6, label: 'Games', prefix: '' },
            { value: 100, label: 'Provably Fair', prefix: '' },
            { value: 5, label: 'VIP Tiers', prefix: '' },
            { value: 24, label: 'Hour Access', prefix: '' },
          ].map((stat, i) => (
            <motion.div key={i} variants={fadeUp} className="card p-6">
              <div className="text-3xl md:text-4xl font-mono font-bold" style={{ color: 'var(--gold)' }}>
                <AnimatedNumber value={stat.value} prefix={stat.prefix} />
                {stat.label === 'Provably Fair' ? '%' : ''}
              </div>
              <div className="mt-2 text-xs uppercase tracking-widest" style={{ color: 'var(--text-tertiary)' }}>
                {stat.label}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* === SECTION 5: TIER REVEAL === */}
      <section className="min-h-screen flex items-center justify-center px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.5 }}
          variants={stagger}
          className="text-center"
        >
          <motion.p
            variants={fadeUp}
            className="text-sm uppercase tracking-widest mb-8"
            style={{ color: 'var(--text-tertiary)' }}
          >
            Five tiers. One throne.
          </motion.p>

          <div className="flex flex-wrap justify-center gap-6">
            {[
              { name: 'Ember', color: '#ff6b35', xp: '0' },
              { name: 'Shadow', color: '#6a5acd', xp: '5K' },
              { name: 'Eclipse', color: '#1a0a2e', xp: '25K', border: '#6a5acd' },
              { name: 'Supernova', color: '#c9a84c', xp: '100K' },
              { name: 'Vanta Black', color: '#050507', xp: '500K', border: '#c9a84c' },
            ].map((tier, i) => (
              <motion.div
                key={tier.name}
                variants={fadeUp}
                className="w-28 h-36 rounded-2xl flex flex-col items-center justify-center p-4"
                style={{
                  background: tier.color === '#050507'
                    ? 'linear-gradient(135deg, #0a0a0a, #050507)'
                    : `${tier.color}15`,
                  border: `1px solid ${tier.border || tier.color}30`,
                }}
                whileHover={{
                  scale: 1.08,
                  boxShadow: `0 0 30px ${tier.border || tier.color}25`,
                }}
              >
                <span
                  className="text-xs font-semibold uppercase tracking-wider"
                  style={{ color: tier.border || tier.color }}
                >
                  {tier.name}
                </span>
                <span className="mt-2 text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
                  {tier.xp} XP
                </span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* === SECTION 6: THE ENTER === */}
      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 pb-24">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={stagger}
          className="text-center"
        >
          <motion.p
            variants={fadeUp}
            className="font-display text-2xl md:text-4xl italic mb-4"
            style={{ color: 'var(--text-secondary)' }}
          >
            You didn't find Vantaris.
          </motion.p>
          <motion.p
            variants={fadeUp}
            className="font-display text-3xl md:text-5xl font-bold mb-12"
            style={{ color: 'var(--text-primary)' }}
          >
            Vantaris found you.
          </motion.p>

          <motion.div variants={fadeUp}>
            <Link href="/lobby">
              <motion.button
                className="btn-primary px-12 py-4 text-lg tracking-widest"
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.98 }}
              >
                ENTER
              </motion.button>
            </Link>
          </motion.div>

          <motion.p
            variants={fadeUp}
            className="mt-8 text-xs"
            style={{ color: 'var(--text-tertiary)' }}
          >
            18+ only. Play responsibly. Provably fair.
          </motion.p>
        </motion.div>
      </section>

    </main>
  )
}
