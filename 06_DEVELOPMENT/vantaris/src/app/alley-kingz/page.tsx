'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { EmailCapture } from '@/components/shared/EmailCapture'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const FACTIONS = [
  { name: 'East Oakland', color: '#ff6b35', trait: 'Aggression' },
  { name: 'South Central', color: '#e91e63', trait: 'Defense' },
  { name: 'Bronx', color: '#58a6ff', trait: 'Speed' },
  { name: 'Southside Chicago', color: '#00e676', trait: 'Endurance' },
  { name: 'Fifth Ward Houston', color: '#c9a84c', trait: 'Power' },
  { name: 'Zone 6 Atlanta', color: '#9b59b6', trait: 'Stealth' },
  { name: 'Camden', color: '#ff2d55', trait: 'Tactics' },
  { name: 'North Philly', color: '#27ae60', trait: 'Resilience' },
  { name: 'Overtown Miami', color: '#f39c12', trait: 'Charisma' },
  { name: 'Watts', color: '#e74c3c', trait: 'Loyalty' },
]

const FEATURES = [
  { title: '41 Unique Cards', desc: 'Hand-designed characters with lore, abilities, and faction combos that hit different.' },
  { title: 'Real-Time PvP', desc: 'No turn timers. Play cards as fast as you can think.' },
  { title: '10 City Factions', desc: 'Each faction has unique playstyles, bonuses, and story arcs.' },
  { title: 'NFT Marketplace', desc: 'Trade rare cards. True ownership on the blockchain.' },
  { title: 'VIP Pass $4.99/mo', desc: 'Exclusive cards, early access, and tournament entry.' },
  { title: 'Ranked Seasons', desc: 'Climb the leaderboard. Win real prizes every season.' },
]

export default function AlleyKingzPage() {
  return (
    <main className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>

      {/* Hero */}
      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.p variants={fadeUp} className="text-xs uppercase tracking-widest mb-4" style={{ color: '#ff6b35', letterSpacing: '4px' }}>
            EVERLIGHT VENTURES PRESENTS
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-5xl md:text-7xl font-bold"
            style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #ff6b35, #ff9a5c, #ff6b35)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            ALLEY KINGZ
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 text-xl" style={{ color: 'var(--text-secondary)' }}>
            Street culture meets AAA card battling. 41 cards. 10 factions. No mercy.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 max-w-md mx-auto">
            <EmailCapture source="alley-kingz" color="#ff6b35" buttonText="JOIN WAITLIST" successTitle="You're on the list." successDesc="First 1,000 get a free legendary card." />
          </motion.div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-5xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold text-center mb-12" style={{ fontFamily: "'Cinzel', serif", color: '#ff6b35' }}>
            The Game
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map(f => (
              <motion.div key={f.title} variants={fadeUp} className="p-6 rounded-2xl" style={{ background: 'rgba(255,107,53,0.05)', border: '1px solid rgba(255,107,53,0.15)' }}>
                <h3 className="text-sm font-bold tracking-wider mb-2" style={{ color: '#ff6b35', fontFamily: "'Cinzel', serif" }}>{f.title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-tertiary)' }}>{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Factions */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-5xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold text-center mb-12" style={{ fontFamily: "'Cinzel', serif", color: '#ff6b35' }}>
            10 City Factions
          </motion.h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {FACTIONS.map(f => (
              <motion.div key={f.name} variants={fadeUp} className="p-4 rounded-xl text-center" style={{ background: `${f.color}08`, border: `1px solid ${f.color}20` }}>
                <p className="text-xs font-bold tracking-wider" style={{ color: f.color, fontFamily: "'Cinzel', serif" }}>{f.name}</p>
                <p className="text-[10px] mt-1" style={{ color: 'var(--text-tertiary)' }}>{f.trait}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6 text-center">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger}>
          <motion.p variants={fadeUp} className="text-lg" style={{ color: 'var(--text-secondary)' }}>
            Built by Everlight Ventures. Powered by street culture.
          </motion.p>
          <motion.p variants={fadeUp} className="mt-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
            Join the waitlist. First 1,000 players get a free legendary card.
          </motion.p>
        </motion.div>
      </section>
    </main>
  )
}
