'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect, useRef } from 'react'

interface CasinoLoaderProps {
  onComplete: () => void
}

export function CasinoLoader({ onComplete }: CasinoLoaderProps) {
  const [phase, setPhase] = useState<'video' | 'reveal' | 'done'>('video')
  const [progress, setProgress] = useState(0)
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    // Progress bar fills over 4 seconds
    const start = Date.now()
    const duration = 4000
    const tick = () => {
      const elapsed = Date.now() - start
      const pct = Math.min(100, (elapsed / duration) * 100)
      setProgress(pct)
      if (elapsed < duration) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)

    // Phase transitions
    const t1 = setTimeout(() => setPhase('reveal'), 3500)
    const t2 = setTimeout(() => { setPhase('done'); onComplete() }, 4500)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [onComplete])

  return (
    <AnimatePresence>
      {phase !== 'done' && (
        <motion.div
          className="fixed inset-0 z-[10000] flex flex-col items-center justify-center"
          style={{ background: '#050507' }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}>

          {/* Full-screen video background */}
          <video
            ref={videoRef}
            autoPlay muted playsInline
            className="absolute inset-0 w-full h-full object-cover"
            style={{ opacity: phase === 'reveal' ? 0.3 : 0.6, transition: 'opacity 0.8s' }}>
            <source src="/videos/casino-entry.mp4" type="video/mp4" />
          </video>

          {/* Dark overlay for text readability */}
          <div className="absolute inset-0" style={{
            background: 'radial-gradient(ellipse at 50% 50%, rgba(5,5,7,0.3) 0%, rgba(5,5,7,0.7) 100%)',
          }} />

          {/* Content */}
          <div className="relative z-10 text-center">
            {/* VANTARIS logo */}
            <motion.h1
              initial={{ opacity: 0, scale: 0.9, letterSpacing: '0.1em' }}
              animate={{ opacity: 1, scale: 1, letterSpacing: '0.5em' }}
              transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
              className="text-4xl md:text-6xl lg:text-7xl font-bold"
              style={{
                fontFamily: "'Cormorant Garamond', serif",
                background: 'linear-gradient(180deg, #E8D48B 0%, #D4AF37 40%, #996515 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                textShadow: 'none',
              }}>
              VANTARIS
            </motion.h1>

            {/* Tagline */}
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.8 }}
              className="mt-4 text-[11px] uppercase tracking-[0.4em] font-light"
              style={{ color: '#D4AF37' }}>
              The darkest star burns brightest
            </motion.p>

            {/* Everlight sub-brand */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 1.2 }}
              className="mt-2 text-[9px] uppercase tracking-[0.3em]"
              style={{ color: '#555' }}>
              An Everlight Ventures Experience
            </motion.p>
          </div>

          {/* Progress bar at bottom */}
          <div className="absolute bottom-12 left-1/2 -translate-x-1/2 w-48">
            <div className="h-px w-full rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)' }}>
              <motion.div
                className="h-full rounded-full"
                style={{
                  width: `${progress}%`,
                  background: 'linear-gradient(90deg, #996515, #D4AF37, #E8D48B)',
                  transition: 'width 0.1s linear',
                }}
              />
            </div>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="text-center mt-3 text-[9px] uppercase tracking-[0.3em]"
              style={{ color: '#444' }}>
              {progress < 30 ? 'Shuffling the deck...' : progress < 60 ? 'Setting the table...' : progress < 90 ? 'Dealing you in...' : 'Welcome.'}
            </motion.p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
