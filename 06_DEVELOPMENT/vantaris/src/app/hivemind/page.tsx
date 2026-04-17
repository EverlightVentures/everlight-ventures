'use client'

import { motion } from 'framer-motion'
import { EmailCapture } from '@/components/shared/EmailCapture'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const CAPABILITIES = [
  { title: 'COMMAND PLANE', desc: 'Hive routes requests across coding, broker ops, automation, content, and trading review. One prompt enters. The right agents, tools, and workflows activate.' },
  { title: 'SHARED MEMORY', desc: 'MCP resources, workspace manifests, RAG, and notes give every agent the same project context. Less repetition. Better hand-offs.' },
  { title: 'EXECUTIVE BOARD', desc: 'Business OS shows revenue streams, incidents, approvals, broker pipeline, and the trading watchtower in one board. You see what is moving and what is broken without opening six apps.' },
  { title: 'MONETIZATION LAYER', desc: 'Stripe, funnels, outreach, affiliate drops, digital products, and services all feed the same system instead of living as disconnected side projects.' },
]

const STEPS = [
  { num: '01', title: 'CONNECT THE STACK', desc: 'Your models, your APIs, your revenue rails. Supabase, Stripe, GitHub, Google, n8n, and your chosen agents connect into one operating layer.' },
  { num: '02', title: 'DEFINE THE CONTROL FLOW', desc: 'Workflows decide what can run automatically, what needs approval, what gets escalated, and what goes back into memory.' },
  { num: '03', title: 'LET THE HIVE RUN', desc: 'One command triggers agents, tools, workflows, and notifications. The result comes back with context, artifacts, telemetry, and a record of what the system actually did.' },
]

const TIERS = [
  { name: 'Solo', price: '$29', desc: 'For solo operators who need the command plane and shared memory.' },
  { name: 'Pro', price: '$59', desc: 'Business OS dashboard, multi-agent workflows, persistent memory, and public/private telemetry surfaces.', featured: true },
  { name: 'Team', price: '$99', desc: 'Everything in Pro plus multi-user access, shared workflows, and approvals across the team.' },
]

export default function HiveMindPage() {
  return (
    <main className="min-h-screen" style={{ background: '#0A0A0A' }}>

      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.h1 variants={fadeUp} className="text-4xl md:text-6xl font-bold"
            style={{ fontFamily: "'Cormorant Garamond', serif", color: '#7C3AED' }}>
            HIVE MIND
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 text-xl max-w-2xl mx-auto" style={{ color: '#E5E5E5' }}>
            Stop juggling tools. Start running one operating system.
          </motion.p>
          <motion.p variants={fadeUp} className="mt-4 text-sm max-w-xl mx-auto" style={{ color: '#8A8A8A' }}>
            Agents. Workflows. Shared memory. Approvals. Revenue telemetry. One command layer for the whole machine. This is the system running Everlight Ventures right now. We are packaging it for operators who think the same way.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 max-w-md mx-auto">
            <EmailCapture source="hivemind" color="#7C3AED" buttonText="JOIN WAITLIST" successTitle="You're on the list." successDesc="Founding pricing for the first 50 members." placeholder="your@email.com" />
          </motion.div>
          <motion.p variants={fadeUp} className="mt-3 text-xs" style={{ color: '#8A8A8A' }}>Early access opening Q2 2026. Limited seats.</motion.p>
        </motion.div>
      </section>

      {/* The Problem */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-6" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#7C3AED' }}>
            You have AI subscriptions. You do not have an operating system.
          </motion.h2>
          <motion.p variants={fadeUp} className="text-sm leading-relaxed mb-4" style={{ color: '#8A8A8A' }}>
            Right now you are still the middleware. Strategy lives in one chat. Code lives in another. Ops tasks sit in notes. Stripe events, leads, alerts, and broker deals all happen in separate tools. The work may be smart, but the system is still fragmented.
          </motion.p>
          <motion.p variants={fadeUp} className="text-sm leading-relaxed" style={{ color: '#8A8A8A' }}>
            Every context switch costs time. Every missing hand-off costs money. Every stale dashboard costs trust. If your business only runs when you are watching it, you do not have leverage yet.
          </motion.p>
        </motion.div>
      </section>

      {/* What It Is */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-8" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#7C3AED' }}>
            What It Actually Is
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {CAPABILITIES.map(c => (
              <motion.div key={c.title} variants={fadeUp} className="p-6 rounded-xl" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
                <h3 className="text-xs font-bold tracking-wider mb-2" style={{ color: '#7C3AED' }}>{c.title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: '#8A8A8A' }}>{c.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-8" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#7C3AED' }}>How It Works</motion.h2>
          <div className="space-y-4">
            {STEPS.map(s => (
              <motion.div key={s.num} variants={fadeUp} className="p-6 rounded-xl flex gap-5 items-start" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
                <span className="text-2xl font-bold shrink-0" style={{ color: '#7C3AED', opacity: 0.4 }}>{s.num}</span>
                <div>
                  <h3 className="text-xs font-bold tracking-wider mb-1" style={{ color: '#7C3AED' }}>{s.title}</h3>
                  <p className="text-xs leading-relaxed" style={{ color: '#8A8A8A' }}>{s.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Built In Production */}
      <section className="py-16 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto text-center">
          <motion.p variants={fadeUp} className="text-sm leading-relaxed" style={{ color: '#8A8A8A' }}>
            Hive Mind is the internal system that runs Everlight Ventures. It is not being designed. It is being used. It manages broker workflows, the trading watchtower, lead funnels, content systems, and internal ops across the portfolio. What we are building for you is a productized version of what already exists. When it ships, it will not be version one. It will be the version we have been running on ourselves.
          </motion.p>
        </motion.div>
      </section>

      {/* Pricing */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold text-center mb-8" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#7C3AED' }}>Pricing (Planned)</motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {TIERS.map(t => (
              <motion.div key={t.name} variants={fadeUp} className="p-6 rounded-xl text-center"
                style={{ background: t.featured ? '#7C3AED08' : '#1A1A1A', border: `1px solid ${t.featured ? '#7C3AED30' : '#2A2A2A'}` }}>
                <h3 className="text-sm font-bold tracking-wider mb-3" style={{ color: t.featured ? '#7C3AED' : '#8A8A8A' }}>{t.name}</h3>
                <p className="text-3xl font-bold" style={{ color: '#E5E5E5' }}>{t.price}<span className="text-sm font-normal" style={{ color: '#8A8A8A' }}>/mo</span></p>
                <p className="text-xs mt-3" style={{ color: '#8A8A8A' }}>{t.desc}</p>
              </motion.div>
            ))}
          </div>
          <p className="text-xs text-center mt-4" style={{ color: '#8A8A8A' }}>Founding members get their tier price locked for life.</p>
        </motion.div>
      </section>
    </main>
  )
}
