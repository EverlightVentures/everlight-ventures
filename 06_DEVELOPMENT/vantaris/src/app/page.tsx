'use client'

import { motion } from 'framer-motion'
import { lazy, Suspense } from 'react'
import Link from 'next/link'

const GoldParticles = lazy(() => import('@/components/shared/GoldParticles').then(m => ({ default: m.GoldParticles })))

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const VENTURES = [
  {
    name: 'Everlight Publishing',
    desc: 'Independent publishing across children\'s fiction, literary thrillers, and interactive learning. Home to the Adventures with Sam and Robo series and Beyond the Veil, a quantum western thriller.',
    href: '/publishing',
    color: '#7B5EA7',
    cta: 'Browse Our Books',
  },
  {
    name: 'Alley Kingz',
    desc: 'A real-time PvP card battler set in the streets. Forty-one characters across ten city factions. Each card is a dog breed rendered in hyper-real urban art with Three.js 3D. Playable in-browser right now.',
    href: '/lobby',
    color: '#00F5FF',
    cta: 'Play the Demo',
  },
  {
    name: 'Onyx POS',
    desc: 'Point-of-sale software for small retail. $49 a month, flat rate, no per-transaction fees. Inventory tracking, employee time clock, payroll, sales analytics, and mobile checkout.',
    href: '/onyx',
    color: '#D4A017',
    cta: 'Start Free Trial',
  },
  {
    name: 'Hive Mind',
    desc: 'An AI orchestration platform that coordinates Claude, Gemini, Codex, and Perplexity as a unified team. War room sessions, smart routing, persistent memory, and a taskboard for AI-to-human handoff.',
    href: '/hivemind',
    color: '#D4AF37',
    cta: 'Join the Waitlist',
  },
  {
    name: 'HIM Loadout',
    desc: 'Curated gear for men. Tech, EDC, fitness, grooming, outdoor, and style -- researched and filtered down to what is actually worth buying. Affiliate model: you pay the same price, we earn a commission.',
    href: '/him-loadout',
    color: '#4A7C9B',
    cta: 'Browse the Drops',
  },
  {
    name: 'Everlight Logistics',
    desc: 'Fulfillment, warehousing, last-mile delivery, and supply chain consulting for small businesses and e-commerce operators. This is where Everlight started.',
    href: '/logistics',
    color: '#D4963A',
    cta: 'Get a Quote',
  },
]

const PROOF = [
  { number: '5', label: 'Books Published' },
  { number: '41', label: 'Game Characters' },
  { number: 'LIVE', label: 'Trading Bot' },
  { number: '$49/mo', label: 'POS System' },
]

export default function HomePage() {
  return (
    <main className="min-h-screen" style={{ background: '#0A0A0A' }}>

      {/* Hero */}
      <section className="min-h-[90vh] flex flex-col items-center justify-center px-6 text-center relative overflow-hidden">
        <Suspense fallback={null}><GoldParticles /></Suspense>
        <motion.div initial="hidden" animate="visible" variants={stagger} className="relative z-10">
          <motion.h1 variants={fadeUp} className="text-4xl md:text-6xl lg:text-7xl font-bold leading-tight"
            style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4AF37' }}>
            Build Different.<br />Build in the Light.
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-6 text-lg md:text-xl max-w-2xl mx-auto" style={{ color: '#E5E5E5', fontFamily: "'Inter', sans-serif" }}>
            Everlight Ventures is a venture studio that builds, operates, and scales businesses across commerce, publishing, software, and finance.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-10">
            <Link href="#portfolio">
              <motion.button className="px-8 py-3 rounded-xl text-sm font-bold tracking-widest"
                style={{ background: '#D4AF37', color: '#0A0A0A', fontFamily: "'Inter', sans-serif" }}
                whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                EXPLORE THE VENTURES
              </motion.button>
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* Live Proof Strip */}
      <section className="py-8 px-6 border-y" style={{ borderColor: '#2A2A2A' }}>
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6">
          {PROOF.map(p => (
            <motion.div key={p.label} initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} className="text-center">
              <p className="text-2xl md:text-3xl font-bold" style={{ color: '#D4AF37', fontFamily: "'Cormorant Garamond', serif" }}>{p.number}</p>
              <p className="text-xs uppercase tracking-wider mt-1" style={{ color: '#8A8A8A' }}>{p.label}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Portfolio */}
      <section id="portfolio" className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-5xl mx-auto">
          <motion.p variants={fadeUp} className="text-sm mb-2" style={{ color: '#8A8A8A' }}>
            Each venture operates independently but shares infrastructure, automation, and a unified AI operations layer.
          </motion.p>
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold mb-12" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4AF37' }}>
            The Portfolio
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {VENTURES.map(v => (
              <motion.div key={v.name} variants={fadeUp}>
                <Link href={v.href}>
                  <motion.div className="p-6 rounded-xl h-full cursor-pointer"
                    style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}
                    whileHover={{ borderColor: `${v.color}40`, boxShadow: `0 0 20px ${v.color}10` }}>
                    <h3 className="text-base font-bold tracking-wide mb-3" style={{ color: v.color, fontFamily: "'Inter', sans-serif" }}>{v.name}</h3>
                    <p className="text-sm leading-relaxed mb-4" style={{ color: '#8A8A8A' }}>{v.desc}</p>
                    <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: v.color }}>{v.cta} &rarr;</span>
                  </motion.div>
                </Link>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* The Story */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold mb-8" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4AF37' }}>
            The Story
          </motion.h2>
          <motion.p variants={fadeUp} className="text-base leading-relaxed mb-4" style={{ color: '#E5E5E5' }}>
            Everlight started on a phone.
          </motion.p>
          <motion.p variants={fadeUp} className="text-base leading-relaxed mb-4" style={{ color: '#8A8A8A' }}>
            Not a pitch deck, not a co-working space, not an accelerator. A Samsung Z Fold, a solar panel, and the idea that you could build a real business from anywhere if you automated enough of the work.
          </motion.p>
          <motion.p variants={fadeUp} className="text-base leading-relaxed mb-4" style={{ color: '#8A8A8A' }}>
            From there, each venture grew out of a real problem or a real conviction. The children's books exist because we wanted to leave something behind that mattered. The game exists because street culture deserved AAA-quality treatment on mobile. The POS system exists because small retailers were bleeding money on percentage fees. The AI platform exists because running this many operations demanded something that did not exist yet.
          </motion.p>
          <motion.p variants={fadeUp} className="text-base leading-relaxed mb-4" style={{ color: '#8A8A8A' }}>
            Nothing here was built on a timeline or a fundraising schedule. Every venture was funded by the last one. Every product ships complete -- not as a beta, not as a proof of concept, but as something you can use today.
          </motion.p>
          <motion.p variants={fadeUp} className="text-base leading-relaxed" style={{ color: '#E5E5E5' }}>
            Everlight is not a brand. It is a body of work -- built over five years, across six industries, by a founder who chose to venture instead of pitch.
          </motion.p>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t" style={{ borderColor: '#2A2A2A' }}>
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div>
              <p className="text-lg font-bold" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4AF37' }}>EVERLIGHT VENTURES</p>
              <p className="text-xs mt-1" style={{ color: '#8A8A8A' }}>Build Different. Build in the Light.</p>
            </div>
            <div className="flex flex-wrap gap-4 text-xs" style={{ color: '#8A8A8A' }}>
              <Link href="/" className="hover:text-white transition-colors">Home</Link>
              <Link href="/publishing" className="hover:text-white transition-colors">Publishing</Link>
              <Link href="/lobby" className="hover:text-white transition-colors">Casino</Link>
              <Link href="/onyx" className="hover:text-white transition-colors">Onyx</Link>
              <Link href="/hivemind" className="hover:text-white transition-colors">Hive Mind</Link>
              <Link href="/him-loadout" className="hover:text-white transition-colors">HIM Loadout</Link>
              <Link href="/logistics" className="hover:text-white transition-colors">Logistics</Link>
              <Link href="/sell" className="hover:text-white transition-colors">Wholesale</Link>
            </div>
          </div>
          <div className="mt-8 pt-6 border-t text-center" style={{ borderColor: '#2A2A2A' }}>
            <p className="text-[10px]" style={{ color: '#8A8A8A' }}>
              &copy; 2026 Everlight Ventures. All rights reserved. Everlight Logistics LLC. hello@everlightventures.io
            </p>
          </div>
        </div>
      </footer>
    </main>
  )
}
