'use client'

import { motion } from 'framer-motion'
import { PageHero } from '@/components/shared/PageHero'
import { GlassCard } from '@/components/shared/GlassCard'
import { SectionDivider } from '@/components/shared/SectionDivider'
import { EmailCapture } from '@/components/shared/EmailCapture'

const C = '#D4A017'

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.1 } } }

const FEATURES = [
  { title: 'Inventory Management', desc: 'Real-time stock tracking, low-inventory alerts, supplier reorder points. Know what you have. Always.' },
  { title: 'Payment Processing', desc: 'Flat-rate processing. No percentage fees that scale against your growth. The more you sell, the more you save.' },
  { title: 'Employee Management', desc: 'Clock-ins, permissions, role-based access, time tracking, shift scheduling. Accountability built in.' },
  { title: 'Sales Analytics', desc: 'Daily, weekly, monthly breakdowns. Exportable reports. Data that helps you make decisions.' },
  { title: 'Multi-Location', desc: 'One dashboard. Every location. Unified inventory, consolidated reporting, per-location views.' },
  { title: 'Mobile POS', desc: 'Any tablet or phone becomes a checkout terminal. Ring up sales from anywhere in your store.' },
]

const PROBLEMS = [
  { title: 'DEATH BY PERCENTAGE', desc: 'Square takes 2.6% + $0.10 per swipe. On $30K/mo that is $780 gone before you pay rent.' },
  { title: 'SOFTWARE BUILT FOR CORPORATIONS', desc: 'Most POS systems were designed for enterprise chains, then dumbed down and resold to you at full price.' },
  { title: 'SUPPORT THAT DISAPPEARS', desc: 'Something breaks on Saturday during your busiest hours. You submit a ticket. You get an auto-reply. Nobody comes.' },
]

export default function OnyxPage() {
  return (
    <main className="min-h-screen" style={{ background: 'linear-gradient(180deg, #08080c 0%, #0c0c12 50%, #0a0a10 100%)' }}>

      <PageHero
        overline="Onyx POS"
        title="Stop overpaying. Start selling."
        subtitle="$49/mo flat. No percentage fees. No contracts."
        description="Built by someone who watched Square skim profits off every swipe and decided to build something better. Tested on a live retail operation."
        color={C}>
        <div className="mt-10 max-w-md mx-auto">
          <EmailCapture source="onyx" color={C} buttonText="START TRIAL" successTitle="Trial started!" successDesc="Check your email." placeholder="Your business email" />
          <p className="mt-3 text-[11px]" style={{ color: '#555' }}>No credit card required. Set up in under 10 minutes.</p>
        </div>
      </PageHero>

      <SectionDivider color={C} />

      {/* The Problem */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>The Problem</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-5xl font-bold mb-12" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            You opened a business,<br /><span style={{ color: '#555' }}>not a payment processing degree program.</span>
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {PROBLEMS.map(p => (
              <motion.div key={p.title} variants={fadeUp}>
                <GlassCard color={C}><div className="p-7">
                  <h3 className="text-[11px] font-bold tracking-[0.15em] mb-3" style={{ color: C }}>{p.title}</h3>
                  <p className="text-[13px] leading-[1.8]" style={{ color: '#888' }}>{p.desc}</p>
                </div></GlassCard>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <SectionDivider color={C} />

      {/* Features */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={stagger} className="max-w-5xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>Features</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-5xl font-bold mb-16" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            Everything you need.<br /><span style={{ color: '#555' }}>Nothing you do not.</span>
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f, i) => (
              <motion.div key={f.title} variants={fadeUp}>
                <GlassCard color={C}><div className="p-7">
                  <span className="text-[40px] font-bold leading-none block mb-4" style={{ fontFamily: "'Cormorant Garamond', serif", color: 'rgba(255,255,255,0.03)' }}>{String(i + 1).padStart(2, '0')}</span>
                  <h3 className="text-sm font-bold tracking-wide mb-3" style={{ color: '#eee' }}>{f.title}</h3>
                  <p className="text-[13px] leading-[1.8]" style={{ color: '#888' }}>{f.desc}</p>
                </div></GlassCard>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <SectionDivider color={C} />

      {/* Pricing */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-md mx-auto text-center">
          <motion.div variants={fadeUp}>
            <GlassCard color={C} hover={false}><div className="p-10">
              <p className="text-[10px] uppercase tracking-[0.3em] mb-2" style={{ color: C }}>ONYX PRO</p>
              <p className="text-5xl font-bold my-6" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>$49<span className="text-lg font-light" style={{ color: '#555' }}>/mo</span></p>
              <div className="h-px mb-6" style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)' }} />
              <ul className="text-left space-y-3 mb-8">
                {['Unlimited transactions', 'Up to 10 employees', 'Inventory management', 'Sales analytics', 'Mobile POS on any device', 'Multi-location (up to 3)', 'Email + chat support', 'All future updates'].map(f => (
                  <li key={f} className="text-[13px] flex items-center gap-3" style={{ color: '#999' }}>
                    <span style={{ color: C }}>+</span> {f}
                  </li>
                ))}
              </ul>
              <p className="text-[11px]" style={{ color: '#555' }}>Cancel anytime. No contracts. Additional locations $19/mo.</p>
            </div></GlassCard>
          </motion.div>
        </motion.div>
      </section>

      {/* Final CTA */}
      <section className="py-28 px-6 text-center">
        <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.8 }}>
          <p className="text-3xl font-bold mb-8" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>Ready?</p>
          <div className="max-w-md mx-auto">
            <EmailCapture source="onyx" color={C} buttonText="START TRIAL" successTitle="You're in!" successDesc="Check your email." placeholder="Your business email" />
          </div>
        </motion.div>
      </section>
    </main>
  )
}
