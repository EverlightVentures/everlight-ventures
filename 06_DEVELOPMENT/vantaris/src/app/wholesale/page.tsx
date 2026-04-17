'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import { useLeadForm } from '@/hooks/useLeadForm'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const PROCESS = [
  { step: '01', title: 'We Find the Deal', desc: 'Our AI scouts distressed properties daily -- pre-foreclosures, tax liens, code violations, tired landlords. We find sellers who need to move fast.' },
  { step: '02', title: 'We Lock the Contract', desc: 'We negotiate directly with sellers and lock properties under contract at wholesale prices. No middlemen, no inflated ARVs.' },
  { step: '03', title: 'We Deliver to You', desc: 'Cash buyers and investors get pre-packaged deals with comps, repair estimates, ARV analysis, and title work already started.' },
  { step: '04', title: 'You Close and Profit', desc: 'Buy at wholesale, rehab or rent, and keep the spread. We handle the legwork. You bring the capital.' },
]

const MARKETS = [
  'Sacramento, CA', 'Fairfield, CA', 'Vallejo, CA', 'Oakland, CA',
  'Stockton, CA', 'Modesto, CA', 'Fresno, CA', 'Bakersfield, CA',
]

function BuyerSignup() {
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const { loading, submitted, error, handleSubmit } = useLeadForm({ source: 'wholesale' })

  if (submitted) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-6 rounded-2xl text-center" style={{ background: 'rgba(39,174,96,0.08)', border: '1px solid rgba(39,174,96,0.3)' }}>
        <p className="text-lg font-bold" style={{ color: '#27ae60', fontFamily: "'Cinzel', serif" }}>You're on the list.</p>
        <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>We'll send you deals as they come in. Check your email.</p>
      </motion.div>
    )
  }

  return (
    <form onSubmit={e => { e.preventDefault(); handleSubmit({ email, name, phone }) }} className="space-y-4">
      <input type="text" placeholder="Your name" value={name} onChange={e => setName(e.target.value)} required
        className="w-full px-4 py-3 rounded-xl text-sm outline-none"
        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
      <input type="email" placeholder="Email address" value={email} onChange={e => setEmail(e.target.value)} required
        className="w-full px-4 py-3 rounded-xl text-sm outline-none"
        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
      <input type="tel" placeholder="Phone (optional)" value={phone} onChange={e => setPhone(e.target.value)}
        className="w-full px-4 py-3 rounded-xl text-sm outline-none"
        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
      {error && <p className="text-xs text-red-400">{error}</p>}
      <motion.button type="submit" disabled={loading} className="w-full py-3 rounded-xl text-sm font-bold tracking-widest"
        style={{ background: 'linear-gradient(135deg, #27ae60, #58d68d)', color: '#000', fontFamily: "'Cinzel', serif", opacity: loading ? 0.6 : 1 }}
        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
        {loading ? 'SUBMITTING...' : 'JOIN BUYER LIST'}
      </motion.button>
    </form>
  )
}

export default function WholesalePage() {
  return (
    <main className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>

      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.p variants={fadeUp} className="text-xs uppercase tracking-widest mb-4" style={{ color: '#27ae60', letterSpacing: '4px' }}>
            EVERLIGHT VENTURES
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-5xl md:text-7xl font-bold"
            style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #27ae60, #58d68d, #27ae60)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            WHOLESALE
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 text-xl max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
            Off-market distressed properties delivered to cash buyers and investors. AI-powered deal sourcing. No license needed in California.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 max-w-md mx-auto">
            <BuyerSignup />
          </motion.div>
        </motion.div>
      </section>

      {/* Process */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold text-center mb-12" style={{ fontFamily: "'Cinzel', serif", color: '#27ae60' }}>
            How It Works
          </motion.h2>
          <div className="space-y-4">
            {PROCESS.map(p => (
              <motion.div key={p.step} variants={fadeUp} className="p-6 rounded-2xl flex gap-6 items-start"
                style={{ background: 'rgba(39,174,96,0.05)', border: '1px solid rgba(39,174,96,0.15)' }}>
                <span className="text-3xl font-bold shrink-0" style={{ color: '#27ae60', fontFamily: "'Cinzel', serif", opacity: 0.4 }}>{p.step}</span>
                <div>
                  <h3 className="text-sm font-bold tracking-wider mb-2" style={{ color: '#27ae60', fontFamily: "'Cinzel', serif" }}>{p.title}</h3>
                  <p className="text-xs leading-relaxed" style={{ color: 'var(--text-tertiary)' }}>{p.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Markets */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto text-center">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-8" style={{ fontFamily: "'Cinzel', serif", color: '#27ae60' }}>
            Active Markets
          </motion.h2>
          <div className="flex flex-wrap justify-center gap-2">
            {MARKETS.map(m => (
              <motion.span key={m} variants={fadeUp} className="px-3 py-1.5 rounded-full text-xs"
                style={{ background: 'rgba(39,174,96,0.1)', border: '1px solid rgba(39,174,96,0.2)', color: '#27ae60' }}>
                {m}
              </motion.span>
            ))}
          </div>
        </motion.div>
      </section>

      <section className="py-16 px-6 text-center">
        <motion.p initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
          Everlight Ventures LLC -- Licensed and insured. Not a real estate brokerage. We operate as principals (equitable interest holders) in all transactions.
        </motion.p>
      </section>
    </main>
  )
}
