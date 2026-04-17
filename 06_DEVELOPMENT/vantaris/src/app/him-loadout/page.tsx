'use client'

import { motion } from 'framer-motion'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const CATEGORIES = [
  { name: 'EDC', desc: 'Everyday carry essentials. Knives, wallets, flashlights.', color: '#ff2d55', icon: '\u2694' },
  { name: 'Tech', desc: 'Gadgets that actually work. Chargers, headphones, tools.', color: '#58a6ff', icon: '\u2699' },
  { name: 'Fitness', desc: 'Home gym, supplements, recovery gear.', color: '#00e676', icon: '\u2605' },
  { name: 'Style', desc: 'Watches, sunglasses, grooming. No fast fashion.', color: '#c9a84c', icon: '\u2666' },
  { name: 'Outdoor', desc: 'Camping, survival, overlanding gear.', color: '#27ae60', icon: '\u2302' },
  { name: 'Auto', desc: 'Detailing kits, dash cams, mods.', color: '#e74c3c', icon: '\u2708' },
]

export default function HIMLoadoutPage() {
  return (
    <main className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>

      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.p variants={fadeUp} className="text-xs uppercase tracking-widest mb-4" style={{ color: '#ff2d55', letterSpacing: '4px' }}>
            EVERLIGHT VENTURES
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-5xl md:text-7xl font-bold"
            style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #ff2d55, #ff6b8a, #ff2d55)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            HIM LOADOUT
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 text-xl max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
            Curated gear for the modern man. Honest reviews. No sponsored junk. Every link earns us a commission -- we only recommend what we actually use.
          </motion.p>
        </motion.div>
      </section>

      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-5xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold text-center mb-12" style={{ fontFamily: "'Cinzel', serif", color: '#ff2d55' }}>
            Categories
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {CATEGORIES.map(c => (
              <motion.div key={c.name} variants={fadeUp} className="p-6 rounded-2xl"
                style={{ background: `${c.color}08`, border: `1px solid ${c.color}20` }}>
                <span className="text-2xl block mb-3" style={{ color: c.color }}>{c.icon}</span>
                <h3 className="text-sm font-bold tracking-wider mb-2" style={{ color: c.color, fontFamily: "'Cinzel', serif" }}>{c.name}</h3>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-tertiary)' }}>{c.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto text-center">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-4" style={{ fontFamily: "'Cinzel', serif", color: '#ff2d55' }}>
            How It Works
          </motion.h2>
          <motion.p variants={fadeUp} className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            We test everything ourselves. If it breaks, we tell you. If it holds up, we link it. Every product has a real review from someone who actually used it -- not an influencer who got it free. Affiliate links support Everlight Ventures at no extra cost to you.
          </motion.p>
        </motion.div>
      </section>
    </main>
  )
}
