'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { useLeadForm } from '@/hooks/useLeadForm'
import type { LeadSource } from '@/lib/leads'

interface EmailCaptureProps {
  source: LeadSource
  color: string
  buttonText?: string
  successTitle?: string
  successDesc?: string
  placeholder?: string
}

export function EmailCapture({ source, color, buttonText = 'JOIN WAITLIST', successTitle = "You're in.", successDesc = "We'll be in touch.", placeholder = 'Enter your email' }: EmailCaptureProps) {
  const [email, setEmail] = useState('')
  const { loading, submitted, error, handleSubmit } = useLeadForm({ source })

  if (submitted) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-4 rounded-xl text-center" style={{ background: `${color}10`, border: `1px solid ${color}30` }}>
        <p className="text-sm font-bold" style={{ color, fontFamily: "'Cinzel', serif" }}>{successTitle}</p>
        <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{successDesc}</p>
      </motion.div>
    )
  }

  return (
    <form onSubmit={e => { e.preventDefault(); handleSubmit({ email }) }} className="flex gap-2">
      <input type="email" placeholder={placeholder} value={email} onChange={e => setEmail(e.target.value)} required
        className="flex-1 px-4 py-3 rounded-xl text-sm outline-none"
        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
      <motion.button type="submit" disabled={loading} className="px-6 py-3 rounded-xl text-xs font-bold tracking-widest whitespace-nowrap"
        style={{ background: `linear-gradient(135deg, ${color}, ${color}cc)`, color: '#000', fontFamily: "'Cinzel', serif", opacity: loading ? 0.6 : 1 }}
        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
        {loading ? '...' : buttonText}
      </motion.button>
      {error && <p className="text-xs text-red-400 absolute mt-14">{error}</p>}
    </form>
  )
}
