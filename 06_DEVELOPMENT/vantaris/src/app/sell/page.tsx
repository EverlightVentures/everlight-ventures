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
  { title: 'WHEN THE LETTERS KEEP COMING', desc: "Behind on payments. Notices in the mail. Every month feels heavier than the last. You don't need a six-month listing. You need a way out that respects your timing." },
  { title: 'A HOUSE YOU DIDN\'T ASK FOR', desc: "Inherited from family. Out of state. Full of memories you can't sort through right now. Taxes and insurance bleed every month. We can take it from here." },
  { title: 'MORE REPAIRS THAN YOU HAVE', desc: "Roof, foundation, plumbing, the whole list. Listing agents quote a year of work first. We buy as-is, no contractor walkthroughs, no scope-creep." },
  { title: 'LIFE MOVED FIRST', desc: "Divorce. Job two states away. New chapter. The house is the last thing standing between you and the next thing. We move at the speed your life is moving." },
  { title: 'YOU\'RE DONE BEING A LANDLORD', desc: "Late rent, broken windows, midnight calls. You earned the equity. You don't owe the property another year of your weekends." },
  { title: 'THE CITY IS LOSING PATIENCE', desc: "Code violations stacking. Liens compounding. You want resolution, not another letter. We work directly with title to clear it at close." },
]

const STEPS = [
  { num: '01', title: 'Tell Us Where You Stand',         desc: "Address, condition, what's actually going on. Two minutes. We listen first, then we work the numbers. No pressure to decide on the spot." },
  { num: '02', title: 'A Real Number Within 24 Hours',   desc: "Not a teaser, not a moving target. The price we send is the price we close at. If we change something, we tell you why, in plain English." },
  { num: '03', title: 'You Pick The Day',                desc: "Seven days, thirty days, after the kids' school year, after probate clears. We work to your calendar. Title, escrow, paperwork is on us." },
]

const TRUST = [
  { stat: '$0',    label: 'Agent fees or commissions' },
  { stat: '7 Days', label: 'Possible close' },
  { stat: '100%',  label: 'Cash, the check clears' },
  { stat: 'As-Is', label: 'Bring nothing but the keys' },
]

const WHY_US = [
  {
    title: 'WE LISTEN BEFORE WE MAKE AN OFFER',
    desc: "Most cash buyers send the same lowball within an hour. We read what you wrote. We pull the comps. We call you. Then we make a number we can stand behind."
  },
  {
    title: 'NO LOWBALL-THEN-RENEGOTIATE',
    desc: "Some buyers throw out a high number, sign you up, then chip away during inspection. We quote the close price. If something's off, we tell you before contract, not after."
  },
  {
    title: 'TRANSPARENT ABOUT WHERE WE WORK',
    desc: "We're active in California, Ohio, Texas, Georgia, Florida, Arizona, Tennessee, and Missouri. If you're outside our footprint, we tell you and refer you to a partner who actually buys there. We don't string people along."
  },
  {
    title: 'YOUR STORY IS NOT FOR SALE',
    desc: "Your name, address, and situation stay with us and the closing team. We don't sell your info to a 'buyer list' or auction it across investors. Inbound seller > outbound cold list, and we treat you that way."
  },
  {
    title: 'BUILT BY OPERATORS, NOT MIDDLEMEN',
    desc: "We close because we want the house, not because we have to. We use real escrow, real title, real attorneys when the situation calls for it. The check clears. Always."
  },
  {
    title: 'WHEN WE CAN\'T HELP, WE SAY SO',
    desc: "Some houses don't fit our buy box. Some situations need a different kind of help. We tell you on the call, point you to who's better suited, and wish you well. No bait-and-bounce."
  },
]

// Active wholesale states. Mirror of state_gates.json (active_in_pipeline=true).
// Shown to visitors so they know up-front whether we work in their area.
const ACTIVE_STATES: { code: string; name: string; cities: string[] }[] = [
  { code: 'CA', name: 'California', cities: ['Sacramento', 'Fairfield', 'Vallejo', 'Oakland', 'Stockton'] },
  { code: 'OH', name: 'Ohio',       cities: ['Cleveland', 'Columbus', 'Cincinnati'] },
  { code: 'TX', name: 'Texas',      cities: ['Dallas', 'Houston', 'San Antonio'] },
  { code: 'GA', name: 'Georgia',    cities: ['Atlanta', 'Savannah'] },
  { code: 'FL', name: 'Florida',    cities: ['Tampa', 'Orlando', 'Jacksonville'] },
  { code: 'AZ', name: 'Arizona',    cities: ['Phoenix', 'Tucson'] },
  { code: 'TN', name: 'Tennessee',  cities: ['Nashville', 'Memphis'] },
  { code: 'MO', name: 'Missouri',   cities: ['St Louis', 'Kansas City'] },
]
const MARKETS = ACTIVE_STATES.flatMap(s => s.cities)

function detectState(address: string): string {
  const m = address.toUpperCase().match(/,\s*([A-Z]{2})\s*(?:\d{5}|$|,)/)
  return m ? m[1] : ''
}

function PropertyForm() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [situation, setSituation] = useState('')
  const [preforeclosure, setPreforeclosure] = useState(false)
  const { loading, submitted, error, handleSubmit } = useLeadForm({ source: 'wholesale' })

  const detectedState = detectState(address)
  const stateActive = detectedState && ACTIVE_STATES.some(s => s.code === detectedState)
  const stateInactive = detectedState && !stateActive

  if (submitted) {
    return (
      <GlassCard color={C} hover={false}><div className="p-8 text-center">
        <p className="text-2xl font-bold" style={{ fontFamily: "'Cormorant Garamond', serif", color: C }}>We've got it from here.</p>
        <p className="text-sm mt-3 max-w-md mx-auto leading-relaxed" style={{ color: '#aaa' }}>
          A real person will call you within 24 hours. We'll listen first, ask a few questions, and follow up with a number you can sit with. No pressure. No spam. No hard pitch.
        </p>
        <p className="text-[11px] mt-4" style={{ color: '#666' }}>If we're not the right fit, we'll tell you who is.</p>
      </div></GlassCard>
    )
  }

  const inputStyle = { background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', color: '#eee', borderRadius: '12px' }

  return (
    <form onSubmit={e => { e.preventDefault(); handleSubmit({ email, name, phone, message: situation, metadata: { address, state: detectedState, preforeclosure } }) }} className="space-y-4">
      <input type="text" placeholder="Your name" value={name} onChange={e => setName(e.target.value)} required className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />
      <input type="text" placeholder="Property address (street, city, ST zip)" value={address} onChange={e => setAddress(e.target.value)} required className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />
      {stateInactive && (
        <p className="text-[11px] px-1" style={{ color: '#d4a843' }}>
          We don't currently buy in {detectedState}. Submit anyway and we'll refer you to a vetted partner who does.
        </p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />
        <input type="tel" placeholder="Phone" value={phone} onChange={e => setPhone(e.target.value)} className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />
      </div>
      <textarea placeholder="What's going on? (foreclosure, inherited, repairs, relocating, etc.)" value={situation} onChange={e => setSituation(e.target.value)} rows={3} className="w-full px-4 py-3 text-sm outline-none resize-none" style={inputStyle} />

      <label className="flex items-start gap-3 px-1 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={preforeclosure}
          onChange={e => setPreforeclosure(e.target.checked)}
          className="mt-1 w-4 h-4 cursor-pointer"
          style={{ accentColor: C }}
        />
        <span className="text-[11px] leading-snug" style={{ color: '#888' }}>
          Pre-foreclosure or auction scheduled. Tick this if you've received a Notice of Default, are behind on payments, or have a trustee sale date. Different process applies, different timeline.
        </span>
      </label>

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
        title="When the house has to go, the way it goes matters."
        subtitle="A real number in 24 hours. Close on your timeline. Zero fees, zero games."
        description="Whatever brought you here, divorce, inheritance, job 1,800 miles away, foreclosure breathing down your neck, you don't owe us your story. But if you tell us, we'll work with it. We buy as-is, close in escrow, and the check clears. You walk away whole."
        color={C} />

      <SectionDivider color={C} />

      {/* The Problem -- speak to their pain */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={stagger} className="max-w-5xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>Sound Familiar?</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-5xl font-bold mb-6" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            You're not stuck.<br /><span style={{ color: C }}>You just need the right exit.</span>
          </motion.h2>
          <motion.p variants={fadeUp} className="text-[14px] md:text-[15px] mb-16 max-w-2xl leading-[1.8]" style={{ color: '#888' }}>
            Selling a house in a hard moment isn't a transaction, it's a decision. We've sat at kitchen tables and on phone calls with hundreds of folks in these exact situations. None of them sound the same. None of them deserve a script.
          </motion.p>
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

      {/* Why Us -- the trust play */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={stagger} className="max-w-5xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>Why Everlight</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-5xl font-bold mb-6" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            The cash-offer game has a reputation.<br /><span style={{ color: C }}>We're rebuilding it.</span>
          </motion.h2>
          <motion.p variants={fadeUp} className="text-[14px] md:text-[15px] mb-14 max-w-2xl leading-[1.8]" style={{ color: '#888' }}>
            You've probably gotten the postcards, the spam texts, the "I'll buy your house today!" calls. Most of them are middlemen reselling your information for a fee. We're not them. Here's how we're different, in writing, on a public page, where you can hold us to it.
          </motion.p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {WHY_US.map(w => (
              <motion.div key={w.title} variants={fadeUp}>
                <GlassCard color={C}><div className="p-7">
                  <h3 className="text-[11px] font-bold tracking-[0.15em] mb-3" style={{ color: C }}>{w.title}</h3>
                  <p className="text-[13px] leading-[1.85]" style={{ color: '#aaa' }}>{w.desc}</p>
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
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>How It Works</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-4xl font-bold mb-3" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            Three steps. No surprises.
          </motion.h2>
          <motion.p variants={fadeUp} className="text-[14px] mb-12 max-w-xl leading-[1.7]" style={{ color: '#888' }}>
            We don't make you sit through a sales pitch to find out the number. The whole process, from form to wire transfer, is built to respect your time.
          </motion.p>
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

      {/* Markets -- transparent state list */}
      <section className="py-12 px-6 text-center">
        <p className="text-[10px] uppercase tracking-[0.4em] mb-3" style={{ color: C }}>Where We Operate</p>
        <p className="text-[12px] mb-6 max-w-2xl mx-auto" style={{ color: '#888' }}>
          We're licensed and active in these states. Outside our footprint, we'll refer you to a vetted partner who actually buys in your area, no gatekeeping, no string-along.
        </p>
        <div className="flex flex-wrap justify-center gap-2 max-w-3xl mx-auto">
          {ACTIVE_STATES.map(s => (
            <span key={s.code} className="px-3 py-1 rounded-full text-[11px] tracking-wide"
              style={{ background: `${C}15`, border: `1px solid ${C}30`, color: C }}>
              {s.name}
            </span>
          ))}
        </div>
        <div className="flex flex-wrap justify-center gap-1.5 mt-4 max-w-3xl mx-auto">
          {MARKETS.map(m => (
            <span key={m} className="px-2.5 py-0.5 rounded-full text-[10px]"
              style={{ background: `${C}08`, color: '#888' }}>{m}</span>
          ))}
        </div>
      </section>

      <SectionDivider color={C} />

      {/* The Form -- the money section */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-2xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>Tell Us Where You Stand</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-4xl font-bold mb-3" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            Whenever you're ready, we listen first.
          </motion.h2>
          <motion.p variants={fadeUp} className="text-[14px] mb-10 leading-[1.7]" style={{ color: '#888' }}>
            Two minutes to fill out. We respond with a real call from a real person. You'll have a number you can think about, sleep on, run by your family, and decide on, on your terms.
          </motion.p>
          <motion.div variants={fadeUp}>
            <PropertyForm />
          </motion.div>
        </motion.div>
      </section>
    </main>
  )
}
