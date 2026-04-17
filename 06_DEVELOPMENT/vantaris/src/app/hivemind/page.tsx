'use client'

import { motion } from 'framer-motion'
import { EmailCapture } from '@/components/shared/EmailCapture'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const MODELS = [
  { name: 'Claude', provider: 'Anthropic', color: '#c9a84c', desc: 'Deep reasoning, code generation, long-context analysis.' },
  { name: 'Gemini', provider: 'Google', color: '#58a6ff', desc: 'Multimodal intelligence. Vision, audio, and text.' },
  { name: 'Codex', provider: 'OpenAI', color: '#00e676', desc: 'Code-first agent. Build, debug, deploy.' },
  { name: 'Perplexity', provider: 'Perplexity AI', color: '#9b59b6', desc: 'Real-time web research with citations.' },
]

const FEATURES = [
  { title: 'War Room', desc: 'All four AI models in one interface. Ask a question, get four perspectives. Pick the best answer or let them debate.' },
  { title: 'Agent Teams', desc: '42 specialized AI agents organized into fire teams. Each has a name, personality, and domain expertise. They collaborate like a real company.' },
  { title: 'Auto-Dispatch', desc: 'Describe what you need. The system classifies your request and routes it to the right agents automatically. No manual assignment.' },
  { title: 'Memory Layer', desc: 'Blinko-powered RAG knowledge base. Your AI remembers past conversations, decisions, and context across sessions.' },
  { title: 'Slack Integration', desc: 'Agents post updates, reports, and alerts directly to your Slack channels. Stay informed without checking dashboards.' },
  { title: 'Google Docs Output', desc: 'Every report, analysis, and deliverable auto-published to branded Google Docs. Professional output, zero formatting.' },
]

const TIERS = [
  { name: 'Solo', price: '$29', features: ['1 user', '4 AI models', 'Basic agents', '1,000 queries/mo'] },
  { name: 'Team', price: '$79', features: ['5 users', 'Full agent roster', 'Slack integration', '10,000 queries/mo'], featured: true },
  { name: 'Enterprise', price: '$149', features: ['Unlimited users', 'Custom agents', 'API access', 'Unlimited queries', 'Priority support'] },
]

export default function HiveMindPage() {
  return (
    <main className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>

      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.p variants={fadeUp} className="text-xs uppercase tracking-widest mb-4" style={{ color: '#58a6ff', letterSpacing: '4px' }}>
            EVERLIGHT VENTURES
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-5xl md:text-7xl font-bold"
            style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #58a6ff, #8ec5ff, #58a6ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            HIVE MIND AI
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 text-xl max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
            Claude, Gemini, Codex, and Perplexity in one war room. 42 AI agents that work like a real team. The platform that replaced a $50,000/year operations team.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 max-w-md mx-auto">
            <EmailCapture source="hivemind" color="#58a6ff" buttonText="REQUEST ACCESS" successTitle="Access requested." successDesc="We'll send your invite within 48 hours." />
          </motion.div>
        </motion.div>
      </section>

      {/* Models */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold text-center mb-12" style={{ fontFamily: "'Cinzel', serif", color: '#58a6ff' }}>
            Four Models. One Brain.
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {MODELS.map(m => (
              <motion.div key={m.name} variants={fadeUp} className="p-6 rounded-2xl"
                style={{ background: `${m.color}06`, border: `1px solid ${m.color}20` }}>
                <h3 className="text-lg font-bold mb-1" style={{ color: m.color, fontFamily: "'Cinzel', serif" }}>{m.name}</h3>
                <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--text-tertiary)' }}>{m.provider}</p>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{m.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-5xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold text-center mb-12" style={{ fontFamily: "'Cinzel', serif", color: '#58a6ff' }}>
            How It Works
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map(f => (
              <motion.div key={f.title} variants={fadeUp} className="p-6 rounded-2xl"
                style={{ background: 'rgba(88,166,255,0.05)', border: '1px solid rgba(88,166,255,0.15)' }}>
                <h3 className="text-sm font-bold tracking-wider mb-2" style={{ color: '#58a6ff', fontFamily: "'Cinzel', serif" }}>{f.title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-tertiary)' }}>{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Pricing */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl md:text-4xl font-bold text-center mb-12" style={{ fontFamily: "'Cinzel', serif", color: '#58a6ff' }}>
            Pricing
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {TIERS.map(t => (
              <motion.div key={t.name} variants={fadeUp} className="p-6 rounded-2xl text-center"
                style={{
                  background: t.featured ? 'rgba(88,166,255,0.08)' : 'rgba(255,255,255,0.02)',
                  border: `1px solid ${t.featured ? 'rgba(88,166,255,0.3)' : 'rgba(255,255,255,0.08)'}`,
                }}>
                <h3 className="text-sm font-bold tracking-wider mb-3" style={{ color: t.featured ? '#58a6ff' : 'var(--text-secondary)', fontFamily: "'Cinzel', serif" }}>{t.name}</h3>
                <p className="text-3xl font-bold" style={{ color: '#fff' }}>{t.price}<span className="text-sm font-normal" style={{ color: 'var(--text-tertiary)' }}>/mo</span></p>
                <ul className="mt-4 space-y-2 text-left">
                  {t.features.map(f => (
                    <li key={f} className="text-xs flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
                      <span style={{ color: '#58a6ff' }}>{'\u2713'}</span> {f}
                    </li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>
    </main>
  )
}
