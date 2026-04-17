'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import { useLeadForm } from '@/hooks/useLeadForm'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const SERVICES = [
  { title: 'Fulfillment', desc: 'We pick, pack, and ship your orders. Same-day processing. Real-time tracking. You sell, we handle the rest.', icon: '\u2B23' },
  { title: 'Warehousing', desc: 'Secure storage in Northern California. Climate controlled. Inventory management included. Scale up or down.', icon: '\u2302' },
  { title: 'Last-Mile Delivery', desc: 'Local delivery for small businesses. Same-day and next-day options. Bay Area and Sacramento coverage.', icon: '\u2708' },
  { title: 'Returns Processing', desc: 'We handle returns, inspect items, restock or dispose. Full reporting on return rates and reasons.', icon: '\u21BA' },
]

const STATS = [
  { number: '24hr', label: 'Average fulfillment time' },
  { number: '99.2%', label: 'Order accuracy rate' },
  { number: '$0', label: 'Setup fees' },
  { number: '50+', label: 'Small businesses served' },
]

function QuoteForm() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const { loading, submitted, error, handleSubmit } = useLeadForm({ source: 'logistics' })

  if (submitted) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-6 rounded-2xl text-center" style={{ background: 'rgba(155,89,182,0.08)', border: '1px solid rgba(155,89,182,0.3)' }}>
        <p className="text-lg font-bold" style={{ color: '#9b59b6', fontFamily: "'Cinzel', serif" }}>Quote Request Received</p>
        <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>We'll get back to you within 24 hours.</p>
      </motion.div>
    )
  }

  return (
    <form onSubmit={e => { e.preventDefault(); handleSubmit({ email, name, message }) }} className="space-y-4">
      <input type="text" placeholder="Your name" value={name} onChange={e => setName(e.target.value)} required
        className="w-full px-4 py-3 rounded-xl text-sm outline-none" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
      <input type="email" placeholder="Email address" value={email} onChange={e => setEmail(e.target.value)} required
        className="w-full px-4 py-3 rounded-xl text-sm outline-none" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
      <textarea placeholder="Tell us about your fulfillment needs" value={message} onChange={e => setMessage(e.target.value)} rows={3} required
        className="w-full px-4 py-3 rounded-xl text-sm outline-none resize-none" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
      {error && <p className="text-xs text-red-400">{error}</p>}
      <motion.button type="submit" disabled={loading} className="w-full py-3 rounded-xl text-sm font-bold tracking-widest"
        style={{ background: 'linear-gradient(135deg, #9b59b6, #c39bd3)', color: '#000', fontFamily: "'Cinzel', serif", opacity: loading ? 0.6 : 1 }}
        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
        {loading ? 'SUBMITTING...' : 'GET A QUOTE'}
      </motion.button>
    </form>
  )
}

export default function LogisticsPage() {
  return (
    <main className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>

      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.p variants={fadeUp} className="text-xs uppercase tracking-widest mb-4" style={{ color: '#9b59b6', letterSpacing: '4px' }}>
            EVERLIGHT VENTURES
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-5xl md:text-7xl font-bold"
            style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #9b59b6, #c39bd3, #9b59b6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            LOGISTICS
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 text-xl max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
            Fulfillment, warehousing, and last-mile delivery for small businesses. You focus on selling. We handle moving product.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 max-w-md mx-auto">
            <QuoteForm />
          </motion.div>
        </motion.div>
      </section>

      {/* Stats */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6">
          {STATS.map(s => (
            <motion.div key={s.label} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center">
              <p className="text-3xl font-bold" style={{ color: '#9b59b6', fontFamily: "'Cinzel', serif" }}>{s.number}</p>
              <p className="text-[10px] uppercase tracking-wider mt-1" style={{ color: 'var(--text-tertiary)' }}>{s.label}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Services */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold text-center mb-12" style={{ fontFamily: "'Cinzel', serif", color: '#9b59b6' }}>
            What We Do
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {SERVICES.map(s => (
              <motion.div key={s.title} variants={fadeUp} className="p-6 rounded-2xl"
                style={{ background: 'rgba(155,89,182,0.05)', border: '1px solid rgba(155,89,182,0.15)' }}>
                <span className="text-2xl block mb-3" style={{ color: '#9b59b6' }}>{s.icon}</span>
                <h3 className="text-sm font-bold tracking-wider mb-2" style={{ color: '#9b59b6', fontFamily: "'Cinzel', serif" }}>{s.title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-tertiary)' }}>{s.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <section className="py-16 px-6 text-center">
        <motion.p initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
          Everlight Logistics LLC -- Fairfield, California. Serving the Bay Area and beyond.
        </motion.p>
      </section>
    </main>
  )
}
