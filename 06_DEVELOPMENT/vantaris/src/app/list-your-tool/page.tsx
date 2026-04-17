'use client'

import { motion } from 'framer-motion'
import { useState, useRef } from 'react'
import { useLeadForm } from '@/hooks/useLeadForm'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

export default function ListYourToolPage() {
  const formRef = useRef<HTMLFormElement>(null)
  const { loading, submitted, error, handleSubmit } = useLeadForm({ source: 'list-tool' })

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    const fd = new FormData(formRef.current!)
    handleSubmit({
      name: fd.get('name') as string,
      email: fd.get('email') as string,
      message: fd.get('description') as string,
      metadata: {
        tool_name: fd.get('tool_name') as string,
        url: fd.get('url') as string,
      },
    })
  }

  return (
    <main className="min-h-screen py-20 px-6" style={{ background: 'var(--vanta-void)' }}>
      <motion.div initial="hidden" animate="visible" variants={stagger} className="max-w-2xl mx-auto">

        <motion.div variants={fadeUp} className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
            List Your Tool
          </h1>
          <p className="mt-4 text-lg" style={{ color: 'var(--text-secondary)' }}>
            Have a SaaS product, service, or tool? Get it in front of our audience. We review every submission.
          </p>
        </motion.div>

        {submitted ? (
          <motion.div variants={fadeUp} className="p-8 rounded-2xl text-center" style={{ background: 'rgba(201,168,76,0.05)', border: '1px solid rgba(201,168,76,0.2)' }}>
            <p className="text-xl font-bold mb-2" style={{ color: 'var(--gold)', fontFamily: "'Cinzel', serif" }}>Submission Received</p>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>We review submissions within 48 hours. We'll reach out via email if your tool is a fit.</p>
          </motion.div>
        ) : (
          <motion.form ref={formRef} variants={fadeUp} className="space-y-6" onSubmit={onSubmit}>
            {[
              { label: 'Your Name', name: 'name', type: 'text' },
              { label: 'Email', name: 'email', type: 'email' },
              { label: 'Tool / Product Name', name: 'tool_name', type: 'text' },
              { label: 'Website URL', name: 'url', type: 'url' },
            ].map(field => (
              <div key={field.name}>
                <label className="block text-xs uppercase tracking-wider mb-2" style={{ color: 'var(--text-tertiary)' }}>{field.label}</label>
                <input type={field.type} name={field.name} required
                  className="w-full px-4 py-3 rounded-xl text-sm outline-none"
                  style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
              </div>
            ))}
            <div>
              <label className="block text-xs uppercase tracking-wider mb-2" style={{ color: 'var(--text-tertiary)' }}>Description</label>
              <textarea name="description" rows={4} required
                className="w-full px-4 py-3 rounded-xl text-sm outline-none resize-none"
                style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }}
                placeholder="What does your tool do? Who is it for?" />
            </div>
            {error && <p className="text-xs text-red-400">{error}</p>}
            <motion.button type="submit" disabled={loading} className="w-full py-3 rounded-xl text-sm font-bold tracking-widest"
              style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif", opacity: loading ? 0.6 : 1 }}
              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}>
              {loading ? 'SUBMITTING...' : 'SUBMIT FOR REVIEW'}
            </motion.button>
          </motion.form>
        )}
      </motion.div>
    </main>
  )
}
