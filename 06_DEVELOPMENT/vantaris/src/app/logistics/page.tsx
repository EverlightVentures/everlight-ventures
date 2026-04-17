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
  { title: 'E-COMMERCE FULFILLMENT', desc: 'Pick, pack, and ship. Integrated with your storefront. Shopify, WooCommerce, and custom API supported.' },
  { title: 'LAST-MILE DELIVERY', desc: 'Fast, trackable delivery to your customer\'s door. Regional carrier partnerships and route optimization keep costs low.' },
  { title: 'WAREHOUSE MANAGEMENT', desc: 'Scalable storage with real-time inventory visibility. Barcode tracking, cycle counting, zero shrinkage target.' },
  { title: 'SUPPLY CHAIN CONSULTING', desc: 'We audit your logistics stack and build a plan to cut costs, reduce transit times, and eliminate failure points.' },
]

const PROOF = [
  { title: 'SPEED', desc: 'Two-day fulfillment standard. Same-day processing on orders received before 2 PM PT.' },
  { title: 'RELIABILITY', desc: '99.8% order accuracy. Every package scanned, verified, and tracked from warehouse to doorstep.' },
  { title: 'OPERATOR-BUILT', desc: 'This company was built by someone who ships product. Not a consultant. Not a broker. An operator.' },
]

function QuoteForm() {
  const [name, setName] = useState('')
  const [company, setCompany] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [volume, setVolume] = useState('')
  const [services, setServices] = useState('')
  const { loading, submitted, error, handleSubmit } = useLeadForm({ source: 'logistics' })

  if (submitted) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-6 rounded-xl text-center" style={{ background: '#1A1A1A', border: '1px solid #D4963A30' }}>
        <p className="text-lg font-bold" style={{ color: '#D4963A', fontFamily: "'Cormorant Garamond', serif" }}>Quote Request Received</p>
        <p className="text-sm mt-2" style={{ color: '#8A8A8A' }}>We will put together a custom logistics plan within 48 hours.</p>
      </motion.div>
    )
  }

  const inputStyle = { background: '#1A1A1A', border: '1px solid #2A2A2A', color: '#E5E5E5' }

  return (
    <form onSubmit={e => { e.preventDefault(); handleSubmit({ email, name, phone, message: services, metadata: { company, volume } }) }} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <input type="text" placeholder="Name" value={name} onChange={e => setName(e.target.value)} required className="w-full px-4 py-3 rounded-xl text-sm outline-none" style={inputStyle} />
        <input type="text" placeholder="Company" value={company} onChange={e => setCompany(e.target.value)} className="w-full px-4 py-3 rounded-xl text-sm outline-none" style={inputStyle} />
        <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full px-4 py-3 rounded-xl text-sm outline-none" style={inputStyle} />
        <input type="tel" placeholder="Phone" value={phone} onChange={e => setPhone(e.target.value)} className="w-full px-4 py-3 rounded-xl text-sm outline-none" style={inputStyle} />
      </div>
      <input type="text" placeholder="Monthly Volume (e.g. 500 orders/mo)" value={volume} onChange={e => setVolume(e.target.value)} className="w-full px-4 py-3 rounded-xl text-sm outline-none" style={inputStyle} />
      <textarea placeholder="Services Needed" value={services} onChange={e => setServices(e.target.value)} rows={3} className="w-full px-4 py-3 rounded-xl text-sm outline-none resize-none" style={inputStyle} />
      {error && <p className="text-xs text-red-400">{error}</p>}
      <motion.button type="submit" disabled={loading} className="w-full py-3 rounded-xl text-sm font-bold tracking-widest"
        style={{ background: '#D4963A', color: '#0A0A0A', opacity: loading ? 0.6 : 1 }}
        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
        {loading ? 'SUBMITTING...' : 'REQUEST A QUOTE'}
      </motion.button>
    </form>
  )
}

export default function LogisticsPage() {
  return (
    <main className="min-h-screen" style={{ background: '#0A0A0A' }}>

      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.h1 variants={fadeUp} className="text-4xl md:text-6xl font-bold"
            style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4963A' }}>
            EVERLIGHT LOGISTICS
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-2 text-lg" style={{ color: '#D4963A' }}>Where it all started.</motion.p>
          <motion.p variants={fadeUp} className="mt-4 text-sm max-w-2xl mx-auto leading-relaxed" style={{ color: '#8A8A8A' }}>
            Everlight Logistics LLC is the legal entity behind every venture on this site. Before the books, the game, the software, and the AI -- there was freight. Real shipments, real clients, real margins. We handle fulfillment, warehousing, last-mile delivery, and supply chain consulting for small businesses and e-commerce operators.
          </motion.p>
        </motion.div>
      </section>

      {/* Services */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-8" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4963A' }}>What We Do</motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {SERVICES.map(s => (
              <motion.div key={s.title} variants={fadeUp} className="p-6 rounded-xl" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
                <h3 className="text-xs font-bold tracking-wider mb-2" style={{ color: '#D4963A' }}>{s.title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: '#8A8A8A' }}>{s.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Why Us */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-8" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4963A' }}>Why Us</motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {PROOF.map(p => (
              <motion.div key={p.title} variants={fadeUp} className="p-6 rounded-xl" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
                <h3 className="text-xs font-bold tracking-wider mb-2" style={{ color: '#D4963A' }}>{p.title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: '#8A8A8A' }}>{p.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Quote Form */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-2xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-2" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4963A' }}>Get a Quote</motion.h2>
          <motion.p variants={fadeUp} className="text-sm mb-8" style={{ color: '#8A8A8A' }}>Tell us what you ship and how much. We will put together a custom logistics plan within 48 hours.</motion.p>
          <motion.div variants={fadeUp}>
            <QuoteForm />
          </motion.div>
        </motion.div>
      </section>
    </main>
  )
}
