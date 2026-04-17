'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { EmailCapture } from '@/components/shared/EmailCapture'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const FEATURES = [
  { title: '$49/mo Flat', desc: 'No percentage fees. No hidden charges. No transaction cuts. One price, unlimited sales.', icon: '\u2B23' },
  { title: 'Real Retail Tested', desc: 'Built and battle-tested in a live retail store. Not a Silicon Valley prototype -- a working tool.', icon: '\u2713' },
  { title: 'Inventory Tracking', desc: 'Real-time stock levels, low-stock alerts, barcode scanning. Know what you have and what you need.', icon: '\u2637' },
  { title: 'Employee Management', desc: 'Clock in/out, permissions, sales tracking per employee. Trust but verify.', icon: '\u2605' },
  { title: 'Analytics Dashboard', desc: 'Daily sales, top products, peak hours, profit margins. Data that helps you make money.', icon: '\u2B50' },
  { title: 'Offline Mode', desc: 'Internet goes down? Keep selling. Syncs when you reconnect. Your business never stops.', icon: '\u26A1' },
]

const PRICING = [
  { name: 'Starter', price: '$49', period: '/mo', features: ['1 register', 'Unlimited transactions', 'Basic analytics', 'Email support'], cta: 'Start Free Trial' },
  { name: 'Pro', price: '$99', period: '/mo', features: ['3 registers', 'Advanced analytics', 'Employee management', 'Priority support', 'API access'], cta: 'Start Free Trial', featured: true },
  { name: 'Enterprise', price: '$199', period: '/mo', features: ['Unlimited registers', 'Multi-location', 'Custom integrations', 'Dedicated support', 'White-label option'], cta: 'Contact Sales' },
]

export default function OnyxPage() {
  return (
    <main className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>

      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.p variants={fadeUp} className="text-xs uppercase tracking-widest mb-4" style={{ color: '#00e676', letterSpacing: '4px' }}>
            EVERLIGHT VENTURES
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-5xl md:text-7xl font-bold"
            style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #00e676, #69f0ae, #00e676)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            ONYX POS
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 text-xl max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
            Point-of-sale for real retail. No percentage fees. No hidden costs. $49/mo flat. Built by a store owner, for store owners.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 max-w-md mx-auto">
            <EmailCapture source="onyx" color="#00e676" buttonText="START TRIAL" successTitle="Trial started!" successDesc="Check your email for login details." />
          </motion.div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-5xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold text-center mb-12" style={{ fontFamily: "'Cinzel', serif", color: '#00e676' }}>
            Built for the Real World
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map(f => (
              <motion.div key={f.title} variants={fadeUp} className="p-6 rounded-2xl"
                style={{ background: 'rgba(0,230,118,0.05)', border: '1px solid rgba(0,230,118,0.15)' }}>
                <span className="text-2xl block mb-3" style={{ color: '#00e676' }}>{f.icon}</span>
                <h3 className="text-sm font-bold tracking-wider mb-2" style={{ color: '#00e676', fontFamily: "'Cinzel', serif" }}>{f.title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-tertiary)' }}>{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Pricing */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold text-center mb-12" style={{ fontFamily: "'Cinzel', serif", color: '#00e676' }}>
            Simple Pricing
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {PRICING.map(p => (
              <motion.div key={p.name} variants={fadeUp} className="p-6 rounded-2xl text-center"
                style={{
                  background: p.featured ? 'rgba(0,230,118,0.08)' : 'rgba(255,255,255,0.02)',
                  border: `1px solid ${p.featured ? 'rgba(0,230,118,0.3)' : 'rgba(255,255,255,0.08)'}`,
                }}>
                <h3 className="text-sm font-bold tracking-wider mb-3" style={{ color: p.featured ? '#00e676' : 'var(--text-secondary)', fontFamily: "'Cinzel', serif" }}>{p.name}</h3>
                <p className="text-3xl font-bold" style={{ color: '#fff' }}>{p.price}<span className="text-sm font-normal" style={{ color: 'var(--text-tertiary)' }}>{p.period}</span></p>
                <ul className="mt-4 space-y-2 text-left">
                  {p.features.map(f => (
                    <li key={f} className="text-xs flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
                      <span style={{ color: '#00e676' }}>{'\u2713'}</span> {f}
                    </li>
                  ))}
                </ul>
                <motion.button className="mt-6 w-full py-2 rounded-lg text-xs font-bold tracking-wider"
                  style={{
                    background: p.featured ? 'linear-gradient(135deg, #00e676, #69f0ae)' : 'rgba(255,255,255,0.06)',
                    color: p.featured ? '#000' : 'var(--text-secondary)',
                    border: p.featured ? 'none' : '1px solid rgba(255,255,255,0.1)',
                  }}
                  whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
                  {p.cta}
                </motion.button>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <section className="py-16 px-6 text-center">
        <motion.p initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
          No contracts. Cancel anytime. 14-day free trial on all plans.
        </motion.p>
      </section>
    </main>
  )
}
