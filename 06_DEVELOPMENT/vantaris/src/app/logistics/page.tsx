'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import { PageHero } from '@/components/shared/PageHero'
import { GlassCard } from '@/components/shared/GlassCard'
import { SectionDivider } from '@/components/shared/SectionDivider'
import { useLeadForm } from '@/hooks/useLeadForm'

const C = '#D4963A'

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.1 } } }

const SERVICES = [
  { title: 'E-COMMERCE FULFILLMENT', desc: 'Pick, pack, ship. Integrated with Shopify, WooCommerce, and custom API.' },
  { title: 'LAST-MILE DELIVERY', desc: 'Fast, trackable delivery. Regional carrier partnerships. Route optimization.' },
  { title: 'WAREHOUSE MANAGEMENT', desc: 'Scalable storage. Real-time inventory. Barcode tracking. Zero shrinkage target.' },
  { title: 'SUPPLY CHAIN CONSULTING', desc: 'We audit your stack and build a plan to cut costs and eliminate failure points.' },
]

function QuoteForm() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [company, setCompany] = useState('')
  const [message, setMessage] = useState('')
  const { loading, submitted, error, handleSubmit } = useLeadForm({ source: 'logistics' })

  if (submitted) {
    return (
      <GlassCard color={C} hover={false}><div className="p-8 text-center">
        <p className="text-lg font-bold" style={{ fontFamily: "'Cormorant Garamond', serif", color: C }}>Quote Request Received</p>
        <p className="text-sm mt-2" style={{ color: '#888' }}>Custom logistics plan within 48 hours.</p>
      </div></GlassCard>
    )
  }

  const inputStyle = { background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', color: '#eee', borderRadius: '12px' }

  return (
    <form onSubmit={e => { e.preventDefault(); handleSubmit({ email, name, message, metadata: { company } }) }} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <input type="text" placeholder="Name" value={name} onChange={e => setName(e.target.value)} required className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />
        <input type="text" placeholder="Company" value={company} onChange={e => setCompany(e.target.value)} className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />
      </div>
      <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />
      <textarea placeholder="What do you ship and how much?" value={message} onChange={e => setMessage(e.target.value)} rows={3} className="w-full px-4 py-3 text-sm outline-none resize-none" style={inputStyle} />
      {error && <p className="text-xs text-red-400">{error}</p>}
      <motion.button type="submit" disabled={loading} className="w-full py-3 rounded-full text-xs font-semibold tracking-[0.2em] uppercase"
        style={{ background: C, color: '#0A0A0A', opacity: loading ? 0.6 : 1 }}
        whileHover={{ scale: 1.02, boxShadow: `0 0 30px ${C}20` }} whileTap={{ scale: 0.97 }}>
        {loading ? 'SUBMITTING...' : 'REQUEST A QUOTE'}
      </motion.button>
    </form>
  )
}

export default function LogisticsPage() {
  return (
    <main className="min-h-screen" style={{ background: 'linear-gradient(180deg, #08080c 0%, #0c0c12 50%, #0a0a10 100%)' }}>

      <PageHero
        overline="Everlight Logistics"
        title="Where it all started."
        subtitle="The backbone of every venture."
        description="Fulfillment, warehousing, last-mile delivery, and supply chain consulting. The same automation philosophy that powers the rest of Everlight started here."
        color={C} />

      <SectionDivider color={C} />

      {/* Services */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>Services</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-5xl font-bold mb-16" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            What we do.
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {SERVICES.map(s => (
              <motion.div key={s.title} variants={fadeUp}>
                <GlassCard color={C}><div className="p-7">
                  <h3 className="text-[11px] font-bold tracking-[0.15em] mb-3" style={{ color: C }}>{s.title}</h3>
                  <p className="text-[13px] leading-[1.8]" style={{ color: '#888' }}>{s.desc}</p>
                </div></GlassCard>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <SectionDivider color={C} />

      {/* Quote Form */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-2xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>Get a Quote</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl font-bold mb-8" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            Tell us what you ship.
          </motion.h2>
          <motion.div variants={fadeUp}><QuoteForm /></motion.div>
        </motion.div>
      </section>
    </main>
  )
}
