'use client'

import { motion } from 'framer-motion'
import { PageHero } from '@/components/shared/PageHero'
import { GlassCard } from '@/components/shared/GlassCard'
import { SectionDivider } from '@/components/shared/SectionDivider'
import { EmailCapture } from '@/components/shared/EmailCapture'

const C = '#4A7C9B'

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.1 } } }

const CATEGORIES = [
  { name: 'TECH', desc: 'Gadgets, chargers, audio, and accessories that actually perform.' },
  { name: 'EDC', desc: 'Knives, wallets, multitools, and the things you reach for daily.' },
  { name: 'FITNESS', desc: 'Training gear, recovery tools, and supplements worth the money.' },
  { name: 'GROOMING', desc: 'Skincare, beard care, and hardware that does what it claims.' },
  { name: 'OUTDOOR', desc: 'Camping, hiking, and adventure gear tested in the field.' },
  { name: 'STYLE', desc: 'Watches, bags, sunglasses, and wardrobe picks with substance.' },
]

export default function HIMLoadoutPage() {
  return (
    <main className="min-h-screen" style={{ background: 'linear-gradient(180deg, #08080c 0%, #0c0c12 50%, #0a0a10 100%)' }}>

      <PageHero
        overline="HIM Loadout"
        title="Gear that earns its place."
        subtitle="Researched. Filtered. No sponsored junk."
        description="We find the products worth buying so you do not have to dig through 47 Amazon pages. New drops every week. You pay the same price -- we earn a commission."
        color={C} />

      <SectionDivider color={C} />

      {/* Categories */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={stagger} className="max-w-5xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>Categories</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-5xl font-bold mb-16" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            Six verticals.<br /><span style={{ color: '#555' }}>Zero filler.</span>
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {CATEGORIES.map((c, i) => (
              <motion.div key={c.name} variants={fadeUp}>
                <GlassCard color={C}><div className="p-7">
                  <span className="text-[40px] font-bold leading-none block mb-3" style={{ fontFamily: "'Cormorant Garamond', serif", color: 'rgba(255,255,255,0.03)' }}>{String(i + 1).padStart(2, '0')}</span>
                  <h3 className="text-[11px] font-bold tracking-[0.15em] mb-3" style={{ color: C }}>{c.name}</h3>
                  <p className="text-[13px] leading-[1.8]" style={{ color: '#888' }}>{c.desc}</p>
                </div></GlassCard>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <SectionDivider color={C} />

      {/* How It Works */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          {[
            { num: '01', title: 'WE FIND IT', desc: 'Every product gets researched. Overpriced, overhyped, or under-built? Cut.' },
            { num: '02', title: 'YOU DECIDE', desc: 'Honest specs, real use cases, what we actually think. No paid placements.' },
            { num: '03', title: 'YOU BUY DIRECT', desc: 'Links go to the brand. We earn a small affiliate cut. You pay the same either way.' },
          ].map(s => (
            <motion.div key={s.num} variants={fadeUp} className="mb-4">
              <GlassCard color={C}><div className="p-7 flex gap-6 items-start">
                <span className="text-3xl font-bold shrink-0" style={{ fontFamily: "'Cormorant Garamond', serif", color: `${C}30` }}>{s.num}</span>
                <div>
                  <h3 className="text-[11px] font-bold tracking-[0.15em] mb-2" style={{ color: C }}>{s.title}</h3>
                  <p className="text-[13px] leading-[1.8]" style={{ color: '#888' }}>{s.desc}</p>
                </div>
              </div></GlassCard>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* Subscribe */}
      <section className="py-28 px-6 text-center">
        <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
          <p className="text-sm mb-6" style={{ color: '#666' }}>New drops every week. Get them before they go mainstream.</p>
          <div className="max-w-md mx-auto">
            <EmailCapture source="alley-kingz" color={C} buttonText="SUBSCRIBE" successTitle="You're in." successDesc="Drops straight to your inbox." />
          </div>
        </motion.div>
      </section>
    </main>
  )
}
