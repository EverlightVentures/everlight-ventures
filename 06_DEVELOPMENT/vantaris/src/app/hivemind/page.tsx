'use client'

import { motion } from 'framer-motion'
import { PageHero } from '@/components/shared/PageHero'
import { GlassCard } from '@/components/shared/GlassCard'
import { SectionDivider } from '@/components/shared/SectionDivider'
import { EmailCapture } from '@/components/shared/EmailCapture'

const C = '#7C3AED'

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.1 } } }

const CAPABILITIES = [
  { title: 'COMMAND PLANE', desc: 'One prompt enters. The right agents, tools, and workflows activate. Coding, ops, content, marketing, sales -- all routed automatically.' },
  { title: 'SHARED MEMORY', desc: 'RAG knowledge base, workspace manifests, and persistent notes give every agent the same context. No more repeating yourself.' },
  { title: 'EXECUTIVE BOARD', desc: 'Revenue, incidents, approvals, deal pipeline, performance metrics. One board. Zero tab-switching.' },
  { title: 'MONETIZATION LAYER', desc: 'Stripe, funnels, outreach, digital products, services. One system instead of twelve disconnected side projects.' },
]

const STEPS = [
  { num: '01', title: 'CONNECT', desc: 'Your models, APIs, and revenue rails. Supabase, Stripe, GitHub, Google, n8n. One operating layer.' },
  { num: '02', title: 'DEFINE', desc: 'Workflows decide what runs automatically, what needs approval, what gets escalated, what goes to memory.' },
  { num: '03', title: 'DEPLOY', desc: 'One command triggers agents, tools, workflows, notifications. Results come back with context and a full audit trail.' },
]

const TIERS = [
  { name: 'Solo', price: '$29', desc: 'Command plane + shared memory for solo operators.' },
  { name: 'Pro', price: '$59', desc: 'Business OS, multi-agent workflows, persistent memory, telemetry.', featured: true },
  { name: 'Team', price: '$99', desc: 'Everything in Pro + multi-user, shared workflows, approvals.' },
]

export default function HiveMindPage() {
  return (
    <main className="min-h-screen relative" style={{ background: 'linear-gradient(180deg, #08080c 0%, #0c0c12 50%, #0a0a10 100%)' }}>
      {/* Ambient video background */}
      <video autoPlay muted loop playsInline className="fixed inset-0 w-full h-full object-cover pointer-events-none" style={{ opacity: 0.12, zIndex: 0 }}>
        <source src="/videos/hivemind-loop.mp4" type="video/mp4" />
      </video>
      <div className="fixed inset-0 pointer-events-none" style={{ background: 'radial-gradient(ellipse at 50% 50%, transparent 30%, rgba(8,8,12,0.9) 100%)', zIndex: 0 }} />

      <PageHero
        overline="Hive Mind"
        title="One operating system. Not twelve tools."
        subtitle="Agents. Workflows. Memory. Revenue. One layer."
        description="This is the system running Everlight Ventures right now. We are packaging it for operators who think the same way."
        color={C}>
        <div className="mt-10 max-w-md mx-auto">
          <EmailCapture source="hivemind" color={C} buttonText="JOIN WAITLIST" successTitle="You're on the list." successDesc="Founding pricing for the first 50." placeholder="your@email.com" />
          <p className="mt-3 text-[11px]" style={{ color: '#555' }}>Early access opening Q2 2026. Limited seats.</p>
        </div>
      </PageHero>

      <SectionDivider color={C} />

      {/* Capabilities */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={stagger} className="max-w-5xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>Architecture</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-5xl font-bold mb-16" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            What it actually is.
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {CAPABILITIES.map(c => (
              <motion.div key={c.title} variants={fadeUp}>
                <GlassCard color={C}><div className="p-7">
                  <h3 className="text-[11px] font-bold tracking-[0.15em] mb-3" style={{ color: C }}>{c.title}</h3>
                  <p className="text-[13px] leading-[1.8]" style={{ color: '#888' }}>{c.desc}</p>
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
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>Process</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-5xl font-bold mb-16" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            Three steps.
          </motion.h2>
          <div className="space-y-4">
            {STEPS.map(s => (
              <motion.div key={s.num} variants={fadeUp}>
                <GlassCard color={C}><div className="p-7 flex gap-6 items-start">
                  <span className="text-3xl font-bold shrink-0" style={{ fontFamily: "'Cormorant Garamond', serif", color: `${C}30` }}>{s.num}</span>
                  <div>
                    <h3 className="text-[11px] font-bold tracking-[0.15em] mb-2" style={{ color: C }}>{s.title}</h3>
                    <p className="text-[13px] leading-[1.8]" style={{ color: '#888' }}>{s.desc}</p>
                  </div>
                </div></GlassCard>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <SectionDivider color={C} />

      {/* Pricing */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-3xl font-bold text-center mb-12" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>Pricing (Planned)</motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {TIERS.map(t => (
              <motion.div key={t.name} variants={fadeUp}>
                <GlassCard color={t.featured ? C : '#fff'} hover={false}><div className="p-8 text-center">
                  <p className="text-[11px] font-bold tracking-[0.15em] mb-4" style={{ color: t.featured ? C : '#666' }}>{t.name}</p>
                  <p className="text-4xl font-bold mb-4" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>{t.price}<span className="text-sm font-light" style={{ color: '#555' }}>/mo</span></p>
                  <p className="text-[13px] leading-[1.7]" style={{ color: '#777' }}>{t.desc}</p>
                </div></GlassCard>
              </motion.div>
            ))}
          </div>
          <p className="text-[11px] text-center mt-6" style={{ color: '#555' }}>Founding members get their tier price locked for life.</p>
        </motion.div>
      </section>
    </main>
  )
}
