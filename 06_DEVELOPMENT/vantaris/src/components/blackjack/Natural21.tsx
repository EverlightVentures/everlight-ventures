'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState, useRef } from 'react'

/**
 * Full-screen Natural 21 celebration.
 * Plays the video overlay for ~3 seconds when player hits blackjack.
 */
export function Natural21Overlay({ show, onDone }: { show: boolean; onDone: () => void }) {
  const [visible, setVisible] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  // Keep the latest onDone without making it an effect dependency.
  const onDoneRef = useRef(onDone)
  onDoneRef.current = onDone

  useEffect(() => {
    if (!show) return
    setVisible(true)
    // Play video from start
    if (videoRef.current) {
      videoRef.current.currentTime = 0
      videoRef.current.play().catch(() => {})
    }
    // Auto-dismiss after 3s. Depend ONLY on `show`: the parent passes a fresh inline
    // onDone every render, so including it here re-ran this effect constantly and reset
    // the timer forever -> the overlay never dismissed ("frozen on the page").
    const t = setTimeout(() => {
      setVisible(false)
      onDoneRef.current()
    }, 3000)
    return () => clearTimeout(t)
  }, [show])

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="fixed inset-0 z-[100] flex items-center justify-center pointer-events-none">

          {/* Video overlay */}
          <video
            ref={videoRef}
            muted
            playsInline
            className="absolute inset-0 w-full h-full object-cover"
            style={{ opacity: 0.6 }}>
            <source src="/videos/natural-21.mp4" type="video/mp4" />
          </video>

          {/* Text overlay */}
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 1.2, opacity: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="relative z-10 text-center">
            <p className="text-6xl md:text-8xl font-bold tracking-wider"
              style={{
                fontFamily: "'Cormorant Garamond', serif",
                background: 'linear-gradient(180deg, #E8D48B, #D4AF37, #996515)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                filter: 'drop-shadow(0 0 30px rgba(212,175,55,0.5))',
              }}>
              BLACKJACK!
            </p>
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="mt-2 text-sm tracking-[0.3em] uppercase"
              style={{ color: '#D4AF37' }}>
              Natural 21
            </motion.p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
