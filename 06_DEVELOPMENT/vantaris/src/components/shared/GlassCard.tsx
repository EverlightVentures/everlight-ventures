'use client'

import { motion } from 'framer-motion'

interface GlassCardProps {
  children: React.ReactNode
  color?: string
  className?: string
  hover?: boolean
}

export function GlassCard({ children, color = '#D4AF37', className = '', hover = true }: GlassCardProps) {
  return (
    <motion.div
      className={`relative rounded-2xl overflow-hidden ${className}`}
      style={{
        background: 'linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015))',
        backdropFilter: 'blur(40px)',
        border: '1px solid rgba(255,255,255,0.06)',
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06)',
      }}
      {...(hover ? {
        whileHover: {
          borderColor: `${color}25`,
          boxShadow: `0 8px 32px ${color}06, inset 0 1px 0 rgba(255,255,255,0.1)`,
          y: -2,
        },
        transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] },
      } : {})}>
      {/* Frost top edge */}
      <div className="absolute top-0 left-0 right-0 h-px"
        style={{ background: 'linear-gradient(90deg, transparent 10%, rgba(255,255,255,0.08) 50%, transparent 90%)' }} />
      <div className="relative z-10">
        {children}
      </div>
    </motion.div>
  )
}
