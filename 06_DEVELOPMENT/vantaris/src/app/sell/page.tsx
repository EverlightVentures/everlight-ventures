'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import { useLeadForm } from '@/hooks/useLeadForm'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const STATS = [
  { number: '7-Day', label: 'Average Close' },
  { number: '100%', label: 'Cash Offers' },
  { number: '6', label: 'Active Markets' },
]

const STEPS = [
  { num: '01', title: 'Submit Your Property', desc: 'Tell us about your property. Address, condition, situation. Takes 2 minutes.' },
  { num: '02', title: 'Receive a Cash Offer', desc: 'We evaluate the property and send you a no-obligation cash offer within 24 hours.' },
  { num: '03', title: 'Close on Your Timeline', desc: 'Pick your closing date. We handle title, escrow, and paperwork. Close in as little as 7 days.' },
]

const MARKETS = ['Atlanta', 'Dallas', 'Cleveland', 'St. Louis', 'Jacksonville', 'Sacramento']

function PropertyForm() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [message, setMessage] = useState('')
  const { loading, submitted, error, handleSubmit } = useLeadForm({ source: 'wholesale' })

  if (submitted) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-6 rounded-xl text-center" style={{ background: '#1A1A1A', border: '1px solid #D4AF3730' }}>
        <p className="text-lg font-bold" style={{ color: '#D4AF37', fontFamily: "'Cormorant Garamond', serif" }}>Submission Received</p>
        <p className="text-sm mt-2" style={{ color: '#8A8A8A' }}>We will send you a cash offer within 24 hours.</p>
      </motion.div>
    )
  }

  const inputStyle = { background: '#1A1A1A', border: '1px solid #2A2A2A', color: '#E5E5E5' }

  return (
    <form onSubmit={e => { e.preventDefault(); handleSubmit({ email, name, phone, message, metadata: { address } }) }} className="space-y-4">
      <input type="text" placeholder="Your Name" value={name} onChange={e => setName(e.target.value)} required className="w-full px-4 py-3 rounded-xl text-sm outline-none" style={inputStyle} />
      <input type="text" placeholder="Property Address" value={address} onChange={e => setAddress(e.target.value)} required className="w-full px-4 py-3 rounded-xl text-sm outline-none" style={inputStyle} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full px-4 py-3 rounded-xl text-sm outline-none" style={inputStyle} />
        <input type="tel" placeholder="Phone" value={phone} onChange={e => setPhone(e.target.value)} className="w-full px-4 py-3 rounded-xl text-sm outline-none" style={inputStyle} />
      </div>
      <textarea placeholder="Tell us about the property and your situation" value={message} onChange={e => setMessage(e.target.value)} rows={3} className="w-full px-4 py-3 rounded-xl text-sm outline-none resize-none" style={inputStyle} />
      {error && <p className="text-xs text-red-400">{error}</p>}
      <motion.button type="submit" disabled={loading} className="w-full py-3 rounded-xl text-sm font-bold tracking-widest"
        style={{ background: '#D4AF37', color: '#0A0A0A', opacity: loading ? 0.6 : 1 }}
        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
        {loading ? 'SUBMITTING...' : 'GET MY CASH OFFER'}
      </motion.button>
    </form>
  )
}

export default function SellPage() {
  return (
    <main className="min-h-screen" style={{ background: '#0A0A0A' }}>

      <section className="min-h-[60vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.h1 variants={fadeUp} className="text-4xl md:text-6xl font-bold"
            style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4AF37' }}>
            Get a Cash Offer for Your Property
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 text-lg max-w-2xl mx-auto" style={{ color: '#E5E5E5' }}>
            We buy properties as-is for cash. No agents, no fees, no repairs. Close in as little as 7 days.
          </motion.p>
        </motion.div>
      </section>

      {/* Stats */}
      <section className="py-8 px-6">
        <div className="max-w-3xl mx-auto grid grid-cols-3 gap-6">
          {STATS.map(s => (
            <motion.div key={s.label} initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} className="text-center">
              <p className="text-2xl font-bold" style={{ color: '#D4AF37', fontFamily: "'Cormorant Garamond', serif" }}>{s.number}</p>
              <p className="text-[10px] uppercase tracking-wider mt-1" style={{ color: '#8A8A8A' }}>{s.label}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-8" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4AF37' }}>How It Works</motion.h2>
          <div className="space-y-4">
            {STEPS.map(s => (
              <motion.div key={s.num} variants={fadeUp} className="p-6 rounded-xl flex gap-5 items-start" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
                <span className="text-2xl font-bold shrink-0" style={{ color: '#D4AF37', opacity: 0.4 }}>{s.num}</span>
                <div>
                  <h3 className="text-sm font-bold mb-1" style={{ color: '#D4AF37' }}>{s.title}</h3>
                  <p className="text-xs leading-relaxed" style={{ color: '#8A8A8A' }}>{s.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Markets */}
      <section className="py-12 px-6 text-center">
        <div className="flex flex-wrap justify-center gap-2">
          {MARKETS.map(m => (
            <span key={m} className="px-3 py-1.5 rounded-full text-xs" style={{ background: '#D4AF3710', border: '1px solid #D4AF3720', color: '#D4AF37' }}>{m}</span>
          ))}
        </div>
      </section>

      {/* Form */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-2xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-2" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4AF37' }}>Submit Your Property</motion.h2>
          <motion.p variants={fadeUp} className="text-sm mb-8" style={{ color: '#8A8A8A' }}>No obligation. No pressure. Just a fair cash offer.</motion.p>
          <motion.div variants={fadeUp}><PropertyForm /></motion.div>
        </motion.div>
      </section>
    </main>
  )
}
