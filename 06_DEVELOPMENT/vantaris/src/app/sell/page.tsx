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
  { title: 'AI Strategy Audit', desc: 'We audit your current operations and identify where AI saves the most time and money. No buzzwords. Just math.', price: '$2,000', icon: '\u2B50' },
  { title: 'Custom AI Build', desc: 'We build your AI system from scratch. Chatbots, automation pipelines, agent workflows, dashboards. Deployed and maintained.', price: '$2k-5k', icon: '\u2699' },
  { title: 'Monthly Retainer', desc: 'Ongoing AI ops. We manage your AI systems, optimize them monthly, and add new capabilities as your business grows.', price: '$2,000/mo', icon: '\u21BA' },
]

const RESULTS = [
  { metric: '$50,000/yr', label: 'Operations cost replaced by AI at Everlight' },
  { metric: '42', label: 'AI agents running 24/7 across 8 ventures' },
  { metric: '5 years', label: 'Of AI-first development experience' },
  { metric: '8', label: 'Operating businesses built with AI' },
]

const STACK = [
  'Claude (Anthropic)', 'Gemini (Google)', 'OpenAI / Codex', 'Perplexity',
  'n8n Automation', 'Supabase', 'Stripe', 'Slack Integration',
  'Custom Dashboards', 'RAG / Knowledge Bases', 'Voice AI', 'Email Automation',
]

function ConsultingForm() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const { loading, submitted, error, handleSubmit } = useLeadForm({ source: 'consulting' })

  if (submitted) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-6 rounded-2xl text-center" style={{ background: 'rgba(201,168,76,0.08)', border: '1px solid rgba(201,168,76,0.3)' }}>
        <p className="text-lg font-bold" style={{ color: 'var(--gold)', fontFamily: "'Cinzel', serif" }}>Request Received</p>
        <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>We'll reach out within 24 hours to schedule a call.</p>
      </motion.div>
    )
  }

  return (
    <form onSubmit={e => { e.preventDefault(); handleSubmit({ email, name, message }) }} className="space-y-4">
      <input type="text" placeholder="Your name" value={name} onChange={e => setName(e.target.value)} required
        className="w-full px-4 py-3 rounded-xl text-sm outline-none" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
      <input type="email" placeholder="Email address" value={email} onChange={e => setEmail(e.target.value)} required
        className="w-full px-4 py-3 rounded-xl text-sm outline-none" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
      <textarea placeholder="What does your business need? What are you trying to automate?" value={message} onChange={e => setMessage(e.target.value)} rows={4} required
        className="w-full px-4 py-3 rounded-xl text-sm outline-none resize-none" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
      {error && <p className="text-xs text-red-400">{error}</p>}
      <motion.button type="submit" disabled={loading} className="w-full py-3 rounded-xl text-sm font-bold tracking-widest"
        style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif", opacity: loading ? 0.6 : 1 }}
        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
        {loading ? 'SUBMITTING...' : 'BOOK A CALL'}
      </motion.button>
    </form>
  )
}

export default function SellPage() {
  return (
    <main className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>

      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.p variants={fadeUp} className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--gold)', letterSpacing: '4px' }}>
            EVERLIGHT VENTURES
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-4xl md:text-6xl font-bold"
            style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #c9a84c, #e8c55a, #c9a84c)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            AI Consulting
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 text-xl max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
            We don't just talk about AI. We run 8 businesses on it. Let us build the same for you.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 max-w-md mx-auto">
            <ConsultingForm />
          </motion.div>
        </motion.div>
      </section>

      {/* Results */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6">
          {RESULTS.map(r => (
            <motion.div key={r.label} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center">
              <p className="text-2xl font-bold" style={{ color: 'var(--gold)', fontFamily: "'Cinzel', serif" }}>{r.metric}</p>
              <p className="text-[10px] uppercase tracking-wider mt-1" style={{ color: 'var(--text-tertiary)' }}>{r.label}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Services */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold text-center mb-12" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
            What We Offer
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {SERVICES.map(s => (
              <motion.div key={s.title} variants={fadeUp} className="p-6 rounded-2xl"
                style={{ background: 'rgba(201,168,76,0.05)', border: '1px solid rgba(201,168,76,0.15)' }}>
                <span className="text-2xl block mb-3" style={{ color: 'var(--gold)' }}>{s.icon}</span>
                <h3 className="text-sm font-bold tracking-wider mb-1" style={{ color: 'var(--gold)', fontFamily: "'Cinzel', serif" }}>{s.title}</h3>
                <p className="text-lg font-bold mb-2" style={{ color: '#fff' }}>{s.price}</p>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-tertiary)' }}>{s.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Stack */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto text-center">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-8" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
            Our Stack
          </motion.h2>
          <div className="flex flex-wrap justify-center gap-2">
            {STACK.map(s => (
              <motion.span key={s} variants={fadeUp} className="px-3 py-1.5 rounded-full text-xs"
                style={{ background: 'rgba(201,168,76,0.1)', border: '1px solid rgba(201,168,76,0.2)', color: 'var(--gold)' }}>
                {s}
              </motion.span>
            ))}
          </div>
        </motion.div>
      </section>

      <section className="py-16 px-6 text-center">
        <motion.p initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
          Everlight Ventures LLC -- Fairfield, California. hello@everlightventures.io
        </motion.p>
      </section>
    </main>
  )
}
