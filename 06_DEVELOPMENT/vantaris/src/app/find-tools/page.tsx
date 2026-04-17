'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.1 } } }

const TOOLS = [
  { name: 'Onyx POS', desc: 'Point-of-sale for retail stores. $49/mo flat.', category: 'Business', href: '/onyx', color: '#00e676' },
  { name: 'Hive Mind AI', desc: 'AI orchestration platform with 42 agents.', category: 'AI', href: '/hivemind', color: '#58a6ff' },
  { name: 'Vantaris Casino', desc: 'Provably fair sweepstakes casino engine.', category: 'Gaming', href: '/lobby', color: '#c9a84c' },
  { name: 'Alley Kingz', desc: 'Real-time PvP card battler.', category: 'Gaming', href: '/alley-kingz', color: '#ff6b35' },
  { name: 'Everlight Logistics', desc: 'Fulfillment and last-mile delivery.', category: 'Service', href: '/logistics', color: '#9b59b6' },
  { name: 'AI Consulting', desc: 'Custom AI builds and strategy.', category: 'Service', href: '/sell', color: '#c9a84c' },
]

export default function FindToolsPage() {
  return (
    <main className="min-h-screen py-20 px-6" style={{ background: 'var(--vanta-void)' }}>
      <motion.div initial="hidden" animate="visible" variants={stagger} className="max-w-5xl mx-auto">

        <motion.div variants={fadeUp} className="text-center mb-16">
          <h1 className="text-4xl md:text-6xl font-bold" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
            Find Tools
          </h1>
          <p className="mt-4 text-lg" style={{ color: 'var(--text-secondary)' }}>
            Software, services, and platforms built by Everlight Ventures. Everything here is built in-house and battle-tested.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {TOOLS.map(t => (
            <motion.div key={t.name} variants={fadeUp}>
              <Link href={t.href}>
                <motion.div className="p-6 rounded-2xl h-full cursor-pointer"
                  style={{ background: `${t.color}08`, border: `1px solid ${t.color}20` }}
                  whileHover={{ scale: 1.02, borderColor: `${t.color}40` }}>
                  <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full" style={{ background: `${t.color}15`, color: t.color }}>{t.category}</span>
                  <h3 className="text-sm font-bold tracking-wider mt-3 mb-2" style={{ color: t.color, fontFamily: "'Cinzel', serif" }}>{t.name}</h3>
                  <p className="text-xs leading-relaxed" style={{ color: 'var(--text-tertiary)' }}>{t.desc}</p>
                </motion.div>
              </Link>
            </motion.div>
          ))}
        </div>

        <motion.div variants={fadeUp} className="mt-16 text-center">
          <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>Have a tool or service to list?</p>
          <Link href="/list-your-tool">
            <motion.button className="px-8 py-3 rounded-xl text-sm font-bold tracking-widest"
              style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif" }}
              whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              LIST YOUR TOOL
            </motion.button>
          </Link>
        </motion.div>
      </motion.div>
    </main>
  )
}
