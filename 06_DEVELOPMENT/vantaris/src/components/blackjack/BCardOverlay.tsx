'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useRef, useEffect } from 'react'
import { useBlackjackStore } from '@/lib/blackjack-store'
import { BCARD_TAKE_MULT, BCARD_RIDE_MULT, BCARD_PAYOUT_CAP, bcardPayout } from '@/lib/blackjack-engine'

/**
 * THE B-CARDD BET -- the optional jackpot choice.
 *
 * Fires when the player draws $BCARDD's signature B-Card on the VIP (Spanish 21)
 * table. Pauses the hand and offers:
 *   - TAKE IT : guaranteed auto-WIN of the current hand at 100x the QTD avg bet.
 *   - RIDE IT : the B-Card stays as the 8 in this hand; the NEXT hand becomes the
 *               Golden Hand worth 200x -- but only if you BEAT the dealer.
 *
 * Branding follows the locked $BCARDD canon: the buff-dealer look (bacardi_live.mp4).
 * Spec: 01_BUSINESSES/Everlight_Ventures/Everlight_Gaming/Blackjack/BCARDD_BET_SPEC.md
 */
export function BCardOverlay() {
  const { phase, bcardAvgBet, bcardTake, bcardRide } = useBlackjackStore()
  const videoRef = useRef<HTMLVideoElement>(null)

  const show = phase === 'bcard_choice'

  useEffect(() => {
    if (show && videoRef.current) {
      videoRef.current.currentTime = 0
      videoRef.current.play().catch(() => {})
    }
  }, [show])

  if (!show) return null

  // Preview payouts (engine caps both at 888). Round for display.
  const takeAmount = Math.round(bcardPayout(bcardAvgBet, 'take'))
  const rideAmount = Math.round(bcardPayout(bcardAvgBet, 'ride', true))

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.35 }}
        className="fixed inset-0 z-[120] flex items-center justify-center"
        style={{ background: 'radial-gradient(circle at 50% 40%, rgba(20,12,0,0.92), rgba(0,0,0,0.96))' }}
      >
        {/* Buff $BCARDD dealer (canonical look) behind the panel */}
        <video
          ref={videoRef}
          muted
          loop
          playsInline
          className="absolute inset-0 w-full h-full object-cover"
          style={{ opacity: 0.22 }}
        >
          <source src="/dealers/bacardi_live.mp4" type="video/mp4" />
        </video>

        <motion.div
          initial={{ scale: 0.7, opacity: 0, y: 30 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          transition={{ type: 'spring', stiffness: 240, damping: 18 }}
          className="relative z-10 text-center px-5 max-w-[440px]"
        >
          {/* Crowned-B emblem */}
          <motion.div
            animate={{ scale: [1, 1.08, 1], filter: ['drop-shadow(0 0 22px rgba(212,175,55,0.55))', 'drop-shadow(0 0 40px rgba(212,175,55,0.85))', 'drop-shadow(0 0 22px rgba(212,175,55,0.55))'] }}
            transition={{ duration: 2.2, repeat: Infinity }}
            className="mx-auto mb-4 w-20 h-28 rounded-xl flex items-center justify-center"
            style={{
              background: 'linear-gradient(155deg, #1a1408, #0a0a0a)',
              border: '2px solid #D4AF37',
              boxShadow: '0 8px 40px rgba(0,0,0,0.8), inset 0 0 18px rgba(212,175,55,0.18)',
            }}
          >
            <span
              className="text-5xl font-black"
              style={{
                fontFamily: "'Cinzel', serif",
                background: 'linear-gradient(180deg, #E8D48B, #D4AF37, #996515)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              B
            </span>
          </motion.div>

          <p
            className="text-3xl md:text-4xl font-black tracking-wider mb-1"
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              background: 'linear-gradient(180deg, #E8D48B, #D4AF37, #996515)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              filter: 'drop-shadow(0 0 24px rgba(212,175,55,0.45))',
            }}
          >
            THE B-CARDD BET
          </p>
          <p className="text-[11px] tracking-[0.3em] uppercase mb-5" style={{ color: '#D4AF37' }}>
            $BCARDD deals you in
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            {/* TAKE IT -- guaranteed 100x */}
            <motion.button
              onClick={bcardTake}
              whileHover={{ scale: 1.04, boxShadow: '0 0 30px rgba(0,230,118,0.5)' }}
              whileTap={{ scale: 0.97 }}
              className="flex-1 px-5 py-4 rounded-xl text-left"
              style={{
                background: 'linear-gradient(145deg, rgba(0,230,118,0.16), rgba(0,0,0,0.4))',
                border: '1px solid rgba(0,230,118,0.45)',
              }}
            >
              <p className="text-sm font-black tracking-widest" style={{ color: 'var(--win)', fontFamily: "'Cinzel', serif" }}>
                TAKE IT
              </p>
              <p className="text-[10px] mt-1" style={{ color: 'rgba(255,255,255,0.6)' }}>
                Auto-win this hand at {BCARD_TAKE_MULT}x avg bet
              </p>
              <p className="font-mono text-lg font-bold mt-1" style={{ color: 'var(--win)' }}>
                +{takeAmount.toLocaleString()} GC
              </p>
            </motion.button>

            {/* RIDE IT -- 200x golden hand */}
            <motion.button
              onClick={bcardRide}
              whileHover={{ scale: 1.04, boxShadow: '0 0 30px rgba(212,175,55,0.5)' }}
              whileTap={{ scale: 0.97 }}
              className="flex-1 px-5 py-4 rounded-xl text-left"
              style={{
                background: 'linear-gradient(145deg, rgba(212,175,55,0.18), rgba(0,0,0,0.4))',
                border: '1px solid rgba(212,175,55,0.5)',
              }}
            >
              <p className="text-sm font-black tracking-widest" style={{ color: 'var(--gold)', fontFamily: "'Cinzel', serif" }}>
                RIDE IT
              </p>
              <p className="text-[10px] mt-1" style={{ color: 'rgba(255,255,255,0.6)' }}>
                Plays as an 8. Next hand = Golden Hand. Beat the dealer for {BCARD_RIDE_MULT}x.
              </p>
              <p className="font-mono text-lg font-bold mt-1" style={{ color: 'var(--gold)' }}>
                up to +{rideAmount.toLocaleString()} GC
              </p>
            </motion.button>
          </div>

          <p className="text-[9px] mt-4" style={{ color: 'rgba(255,255,255,0.3)' }}>
            Max payout {BCARD_PAYOUT_CAP} GC. For-fun chips only.
          </p>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

/**
 * Golden Hand banner -- shown during the round that follows a RIDE IT choice.
 * "Beat the dealer for 200x." Slim top banner so it does not block the table.
 */
export function GoldenHandBanner() {
  const { goldenHandActive, phase } = useBlackjackStore()
  if (!goldenHandActive) return null
  // Hide once the round is over (the result overlay takes the stage).
  if (phase === 'settled') return null

  return (
    <motion.div
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      className="absolute top-[100px] md:top-[110px] left-1/2 -translate-x-1/2 z-20 px-4 py-2 rounded-full text-center"
      style={{
        background: 'linear-gradient(90deg, rgba(212,175,55,0.18), rgba(153,101,21,0.22), rgba(212,175,55,0.18))',
        border: '1px solid rgba(212,175,55,0.55)',
        boxShadow: '0 0 24px rgba(212,175,55,0.25)',
      }}
    >
      <motion.p
        animate={{ opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 1.8, repeat: Infinity }}
        className="text-[11px] md:text-xs font-black tracking-widest uppercase"
        style={{
          fontFamily: "'Cinzel', serif",
          background: 'linear-gradient(180deg, #E8D48B, #D4AF37)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}
      >
        Golden Hand -- beat the dealer for {BCARD_RIDE_MULT}x
      </motion.p>
    </motion.div>
  )
}
