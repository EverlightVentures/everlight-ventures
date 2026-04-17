'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import { PageHero } from '@/components/shared/PageHero'
import { GlassCard } from '@/components/shared/GlassCard'
import { SectionDivider } from '@/components/shared/SectionDivider'
import { useLeadForm } from '@/hooks/useLeadForm'

const C = '#27ae60'

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.1 } } }

const PROBLEMS = [
  { title: 'BEHIND ON PAYMENTS', desc: 'Foreclosure letters piling up. Every month gets worse. You need a fast exit, not a 6-month listing.' },
  { title: 'INHERITED A PROPERTY', desc: 'You never asked for it. Now you are paying taxes, insurance, and maintenance on a house you do not want.' },
  { title: 'COSTLY REPAIRS', desc: 'The roof, the foundation, the plumbing. Fixing it costs more than you have. Agents will not list it as-is.' },
  { title: 'DIVORCE OR RELOCATION', desc: 'Life changed. You need to move fast. Splitting assets, new job, fresh start. Waiting 90 days is not an option.' },
  { title: 'TIRED LANDLORD', desc: 'Bad tenants, late rent, property damage. You are done. You want out without spending another dollar on it.' },
  { title: 'TAX LIENS OR CODE VIOLATIONS', desc: 'The city is breathing down your neck. Fines are compounding. You need this resolved, not dragged out.' },
]

const STEPS = [
  { num: '01', title: 'Tell Us About Your Property', desc: 'Fill out the form below. Address, condition, your situation. Takes 2 minutes. No obligation.' },
  { num: '02', title: 'Get a Cash Offer in 24 Hours', desc: 'We evaluate your property and send a fair, no-pressure cash offer. No inspections. No appraisals. No games.' },
  { num: '03', title: 'Close on Your Timeline', desc: 'You pick the date. We handle title, escrow, and paperwork. Close in as little as 7 days. Walk away with cash.' },
]

const TRUST = [
  { stat: '$0', label: 'Fees or commissions' },
  { stat: '7 Days', label: 'Fastest close' },
  { stat: '100%', label: 'Cash. No financing.' },
  { stat: 'As-Is', label: 'No repairs needed' },
]

const MARKETS = ['Sacramento', 'Fairfield', 'Vallejo', 'Oakland', 'Stockton', 'Atlanta', 'Dallas', 'Cleveland']

function PropertyForm() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [situation, setSituation] = useState('')
  const { loading, submitted, error, handleSubmit } = useLeadForm({ source: 'wholesale' })

  if (submitted) {
    return (
      <GlassCard color={C} hover={false}><div className="p-8 text-center">
        <p className="text-2xl font-bold" style={{ fontFamily: "'Cormorant Garamond', serif", color: C }}>We Got It.</p>
        <p className="text-sm mt-3" style={{ color: '#999' }}>Expect a call and a cash offer within 24 hours. No pressure. No obligation.</p>
      </div></GlassCard>
    )
  }

  const inputStyle = { background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', color: '#eee', borderRadius: '12px' }

  return (
    <form onSubmit={e => { e.preventDefault(); handleSubmit({ email, name, phone, message: situation, metadata: { address } }) }} className="space-y-4">
      <input type="text" placeholder="Your name" value={name} onChange={e => setName(e.target.value)} required className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />
      <input type="text" placeholder="Property address" value={address} onChange={e => setAddress(e.target.value)} required className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />
        <input type="tel" placeholder="Phone" value={phone} onChange={e => setPhone(e.target.value)} className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />
      </div>
      <textarea placeholder="What's going on? (foreclosure, inherited, repairs, relocating, etc.)" value={situation} onChange={e => setSituation(e.target.value)} rows={3} className="w-full px-4 py-3 text-sm outline-none resize-none" style={inputStyle} />
      {error && <p className="text-xs text-red-400">{error}</p>}
      <motion.button type="submit" disabled={loading} className="w-full py-4 rounded-full text-sm font-bold tracking-[0.2em] uppercase"
        style={{ background: C, color: '#fff', opacity: loading ? 0.6 : 1 }}
        whileHover={{ scale: 1.02, boxShadow: `0 0 30px ${C}30` }} whileTap={{ scale: 0.97 }}>
        {loading ? 'SUBMITTING...' : 'GET MY CASH OFFER'}
      </motion.button>
      <p className="text-[10px] text-center" style={{ color: '#555' }}>No obligation. No spam. Just a fair offer.</p>
    </form>
  )
}

export default function SellPage() {
  return (
    <main className="min-h-screen relative" style={{ background: 'linear-gradient(180deg, #08080c 0%, #0c0c12 50%, #0a0a10 100%)' }}>
      <video autoPlay muted loop playsInline className="fixed inset-0 w-full h-full object-cover pointer-events-none" style={{ opacity: 0.15, zIndex: 0 }}>
        <source src="/videos/wholesale-loop.mp4" type="video/mp4" />
      </video>
      <div className="fixed inset-0 pointer-events-none" style={{ background: 'radial-gradient(ellipse at 50% 50%, transparent 40%, rgba(8,8,12,0.85) 100%)', zIndex: 0 }} />

      <PageHero
        overline="Everlight Home Buyers"
        title="Need to sell fast? We buy houses."
        subtitle="Cash offer in 24 hours. Close in 7 days. Zero fees."
        description="No agents. No inspections. No repairs. No waiting. We buy your property as-is for cash and close on your timeline. You walk away clean."
        color={C} />

      <SectionDivider color={C} />

      {/* The Problem -- speak to their pain */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={stagger} className="max-w-5xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>Sound Familiar?</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-5xl font-bold mb-16" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            Your property is a problem.<br /><span style={{ color: C }}>We make it disappear.</span>
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {PROBLEMS.map((p, i) => (
              <motion.div key={p.title} variants={fadeUp}>
                <GlassCard color={C}><div className="p-7">
                  <span className="text-[40px] font-bold leading-none block mb-3" style={{ fontFamily: "'Cormorant Garamond', serif", color: 'rgba(255,255,255,0.03)' }}>{String(i + 1).padStart(2, '0')}</span>
                  <h3 className="text-[11px] font-bold tracking-[0.15em] mb-3" style={{ color: C }}>{p.title}</h3>
                  <p className="text-[13px] leading-[1.8]" style={{ color: '#888' }}>{p.desc}</p>
                </div></GlassCard>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <SectionDivider color={C} />

      {/* Trust strip */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8">
          {TRUST.map((t, i) => (
            <motion.div key={t.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.6 }}
              className="text-center">
              <p className="text-3xl font-bold" style={{ fontFamily: "'Cormorant Garamond', serif", color: C }}>{t.stat}</p>
              <p className="text-[10px] uppercase tracking-[0.2em] mt-2" style={{ color: '#555' }}>{t.label}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <SectionDivider color={C} />

      {/* How It Works */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>How It Works</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-4xl font-bold mb-12" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            Three steps. That's it.
          </motion.h2>
          <div className="space-y-4">
            {STEPS.map(s => (
              <motion.div key={s.num} variants={fadeUp}>
                <GlassCard color={C}><div className="p-7 flex gap-6 items-start">
                  <span className="text-3xl font-bold shrink-0" style={{ fontFamily: "'Cormorant Garamond', serif", color: `${C}30` }}>{s.num}</span>
                  <div>
                    <h3 className="text-sm font-bold mb-2" style={{ color: '#eee' }}>{s.title}</h3>
                    <p className="text-[13px] leading-[1.8]" style={{ color: '#888' }}>{s.desc}</p>
                  </div>
                </div></GlassCard>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <SectionDivider color={C} />

      {/* Markets */}
      <section className="py-12 px-6 text-center">
        <p className="text-[10px] uppercase tracking-[0.4em] mb-4" style={{ color: C }}>Active Markets</p>
        <div className="flex flex-wrap justify-center gap-2">
          {MARKETS.map(m => (
            <span key={m} className="px-4 py-1.5 rounded-full text-[11px] tracking-wide"
              style={{ background: `${C}10`, border: `1px solid ${C}20`, color: C }}>{m}</span>
          ))}
        </div>
      </section>

      <SectionDivider color={C} />

      {/* The Form -- the money section */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-2xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>Get Your Offer</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-4xl font-bold mb-3" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            Ready to walk away clean?
          </motion.h2>
          <motion.p variants={fadeUp} className="text-[14px] mb-10" style={{ color: '#777' }}>
            Fill this out. We call you. You get a number. If it works, we close. If not, no hard feelings.
          </motion.p>
          <motion.div variants={fadeUp}>
            <PropertyForm />
          </motion.div>
        </motion.div>
      </section>
    </main>
  )
}
