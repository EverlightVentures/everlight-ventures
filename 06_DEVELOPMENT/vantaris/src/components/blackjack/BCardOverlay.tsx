'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useRef, useEffect, useState } from 'react'
import { useBlackjackStore } from '@/lib/blackjack-store'
import { playBlackjack } from '@/lib/audio-engine'
import { BCARD_TAKE_MULT, BCARD_RIDE_MULT, BCARD_PAYOUT_CAP, bcardPayout } from '@/lib/blackjack-engine'

/**
 * THE B-CARDD BET -- the 1-in-a-million jackpot moment.
 *
 * Fires when the player draws $BCARDD's signature B-Card on the VIP (Spanish 21)
 * table. Two stages, both inside this one overlay:
 *
 *   1. REVEAL (the cinematic): the dark falls, the buff $BCARDD dealer looms behind,
 *      the card FLIPS face-up in 3D, gold rays burst, a triumphant sting plays, and
 *      "THE B-CARDD BET" slams in. ~2.2s of "holy cow it actually hit."
 *   2. CHOICE: the card slots up to a hero frame and the offer rises --
 *        - TAKE IT : guaranteed auto-WIN of the current hand at 100x the QTD avg bet.
 *        - RIDE IT : the B-Card stays as the 8; the NEXT hand becomes the Golden Hand
 *                    worth 200x -- but only if you BEAT the dealer.
 *
 * The reveal is PURE PRESENTATION -- it owns no game state. The store already moved
 * to phase 'bcard_choice' when the card was drawn; this component just mounts on that
 * and runs the cinematic locally before exposing the same TAKE/RIDE handlers. No new
 * phase, no store timers, no risk to deal/settle logic.
 *
 * Branding follows the locked $BCARDD canon: the official buff-dealer footage
 * (official_bdl.mp4). Spec: Everlight_Gaming/Blackjack/BCARDD_BET_SPEC.md
 */

const REVEAL_MS = 2200  // how long the cinematic holds before the choice rises

export function BCardOverlay() {
  const { phase, bcardAvgBet, bcardTake, bcardRide } = useBlackjackStore()
  const videoRef = useRef<HTMLVideoElement>(null)
  const [stage, setStage] = useState<'reveal' | 'choice'>('reveal')

  const show = phase === 'bcard_choice'

  // On each fresh B-Card draw: reset to the cinematic, play the dealer + sting,
  // then promote to the choice after the reveal holds.
  useEffect(() => {
    if (!show) return
    setStage('reveal')
    if (videoRef.current) {
      videoRef.current.currentTime = 0
      videoRef.current.play().catch(() => {})
    }
    playBlackjack().catch(() => {})
    const t = setTimeout(() => setStage('choice'), REVEAL_MS)
    return () => clearTimeout(t)
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
        className="fixed inset-0 z-[120] flex items-center justify-center overflow-hidden"
        style={{ background: 'radial-gradient(circle at 50% 40%, rgba(20,12,0,0.92), rgba(0,0,0,0.97))' }}
      >
        {/* Buff $BCARDD dealer (official canon look) looming behind everything */}
        <video
          ref={videoRef}
          muted
          loop
          playsInline
          className="absolute inset-0 w-full h-full object-cover"
          style={{ opacity: stage === 'reveal' ? 0.34 : 0.2, transition: 'opacity 0.6s ease' }}
        >
          <source src="/dealers/official_bdl.mp4" type="video/mp4" />
        </video>

        {/* Gold ray burst -- spins slowly behind the card, brighter during the reveal */}
        <motion.div
          aria-hidden
          className="absolute left-1/2 top-1/2 pointer-events-none"
          style={{
            width: 680, height: 680, marginLeft: -340, marginTop: -340,
            background:
              'repeating-conic-gradient(from 0deg at 50% 50%, rgba(212,175,55,0.16) 0deg, rgba(212,175,55,0) 9deg 18deg)',
            maskImage: 'radial-gradient(circle, #000 0%, #000 38%, transparent 68%)',
            WebkitMaskImage: 'radial-gradient(circle, #000 0%, #000 38%, transparent 68%)',
          }}
          animate={{ rotate: 360, opacity: stage === 'reveal' ? 0.9 : 0.4 }}
          transition={{ rotate: { duration: 22, repeat: Infinity, ease: 'linear' }, opacity: { duration: 0.6 } }}
        />

        {/* One-shot flash at the moment of the flip */}
        <motion.div
          aria-hidden
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(circle at 50% 42%, rgba(232,212,139,0.55), transparent 60%)' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.8, 0] }}
          transition={{ duration: 0.7, times: [0, 0.25, 1] }}
        />

        <div className="relative z-10 flex flex-col items-center px-5 max-w-[460px]">
          {/* ===== THE B-CARD ITSELF -- a real 3D flip ===== */}
          <motion.div
            className="relative"
            style={{ perspective: 900 }}
            initial={{ scale: 0.4, y: 30 }}
            animate={{
              scale: stage === 'reveal' ? 1 : 0.62,
              y: stage === 'reveal' ? 0 : -6,
            }}
            transition={{ type: 'spring', stiffness: 200, damping: 16 }}
          >
            <motion.div
              className="relative"
              style={{ width: 132, height: 184, transformStyle: 'preserve-3d' }}
              initial={{ rotateY: 180 }}
              animate={{ rotateY: 0 }}
              transition={{ delay: 0.15, duration: 0.85, ease: [0.22, 1, 0.36, 1] }}
            >
              {/* BACK face ($BCARDD filigree) */}
              <div
                className="absolute inset-0 rounded-2xl flex items-center justify-center"
                style={{
                  backfaceVisibility: 'hidden',
                  WebkitBackfaceVisibility: 'hidden',
                  transform: 'rotateY(180deg)',
                  background: 'repeating-linear-gradient(45deg, #14100a 0 8px, #1c1608 8px 16px)',
                  border: '2px solid #6b5618',
                  boxShadow: '0 12px 40px rgba(0,0,0,0.8)',
                }}
              >
                <span className="text-2xl" style={{ color: '#6b5618' }}>♛</span>
              </div>

              {/* FRONT face (the crowned-B hero, plays as an 8) */}
              <div
                className="absolute inset-0 rounded-2xl p-2 flex flex-col justify-between"
                style={{
                  backfaceVisibility: 'hidden',
                  WebkitBackfaceVisibility: 'hidden',
                  background: 'linear-gradient(160deg, #fbf4dd 0%, #efe2b3 55%, #d9c47e 100%)',
                  border: '2px solid #D4AF37',
                  boxShadow: '0 12px 48px rgba(0,0,0,0.85), 0 0 36px rgba(212,175,55,0.5), inset 0 0 14px rgba(212,175,55,0.25)',
                }}
              >
                {/* corner index: 8, because B = 8 */}
                <span className="text-base font-black leading-none self-start" style={{ color: '#8a6d12', fontFamily: "'Cinzel', serif" }}>8</span>
                {/* crowned B center */}
                <span
                  className="absolute inset-0 flex items-center justify-center text-6xl font-black"
                  style={{
                    fontFamily: "'Cinzel', serif",
                    background: 'linear-gradient(180deg, #b8860b, #8a6d12 60%, #6b5310)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    filter: 'drop-shadow(0 1px 0 rgba(255,255,255,0.4))',
                  }}
                >
                  B
                </span>
                <span className="absolute left-1/2 -translate-x-1/2 top-2 text-[9px]" style={{ color: '#b8860b' }}>♛</span>
                <span className="text-[7px] tracking-[0.25em] self-center" style={{ color: '#8a6d12' }}>$BCARDD</span>
                <span className="text-base font-black leading-none self-end rotate-180" style={{ color: '#8a6d12', fontFamily: "'Cinzel', serif" }}>8</span>
              </div>
            </motion.div>
          </motion.div>

          {/* ===== TITLES ===== */}
          <motion.p
            className="mt-4 text-[11px] tracking-[0.42em] uppercase"
            style={{ color: '#D4AF37' }}
            initial={{ opacity: 0, letterSpacing: '0.1em' }}
            animate={{ opacity: 1, letterSpacing: '0.42em' }}
            transition={{ delay: 0.55, duration: 0.5 }}
          >
            1 in a Million
          </motion.p>
          <motion.p
            className="text-3xl md:text-4xl font-black tracking-wider"
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              background: 'linear-gradient(180deg, #E8D48B, #D4AF37, #996515)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              filter: 'drop-shadow(0 0 24px rgba(212,175,55,0.45))',
            }}
            initial={{ opacity: 0, scale: 1.25 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.7, type: 'spring', stiffness: 260, damping: 14 }}
          >
            THE B-CARDD BET
          </motion.p>

          {/* ===== THE CHOICE (rises after the reveal) ===== */}
          <AnimatePresence>
            {stage === 'choice' && (
              <motion.div
                key="choice"
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 16 }}
                transition={{ duration: 0.4 }}
                className="w-full mt-5"
              >
                <p className="text-[11px] tracking-[0.3em] uppercase mb-4 text-center" style={{ color: '#D4AF37' }}>
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

                <p className="text-[9px] mt-4 text-center" style={{ color: 'rgba(255,255,255,0.3)' }}>
                  Max payout {BCARD_PAYOUT_CAP} GC. For-fun chips only.
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
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
