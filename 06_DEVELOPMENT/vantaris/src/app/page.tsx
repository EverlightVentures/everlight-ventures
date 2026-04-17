'use client'

import { motion, useScroll, useTransform, useMotionValueEvent, useInView } from 'framer-motion'
import { lazy, Suspense, useRef, useState, useEffect } from 'react'
import Link from 'next/link'

const GoldHeroScene = lazy(() => import('@/components/shared/GoldHeroScene').then(m => ({ default: m.GoldHeroScene })))
import { TextReveal } from '@/components/shared/TextReveal'

/* ================================================================
   EVERLIGHT VENTURES -- HOMEPAGE
   Design references: ABTC (institutional dark luxury), Carles Faus
   (spatial silence), Aventura (warm champagne), Lando Norris (bold
   typography + immersive scroll). Awwwards-tier pacing.
   ================================================================ */

const VENTURES = [
  { name: 'Publishing', desc: 'Children\'s fiction, literary thrillers, interactive learning. Five complete books. Full audiobooks. Available now.', href: '/publishing', color: '#7B5EA7', cta: 'Browse Books' },
  { name: 'Vantaris Casino', desc: 'Provably fair. AI dealers. Six hand-coded games. Sweepstakes model. The house is transparent.', href: '/vantaris', color: '#D4AF37', cta: 'Enter Casino' },
  { name: 'Onyx POS', desc: '$49/mo flat. No percentage fees. Inventory, employees, analytics. Tested on a live retail operation.', href: '/onyx', color: '#D4A017', cta: 'Free Trial' },
  { name: 'Hive Mind', desc: 'Claude, Gemini, Codex, Perplexity. 42 agents. One command layer. The OS that runs Everlight.', href: '/hivemind', color: '#7C3AED', cta: 'Waitlist' },
  { name: 'HIM Loadout', desc: 'Curated gear for men. Researched. Filtered. Honest. Affiliate model, same price for you.', href: '/him-loadout', color: '#4A7C9B', cta: 'Browse Drops' },
  { name: 'Logistics', desc: 'Fulfillment, warehousing, last-mile. Where Everlight started. The legal backbone of everything.', href: '/logistics', color: '#D4963A', cta: 'Get Quote' },
]

// Animated counter
function Counter({ target, suffix = '' }: { target: string; suffix?: string }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true })
  const [count, setCount] = useState(0)
  const num = parseInt(target.replace(/\D/g, ''))

  useEffect(() => {
    if (!inView || isNaN(num)) return
    let frame = 0
    const total = 40
    const step = () => {
      frame++
      setCount(Math.round((frame / total) * num))
      if (frame < total) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [inView, num])

  return <span ref={ref}>{isNaN(num) ? target : count}{suffix}</span>
}

export default function HomePage() {
  const containerRef = useRef(null)
  const { scrollYProgress } = useScroll()
  const heroY = useTransform(scrollYProgress, [0, 0.3], [0, -100])
  const heroBlur = useTransform(scrollYProgress, [0, 0.2], [0, 8])
  const [scrolled, setScrolled] = useState(false)

  useMotionValueEvent(scrollYProgress, 'change', v => setScrolled(v > 0.05))

  return (
    <main ref={containerRef} className="min-h-screen relative" style={{ background: 'linear-gradient(180deg, #08080c 0%, #0c0c12 30%, #0e0e16 60%, #0a0a10 100%)' }}>

      {/* ============================================
          HERO -- Cinematic, full-viewport, scroll-reactive
          ============================================ */}
      <section className="h-screen flex flex-col items-center justify-center px-6 text-center relative overflow-hidden">

        {/* Layered ambient gradients */}
        <div className="absolute inset-0" style={{
          background: `
            radial-gradient(ellipse 80% 60% at 50% 45%, rgba(212,175,55,0.07) 0%, transparent 70%),
            radial-gradient(ellipse 60% 40% at 20% 80%, rgba(123,94,167,0.04) 0%, transparent 60%),
            radial-gradient(ellipse 50% 50% at 85% 15%, rgba(212,150,58,0.03) 0%, transparent 50%)
          `,
        }} />

        {/* Horizontal light band */}
        <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 h-[1px] opacity-[0.04]"
          style={{ background: 'linear-gradient(90deg, transparent 10%, #D4AF37, transparent 90%)' }} />

        <Suspense fallback={null}><GoldHeroScene /></Suspense>

        <motion.div style={{ y: heroY }} className="relative z-10 max-w-5xl">

          {/* Overline */}
          <motion.p
            initial={{ opacity: 0, letterSpacing: '0.1em' }}
            animate={{ opacity: 1, letterSpacing: '0.4em' }}
            transition={{ duration: 1.5, delay: 0.3 }}
            className="text-[10px] uppercase font-medium mb-8"
            style={{ color: '#D4AF37' }}>
            Everlight Ventures
          </motion.p>

          {/* Main headline -- per-character reveal */}
          <h1 className="text-[clamp(3rem,8vw,8rem)] font-bold leading-[0.9] tracking-tight"
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              background: 'linear-gradient(180deg, #E8D48B 0%, #D4AF37 50%, #996515 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}>
            <TextReveal text="Build Different." delay={0.8} staggerSpeed={0.04} />
            <br />
            <TextReveal text="Build in the Light." delay={1.4} staggerSpeed={0.04} />
          </h1>

          {/* Subhead */}
          <motion.p
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, delay: 0.9, ease: [0.16, 1, 0.3, 1] }}
            className="mt-8 text-base md:text-lg max-w-xl mx-auto font-light leading-relaxed"
            style={{ color: '#b0b0c0' }}>
            A venture studio that builds, operates, and scales businesses
            across commerce, publishing, software, and finance.
          </motion.p>

          {/* CTA */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 1.3 }}>
            <Link href="#portfolio">
              <motion.button
                className="mt-12 px-10 py-4 rounded-full text-xs font-semibold tracking-[0.25em] uppercase relative overflow-hidden"
                style={{
                  background: 'transparent',
                  border: '1px solid rgba(212,175,55,0.4)',
                  color: '#D4AF37',
                }}
                whileHover={{
                  background: 'rgba(212,175,55,0.08)',
                  borderColor: 'rgba(212,175,55,0.7)',
                  boxShadow: '0 0 30px rgba(212,175,55,0.1)',
                }}
                whileTap={{ scale: 0.97 }}>
                Explore the Ventures
              </motion.button>
            </Link>
          </motion.div>
        </motion.div>

        {/* Scroll line */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 2 }}
          className="absolute bottom-12 left-1/2 -translate-x-1/2 flex flex-col items-center gap-3">
          <span className="text-[9px] uppercase tracking-[0.3em] font-light" style={{ color: '#4a4a5e' }}>Scroll</span>
          <motion.div className="w-px h-12" style={{ background: 'linear-gradient(180deg, #D4AF3740, transparent)' }}
            animate={{ scaleY: [0.3, 1, 0.3], opacity: [0.3, 0.8, 0.3] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }} />
        </motion.div>
      </section>

      {/* ============================================
          PROOF STRIP -- Numbers that animate on scroll
          ============================================ */}
      <section className="py-20 px-6 relative">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-12 md:gap-16">
            {[
              { num: '5', label: 'Books Published', suffix: '' },
              { num: '6', label: 'Casino Games', suffix: '' },
              { num: '42', label: 'AI Agents', suffix: '' },
              { num: '5', label: 'Years Building', suffix: '' },
            ].map((p, i) => (
              <motion.div key={p.label}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.8 }}
                className="text-center">
                <p className="text-4xl md:text-5xl font-bold" style={{
                  fontFamily: "'Cormorant Garamond', serif",
                  background: 'linear-gradient(180deg, #D4AF37, #996515)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}>
                  <Counter target={p.num} suffix={p.suffix} />
                </p>
                <p className="text-[10px] uppercase tracking-[0.2em] mt-3 font-medium" style={{ color: '#4a4a5e' }}>{p.label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================
          PORTFOLIO -- Glass cards, hover lift, glow edge
          ============================================ */}
      <section id="portfolio" className="py-32 px-6">
        <div className="max-w-6xl mx-auto">
          {/* Section header */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-100px' }}
            transition={{ duration: 1 }}>
            <p className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: '#D4AF37' }}>Portfolio</p>
            <h2 className="text-4xl md:text-6xl font-bold leading-[1.05]" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
              Six ventures.<br />
              <span style={{ color: '#4a4a5e' }}>One vision.</span>
            </h2>
            <p className="mt-6 text-sm max-w-lg leading-relaxed" style={{ color: '#4a4a5e' }}>
              Each operates independently. All share infrastructure, automation, and a unified AI operations layer.
            </p>
          </motion.div>

          {/* Cards grid */}
          <div className="mt-20 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {VENTURES.map((v, i) => (
              <motion.div key={v.name}
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08, duration: 0.8 }}>
                <Link href={v.href}>
                  <motion.div
                    className="group relative p-8 rounded-2xl h-full cursor-pointer overflow-hidden"
                    style={{
                      background: 'linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01))',
                      backdropFilter: 'blur(40px)',
                      border: '1px solid rgba(255,255,255,0.06)',
                      boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.05)',
                    }}
                    whileHover={{
                      borderColor: `${v.color}30`,
                      boxShadow: `0 8px 32px ${v.color}08, inset 0 1px 0 rgba(255,255,255,0.08)`,
                      y: -3,
                    }}
                    transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}>

                    {/* Frosted top edge highlight */}
                    <div className="absolute top-0 left-0 right-0 h-px"
                      style={{ background: 'linear-gradient(90deg, transparent 10%, rgba(255,255,255,0.08) 50%, transparent 90%)' }} />

                    {/* Accent line on hover */}
                    <div className="absolute top-0 left-0 right-0 h-px scale-x-0 group-hover:scale-x-100 transition-transform duration-700 origin-left"
                      style={{ background: `linear-gradient(90deg, ${v.color}80, transparent)` }} />

                    {/* Number */}
                    <span className="text-[72px] font-bold absolute top-2 right-5 leading-none select-none"
                      style={{ fontFamily: "'Cormorant Garamond', serif", color: 'rgba(255,255,255,0.025)' }}>
                      {String(i + 1).padStart(2, '0')}
                    </span>

                    {/* Content */}
                    <div className="relative z-10">
                      <h3 className="text-lg font-bold tracking-wide mb-4" style={{ color: '#eee' }}>{v.name}</h3>
                      <p className="text-[13px] leading-[1.7] mb-8" style={{ color: '#999' }}>{v.desc}</p>
                      <span className="text-[11px] font-semibold uppercase tracking-[0.2em] flex items-center gap-2 transition-all duration-500 group-hover:gap-4"
                        style={{ color: v.color }}>
                        {v.cta}
                        <span>&rarr;</span>
                      </span>
                    </div>
                  </motion.div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================
          BUILT TO LAST -- Clean, confident, not arrogant
          ============================================ */}
      <section className="py-32 px-6 relative">
        {/* Subtle silver ambient */}
        <div className="absolute inset-0 pointer-events-none" style={{
          background: 'radial-gradient(ellipse 50% 40% at 70% 40%, rgba(200,200,220,0.02) 0%, transparent 70%)',
        }} />

        <div className="max-w-3xl mx-auto relative">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-100px' }}
            transition={{ duration: 1 }}>
            <p className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: '#D4AF37' }}>Built to Last</p>
            <h2 className="text-3xl md:text-5xl font-bold leading-[1.1] mb-6" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
              Five years. Six industries.<br />
              <span style={{ color: '#D4AF37' }}>Zero outside capital.</span>
            </h2>
          </motion.div>

          {/* Glass panel with silver frost */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="mt-12 p-8 md:p-10 rounded-2xl relative overflow-hidden"
            style={{
              background: 'linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015))',
              backdropFilter: 'blur(40px)',
              border: '1px solid rgba(255,255,255,0.06)',
              boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06)',
            }}>
            {/* Top frost line */}
            <div className="absolute top-0 left-0 right-0 h-px" style={{ background: 'linear-gradient(90deg, transparent 10%, rgba(255,255,255,0.1) 50%, transparent 90%)' }} />

            <div className="space-y-6">
              <p className="text-[15px] leading-[1.9]" style={{ color: '#bbb' }}>
                Everlight Ventures is a bootstrapped venture studio that builds, launches, and operates companies across publishing, gaming, point-of-sale software, AI orchestration, logistics, and affiliate commerce. Every product ships complete. Every venture funds the next.
              </p>
              <p className="text-[15px] leading-[1.9]" style={{ color: '#999' }}>
                We run lean by design. AI-powered operations handle what most companies staff entire departments for. That efficiency is not a shortcut -- it is the architecture. It lets a small team move faster, ship cleaner, and stay independent.
              </p>
              <p className="text-[15px] leading-[1.9]" style={{ color: '#999' }}>
                Nothing here came from a pitch deck or a fundraising schedule. Each venture started with a real problem and a conviction that we could solve it better. Five years of that approach built a portfolio that speaks for itself.
              </p>
            </div>

            {/* Closing line */}
            <div className="mt-8 pt-6 relative">
              <div className="absolute top-0 left-0 right-0 h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(212,175,55,0.2), transparent)' }} />
              <p className="text-lg font-light tracking-wide" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4AF37' }}>
                We do not talk about what we are building. We ship it.
              </p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ============================================
          FOOTER -- Restrained, premium
          ============================================ */}
      <footer className="py-20 px-6 relative">
        <div className="absolute top-0 left-0 right-0 h-px" style={{ background: 'linear-gradient(90deg, transparent 20%, rgba(255,255,255,0.05), transparent 80%)' }} />
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col md:flex-row items-start md:items-end justify-between gap-10">
            <div>
              <p className="text-3xl font-bold tracking-wide" style={{
                fontFamily: "'Cormorant Garamond', serif",
                background: 'linear-gradient(180deg, #D4AF37, #996515)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}>EVERLIGHT</p>
              <p className="text-[11px] mt-2 font-light tracking-wide" style={{ color: '#4a4a5e' }}>Build Different. Build in the Light.</p>
            </div>
            <div className="flex flex-wrap gap-x-8 gap-y-3 text-[11px] tracking-wide" style={{ color: '#4a4a5e' }}>
              {[
                ['Home', '/'], ['Publishing', '/publishing'], ['Casino', '/vantaris'],
                ['Onyx', '/onyx'], ['Hive Mind', '/hivemind'], ['Logistics', '/logistics'],
                ['Wholesale', '/sell'],
              ].map(([label, href]) => (
                <Link key={label} href={href} className="hover:text-white transition-colors duration-500">{label}</Link>
              ))}
            </div>
          </div>
          <div className="mt-16 pt-8 relative">
            <div className="absolute top-0 left-0 right-0 h-px" style={{ background: 'linear-gradient(90deg, transparent 20%, rgba(255,255,255,0.04), transparent 80%)' }} />
            <p className="text-[10px] font-light tracking-wide" style={{ color: '#333' }}>
              &copy; 2026 Everlight Ventures. All rights reserved. Everlight Logistics LLC. hello@everlightventures.io
            </p>
          </div>
        </div>
      </footer>
    </main>
  )
}
