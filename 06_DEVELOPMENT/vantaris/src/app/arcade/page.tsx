'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.1 } } }

const GAMES = [
  { name: 'Blackjack', desc: 'Multi-seat, side bets, AI dealers. The crown jewel.', href: '/play/blackjack', color: '#c9a84c', icon: '\u2660', status: 'LIVE' },
  { name: 'Crash', desc: 'Ride the multiplier. Cash out before it crashes.', href: '/play/crash', color: '#ff6b35', icon: '\u26A1', status: 'LIVE' },
  { name: 'Dice', desc: 'Roll over/under. Set your odds. Provably fair.', href: '/play/dice', color: '#58a6ff', icon: '\u2684', status: 'LIVE' },
  { name: 'Mines', desc: 'Minesweeper meets gambling. Every tile is a risk.', href: '/play/mines', color: '#00e676', icon: '\u2739', status: 'LIVE' },
  { name: 'Plinko', desc: 'Drop the ball. Watch it bounce. Pray for gold.', href: '/play/plinko', color: '#e91e63', icon: '\u25BD', status: 'LIVE' },
  { name: 'Roulette', desc: 'European single-zero. Classic casino energy.', href: '/play/roulette', color: '#9b59b6', icon: '\u25CE', status: 'LIVE' },
]

const VENTURES = [
  { name: 'Alley Kingz', desc: 'Real-time PvP card battler. 41 cards. 10 city factions.', href: '/alley-kingz', color: '#ff6b35', icon: '\u265A' },
  { name: 'Onyx POS', desc: 'Point-of-sale for real retail. $49/mo flat.', href: '/onyx', color: '#00e676', icon: '\u2B23' },
  { name: 'Hive Mind AI', desc: 'AI orchestration. Claude, Gemini, Codex in one war room.', href: '/hivemind', color: '#58a6ff', icon: '\u2B50' },
  { name: 'HIM Loadout', desc: 'Curated gear for the modern man.', href: '/him-loadout', color: '#ff2d55', icon: '\u2606' },
  { name: 'Publishing', desc: 'Independent books. Thriller + children\'s series.', href: '/publishing', color: '#e91e63', icon: '\u270E' },
  { name: 'Logistics', desc: 'Fulfillment and last-mile delivery.', href: '/logistics', color: '#9b59b6', icon: '\u2708' },
  { name: 'We Buy Houses', desc: 'Need to sell fast? Cash offer in 24 hours.', href: '/sell', color: '#27ae60', icon: '\u2302' },
]

export default function ArcadePage() {
  return (
    <main className="min-h-screen py-20 px-6" style={{ background: 'var(--vanta-void)' }}>
      <motion.div initial="hidden" animate="visible" variants={stagger} className="max-w-6xl mx-auto">

        <motion.div variants={fadeUp} className="text-center mb-16">
          <p className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--text-tertiary)', letterSpacing: '4px' }}>VANTARIS CASINO</p>
          <h1 className="text-4xl md:text-6xl font-bold" style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #c9a84c, #e8c55a, #c9a84c)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            The Arcade
          </h1>
          <p className="mt-4 text-lg" style={{ color: 'var(--text-secondary)' }}>
            Six provably fair games. Eight operating ventures. All under one roof.
          </p>
        </motion.div>

        {/* Casino Games */}
        <motion.h2 variants={fadeUp} className="text-xl font-bold tracking-wider mb-6" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
          Casino Games
        </motion.h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-16">
          {GAMES.map(g => (
            <motion.div key={g.name} variants={fadeUp}>
              <Link href={g.href}>
                <motion.div className="p-6 rounded-2xl h-full cursor-pointer relative overflow-hidden"
                  style={{ background: `${g.color}08`, border: `1px solid ${g.color}20` }}
                  whileHover={{ scale: 1.02, borderColor: `${g.color}40`, boxShadow: `0 0 20px ${g.color}15` }}>
                  <span className="absolute top-4 right-4 text-[9px] font-bold px-2 py-0.5 rounded-full" style={{ background: `${g.color}20`, color: g.color }}>{g.status}</span>
                  <span className="text-3xl block mb-3" style={{ color: g.color }}>{g.icon}</span>
                  <h3 className="text-sm font-bold tracking-wider mb-2" style={{ color: g.color, fontFamily: "'Cinzel', serif" }}>{g.name}</h3>
                  <p className="text-xs leading-relaxed" style={{ color: 'var(--text-tertiary)' }}>{g.desc}</p>
                </motion.div>
              </Link>
            </motion.div>
          ))}
        </div>

        {/* Ventures */}
        <motion.h2 variants={fadeUp} className="text-xl font-bold tracking-wider mb-6" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
          Everlight Ventures
        </motion.h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {VENTURES.map(v => (
            <motion.div key={v.name} variants={fadeUp}>
              <Link href={v.href}>
                <motion.div className="p-5 rounded-2xl h-full cursor-pointer"
                  style={{ background: `${v.color}08`, border: `1px solid ${v.color}20` }}
                  whileHover={{ scale: 1.02, borderColor: `${v.color}40` }}>
                  <span className="text-2xl block mb-2" style={{ color: v.color }}>{v.icon}</span>
                  <h3 className="text-xs font-bold tracking-wider mb-1" style={{ color: v.color, fontFamily: "'Cinzel', serif" }}>{v.name}</h3>
                  <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-tertiary)' }}>{v.desc}</p>
                </motion.div>
              </Link>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </main>
  )
}
