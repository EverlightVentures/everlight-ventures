'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect } from 'react'

export function IntroLoader({ onComplete }: { onComplete: () => void }) {
  const [phase, setPhase] = useState<'playing' | 'fade' | 'done'>('playing')

  useEffect(() => {
    const t1 = setTimeout(() => setPhase('fade'), 3500)
    const t2 = setTimeout(() => { setPhase('done'); onComplete() }, 4300)
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

          {/* Full-screen video */}
          <video
            autoPlay muted playsInline
            className="absolute inset-0 w-full h-full object-cover"
            style={{ opacity: phase === 'fade' ? 0.2 : 0.7, transition: 'opacity 0.8s' }}>
            <source src="/videos/ev-loading.mp4" type="video/mp4" />
          </video>

          {/* Dark overlay */}
          <div className="absolute inset-0" style={{
            background: 'radial-gradient(ellipse at 50% 50%, rgba(5,5,7,0.2) 0%, rgba(5,5,7,0.6) 100%)',
          }} />

          {/* Logo */}
          <div className="relative z-10 text-center">
            <motion.h1
              initial={{ opacity: 0, scale: 0.9, letterSpacing: '0.1em' }}
              animate={{ opacity: 1, scale: 1, letterSpacing: '0.5em' }}
              transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
              className="text-3xl md:text-5xl font-bold"
              style={{
                fontFamily: "'Cormorant Garamond', serif",
                background: 'linear-gradient(180deg, #E8D48B 0%, #D4AF37 40%, #996515 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}>
              EVERLIGHT
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.8 }}
              className="mt-3 text-[10px] uppercase tracking-[0.4em] font-light"
              style={{ color: '#D4AF37' }}>
              Ventures
            </motion.p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
