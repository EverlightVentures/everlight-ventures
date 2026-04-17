'use client'

import { motion } from 'framer-motion'
import { TextReveal } from './TextReveal'

interface PageHeroProps {
  overline: string
  title: string
  subtitle?: string
  description?: string
  color: string
  children?: React.ReactNode
}

export function PageHero({ overline, title, subtitle, description, color, children }: PageHeroProps) {
  return (
    <section className="min-h-[75vh] flex flex-col items-center justify-center px-6 text-center relative overflow-hidden">
      {/* Ambient gradient */}
      <div className="absolute inset-0 pointer-events-none" style={{
        background: `radial-gradient(ellipse 60% 50% at 50% 50%, ${color}08 0%, transparent 70%)`,
      }} />

      {/* Horizontal light line */}
      <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 h-px opacity-[0.03]"
        style={{ background: `linear-gradient(90deg, transparent 10%, ${color}, transparent 90%)` }} />

      <div className="relative z-10 max-w-3xl">
        {/* Overline */}
        <motion.p
          initial={{ opacity: 0, letterSpacing: '0.1em' }}
          animate={{ opacity: 1, letterSpacing: '0.4em' }}
          transition={{ duration: 1.5, delay: 0.2 }}
          className="text-[10px] uppercase font-medium mb-6"
          style={{ color }}>
          {overline}
        </motion.p>

        {/* Title -- per-character reveal */}
        <h1 className="text-[clamp(2.5rem,6vw,5rem)] font-bold leading-[0.95] tracking-tight"
          style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
          <TextReveal text={title} delay={0.4} staggerSpeed={0.03} />
        </h1>

        {subtitle && (
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 1 }}
            className="mt-4 text-lg font-light"
            style={{ color }}>
            {subtitle}
          </motion.p>
        )}

        {description && (
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 1.2 }}
            className="mt-6 text-[15px] max-w-xl mx-auto font-light leading-relaxed"
            style={{ color: '#999' }}>
            {description}
          </motion.p>
        )}

        {children && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 1.4 }}>
            {children}
          </motion.div>
        )}
      </div>
    </section>
  )
}
