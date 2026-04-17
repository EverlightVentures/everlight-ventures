'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect } from 'react'

export function IntroLoader({ onComplete }: { onComplete: () => void }) {
  const [phase, setPhase] = useState<'logo' | 'expand' | 'done'>('logo')

  useEffect(() => {
    const t1 = setTimeout(() => setPhase('expand'), 1800)
    const t2 = setTimeout(() => { setPhase('done'); onComplete() }, 2600)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [onComplete])

  return (
    <AnimatePresence>
      {phase !== 'done' && (
        <motion.div
          className="fixed inset-0 z-[10000] flex items-center justify-center"
          style={{ background: '#050507' }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}>

          {/* Gold line expanding */}
          <motion.div
            className="absolute top-1/2 left-1/2 h-px -translate-x-1/2"
            initial={{ width: 0 }}
            animate={{ width: phase === 'expand' ? '100vw' : 80 }}
            transition={{ duration: phase === 'expand' ? 0.8 : 1.2, ease: [0.16, 1, 0.3, 1] }}
            style={{ background: 'linear-gradient(90deg, transparent, #D4AF37, transparent)' }}
          />

          {/* Logo text */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: phase === 'logo' ? 1 : 0, scale: phase === 'logo' ? 1 : 1.1 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}>
            <p className="text-3xl md:text-4xl font-bold tracking-[0.3em]"
              style={{
                fontFamily: "'Cormorant Garamond', serif",
                background: 'linear-gradient(180deg, #E8D48B, #D4AF37, #996515)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}>
              EVERLIGHT
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
