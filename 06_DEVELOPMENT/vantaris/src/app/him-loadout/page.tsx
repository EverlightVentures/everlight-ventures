'use client'

import { motion } from 'framer-motion'
import { EmailCapture } from '@/components/shared/EmailCapture'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const CATEGORIES = [
  { name: 'TECH', desc: 'Gadgets, chargers, audio, and accessories that actually perform.' },
  { name: 'EDC', desc: 'Knives, wallets, multitools, and the things you reach for daily.' },
  { name: 'FITNESS', desc: 'Training gear, recovery tools, and supplements worth the money.' },
  { name: 'GROOMING', desc: 'Skincare, beard care, and hardware that does what it claims.' },
  { name: 'OUTDOOR', desc: 'Camping, hiking, and adventure gear tested in the field.' },
  { name: 'STYLE', desc: 'Watches, bags, sunglasses, and wardrobe picks with substance.' },
]

const STEPS = [
  { num: '01', title: 'WE FIND IT', desc: 'Every product gets researched. If it is overpriced, overhyped, or under-built, it does not make the cut.' },
  { num: '02', title: 'YOU DECIDE', desc: 'Browse by category. Every listing includes honest specs, use cases, and what we actually think. No paid placements.' },
  { num: '03', title: 'YOU BUY DIRECT', desc: 'Links go straight to the brand or retailer. We earn a small affiliate commission. You pay the same price either way. No inventory. No markup. No tricks.' },
]

export default function HIMLoadoutPage() {
  return (
    <main className="min-h-screen" style={{ background: '#0A0A0A' }}>

      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.h1 variants={fadeUp} className="text-4xl md:text-6xl font-bold"
            style={{ fontFamily: "'Cormorant Garamond', serif", color: '#4A7C9B' }}>
            HIM LOADOUT
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 text-xl max-w-2xl mx-auto" style={{ color: '#E5E5E5' }}>
            Gear for men who do not have time to scroll through garbage.
          </motion.p>
          <motion.p variants={fadeUp} className="mt-4 text-sm" style={{ color: '#8A8A8A' }}>
            We find the products worth buying so you do not have to dig through 47 Amazon pages of sponsored junk. New drops every week.
          </motion.p>
        </motion.div>
      </section>

      {/* Categories */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-4xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {CATEGORIES.map(c => (
              <motion.div key={c.name} variants={fadeUp} className="p-6 rounded-xl" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
                <h3 className="text-xs font-bold tracking-wider mb-2" style={{ color: '#4A7C9B' }}>{c.name}</h3>
                <p className="text-xs leading-relaxed" style={{ color: '#8A8A8A' }}>{c.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-8" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#4A7C9B' }}>How It Works</motion.h2>
          <div className="space-y-4">
            {STEPS.map(s => (
              <motion.div key={s.num} variants={fadeUp} className="p-6 rounded-xl flex gap-5 items-start" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
                <span className="text-2xl font-bold shrink-0" style={{ color: '#4A7C9B', opacity: 0.4 }}>{s.num}</span>
                <div>
                  <h3 className="text-xs font-bold tracking-wider mb-1" style={{ color: '#4A7C9B' }}>{s.title}</h3>
                  <p className="text-xs leading-relaxed" style={{ color: '#8A8A8A' }}>{s.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Subscribe */}
      <section className="py-20 px-6 text-center">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger}>
          <motion.p variants={fadeUp} className="text-sm mb-6" style={{ color: '#8A8A8A' }}>New drops hit every week. Get them before they go mainstream.</motion.p>
          <motion.div variants={fadeUp} className="max-w-md mx-auto">
            <EmailCapture source="alley-kingz" color="#4A7C9B" buttonText="SUBSCRIBE" successTitle="You're in." successDesc="New drops straight to your inbox." />
          </motion.div>
        </motion.div>
      </section>
    </main>
  )
}
