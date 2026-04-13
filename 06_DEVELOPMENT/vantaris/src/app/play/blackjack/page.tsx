'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useCallback, useMemo } from 'react'
import { useBlackjackStore } from '@/lib/blackjack-store'
import { getSkin, getCardBack, getRarityEffect } from '@/lib/card-skins'
import {
  WinParticles, XPBar, AchievementPopup, VantarisBoutique,
  GemStore, FreeChips, AvatarBuilder, DEFAULT_AVATAR,
  PlayerProfilePanel, Leaderboard, CasinoScene3D, CasinoChip,
} from '@/components/blackjack'
import type { Achievement, AvatarConfig } from '@/components/blackjack'
import type { Card as CardData } from '@/lib/blackjack-engine'
import { useState, useRef } from 'react'

// Audio engine (Tone.js procedural sounds)
import {
  startAmbientMusic, stopAmbientMusic,
  playCardDeal, playChipClink, playHit, playStand,
  playWin, playBlackjack, playLoss, playBust, playSplit,
  playButtonClick, playNotification,
  setSoundEnabled,
} from '@/lib/audio-engine'

// GSAP cinematic animations
import {
  screenShake, lightningFlash, animateCounter,
} from '@/lib/gsap-animations'

/**
 * Vantaris Blackjack -- Full Refactor
 *
 * This page is a THIN UI LAYER. All game logic lives in:
 * - blackjack-engine.ts (pure game rules)
 * - blackjack-store.ts (Zustand state + actions)
 * - card-skins.ts (visual card system)
 *
 * This file only handles:
 * - Rendering cards, chips, HUD, overlays
 * - Animations (Framer Motion)
 * - Sound triggers (ElevenLabs + Web Audio)
 * - 3D scene mounting
 */

// ============================================================
// CONSTANTS
// ============================================================

const SUIT_SYMBOLS: Record<string, string> = {
  spades: '\u2660', hearts: '\u2665', diamonds: '\u2666', clubs: '\u2663',
}

const RANK_COLORS: Record<string, string> = {
  Bronze: '#cd7f32', Silver: '#c0c0c0', Gold: '#ffd700',
  Platinum: '#e5e4e2', Diamond: '#b9f2ff', Legend: '#ff6b35',
  Ember: '#ff6b35', Shadow: '#6a5acd', Eclipse: '#9966ff',
  Supernova: '#c9a84c', 'Vanta Black': '#ffffff',
}

const DEALER_LINES: Record<string, Record<string, string[]>> = {
  aria: {
    deal: ["Cards are out. Let's see what the deck thinks of you.", "Fresh hand. Fresh chance.", "The table is set."],
    hit: ["Bold move.", "Another one? I like your confidence.", "The deck is listening."],
    stand: ["Standing firm. Respect.", "Smart. Let the dealer work."],
    bust: ["Over 21. It happens to the best.", "The cards were not kind."],
    win: ["Well played. The table bows.", "Clean win. Fortune favors you tonight."],
    blackjack: ["Twenty-one. Flawless.", "Natural blackjack. The table applauds."],
    push: ["A draw. The universe could not decide."],
    dealer_bust: ["The house falls. Your patience paid off."],
    surrender: ["A strategic retreat. Half your bet returns."],
    insurance: ["Dealer shows an Ace. Insurance?"],
    split: ["Splitting the hand. Bold."],
    charlie: ["Six cards and still standing. Automatic win."],
    idle: ["The table is waiting.", "Take your time.", "Whenever you are ready."],
  },
  marcus: {
    deal: ["Cards down. No mercy.", "Let us see what you are made of."],
    hit: ["Another card. You got nerves.", "Going for it. Respect."],
    stand: ["Holding. Smart or scared? We will find out."],
    bust: ["Busted. The table does not lie."],
    win: ["You beat the Shark. Take your chips.", "Good win. Do not get comfortable."],
    blackjack: ["Natural 21. Even I am impressed.", "Perfect hand. Respect."],
    push: ["Push. Nobody wins. Boring."],
    dealer_bust: ["I busted. Enjoy it while it lasts."],
    surrender: ["Walking away? Sometimes that is the smartest play."],
    insurance: ["Ace showing. Want protection?"],
    split: ["Splitting. You got money to burn."],
    charlie: ["Six cards without going over. The Shark tips his hat."],
    idle: ["You going to play or just stare?", "Clock is ticking."],
  },
  kanisha: {
    deal: ["Showtime! Cards are out!", "VIP table is live! Let us go!"],
    hit: ["Hit it! I love the energy!", "Another one! You are on fire!"],
    stand: ["Standing strong! Let me do my thing now."],
    bust: ["Oh no! Over 21!", "Ooh that hurts. You will bounce back."],
    win: ["YES! That is how we do it in the VIP!", "Winner winner!"],
    blackjack: ["BLACKJACK! The VIP lounge goes crazy!", "Twenty-one baby! Natural!"],
    push: ["A tie! The drama! We go again!"],
    dealer_bust: ["The house busted! Tonight belongs to YOU!"],
    surrender: ["Taking the safe road? VIP wisdom."],
    insurance: ["Ace up top! Want insurance, superstar?"],
    split: ["Splitting! Double the fun, double the drama!"],
    charlie: ["SIX CARDS and still in! The lounge is losing it!"],
    idle: ["The VIP lounge is waiting!", "Take your time, superstar."],
  },
  bacardi: {
    deal: ["Cards are cold. Like me.", "The ice table is open. Play or leave."],
    hit: ["Another card. Brave or foolish. We will see."],
    stand: ["Standing. The ice approves."],
    bust: ["Busted. The ice is unforgiving."],
    win: ["You beat the Ice. That does not happen often."],
    blackjack: ["Natural 21 at the ice table. Legends will speak of this."],
    push: ["Push. The ice and the player are equal. For now."],
    dealer_bust: ["The ice cracked. It will not happen twice."],
    surrender: ["Surrendering at the ice table? Smart. Most do not survive."],
    insurance: ["Ace in the frost. Insure yourself. Or do not."],
    split: ["Splitting at the ice table. Dangerous. I like it."],
    charlie: ["Six cards against the Ice. You have earned my respect."],
    idle: ["The ice waits for no one.", "Still here? Then play."],
  },
}

// ============================================================
// ELEVENLABS VOICE
// ============================================================

const SUPABASE_URL = 'https://jdqqmsmwmbsnlnstyavl.supabase.co'

async function speakLine(text: string, voiceId: string) {
  try {
    const resp = await fetch(`${SUPABASE_URL}/functions/v1/dealer-speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice_id: voiceId }),
    })
    if (resp.ok) {
      const blob = await resp.blob()
      const audio = new Audio(URL.createObjectURL(blob))
      audio.volume = 0.7
      await audio.play()
    }
  } catch {
    if ('speechSynthesis' in window) {
      const utter = new SpeechSynthesisUtterance(text)
      utter.rate = 0.88
      utter.pitch = 0.85
      window.speechSynthesis.speak(utter)
    }
  }
}

function useDealerSpeak() {
  const { activeDealer, voiceEnabled, phase, outcome } = useBlackjackStore()

  const speak = useCallback((category: string) => {
    const lines = DEALER_LINES[activeDealer.id]?.[category] || DEALER_LINES.aria.idle
    const line = lines[Math.floor(Math.random() * lines.length)]
    useBlackjackStore.getState().setDealerLine(line)
    if (voiceEnabled) {
      speakLine(line, activeDealer.voiceId)
    }
  }, [activeDealer, voiceEnabled])

  return speak
}

// ============================================================
// AMBIENT MUSIC
// ============================================================

// Old inline music removed -- now using Tone.js via audio-engine.ts

// ============================================================
// PLAYING CARD COMPONENT
// ============================================================

function PlayingCard({ card, index, skinId }: { card: CardData; index: number; skinId: string }) {
  const skin = getSkin(skinId)
  const overlap = Math.min(index * 36, 160)
  const rarity = card.rarity || 'common'
  const rarityEffect = getRarityEffect(rarity)

  if (card.faceDown) {
    const back = getCardBack(useBlackjackStore.getState().player.equippedCardBack)
    return (
      <motion.div
        initial={{ opacity: 0, x: 200, rotateY: 180, scale: 0 }}
        animate={{ opacity: 1, x: 0, rotateY: 0, scale: 1 }}
        transition={{ duration: 0.4, delay: index * 0.3, ease: [0.34, 1.56, 0.64, 1] }}
        className="absolute top-0 w-[70px] h-[100px] md:w-[80px] md:h-[115px] rounded-lg no-select flex items-center justify-center"
        style={{
          left: `${overlap}px`,
          background: back.background,
          border: `2px solid ${back.borderColor}`,
          boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
          zIndex: index,
        }}
      >
        <span style={{ fontSize: '2rem', color: back.iconColor }}>{back.centerIcon}</span>
      </motion.div>
    )
  }

  const isRed = card.suit === 'hearts' || card.suit === 'diamonds'
  const suitColor = isRed ? skin.redSuitColor : skin.blackSuitColor
  const symbol = SUIT_SYMBOLS[card.suit]
  const isFace = ['J', 'Q', 'K', 'A'].includes(card.rank)

  // Rarity-based visual enhancements
  const rarityGlow = rarityEffect.glowEffect || ''
  const hasShimmer = rarityEffect.shimmerEffect !== null

  return (
    <motion.div
      initial={{ opacity: 0, x: 200, rotateY: -180, scale: 0 }}
      animate={{ opacity: 1, x: 0, rotateY: 0, scale: 1 }}
      transition={{ duration: 0.5, delay: index * 0.3, type: 'spring', stiffness: 120, damping: 14 }}
      className="absolute top-0 w-[70px] h-[100px] md:w-[80px] md:h-[115px] rounded-lg flex flex-col justify-between p-1.5 no-select"
      style={{
        left: `${overlap}px`,
        background: skin.cardBg,
        border: `1px solid ${isFace ? skin.cardBorder : '#ddd'}`,
        boxShadow: `0 4px 20px rgba(0,0,0,0.6)${rarityGlow ? `, ${rarityGlow}` : ''}${skin.hoverGlow ? `, 0 0 8px ${skin.hoverGlow}20` : ''}`,
        zIndex: index,
        fontFamily: skin.rankFont,
        overflow: 'hidden',
      }}
    >
      {/* Holographic shimmer overlay (for rare+ cards) */}
      {hasShimmer && (
        <motion.div
          className="absolute inset-0 pointer-events-none rounded-lg"
          style={{
            background: rarityEffect.shimmerEffect === 'diagonal_sweep'
              ? `linear-gradient(${rarityEffect.shimmerAngle}deg, transparent 30%, rgba(255,255,255,0.12) 50%, transparent 70%)`
              : rarityEffect.shimmerEffect === 'holographic'
                ? 'linear-gradient(135deg, rgba(255,0,0,0.05), rgba(0,255,0,0.05), rgba(0,0,255,0.05), rgba(255,255,0,0.05), rgba(255,0,255,0.05))'
                : rarityEffect.shimmerEffect === 'full_spectrum'
                  ? 'linear-gradient(45deg, rgba(255,0,0,0.08), rgba(255,165,0,0.08), rgba(255,255,0,0.08), rgba(0,128,0,0.08), rgba(0,0,255,0.08), rgba(128,0,128,0.08))'
                  : 'none',
            backgroundSize: '200% 200%',
            mixBlendMode: 'screen',
          }}
          animate={{
            backgroundPosition: ['0% 0%', '200% 200%'],
          }}
          transition={{
            duration: rarityEffect.shimmerSpeed || 3,
            repeat: Infinity,
            ease: 'linear',
          }}
        />
      )}
      <div className="leading-none">
        <div className="text-base md:text-lg font-bold" style={{ color: suitColor }}>{card.rank}</div>
        <div className="text-xs" style={{ color: suitColor }}>{symbol}</div>
      </div>
      <div className="flex-1 flex items-center justify-center">
        <span className="text-xl md:text-2xl" style={{ color: suitColor, opacity: isFace ? 1 : 0.5 }}>
          {isFace ? card.rank : symbol}
        </span>
      </div>
      <div className="leading-none text-right rotate-180">
        <div className="text-base md:text-lg font-bold" style={{ color: suitColor }}>{card.rank}</div>
        <div className="text-xs" style={{ color: suitColor }}>{symbol}</div>
      </div>
    </motion.div>
  )
}

// ============================================================
// HAND DISPLAY
// ============================================================

function Hand({ cards, label, active, showValue, skinId }: {
  cards: CardData[]; label: string; active: boolean; showValue: boolean; skinId: string
}) {
  const visible = cards.filter(c => !c.faceDown)
  let val = 0, aces = 0
  for (const c of visible) {
    val += ['J','Q','K'].includes(c.rank) ? 10 : c.rank === 'A' ? 11 : parseInt(c.rank)
    if (c.rank === 'A') aces++
  }
  while (val > 21 && aces > 0) { val -= 10; aces-- }
  const bust = val > 21
  const bj = cards.length === 2 && val === 21

  return (
    <div className="text-center">
      <p className="text-[10px] uppercase tracking-widest mb-2" style={{
        color: active ? 'var(--gold)' : 'rgba(255,255,255,0.4)',
        fontFamily: "'Cinzel', serif", letterSpacing: '2px',
      }}>
        {label}
      </p>
      <div className="relative h-[100px] md:h-[115px] inline-block" style={{ minWidth: `${Math.min(cards.length * 36, 160) + 80}px` }}>
        {cards.map((c, i) => <PlayingCard key={`${c.rank}${c.suit}${i}${c.faceDown}`} card={c} index={i} skinId={skinId} />)}
      </div>
      {showValue && cards.length > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-2">
          <span className="text-2xl md:text-3xl font-black" style={{
            fontFamily: "'Cinzel', serif",
            color: bj ? 'var(--gold)' : bust ? 'var(--loss)' : '#fff',
            textShadow: bj ? '0 0 20px rgba(201,168,76,0.5)' : 'none',
          }}>
            {val}
          </span>
          {bj && <span className="ml-2 text-xs font-bold" style={{ color: 'var(--gold)' }}>BLACKJACK</span>}
          {bust && <span className="ml-2 text-xs font-bold" style={{ color: 'var(--loss)' }}>BUST</span>}
        </motion.div>
      )}
    </div>
  )
}

// ============================================================
// DEALER PANEL
// ============================================================

function DealerPanel() {
  const { activeDealer, dealerLine, showDealerSelect, togglePanel, setDealer } = useBlackjackStore()

  const dealers = [
    { id: 'aria', name: 'Aria Sinclair', title: 'House Dealer', vip: false, voiceId: 'EXAVITQu4vr4xnSDxMaL', color: '#c9a84c' },
    { id: 'marcus', name: 'Marcus Vega', title: 'High Roller', vip: false, voiceId: 'onwK4e9ZLuTAKqWW03F9', color: '#ff6b35' },
    { id: 'kanisha', name: 'Kanisha Thompson', title: 'VIP Lounge', vip: true, voiceId: 'XrExE9yKIg1WjnnlVkGX', color: '#e91e63' },
    { id: 'bacardi', name: 'Bacardi Ice', title: 'VIP Elite', vip: true, voiceId: 'onwK4e9ZLuTAKqWW03F9', color: '#00bcd4' },
  ]

  return (
    <div className="absolute right-4 top-[70px] z-20">
      <motion.div
        className="glass p-3 rounded-xl flex items-start gap-3 max-w-[240px] cursor-pointer"
        onClick={() => togglePanel('dealerSelect')}
        key={dealerLine}
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      >
        <div className="w-11 h-11 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
          style={{ background: `${activeDealer.color}30`, color: activeDealer.color, border: `2px solid ${activeDealer.color}60`, boxShadow: `0 0 20px ${activeDealer.color}30` }}>
          {activeDealer.name[0]}
        </div>
        <div className="min-w-0">
          <p className="text-xs font-semibold" style={{ color: activeDealer.color, fontFamily: "'Cinzel', serif" }}>
            {activeDealer.name}
          </p>
          <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>{activeDealer.title}</p>
          <p className="text-[10px] italic mt-1 line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
            &ldquo;{dealerLine}&rdquo;
          </p>
        </div>
      </motion.div>

      <AnimatePresence>
        {showDealerSelect && (
          <motion.div
            initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            className="glass-elevated p-3 rounded-xl mt-2 w-[260px] space-y-1.5"
          >
            {dealers.map(d => (
              <div key={d.id} onClick={() => setDealer(d)}
                className="flex items-center gap-2.5 p-2 rounded-lg cursor-pointer transition-colors"
                style={{
                  background: activeDealer.id === d.id ? `${d.color}12` : 'transparent',
                  border: `1px solid ${activeDealer.id === d.id ? d.color + '40' : 'transparent'}`,
                }}>
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                  style={{ background: d.color + '25', color: d.color }}>
                  {d.name[0]}
                </div>
                <div className="flex-1">
                  <p className="text-xs font-semibold" style={{ color: d.color }}>{d.name}</p>
                  <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>{d.title}</p>
                </div>
                {d.vip && <span className="text-[7px] bg-yellow-500 text-black font-bold px-1 rounded">VIP</span>}
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ============================================================
// OUTCOME OVERLAY
// ============================================================

function OutcomeOverlay() {
  const { outcome, winAmount, player, lightning } = useBlackjackStore()
  if (!outcome) return null

  const config: Record<string, { text: string; color: string; glow: string }> = {
    blackjack: { text: 'BLACKJACK', color: 'var(--gold)', glow: 'rgba(201,168,76,0.3)' },
    charlie: { text: 'SIX CARD CHARLIE', color: 'var(--gold)', glow: 'rgba(201,168,76,0.25)' },
    win: { text: 'YOU WIN', color: 'var(--win)', glow: 'rgba(0,230,118,0.2)' },
    loss: { text: 'DEALER WINS', color: 'var(--loss)', glow: 'rgba(255,45,85,0.12)' },
    bust: { text: 'BUST', color: 'var(--loss)', glow: 'rgba(255,45,85,0.2)' },
    push: { text: 'PUSH', color: '#58a6ff', glow: 'rgba(88,166,255,0.12)' },
    surrender: { text: 'SURRENDER', color: '#8b8b9e', glow: 'rgba(255,255,255,0.05)' },
  }

  const c = config[outcome] || config.loss
  const isWin = outcome === 'win' || outcome === 'blackjack' || outcome === 'charlie'

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.3 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ type: 'spring', stiffness: 300, damping: 15 }}
      className="absolute inset-0 flex items-center justify-center z-30 pointer-events-none"
      style={{ background: `radial-gradient(circle, ${c.glow}, transparent 70%)` }}
    >
      <div className="text-center">
        {lightning.active && lightning.multipliedTotal && isWin && (
          <motion.p
            initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
            className="text-sm font-bold mb-2"
            style={{ color: '#f1c40f' }}
          >
            LIGHTNING {lightning.multiplier}x
          </motion.p>
        )}
        <motion.p
          className="text-4xl md:text-6xl lg:text-7xl font-black tracking-wider"
          style={{
            fontFamily: "'Cinzel', serif",
            color: c.color,
            textShadow: `0 0 40px ${c.glow}, 0 0 80px ${c.glow}`,
            letterSpacing: '4px',
          }}
          animate={outcome === 'blackjack' ? { scale: [1, 1.12, 1] } : {}}
          transition={{ duration: 0.8 }}
        >
          {c.text}
        </motion.p>
        {isWin && winAmount > 0 && (
          <motion.p
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="font-mono text-xl md:text-2xl font-bold mt-3"
            style={{ color: c.color }}
          >
            +{winAmount.toLocaleString()} GC
          </motion.p>
        )}
        {player.presenceMultiplier > 1.0 && isWin && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
            className="text-xs mt-1" style={{ color: 'var(--gold)' }}>
            Presence: {player.presenceMultiplier.toFixed(2)}x
          </motion.p>
        )}
      </div>
    </motion.div>
  )
}

// ============================================================
// SIDE BET DISPLAY
// ============================================================

function SideBetResults() {
  const { sideBets, phase } = useBlackjackStore()
  if (phase !== 'settled') return null

  const results = [
    sideBets.perfectPairs.result ? { name: 'Perfect Pairs', result: sideBets.perfectPairs.result, payout: sideBets.perfectPairs.payout } : null,
    sideBets.twentyOnePlus3.result ? { name: '21+3', result: sideBets.twentyOnePlus3.result, payout: sideBets.twentyOnePlus3.payout } : null,
    sideBets.luckyLadies.result ? { name: 'Lucky Ladies', result: sideBets.luckyLadies.result, payout: sideBets.luckyLadies.payout } : null,
  ].filter(Boolean)

  if (results.length === 0) return null

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="absolute bottom-[180px] left-1/2 -translate-x-1/2 z-20 flex gap-2">
      {results.map((r, i) => (
        <div key={i} className="glass px-3 py-1.5 rounded-lg text-center">
          <p className="text-[9px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>{r!.name}</p>
          <p className="text-xs font-mono font-bold" style={{ color: r!.payout > 0 ? 'var(--win)' : 'var(--loss)' }}>
            {r!.payout > 0 ? `+${r!.payout}` : 'Miss'}
          </p>
        </div>
      ))}
    </motion.div>
  )
}

// ============================================================
// LOADING SCREEN
// ============================================================

function LoadingScreen({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(0)
  const steps = ['LOADING ASSETS', 'BUILDING CASINO TABLE', 'SUMMONING DEALERS', 'SHUFFLING THE DECK', 'IGNITING ATMOSPHERE', 'WELCOME TO VANTARIS']

  useEffect(() => {
    const timer = setInterval(() => {
      setStep(prev => {
        if (prev >= steps.length - 1) { clearInterval(timer); setTimeout(onComplete, 600); return prev }
        return prev + 1
      })
    }, 400)
    return () => clearInterval(timer)
  }, [onComplete])

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center" style={{ background: '#000' }}>
      <motion.h1 className="text-3xl md:text-5xl font-black tracking-widest mb-10"
        style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #c9a84c, #e8c55a)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}
        animate={{ opacity: [0.5, 1, 0.5] }} transition={{ duration: 2, repeat: Infinity }}>
        VANTARIS
      </motion.h1>
      <div className="w-64 md:w-80">
        <div className="h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.1)' }}>
          <motion.div className="h-full rounded-full" style={{ background: 'linear-gradient(90deg, #c9a84c, #e8c55a)' }}
            animate={{ width: `${((step + 1) / steps.length) * 100}%` }} transition={{ duration: 0.3 }} />
        </div>
        <p className="text-xs tracking-widest text-center mt-3" style={{ color: 'rgba(255,255,255,0.4)', letterSpacing: '2px' }}>
          {steps[step]}
        </p>
      </div>
    </div>
  )
}

// ============================================================
// MAIN PAGE
// ============================================================

export default function BlackjackPage() {
  const store = useBlackjackStore()
  const speak = useDealerSpeak()
  const [loading, setLoading] = useState(true)
  const [particleTrigger, setParticleTrigger] = useState(0)
  const [particleType, setParticleType] = useState<'blackjack' | 'win' | 'loss' | null>(null)

  // Overlay panel state (local since these don't affect game)
  const [showBoutique, setShowBoutique] = useState(false)
  const [showGemStore, setShowGemStore] = useState(false)
  const [showFreeChips, setShowFreeChips] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const [showLeaderboard, setShowLeaderboard] = useState(false)
  const [showAvatarBuilder, setShowAvatarBuilder] = useState(false)
  const [avatar, setAvatar] = useState<AvatarConfig>(DEFAULT_AVATAR)

  // Music effect (Tone.js procedural jazz)
  useEffect(() => {
    if (store.musicEnabled) startAmbientMusic()
    else stopAmbientMusic()
    return () => { stopAmbientMusic() }
  }, [store.musicEnabled])

  // Sound enabled sync
  useEffect(() => {
    setSoundEnabled(store.voiceEnabled)
  }, [store.voiceEnabled])

  // Audio on phase changes
  useEffect(() => {
    if (store.phase === 'dealing') {
      speak('deal')
      playCardDeal()       // card snap sound
      playChipClink()      // chip placed sound
    }
  }, [store.phase, speak])

  // Audio + particles + haptics + GSAP on outcomes
  useEffect(() => {
    if (!store.outcome) return

    const gameArea = document.getElementById('game-area')

    if (store.outcome === 'blackjack') {
      setParticleType('blackjack')
      setParticleTrigger(p => p + 1)
      playBlackjack()      // brass fanfare + shimmer
      if (navigator.vibrate) navigator.vibrate([50, 30, 50, 30, 100, 50, 200])
      speak('blackjack')
      // Lightning flash if active
      if (store.lightning.active && gameArea) lightningFlash(gameArea)
    } else if (store.outcome === 'win' || store.outcome === 'charlie') {
      setParticleType('win')
      setParticleTrigger(p => p + 1)
      playWin()            // ascending crystal chime
      if (navigator.vibrate) navigator.vibrate([50, 30, 50, 30, 100])
      speak(store.outcome === 'charlie' ? 'charlie' : 'win')
    } else if (store.outcome === 'bust') {
      setParticleType('loss')
      setParticleTrigger(p => p + 1)
      playBust()           // glass crack + low thud
      if (navigator.vibrate) navigator.vibrate([100, 50, 100])
      if (gameArea) screenShake(gameArea, 5, 0.4)  // GSAP screen shake
      speak('bust')
    } else if (store.outcome === 'loss') {
      setParticleType('loss')
      setParticleTrigger(p => p + 1)
      playLoss()           // descending minor tone
      if (navigator.vibrate) navigator.vibrate([100, 50, 100])
      speak('loss')
    } else if (store.outcome === 'push') {
      speak('push')
    } else if (store.outcome === 'surrender') {
      speak('surrender')
    }

    // Auto-reset after 2.2 seconds
    const timer = setTimeout(() => store.newRound(), 2200)
    return () => clearTimeout(timer)
  }, [store.outcome])

  // Speak on actions
  const handleHit = () => { store.playerHit(); speak('hit'); playHit(); playCardDeal() }
  const handleStand = () => { store.playerStand(); speak('stand'); playStand() }
  const handleDouble = () => { store.playerDouble(); speak('hit'); playCardDeal(); playChipClink() }
  const handleSplit = () => { store.playerSplit(); speak('split'); playSplit() }
  const handleSurrender = () => { store.playerSurrender(); speak('surrender'); playStand() }
  const handleInsurance = (take: boolean) => { store.playerInsurance(take); speak(take ? 'insurance' : 'deal'); if (take) playChipClink() }
  const handleDeal = () => { store.deal(); playButtonClick(); playChipClink() }
  const handleChipSelect = (v: number) => { store.selectChip(v); playChipClink() }
  const handleNewRound = () => { store.newRound(); playButtonClick() }

  if (loading) return <LoadingScreen onComplete={() => setLoading(false)} />

  const skinId = store.player.equippedDeckSkin
  const rankColor = RANK_COLORS[store.player.rank] || '#888'
  const showInsurance = store.phase === 'insurance'
  const showPlayerActions = store.phase === 'player_turn' || store.phase === 'split_turn'
  const canSplit = store.availableActions.includes('split')
  const canDouble = store.availableActions.includes('double')
  const canSurrender = store.availableActions.includes('surrender')

  return (
    <div className="min-h-screen h-screen flex flex-col overflow-hidden" style={{ background: 'var(--vanta-void)' }}>

      {/* === TOP BAR === */}
      <div className="flex items-center justify-between px-4 md:px-6 py-2.5 border-b relative z-20"
        style={{ background: 'linear-gradient(180deg, rgba(0,0,0,0.85), transparent)', borderColor: 'transparent' }}>

        <div className="flex items-center gap-3">
          <h1 className="text-base font-bold tracking-widest"
            style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #c9a84c, #e8c55a)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            VANTARIS
          </h1>
          {/* Chips */}
          <div className="flex items-center gap-1 px-3 py-1 rounded-full" style={{ background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(201,168,76,0.4)' }}>
            <span className="text-xs">&#x1FA99;</span>
            <span className="font-mono text-sm font-bold" style={{ color: 'var(--gold)' }}>{store.player.chips.toLocaleString()}</span>
          </div>
          {/* Gems */}
          <div className="flex items-center gap-1 px-3 py-1 rounded-full" style={{ background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(52,152,219,0.3)' }}>
            <span className="text-xs">&#x1F48E;</span>
            <span className="font-mono text-sm font-bold" style={{ color: '#58a6ff' }}>{store.player.gems}</span>
          </div>
          {/* Rank */}
          <div className="px-2 py-1 rounded-full text-[10px] font-bold tracking-wider"
            style={{ background: `${rankColor}15`, color: rankColor, border: `1px solid ${rankColor}30`, fontFamily: "'Cinzel', serif" }}>
            {store.player.rank}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <XPBar xp={store.player.xp} streak={store.player.currentStreak} />

          {/* Menu buttons */}
          {[
            { label: 'PROFILE', onClick: () => setShowProfile(true), color: 'var(--text-secondary)' },
            { label: 'SHOP', onClick: () => setShowBoutique(true), color: 'var(--text-secondary)' },
            { label: 'GEMS', onClick: () => setShowGemStore(true), color: '#58a6ff' },
            { label: 'FREE', onClick: () => setShowFreeChips(true), color: 'var(--win)' },
            { label: 'RANKS', onClick: () => setShowLeaderboard(true), color: 'var(--gold)' },
          ].map(btn => (
            <button key={btn.label} onClick={btn.onClick}
              className="text-[10px] px-2 py-1 rounded transition-colors hover:bg-white/5"
              style={{ color: btn.color, fontFamily: "'Cinzel', serif", letterSpacing: '1px' }}>
              {btn.label}
            </button>
          ))}

          {/* Music */}
          <button onClick={() => useBlackjackStore.setState({ musicEnabled: !store.musicEnabled })}
            className="text-sm px-1.5 py-1 rounded" style={{ color: store.musicEnabled ? 'var(--gold)' : 'var(--text-tertiary)' }}>
            {store.musicEnabled ? '\u266B' : '\u266B'}
          </button>
          {/* Voice */}
          <button onClick={() => useBlackjackStore.setState({ voiceEnabled: !store.voiceEnabled })}
            className="text-sm px-1.5 py-1 rounded" style={{ color: store.voiceEnabled ? 'var(--win)' : 'var(--text-tertiary)' }}>
            {store.voiceEnabled ? '\uD83D\uDD0A' : '\uD83D\uDD07'}
          </button>
        </div>
      </div>

      {/* === TABLE AREA === */}
      <div id="game-area" className="flex-1 relative overflow-hidden">

        {/* 3D Casino Scene */}
        <CasinoScene3D />

        {/* Win particles */}
        <WinParticles trigger={particleTrigger} type={particleType} />

        {/* Outcome overlay */}
        <AnimatePresence>
          {store.outcome && <OutcomeOverlay />}
        </AnimatePresence>

        {/* Side bet results */}
        <SideBetResults />

        {/* Dealer panel */}
        <DealerPanel />

        {/* Presence indicator (top left) */}
        <div className="absolute top-[60px] left-4 z-10 px-3 py-2 rounded-lg"
          style={{ background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(201,168,76,0.4)' }}>
          <p className="text-[8px] uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.4)', letterSpacing: '1px' }}>TABLE PRESENCE</p>
          <p className="text-base font-bold" style={{ color: 'var(--gold)', fontFamily: "'Cinzel', serif" }}>
            {store.player.presenceMultiplier.toFixed(2)}x
          </p>
        </div>

        {/* Streak display (top center) */}
        {store.player.currentStreak >= 2 && store.phase !== 'betting' && (
          <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
            className="absolute top-[60px] left-1/2 -translate-x-1/2 text-center z-10">
            <span className="text-2xl font-black block" style={{ fontFamily: "'Cinzel', serif", color: '#e67e22' }}>
              {store.player.currentStreak}
            </span>
            <span className="text-[9px] uppercase tracking-widest" style={{ color: '#e67e22', fontFamily: "'Cinzel', serif" }}>
              WIN STREAK
            </span>
          </motion.div>
        )}

        {/* Lightning indicator */}
        {store.lightning.active && store.phase !== 'betting' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="absolute top-[60px] right-[270px] z-10 px-3 py-2 rounded-lg text-center"
            style={{ background: 'rgba(241,196,15,0.1)', border: '1px solid rgba(241,196,15,0.3)' }}>
            <p className="text-[8px] uppercase tracking-widest" style={{ color: '#f1c40f' }}>LIGHTNING</p>
            <p className="text-base font-bold" style={{ color: '#f1c40f', fontFamily: "'Cinzel', serif" }}>
              {store.lightning.multiplier}x on {store.lightning.multipliedTotal}
            </p>
          </motion.div>
        )}

        {/* Card areas (absolute positioned over 3D scene) */}
        <div className="absolute inset-0 z-10 pointer-events-none">
          {/* Dealer hand at 25% from top */}
          <div className="absolute left-1/2 -translate-x-1/2" style={{ top: '22%' }}>
            <Hand cards={store.dealerHand.cards} label="DEALER" active={store.phase === 'dealer_turn'}
              showValue={store.phase === 'dealer_turn' || store.phase === 'settled'} skinId={skinId} />
          </div>

          {/* Player main hand at 58% from top */}
          <div className="absolute left-1/2 -translate-x-1/2" style={{ top: store.splitHand ? '52%' : '58%' }}>
            <Hand cards={store.mainHand.cards} label={store.splitHand ? 'HAND 1' : 'YOUR HAND'}
              active={store.phase === 'player_turn' && store.currentHandIndex === 0}
              showValue={store.mainHand.cards.length > 0} skinId={skinId} />
          </div>

          {/* Split hand (if active) at 72% */}
          {store.splitHand && (
            <div className="absolute left-1/2 -translate-x-1/2" style={{ top: '72%' }}>
              <Hand cards={store.splitHand.cards} label="HAND 2"
                active={store.phase === 'split_turn' && store.currentHandIndex === 1}
                showValue={true} skinId={skinId} />
            </div>
          )}
        </div>
      </div>

      {/* === CONTROLS === */}
      <div className="px-4 md:px-8 py-4 relative z-20"
        style={{ background: 'linear-gradient(0deg, rgba(0,0,0,0.9), transparent)' }}>

        {/* BETTING PHASE */}
        {store.phase === 'betting' && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center gap-3">
            <div className="text-center">
              <p className="text-[9px] uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.4)', fontFamily: "'Cinzel', serif", letterSpacing: '2px' }}>YOUR BET</p>
              <p className="font-mono text-2xl md:text-3xl font-bold" style={{ color: 'var(--gold)' }}>{store.betAmount.toLocaleString()}</p>
            </div>
            <div className="flex gap-3 items-end">
              {[10, 25, 100, 500, 1000, 5000].filter(v => v <= store.player.chips).map(v => (
                <CasinoChip key={v} value={v} selected={store.selectedChip === v}
                  onClick={() => handleChipSelect(v)} size={store.selectedChip === v ? 68 : 56} />
              ))}
            </div>
            <div className="flex gap-2">
              <button onClick={() => store.setBet(Math.max(10, Math.floor(store.betAmount / 2)))} className="btn-ghost text-xs px-3 py-1">1/2</button>
              <button onClick={() => store.setBet(Math.min(store.player.chips, store.betAmount * 2))} className="btn-ghost text-xs px-3 py-1">2x</button>
              <button onClick={() => store.setBet(Math.min(store.player.chips, store.config.maxBet))} className="btn-ghost text-xs px-3 py-1">MAX</button>
            </div>
            <motion.button onClick={handleDeal}
              className="px-14 py-3 text-sm tracking-widest font-bold rounded-xl"
              style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif", letterSpacing: '2px', boxShadow: '0 0 20px rgba(201,168,76,0.5)' }}
              whileHover={{ boxShadow: '0 0 35px rgba(201,168,76,0.8)', y: -2 }}
              whileTap={{ scale: 0.97 }}
              disabled={store.betAmount <= 0 || store.betAmount > store.player.chips}>
              DEAL
            </motion.button>
          </motion.div>
        )}

        {/* INSURANCE PHASE */}
        {showInsurance && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center gap-3">
            <p className="text-sm" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
              Dealer shows an Ace. Take insurance?
            </p>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
              Cost: {Math.floor(store.betAmount / 2).toLocaleString()} GC. Pays 2:1 if dealer has blackjack.
            </p>
            <div className="flex gap-3">
              <motion.button onClick={() => handleInsurance(true)}
                className="btn-primary px-8 py-2 text-sm tracking-widest" whileHover={{ scale: 1.03 }}>
                INSURE
              </motion.button>
              <motion.button onClick={() => handleInsurance(false)}
                className="btn-ghost px-8 py-2 text-sm tracking-widest" whileHover={{ scale: 1.03 }}>
                NO INSURANCE
              </motion.button>
            </div>
          </motion.div>
        )}

        {/* PLAYER ACTION PHASE */}
        {showPlayerActions && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-center gap-3 flex-wrap">
            <motion.button onClick={handleHit}
              className="px-8 py-2.5 text-sm tracking-widest font-bold rounded-xl"
              style={{ background: 'rgba(39,174,96,0.9)', color: '#fff', fontFamily: "'Cinzel', serif" }}
              whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              HIT
            </motion.button>
            <motion.button onClick={handleStand}
              className="px-8 py-2.5 text-sm tracking-widest font-bold rounded-xl"
              style={{ background: 'rgba(231,76,60,0.9)', color: '#fff', fontFamily: "'Cinzel', serif" }}
              whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              STAND
            </motion.button>
            {canDouble && (
              <motion.button onClick={handleDouble}
                className="px-8 py-2.5 text-sm tracking-widest font-bold rounded-xl"
                style={{ background: 'rgba(52,152,219,0.9)', color: '#fff', fontFamily: "'Cinzel', serif" }}
                whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                DOUBLE
              </motion.button>
            )}
            {canSplit && (
              <motion.button onClick={handleSplit}
                className="px-8 py-2.5 text-sm tracking-widest font-bold rounded-xl"
                style={{ background: 'rgba(142,68,173,0.9)', color: '#fff', fontFamily: "'Cinzel', serif" }}
                whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                SPLIT
              </motion.button>
            )}
            {canSurrender && (
              <motion.button onClick={handleSurrender}
                className="px-6 py-2.5 text-xs tracking-widest rounded-xl"
                style={{ background: 'rgba(127,140,141,0.9)', color: '#fff', fontFamily: "'Cinzel', serif" }}
                whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                SURRENDER
              </motion.button>
            )}
          </motion.div>
        )}

        {/* DEALING / DEALER TURN -- loading dots */}
        {(store.phase === 'dealing' || store.phase === 'dealer_turn') && (
          <div className="text-center py-2">
            <motion.div className="inline-flex gap-1" animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.5, repeat: Infinity }}>
              {[0, 1, 2].map(i => <div key={i} className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--gold)' }} />)}
            </motion.div>
          </div>
        )}

        {/* SETTLED -- handled by auto-reset timer in useEffect */}
        {store.phase === 'settled' && (
          <div className="text-center py-2">
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Next hand in a moment...</p>
          </div>
        )}
      </div>

      {/* === OVERLAY PANELS === */}
      <PlayerProfilePanel isOpen={showProfile} onClose={() => setShowProfile(false)}
        stats={store.player} unlockedAchievements={store.player.unlockedAchievements}
        onOpenAvatar={() => { setShowProfile(false); setShowAvatarBuilder(true) }}
        onLogout={() => console.log('logout')} />

      <AvatarBuilder isOpen={showAvatarBuilder} onClose={() => setShowAvatarBuilder(false)}
        currentAvatar={avatar} onSave={setAvatar} />

      <VantarisBoutique isOpen={showBoutique} onClose={() => setShowBoutique(false)}
        chips={store.player.chips} gems={store.player.gems}
        ownedItems={['default_suit']} equippedItems={{ outfit: 'default_suit' }}
        onPurchase={() => {}} onEquip={() => {}} />

      <GemStore isOpen={showGemStore} onClose={() => setShowGemStore(false)}
        currentGems={store.player.gems} onPurchase={() => setShowGemStore(false)} />

      <FreeChips isOpen={showFreeChips} onClose={() => setShowFreeChips(false)}
        refillsRemaining={10} currentStreak={store.player.currentStreak}
        onWatchAd={() => useBlackjackStore.setState(s => ({ player: { ...s.player, chips: s.player.chips + 100 } }))}
        onClaimDaily={() => useBlackjackStore.setState(s => ({ player: { ...s.player, chips: s.player.chips + 100 } }))}
        dailyClaimed={false} />

      <Leaderboard isOpen={showLeaderboard} onClose={() => setShowLeaderboard(false)} />
    </div>
  )
}
