'use client'

import { motion } from 'framer-motion'
import { useState, useEffect, lazy, Suspense } from 'react'
import Link from 'next/link'

const GoldParticles = lazy(() => import('@/components/shared/GoldParticles').then(m => ({ default: m.GoldParticles })))

/**
 * Everlight Ventures Homepage
 *
 * "Build Different. Build in the Light."
 * Venture studio landing page with portfolio showcase.
 */

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}

const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const VENTURES = [
  { name: 'Vantaris Casino', desc: 'Provably fair online casino. Blackjack, Crash, and more. AI dealers. Sweepstakes model.', href: '/lobby', color: '#c9a84c', icon: '\u2660' },
  { name: 'Alley Kingz', desc: 'Real-time PvP card battler. 41 cards, 10 city factions. Street culture meets AAA.', href: '/alley-kingz', color: '#ff6b35', icon: '\u265A' },
  { name: 'Onyx POS', desc: 'Point-of-sale for real retail. $49/mo flat. No percentage fees.', href: '/onyx', color: '#00e676', icon: '\u2B23' },
  { name: 'Hive Mind AI', desc: 'AI orchestration platform. Claude, Gemini, Codex, Perplexity in one war room.', href: '/hivemind', color: '#58a6ff', icon: '\u2B50' },
  { name: 'Publishing', desc: 'Independent books. Sam & Robo children\'s series. Beyond the Veil thriller.', href: '/publishing', color: '#e91e63', icon: '\u270E' },
  { name: 'Logistics', desc: 'Fulfillment, warehousing, last-mile delivery for small businesses.', href: '/logistics', color: '#9b59b6', icon: '\u2708' },
  { name: 'Wholesale', desc: 'Off-market distressed properties delivered to cash buyers and investors.', href: '/wholesale', color: '#27ae60', icon: '\u2302' },
  { name: 'HIM Loadout', desc: 'Curated gear for the modern man. Honest reviews, affiliate links.', href: '/him-loadout', color: '#ff2d55', icon: '\u2606' },
]

export default function HomePage() {
  return (
    <main className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>

      {/* Hero */}
      <section className="min-h-[90vh] flex flex-col items-center justify-center px-6 text-center relative overflow-hidden">
        <Suspense fallback={null}><GoldParticles /></Suspense>
        <motion.div initial="hidden" animate="visible" variants={stagger} className="relative z-10">
          <motion.p variants={fadeUp} className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--text-tertiary)', letterSpacing: '4px' }}>
            EVERLIGHT VENTURES
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-4xl md:text-6xl lg:text-7xl font-bold leading-tight"
            style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #c9a84c, #e8c55a, #c9a84c)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Build Different.<br />Build in the Light.
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-6 text-lg md:text-xl max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
            Tools, stories, and systems for the self-made. Eight operating ventures. No outside capital. Five years of work.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-10 flex gap-4 justify-center flex-wrap">
            <Link href="/lobby">
              <motion.button className="px-8 py-3 rounded-xl text-sm font-bold tracking-widest"
                style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif" }}
                whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                ENTER THE CASINO
              </motion.button>
            </Link>
            <Link href="/arcade">
              <motion.button className="px-8 py-3 rounded-xl text-sm font-bold tracking-widest"
                style={{ background: 'rgba(255,255,255,0.06)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)' }}
                whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                EXPLORE VENTURES
              </motion.button>
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* Story */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger}
          className="max-w-3xl mx-auto text-center">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold mb-6" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
            Our Story
          </motion.h2>
          <motion.p variants={fadeUp} className="text-base md:text-lg leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Everlight started on a phone. Not a pitch deck, not a co-working space. A Samsung Z Fold, a solar panel, and the idea that you could build a real business from anywhere if you automated enough of the work.
          </motion.p>
          <motion.p variants={fadeUp} className="mt-4 text-base md:text-lg leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Five years later, the portfolio spans eight operating ventures -- a POS system tested in a live retail store, a children's book series, a casino hand-coded in Three.js, a trading bot running live, and an AI platform that replaced a $50,000-a-year operations team.
          </motion.p>
        </motion.div>
      </section>

      {/* Ventures Grid */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger}
          className="max-w-6xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold text-center mb-12" style={{ fontFamily: "'Cinzel', serif" }}>
            The Portfolio
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {VENTURES.map((v, i) => (
              <motion.div key={v.name} variants={fadeUp}>
                <Link href={v.href}>
                  <motion.div className="p-6 rounded-2xl h-full cursor-pointer"
                    style={{ background: `${v.color}08`, border: `1px solid ${v.color}20` }}
                    whileHover={{ scale: 1.02, borderColor: `${v.color}40`, boxShadow: `0 0 20px ${v.color}15` }}>
                    <span className="text-2xl block mb-3" style={{ color: v.color }}>{v.icon}</span>
                    <h3 className="text-sm font-bold tracking-wider mb-2" style={{ color: v.color, fontFamily: "'Cinzel', serif" }}>{v.name}</h3>
                    <p className="text-xs leading-relaxed" style={{ color: 'var(--text-tertiary)' }}>{v.desc}</p>
                  </motion.div>
                </Link>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6 text-center">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger}>
          <motion.p variants={fadeUp} className="text-sm uppercase tracking-widest mb-4" style={{ color: 'var(--text-tertiary)' }}>
            Everlight Ventures LLC &middot; Fairfield, California
          </motion.p>
          <motion.p variants={fadeUp} className="text-xl md:text-3xl font-bold" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
            Innovation meets opportunity.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8">
            <Link href="/auth">
              <motion.button className="px-10 py-3 rounded-xl text-sm font-bold tracking-widest"
                style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif" }}
                whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                GET STARTED
              </motion.button>
            </Link>
          </motion.div>
        </motion.div>
      </section>
    </main>
  )
}
