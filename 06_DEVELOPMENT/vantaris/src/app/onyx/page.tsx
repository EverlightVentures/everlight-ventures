'use client'

import { motion } from 'framer-motion'
import { EmailCapture } from '@/components/shared/EmailCapture'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const FEATURES = [
  { title: 'Inventory Management', desc: 'Real-time stock tracking, low-inventory alerts, supplier reorder points. Know what you have. Always.' },
  { title: 'Payment Processing', desc: 'Flat-rate processing. No percentage fees that scale against your growth. The more you sell, the more you save compared to Square.' },
  { title: 'Employee Management', desc: 'Clock-ins, permissions, role-based access, time tracking, shift scheduling. Accountability built in.' },
  { title: 'Sales Analytics', desc: 'Daily, weekly, monthly breakdowns. Exportable reports. Data that helps you make decisions.' },
  { title: 'Multi-Location', desc: 'One dashboard. Every location. Unified inventory, consolidated reporting, per-location views.' },
  { title: 'Mobile POS', desc: 'Any tablet or phone becomes a checkout terminal. Ring up sales from anywhere in your store.' },
]

const FAQ = [
  { q: 'What hardware do I need?', a: 'Any modern tablet, phone, or computer with a browser. Web-based. Optional: receipt printers, barcode scanners, card readers.' },
  { q: 'Can I migrate from my current POS?', a: 'Yes. CSV imports for products, customers, sales history. One-click import templates for Square, Clover, Shopify POS.' },
  { q: 'Is there a contract?', a: 'No. Month-to-month. Cancel from your dashboard. Zero fees.' },
  { q: 'What kind of support?', a: 'Email and live chat. 2-hour response during business hours. Full knowledge base with video walkthroughs.' },
]

export default function OnyxPage() {
  return (
    <main className="min-h-screen" style={{ background: '#0A0A0A' }}>

      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.h1 variants={fadeUp} className="text-4xl md:text-6xl font-bold"
            style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4A017' }}>
            ONYX POS
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 text-xl max-w-2xl mx-auto" style={{ color: '#E5E5E5' }}>
            The point-of-sale system that does not take a cut of your hustle.
          </motion.p>
          <motion.p variants={fadeUp} className="mt-2 text-lg" style={{ color: '#D4A017' }}>
            $49 a month. Flat. No percentage fees. No contracts. No surprises.
          </motion.p>
          <motion.p variants={fadeUp} className="mt-4 text-sm" style={{ color: '#8A8A8A' }}>
            Built by someone who watched Square skim profits off every swipe and decided to build something better.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 max-w-md mx-auto">
            <EmailCapture source="onyx" color="#D4A017" buttonText="START TRIAL" successTitle="Trial started!" successDesc="Check your email for setup instructions." placeholder="Your business email" />
          </motion.div>
          <motion.p variants={fadeUp} className="mt-3 text-xs" style={{ color: '#8A8A8A' }}>No credit card required. Set up in under 10 minutes.</motion.p>
        </motion.div>
      </section>

      {/* The Problem */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-3xl font-bold mb-8" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4A017' }}>
            The Problem
          </motion.h2>
          <motion.div variants={fadeUp} className="p-6 rounded-xl mb-4" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
            <h3 className="text-sm font-bold mb-2" style={{ color: '#D4A017' }}>DEATH BY PERCENTAGE</h3>
            <p className="text-sm" style={{ color: '#8A8A8A' }}>Every swipe, tap, and scan -- Square takes 2.6% plus 10 cents. On $30,000 a month in sales, that is $780 gone before you pay rent. You earned it. Keep it.</p>
          </motion.div>
          <motion.div variants={fadeUp} className="p-6 rounded-xl mb-4" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
            <h3 className="text-sm font-bold mb-2" style={{ color: '#D4A017' }}>SOFTWARE BUILT FOR CORPORATIONS</h3>
            <p className="text-sm" style={{ color: '#8A8A8A' }}>Most POS systems were designed for enterprise chains, then dumbed down and resold to you at full price. Cluttered dashboards, features you will never touch.</p>
          </motion.div>
          <motion.div variants={fadeUp} className="p-6 rounded-xl" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
            <h3 className="text-sm font-bold mb-2" style={{ color: '#D4A017' }}>SUPPORT THAT DISAPPEARS</h3>
            <p className="text-sm" style={{ color: '#8A8A8A' }}>Something breaks on Saturday during your busiest hours. You submit a ticket. You get an auto-reply. You wait. Nobody comes.</p>
          </motion.div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-5xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-3xl font-bold mb-12" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4A017' }}>
            Everything you need. Nothing you do not.
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map(f => (
              <motion.div key={f.title} variants={fadeUp} className="p-6 rounded-xl" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
                <h3 className="text-sm font-bold tracking-wider mb-2" style={{ color: '#D4A017' }}>{f.title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: '#8A8A8A' }}>{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Real Use */}
      <section className="py-16 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto text-center">
          <motion.p variants={fadeUp} className="text-sm leading-relaxed" style={{ color: '#8A8A8A' }}>
            This is not a demo app. Onyx POS ran a live retail operation -- Mountain Gardens Nursery -- handling real sales, real inventory, real employee time tracking, real payroll data. That is the proof.
          </motion.p>
        </motion.div>
      </section>

      {/* Pricing */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-md mx-auto text-center">
          <motion.div variants={fadeUp} className="p-8 rounded-xl" style={{ background: '#1A1A1A', border: '1px solid #D4A01730' }}>
            <h3 className="text-sm font-bold tracking-wider mb-1" style={{ color: '#D4A017' }}>ONYX PRO</h3>
            <p className="text-4xl font-bold my-4" style={{ color: '#E5E5E5' }}>$49<span className="text-lg font-normal" style={{ color: '#8A8A8A' }}>/mo</span></p>
            <p className="text-xs mb-4" style={{ color: '#8A8A8A' }}>Billed monthly. Cancel anytime. No contracts.</p>
            <ul className="text-left space-y-2 mb-6">
              {['Unlimited transactions', 'Up to 10 employee accounts', 'Inventory management', 'Sales analytics and reporting', 'Mobile POS on any device', 'Multi-location support (up to 3)', 'Email and chat support', 'All future updates included'].map(f => (
                <li key={f} className="text-xs flex items-center gap-2" style={{ color: '#8A8A8A' }}>
                  <span style={{ color: '#D4A017' }}>{'\u2713'}</span> {f}
                </li>
              ))}
            </ul>
            <p className="text-[10px]" style={{ color: '#8A8A8A' }}>Additional locations beyond 3: $19/mo each</p>
          </motion.div>
        </motion.div>
      </section>

      {/* FAQ */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-xl font-bold mb-8" style={{ color: '#D4A017' }}>FAQ</motion.h2>
          <div className="space-y-4">
            {FAQ.map(f => (
              <motion.div key={f.q} variants={fadeUp} className="p-4 rounded-xl" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
                <p className="text-sm font-semibold mb-1" style={{ color: '#E5E5E5' }}>{f.q}</p>
                <p className="text-xs" style={{ color: '#8A8A8A' }}>{f.a}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Final CTA */}
      <section className="py-20 px-6 text-center">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger}>
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-2" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4A017' }}>
            Stop overpaying. Start selling.
          </motion.h2>
          <motion.p variants={fadeUp} className="text-sm mb-6" style={{ color: '#8A8A8A' }}>$49 a month. Unlimited transactions. Set up takes less than 10 minutes.</motion.p>
          <motion.div variants={fadeUp} className="max-w-md mx-auto">
            <EmailCapture source="onyx" color="#D4A017" buttonText="START TRIAL" successTitle="You're in!" successDesc="Check your email." placeholder="Your business email" />
          </motion.div>
        </motion.div>
      </section>
    </main>
  )
}
