'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useCallback, useState, useRef } from 'react'
import { useBlackjackStore } from '@/lib/blackjack-store'
import { getSkin, getCardBack, getRarityEffect } from '@/lib/card-skins'
import {
  WinParticles, XPBar, AchievementPopup, VantarisBoutique,
  GemStore, FreeChips, AvatarBuilder, DEFAULT_AVATAR,
  PlayerProfilePanel, Leaderboard, CasinoScene3D,
  BotPlayers, ToastContainer, DealerAvatar,
  WelcomeScreen, isNewPlayer, EmojiReactions, DealerChat, BettingLayout, SocialBar,
} from '@/components/blackjack'
import type { Achievement, AvatarConfig, SeatPosition } from '@/components/blackjack'
import type { Card as CardData } from '@/lib/blackjack-engine'

// Audio engine (Tone.js procedural sounds)
import {
  startAmbientMusic, stopAmbientMusic,
  playCardDeal, playChipClink, playHit, playStand,
  playWin, playBlackjack, playLoss, playBust, playSplit,
  playButtonClick,
  setSoundEnabled,
} from '@/lib/audio-engine'

// GSAP cinematic animations
import {
  screenShake, lightningFlash,
} from '@/lib/gsap-animations'

// Dealer intelligence (mood, chatter, achievements, history)
import {
  postHandSettle, startIdleChatter, stopIdleChatter,
  recalculatePresence,
  queueNarration, narrateResults, clearNarrationQueue,
} from '@/lib/dealer-intelligence'

// Toast helpers (for inline handlers)
import { toast, toastWin, toastInfo } from '@/components/blackjack/VantarisToast'

// Django backend sync (for production deployment)
import { initDjangoSync, syncHandResult } from '@/lib/django-sync'

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
    deal: ["Cards are cold. Like me.", "The ice table is open. Play or leave.", "Fresh deck. Fresh victims.", "Let us see who freezes first.", "The frost deals. You receive."],
    hit: ["Another card. Brave or foolish. We will see.", "You want more? Bold.", "Drawing from the frost.", "Take your card. Feel the chill.", "Interesting choice. The ice watches."],
    stand: ["Standing. The ice approves.", "Firm. Like permafrost.", "You hold your ground. Noted.", "Standing pat. Calculated."],
    bust: ["Busted. The ice is unforgiving.", "Over 21. The frost claims another.", "Too greedy. The ice punishes greed.", "Busted. Cold."],
    win: ["You beat the Ice. That does not happen often.", "Victory at the frost table. Impressive.", "A rare thaw. Take your chips.", "The Ice bows. Do not expect it again.", "You earned that. Respect."],
    blackjack: ["Natural 21 at the ice table. Legends will speak of this.", "Blackjack. The frost has never seen that play.", "Twenty one. Pure. Cold. Perfect.", "Flawless. Even Bacardi Ice is speechless."],
    push: ["Push. The ice and the player are equal. For now.", "A draw. Neither breaks.", "Stalemate. The frost holds."],
    dealer_bust: ["The ice cracked. It will not happen twice.", "I busted. Savor it. It is rare.", "The frost melted. Temporarily.", "Take your chips. The ice will rebuild."],
    surrender: ["Surrendering at the ice table? Smart. Most do not survive.", "Walking away. The survivors always do."],
    insurance: ["Ace in the frost. Insure yourself. Or do not.", "An Ace stares you down. Your call."],
    split: ["Splitting at the ice table. Dangerous. I like it.", "Two hands against the frost. Ambitious."],
    charlie: ["Six cards against the Ice. You have earned my respect.", "Six and still standing. The frost salutes you."],
    idle: ["The ice waits for no one.", "Still here? Then play.", "Silence at the frost table. That is either wisdom or fear.", "The longer you wait, the colder it gets.", "Make your move. The ice does not negotiate."],
  },
}

// ============================================================
// ELEVENLABS VOICE
// ============================================================

const SUPABASE_URL = 'https://jdqqmsmwmbsnlnstyavl.supabase.co'

// Speech cache: pre-warm common phrases for zero-latency dealer voice
const SPEECH_CACHE = new Map<string, Blob>()
const PREWARM_PHRASES = [
  'Place your bets.', 'Cards are dealt.', 'Bust. Dealer wins.',
  'Dealer stands.', 'Blackjack! Congratulations.', 'Winner winner.',
  'Push. No winner this hand.', 'No more bets.',
]

async function prewarmSpeechCache(voiceId: string) {
  for (const phrase of PREWARM_PHRASES) {
    try {
      const resp = await fetch(`${SUPABASE_URL}/functions/v1/dealer-speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: phrase, voice_id: voiceId }),
      })
      if (resp.ok) {
        SPEECH_CACHE.set(`${voiceId}:${phrase}`, await resp.blob())
      }
    } catch (err) {
      console.warn('[tts] Speech cache prewarm failed for:', phrase, err)
    }
  }
}

async function speakLine(text: string, voiceId: string) {
  useBlackjackStore.setState({ speaking: true })

  // Check cache first (zero latency for pre-warmed phrases)
  const cacheKey = `${voiceId}:${text}`
  if (SPEECH_CACHE.has(cacheKey)) {
    const audio = new Audio(URL.createObjectURL(SPEECH_CACHE.get(cacheKey)!))
    audio.volume = 0.7
    audio.onended = () => useBlackjackStore.setState({ speaking: false })
    await audio.play()
    return
  }

  try {
    const resp = await fetch(`${SUPABASE_URL}/functions/v1/dealer-speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice_id: voiceId }),
    })
    if (resp.ok) {
      const blob = await resp.blob()
      // Cache for next time
      if (SPEECH_CACHE.size < 50) SPEECH_CACHE.set(cacheKey, blob)
      const audio = new Audio(URL.createObjectURL(blob))
      audio.volume = 0.7
      audio.onended = () => useBlackjackStore.setState({ speaking: false })
      await audio.play()
      return
    }
  } catch {
    // ElevenLabs failed -- fall through to Web Speech API
  }
  // Web Speech API fallback (free, works offline)
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel() // cancel any pending speech
    const utter = new SpeechSynthesisUtterance(text)
    utter.rate = 0.88
    utter.pitch = 0.85
    utter.volume = 0.85
    utter.onend = () => useBlackjackStore.setState({ speaking: false })
    utter.onerror = () => useBlackjackStore.setState({ speaking: false })
    // Try to find a good voice
    const voices = window.speechSynthesis.getVoices()
    const preferred = voices.find(v => v.name.includes('Google') && v.lang.startsWith('en'))
      || voices.find(v => v.lang.startsWith('en-US'))
      || voices.find(v => v.lang.startsWith('en'))
    if (preferred) utter.voice = preferred
    window.speechSynthesis.speak(utter)
  } else {
    setTimeout(() => useBlackjackStore.setState({ speaking: false }), 2000)
  }
}

const lastSpokenRef: Record<string, string> = {}

function useDealerSpeak() {
  const { activeDealer, voiceEnabled, phase, outcome } = useBlackjackStore()

  const speak = useCallback((category: string) => {
    const lines = DEALER_LINES[activeDealer.id]?.[category] || DEALER_LINES.aria.idle
    // Never repeat the last spoken line in this category
    const lastKey = `${activeDealer.id}:${category}`
    let line = lines[Math.floor(Math.random() * lines.length)]
    if (lines.length > 1 && line === lastSpokenRef[lastKey]) {
      // Pick a different one
      const others = lines.filter(l => l !== lastSpokenRef[lastKey])
      line = others[Math.floor(Math.random() * others.length)]
    }
    lastSpokenRef[lastKey] = line
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
        initial={{ opacity: 0, x: 40, y: -60, rotateY: 90, scale: 0.7 }}
        animate={{ opacity: 1, x: 0, y: 0, rotateY: 0, scale: 1 }}
        transition={{ duration: 0.25, delay: index * 0.15, ease: [0.34, 1.56, 0.64, 1] }}
        className="absolute top-0 w-[70px] h-[100px] md:w-[80px] md:h-[115px] rounded-lg no-select flex items-center justify-center"
        style={{
          left: `${overlap}px`,
          background: back.background,
          border: `2px solid ${back.borderColor}`,
          boxShadow: `0 4px 20px rgba(0,0,0,0.6), 0 0 12px ${back.borderColor}30`,
          zIndex: index,
        }}
      >
        <span style={{ fontSize: '1.6rem', color: back.iconColor }}>{back.centerIcon}</span>
      </motion.div>
    )
  }

  const isRed = card.suit === 'hearts' || card.suit === 'diamonds'
  const suitColor = isRed ? '#e8c55a' : '#c9a84c' // Gold tones for VIP look
  const symbol = SUIT_SYMBOLS[card.suit]
  const isFace = ['J', 'Q', 'K', 'A'].includes(card.rank)

  // Rarity-based visual enhancements
  const rarityGlow = rarityEffect.glowEffect || ''
  const hasShimmer = rarityEffect.shimmerEffect !== null

  return (
    <motion.div
      initial={{ opacity: 0, x: 40, y: -60, rotateY: -90, scale: 0.7 }}
      animate={{ opacity: 1, x: 0, y: 0, rotateY: 0, scale: 1 }}
      transition={{ duration: 0.3, delay: index * 0.15, ease: [0.34, 1.56, 0.64, 1] }}
      className="absolute top-0 w-[70px] h-[100px] md:w-[80px] md:h-[115px] rounded-lg flex flex-col justify-between p-1.5 no-select"
      style={{
        left: `${overlap}px`,
        background: 'linear-gradient(145deg, #1a1a1a, #0d0d0d)',
        border: `1px solid ${isFace ? '#c9a84c' : '#333'}`,
        boxShadow: `0 4px 20px rgba(0,0,0,0.7), 0 0 ${isFace ? '15' : '8'}px rgba(201,168,76,${isFace ? '0.25' : '0.1'})${rarityGlow ? `, ${rarityGlow}` : ''}`,
        zIndex: index,
        fontFamily: "'Cinzel', serif",
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
  const { activeDealer, dealerLine, speaking, showDealerSelect, togglePanel, setDealer } = useBlackjackStore()

  const dealers = [
    { id: 'aria', name: 'Aria Sinclair', title: 'House Dealer', vip: false, voiceId: 'EXAVITQu4vr4xnSDxMaL', color: '#c9a84c' },
    { id: 'marcus', name: 'Marcus Vega', title: 'High Roller', vip: false, voiceId: 'onwK4e9ZLuTAKqWW03F9', color: '#ff6b35' },
    { id: 'kanisha', name: 'Kanisha Thompson', title: 'VIP Lounge', vip: true, voiceId: 'XrExE9yKIg1WjnnlVkGX', color: '#e91e63' },
    { id: 'bacardi', name: 'Bacardi Ice', title: 'VIP Elite', vip: true, voiceId: 'pNInz6obpgDQGcFmaJgB', color: '#00bcd4' },
  ]

  return (
    <div className="absolute left-1/2 -translate-x-1/2 top-[55px] md:top-[65px] z-20">
      <motion.div
        className="glass p-2 md:p-3 rounded-xl flex items-center gap-2 md:gap-3 max-w-[240px] md:max-w-[300px] cursor-pointer"
        onClick={() => togglePanel('dealerSelect')}
        key={dealerLine}
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex-shrink-0">
          <DealerAvatar dealerId={activeDealer.id} color={activeDealer.color} speaking={speaking} size={48} />
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
            className="glass-elevated p-3 rounded-xl mt-2 w-[240px] md:w-[280px] space-y-1.5"
          >
            {dealers.map(d => (
              <div key={d.id} onClick={() => setDealer(d)}
                className="flex items-center gap-2.5 p-2 rounded-lg cursor-pointer transition-colors"
                style={{
                  background: activeDealer.id === d.id ? `${d.color}12` : 'transparent',
                  border: `1px solid ${activeDealer.id === d.id ? d.color + '40' : 'transparent'}`,
                }}>
                <DealerAvatar dealerId={d.id} color={d.color} speaking={false} size={36} />
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
// PROGRESSIVE JACKPOT
const JACKPOT_START = 500000
const JACKPOT_MAX = 5000000
// ============================================================

// Check for suited 7-7-7 (progressive jackpot trigger)
function checkSuited777(cards: CardData[]): boolean {
  if (cards.length < 3) return false
  const sevens = cards.filter(c => c.rank === '7')
  if (sevens.length < 3) return false
  // Check if any 3 sevens share the same suit
  const suitCounts: Record<string, number> = {}
  for (const c of sevens) {
    suitCounts[c.suit] = (suitCounts[c.suit] || 0) + 1
    if (suitCounts[c.suit] >= 3) return true
  }
  return false
}

function ProgressiveJackpot({ betAmount, phase, cards, luckyLuckyActive }: {
  betAmount: number; phase: string; cards: CardData[]; luckyLuckyActive: boolean
}) {
  const [jackpot, setJackpot] = useState(() => {
    if (typeof window === 'undefined') return JACKPOT_START
    const saved = localStorage.getItem('vantaris_jackpot')
    return saved ? parseInt(saved) : 500000
  })
  const [won, setWon] = useState(false)

  // Increment over time (every second) + on bets
  useEffect(() => {
    const timer = setInterval(() => {
      setJackpot(prev => {
        const next = prev + Math.floor(10 + Math.random() * 40)
        if (next >= JACKPOT_MAX) {
          localStorage.setItem('vantaris_jackpot', '500000')
          return JACKPOT_START
        }
        localStorage.setItem('vantaris_jackpot', String(next))
        return next
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Add to jackpot when player deals (1% of Lucky Lucky bets)
  useEffect(() => {
    if (phase === 'dealing' && betAmount > 0 && luckyLuckyActive) {
      setJackpot(prev => {
        const next = prev + Math.floor(betAmount * 0.05) // 5% of bet feeds jackpot
        localStorage.setItem('vantaris_jackpot', String(next))
        return next
      })
    }
  }, [phase])

  // Check for suited 7-7-7 on settle
  useEffect(() => {
    if (phase === 'settled' && luckyLuckyActive && cards.length >= 3) {
      if (checkSuited777(cards)) {
        // JACKPOT HIT!
        setWon(true)
        const winAmount = jackpot
        useBlackjackStore.setState(s => ({
          player: { ...s.player, chips: s.player.chips + winAmount },
        }))
        toast({ type: 'achievement', title: 'PROGRESSIVE JACKPOT!', message: `Suited 7-7-7! You won ${winAmount.toLocaleString()} GC!`, icon: '\uD83C\uDFC6', duration: 8000 })
        setJackpot(500000)
        localStorage.setItem('vantaris_jackpot', '500000')
        setTimeout(() => setWon(false), 5000)
      }
    }
  }, [phase])

  return (
    <div className="absolute top-2 left-1/2 -translate-x-1/2 z-20 text-center">
      <p className="text-[7px] md:text-[8px] uppercase tracking-widest" style={{
        color: 'rgba(201,168,76,0.5)', fontFamily: "'Cinzel', serif", letterSpacing: '2px',
      }}>
        PROGRESSIVE JACKPOT
      </p>
      <motion.p
        key={jackpot}
        className="font-mono text-lg md:text-xl font-black"
        style={{
          background: won
            ? 'linear-gradient(135deg, #00e676, #69f0ae, #00e676)'
            : 'linear-gradient(135deg, #c9a84c, #f0d080, #c9a84c)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          textShadow: 'none',
          filter: won
            ? 'drop-shadow(0 0 20px rgba(0,230,118,0.6))'
            : 'drop-shadow(0 0 8px rgba(201,168,76,0.3))',
        }}
        animate={won ? { scale: [1, 1.3, 1] } : {}}
        transition={won ? { duration: 0.5, repeat: 5 } : {}}
      >
        {won ? 'JACKPOT WON!' : `${jackpot.toLocaleString()} GC`}
      </motion.p>
      {won && (
        <p className="text-[9px] font-bold" style={{ color: 'var(--win)' }}>
          Suited 7-7-7! Congratulations!
        </p>
      )}
    </div>
  )
}

// ============================================================
// SIDE BET DISPLAY
// ============================================================

function SideBetResults() {
  const { sideBets, phase, seats, activeSeatIndices } = useBlackjackStore()
  if (phase !== 'settled') return null

  // Collect side bet results from all active seats
  const allResults: { name: string; result: string; payout: number; seat: number }[] = []
  for (const si of activeSeatIndices) {
    const sb = seats[si]?.sideBets || sideBets
    if (sb.perfectPairs.active) {
      allResults.push({ name: 'PAIRS', result: sb.perfectPairs.result || 'Miss', payout: sb.perfectPairs.payout, seat: si })
    }
    // 21+3 removed from UI per user request
    if (sb.luckyLadies.active) {
      allResults.push({ name: 'LADIES', result: sb.luckyLadies.result || 'Miss', payout: sb.luckyLadies.payout, seat: si })
    }
  }

  if (allResults.length === 0) return null

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="absolute bottom-[180px] left-1/2 -translate-x-1/2 z-20 flex gap-2 flex-wrap justify-center">
      {allResults.map((r, i) => (
        <motion.div key={i} initial={{ scale: 0.8 }} animate={{ scale: 1 }}
          transition={{ delay: i * 0.15, type: 'spring' }}
          className="px-3 py-2 rounded-xl text-center"
          style={{
            background: r.payout > 0 ? 'rgba(0,230,118,0.12)' : 'rgba(255,45,85,0.08)',
            border: `1px solid ${r.payout > 0 ? 'rgba(0,230,118,0.3)' : 'rgba(255,45,85,0.2)'}`,
            boxShadow: r.payout > 0 ? '0 0 12px rgba(0,230,118,0.15)' : 'none',
          }}>
          <p className="text-[8px] uppercase tracking-wider font-bold" style={{ color: r.payout > 0 ? 'var(--win)' : 'var(--loss)' }}>{r.name}</p>
          {r.payout > 0 ? (
            <>
              <p className="text-[9px]" style={{ color: 'rgba(255,255,255,0.6)' }}>{r.result}</p>
              <p className="text-sm font-mono font-bold" style={{ color: 'var(--win)' }}>+{r.payout.toLocaleString()}</p>
            </>
          ) : (
            <p className="text-[10px] font-mono" style={{ color: 'var(--loss)' }}>Miss</p>
          )}
        </motion.div>
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
  const [showWelcome, setShowWelcome] = useState(false)

  // Check localStorage on mount only (avoids SSR hydration mismatch)
  useEffect(() => {
    if (isNewPlayer()) setShowWelcome(true)
  }, [])
  const [loading, setLoading] = useState(true)
  const [particleTrigger, setParticleTrigger] = useState(0)
  const [particleType, setParticleType] = useState<'blackjack' | 'win' | 'loss' | null>(null)

  const [showTablePicker, setShowTablePicker] = useState(false)
  const [showNavMenu, setShowNavMenu] = useState(false)

  // Seat positions projected from 3D scene (for bot labels)
  const defaultSeats: SeatPosition[] = Array(5).fill({ x: 0, y: 0, visible: false })
  const [seatPositions, setSeatPositions] = useState<SeatPosition[]>(defaultSeats)

  // Overlay panel state (local since these don't affect game)
  const [showBoutique, setShowBoutique] = useState(false)
  const [showGemStore, setShowGemStore] = useState(false)
  const [showFreeChips, setShowFreeChips] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const [showLeaderboard, setShowLeaderboard] = useState(false)
  const [showAvatarBuilder, setShowAvatarBuilder] = useState(false)
  const [avatar, setAvatar] = useState<AvatarConfig>(DEFAULT_AVATAR)

  // Free chips state (persisted in localStorage)
  const [adRefills, setAdRefills] = useState(10)
  const [dailyClaimed, setDailyClaimed] = useState(false)
  const [lastBet, setLastBet] = useState(0)

  // Load free chip state from localStorage on mount
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('vantaris_ad_refills') || '{}')
      if (saved.date === new Date().toDateString()) setAdRefills(saved.count)
      if (localStorage.getItem('vantaris_daily') === new Date().toDateString()) setDailyClaimed(true)
    } catch (err) {
      console.warn('[blackjack] Failed to load free chip state:', err)
    }
  }, [])

  // Music effect (Tone.js procedural jazz)
  useEffect(() => {
    if (store.musicEnabled) startAmbientMusic()
    else stopAmbientMusic()
    return () => { stopAmbientMusic() }
  }, [store.musicEnabled])

  // Dealer idle chatter (45-90s interval during betting)
  useEffect(() => {
    startIdleChatter()
    initDjangoSync() // prepare backend connection (no-op in dev)
    // Pre-warm speech cache with common dealer phrases (background, non-blocking)
    if (store.voiceEnabled) {
      prewarmSpeechCache(store.activeDealer.voiceId)
    }
    return () => stopIdleChatter()
  }, [])

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

    // Run dealer intelligence (achievements, mood, history, reshuffle)
    // Narrate per-seat results
    narrateResults()

    // Sync hand result to Django backend (no-op in dev)
    syncHandResult({
      outcome: store.outcome || 'loss',
      player_total: store.mainHand.value,
      dealer_total: store.dealerHand.value,
      bet: store.mainHand.bet,
      payout: store.winAmount,
      side_bets: {},
    })

    const moodLine = postHandSettle()
    if (moodLine) {
      setTimeout(() => {
        useBlackjackStore.setState({ dealerLine: moodLine })
      }, 1500)
    }

    // Auto-reset after 2.5 seconds (slightly longer to allow toasts)
    const timer = setTimeout(() => store.newRound(), 2500)
    return () => clearTimeout(timer)
  }, [store.outcome])

  // Speak on actions
  const handleHit = () => {
    queueNarration('seat_hits', { seat: store.currentSeatIndex + 1 })
    store.playerHit(); speak('hit'); playHit(); playCardDeal()
  }
  const handleStand = () => {
    queueNarration('seat_stands', { seat: store.currentSeatIndex + 1 })
    store.playerStand(); speak('stand'); playStand()
  }
  const handleDouble = () => {
    // DOUBLE DOWN MADNESS -- progressive doubling (double bet + draw card, can repeat)
    queueNarration('seat_doubles', { seat: store.currentSeatIndex + 1 })
    store.playerDoubleHit(); speak('hit'); playCardDeal(); playChipClink()

    const gameArea = document.getElementById('game-area')
    if (gameArea) {
      // Triple flash + heavy shake
      lightningFlash(gameArea)
      setTimeout(() => lightningFlash(gameArea), 150)
      setTimeout(() => lightningFlash(gameArea), 300)
      screenShake(gameArea, 8, 0.5)
    }

    // Gold particle burst for double down
    setParticleType('blackjack')
    setParticleTrigger(p => p + 1)

    // Heavy haptic
    if (navigator.vibrate) navigator.vibrate([50, 30, 80, 30, 120, 50, 200])

    // Play blackjack fanfare for the drama
    playBlackjack()
  }
  const handleSplit = () => { store.playerSplit(); speak('split'); playSplit() }
  const handleSurrender = () => { store.playerSurrender(); speak('surrender'); playStand() }
  const handleInsurance = (take: boolean) => { store.playerInsurance(take); speak(take ? 'insurance' : 'deal'); if (take) playChipClink() }
  const handleDeal = () => {
    setLastBet(store.betAmount) // save for REBET
    clearNarrationQueue()
    queueNarration('cards_out')
    store.deal(); playButtonClick(); playChipClink()
  }
  const handleRebet = () => {
    if (lastBet > 0 && lastBet <= store.player.chips) {
      store.setBet(lastBet)
    }
  }
  const handleChipSelect = (v: number) => { store.selectChip(v); playChipClink() }
  const handleNewRound = () => { store.newRound(); playButtonClick() }

  if (showWelcome) return <WelcomeScreen onComplete={(playerName, dealerId) => {
    // Set chosen dealer
    const dealers = [
      { id: 'aria', name: 'Aria Sinclair', title: 'House Dealer', vip: false, voiceId: 'EXAVITQu4vr4xnSDxMaL', color: '#c9a84c' },
      { id: 'marcus', name: 'Marcus Vega', title: 'High Roller', vip: false, voiceId: 'onwK4e9ZLuTAKqWW03F9', color: '#ff6b35' },
      { id: 'kanisha', name: 'Kanisha Thompson', title: 'VIP Lounge', vip: true, voiceId: 'XrExE9yKIg1WjnnlVkGX', color: '#e91e63' },
      { id: 'bacardi', name: 'Bacardi Ice', title: 'VIP Elite', vip: true, voiceId: 'pNInz6obpgDQGcFmaJgB', color: '#00bcd4' },
    ]
    const dealer = dealers.find(d => d.id === dealerId) || dealers[0]
    store.setDealer(dealer)
    localStorage.setItem('vantaris_player_name', playerName)
    setShowWelcome(false)
  }} />

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

      {/* Toast notification system */}
      <ToastContainer />

      {/* === TOP BAR === */}
      <div className="flex items-center justify-between px-2 md:px-6 py-2 md:py-2.5 border-b relative z-20"
        style={{ background: 'linear-gradient(180deg, rgba(0,0,0,0.85), transparent)', borderColor: 'transparent' }}>

        <div className="flex items-center gap-1.5 md:gap-3">
          {/* Back to lobby */}
          <a href="/lobby" className="text-sm px-1.5 py-1 rounded hover:bg-white/5" style={{ color: 'var(--text-tertiary)' }}>
            {'\u2190'}
          </a>

          {/* Nav menu */}
          <div className="relative">
            <button onClick={() => setShowNavMenu(!showNavMenu)}
              className="text-sm px-1.5 py-1 rounded hover:bg-white/5" style={{ color: 'var(--text-tertiary)' }}>
              {'\u2630'}
            </button>
            <AnimatePresence>
              {showNavMenu && (
                <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                  className="absolute top-full left-0 mt-2 z-50 glass-elevated rounded-xl p-2 w-[180px] space-y-0.5">
                  {[
                    { label: 'Lobby', href: '/lobby', icon: '\u2605' },
                    { label: 'Wallet', href: '/wallet', icon: '\u2668' },
                    { label: 'Rewards', href: '/rewards', icon: '\u2B50' },
                    { label: 'Profile', href: '/profile', icon: '\u263A' },
                    { label: 'Redeem SC', href: '/redeem', icon: '\u2714' },
                    { label: 'Settings', href: '/settings', icon: '\u2699' },
                    { label: 'Support', href: '/support', icon: '\u2753' },
                  ].map(item => (
                    <a key={item.label} href={item.href}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs hover:bg-white/5 transition-colors"
                      style={{ color: 'var(--text-secondary)' }}>
                      <span>{item.icon}</span>
                      <span>{item.label}</span>
                    </a>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="relative">
            <button onClick={() => setShowTablePicker(!showTablePicker)} className="flex items-center gap-1.5">
              <h1 className="text-sm md:text-base font-bold tracking-widest"
                style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #c9a84c, #e8c55a)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                VANTARIS
              </h1>
              <span className="text-[8px] px-1.5 py-0.5 rounded uppercase tracking-wider font-bold"
                style={{
                  background: store.config.lightningEnabled ? 'rgba(241,196,15,0.15)' : 'rgba(201,168,76,0.1)',
                  color: store.config.lightningEnabled ? '#f1c40f' : 'rgba(201,168,76,0.6)',
                  border: `1px solid ${store.config.lightningEnabled ? 'rgba(241,196,15,0.3)' : 'rgba(201,168,76,0.2)'}`,
                  fontFamily: "'Cinzel', serif",
                }}>
                {store.config.variant || 'classic'}
              </span>
            </button>

            <AnimatePresence>
              {showTablePicker && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                  className="absolute top-full left-0 mt-2 z-50 glass-elevated rounded-xl p-2 w-[260px] space-y-1"
                >
                  {[
                    { id: 'classic', name: 'Classic', desc: '$10-$5K, 6 deck, 3:2 BJ', icon: '\u2663', color: '#27ae60' },
                    { id: 'lightning', name: 'Lightning', desc: '$50-$25K, random 2x-25x', icon: '\u26A1', color: '#f1c40f' },
                    { id: 'speed', name: 'Speed', desc: '$25-$10K, fast pace', icon: '\uD83D\uDCA8', color: '#3498db' },
                    { id: 'switch', name: 'Switch', desc: '$100-$25K, 6:5 BJ payout', icon: '\uD83D\uDD00', color: '#9b59b6' },
                    { id: 'highroller', name: 'High Roller', desc: '$500-$50K, all features', icon: '\uD83D\uDC8E', color: '#e74c3c' },
                  ].map(t => (
                    <button key={t.id}
                      onClick={() => { store.setTableVariant(t.id); setShowTablePicker(false) }}
                      className="w-full flex items-center gap-2.5 p-2 rounded-lg text-left transition-colors hover:bg-white/5"
                      style={{
                        background: (store.config.variant || 'classic') === t.id ? `${t.color}12` : 'transparent',
                        border: `1px solid ${(store.config.variant || 'classic') === t.id ? t.color + '40' : 'transparent'}`,
                      }}
                    >
                      <span className="text-base">{t.icon}</span>
                      <div>
                        <p className="text-xs font-semibold" style={{ color: t.color, fontFamily: "'Cinzel', serif" }}>{t.name}</p>
                        <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>{t.desc}</p>
                      </div>
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          {/* Chips */}
          <div className="flex items-center gap-1 px-2 md:px-3 py-1 rounded-full" style={{ background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(201,168,76,0.4)' }}>
            <span className="text-[10px] md:text-xs">{'\uD83E\uDE99'}</span>
            <span className="font-mono text-xs md:text-sm font-bold" style={{ color: store.gameMode === 'sc' ? 'var(--win)' : 'var(--gold)' }}>
              {store.gameMode === 'sc' ? store.player.sweepsCoins.toFixed(2) : store.player.chips.toLocaleString()}
            </span>
          </div>
          {/* Gems */}
          <div className="flex items-center gap-1 px-2 md:px-3 py-1 rounded-full" style={{ background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(52,152,219,0.3)' }}>
            <span className="text-[10px] md:text-xs">{'\uD83D\uDC8E'}</span>
            <span className="font-mono text-xs md:text-sm font-bold" style={{ color: '#58a6ff' }}>{store.player.gems}</span>
          </div>
          {/* Rank (hidden on small mobile) */}
          <div className="hidden sm:block px-2 py-1 rounded-full text-[10px] font-bold tracking-wider"
            style={{ background: `${rankColor}15`, color: rankColor, border: `1px solid ${rankColor}30`, fontFamily: "'Cinzel', serif" }}>
            {store.player.rank}
          </div>
        </div>

        <div className="flex items-center gap-1 md:gap-2">
          <div className="hidden md:block">
            <XPBar xp={store.player.xp} streak={store.player.currentStreak} />
          </div>

          {/* Menu buttons -- icons on mobile, text on desktop */}
          {[
            { label: 'PROFILE', icon: '\uD83D\uDC64', onClick: () => setShowProfile(true), color: 'var(--text-secondary)' },
            { label: 'SHOP', icon: '\uD83D\uDECD\uFE0F', onClick: () => setShowBoutique(true), color: 'var(--text-secondary)' },
            { label: 'FREE', icon: '\uD83C\uDF81', onClick: () => setShowFreeChips(true), color: 'var(--win)' },
            { label: 'RANKS', icon: '\uD83C\uDFC6', onClick: () => setShowLeaderboard(true), color: 'var(--gold)' },
          ].map(btn => (
            <button key={btn.label} onClick={btn.onClick}
              className="text-[10px] px-1.5 md:px-2 py-1 rounded transition-colors hover:bg-white/5"
              style={{ color: btn.color, fontFamily: "'Cinzel', serif", letterSpacing: '1px' }}>
              <span className="md:hidden">{btn.icon}</span>
              <span className="hidden md:inline">{btn.label}</span>
            </button>
          ))}

          {/* GC/SC Mode Toggle */}
          <button onClick={() => {
            const newMode = store.gameMode === 'gc' ? 'sc' : 'gc'
            useBlackjackStore.setState({ gameMode: newMode })
            toastInfo(newMode === 'sc' ? 'Sweepstakes Mode' : 'Social Mode',
              newMode === 'sc' ? 'Playing with SC. Wins redeemable!' : 'Playing with GC. Fun play.')
          }}
            className="text-[9px] px-2 py-1 rounded-full font-bold"
            style={{
              background: store.gameMode === 'sc' ? 'rgba(0,230,118,0.15)' : 'rgba(201,168,76,0.1)',
              color: store.gameMode === 'sc' ? 'var(--win)' : 'var(--gold)',
              border: `1px solid ${store.gameMode === 'sc' ? 'rgba(0,230,118,0.3)' : 'rgba(201,168,76,0.2)'}`,
            }}>
            {store.gameMode === 'sc' ? 'SC' : 'GC'}
          </button>

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

          {/* Fullscreen */}
          <button onClick={() => {
            if (!document.fullscreenElement) {
              document.documentElement.requestFullscreen?.()
            } else {
              document.exitFullscreen?.()
            }
          }}
            className="text-sm px-1.5 py-1 rounded" style={{ color: 'var(--text-tertiary)' }}>
            {'\u26F6'}
          </button>
        </div>
      </div>

      {/* === TABLE AREA === */}
      <div id="game-area" className="flex-1 relative overflow-hidden">

        {/* 3D Casino Scene */}
        <CasinoScene3D onSeatPositions={setSeatPositions} feltColor={
          store.player.equippedFelt === 'felt_crimson' ? '#5c0d0d' :
          store.player.equippedFelt === 'felt_midnight' ? '#0d1a5c' :
          store.player.equippedFelt === 'felt_legend' ? '#0a0a0a' :
          '#0d5c2e'
        } />

        {/* Bot players at projected seat positions */}
        <BotPlayers seatPositions={seatPositions} />

        {/* Betting layout: Mickey Mouse ear circles on table with chip tray */}
        <BettingLayout seatPositions={seatPositions} />

        {/* Social bar: emojis + gifts + chat (near player seat) */}
        <SocialBar seatPositions={seatPositions} />

        {/* Bot emoji reactions (they still react to outcomes) */}
        <EmojiReactions seatPositions={seatPositions} />

        {/* AI dealer chat / strategy coach */}
        <DealerChat />

        {/* Win particles */}
        <WinParticles trigger={particleTrigger} type={particleType} />

        {/* Outcome overlay */}
        <AnimatePresence>
          {store.outcome && <OutcomeOverlay />}
        </AnimatePresence>

        {/* Side bet results */}
        <SideBetResults />

        {/* Progressive Jackpot -- top center, grows in real-time */}
        <ProgressiveJackpot betAmount={store.betAmount} phase={store.phase}
          cards={store.mainHand.cards} luckyLuckyActive={store.sideBets.perfectPairs.active} />

        {/* Dealer panel -- centered on table */}
        <DealerPanel />

        {/* Presence indicator (top left) */}
        {/* Presence indicator -- hidden on very small mobile */}
        <div className="absolute top-[55px] md:top-[60px] left-2 md:left-4 z-10 px-2 md:px-3 py-1.5 md:py-2 rounded-lg hidden sm:block"
          style={{ background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(201,168,76,0.4)' }}>
          <p className="text-[7px] md:text-[8px] uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.4)', letterSpacing: '1px' }}>PRESENCE</p>
          <p className="text-sm md:text-base font-bold" style={{ color: 'var(--gold)', fontFamily: "'Cinzel', serif" }}>
            {store.player.presenceMultiplier.toFixed(2)}x
          </p>
        </div>

        {/* Streak display (top center) -- with fire effects at 3+, golden aura at 5+, lightning at 10+ */}
        {store.player.currentStreak >= 2 && store.phase !== 'betting' && (
          <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
            className="absolute top-[55px] md:top-[60px] left-1/2 -translate-x-1/2 text-center z-10 px-4 py-2 rounded-xl"
            style={{
              background: store.player.currentStreak >= 5
                ? 'radial-gradient(circle, rgba(201,168,76,0.15), transparent 70%)'
                : store.player.currentStreak >= 3
                  ? 'radial-gradient(circle, rgba(230,126,34,0.12), transparent 70%)'
                  : 'transparent',
              boxShadow: store.player.currentStreak >= 10
                ? '0 0 40px rgba(241,196,15,0.3), 0 0 80px rgba(241,196,15,0.1)'
                : store.player.currentStreak >= 5
                  ? '0 0 25px rgba(201,168,76,0.2)'
                  : 'none',
            }}
          >
            {/* Fire emoji for 3+ streak */}
            {store.player.currentStreak >= 3 && (
              <motion.span
                animate={{ y: [0, -3, 0], scale: [1, 1.1, 1] }}
                transition={{ duration: 0.6, repeat: Infinity }}
                className="text-lg block mb-0.5"
              >
                {store.player.currentStreak >= 10 ? '\u26A1' : store.player.currentStreak >= 5 ? '\uD83D\uDD25' : '\uD83D\uDCA5'}
              </motion.span>
            )}
            <motion.span
              className="text-2xl md:text-3xl font-black block"
              style={{
                fontFamily: "'Cinzel', serif",
                color: store.player.currentStreak >= 10 ? '#f1c40f' : store.player.currentStreak >= 5 ? '#c9a84c' : '#e67e22',
                textShadow: store.player.currentStreak >= 5
                  ? '0 0 20px rgba(201,168,76,0.5), 0 0 40px rgba(201,168,76,0.2)'
                  : '0 0 10px rgba(230,126,34,0.3)',
              }}
              animate={store.player.currentStreak >= 5 ? { scale: [1, 1.08, 1] } : {}}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              {store.player.currentStreak}
            </motion.span>
            <span className="text-[8px] md:text-[9px] uppercase tracking-widest block" style={{
              color: store.player.currentStreak >= 5 ? '#c9a84c' : '#e67e22',
              fontFamily: "'Cinzel', serif",
              letterSpacing: '2px',
            }}>
              {store.player.currentStreak >= 10 ? 'LEGENDARY STREAK' : store.player.currentStreak >= 5 ? 'HOT STREAK' : 'WIN STREAK'}
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

          {/* All active seats' cards positioned around the table */}
          {store.activeSeatIndices.map(si => {
            const seat = store.seats[si]
            if (!seat || seat.hand.cards.length === 0) return null
            const seatPos = seatPositions[si]
            const isCurrentSeat = si === store.currentSeatIndex
            const isCenterSeat = si === 2

            // Center seat shows larger + lower, side seats show at their projected position
            if (isCenterSeat) {
              return (
                <div key={si} className="absolute left-1/2 -translate-x-1/2" style={{ top: seat.splitHand ? '48%' : '58%' }}>
                  {/* Main hand */}
                  <div style={{
                    opacity: seat.splitHand && store.currentHandIndex === 1 ? 0.5 : 1,
                    transition: 'opacity 0.3s',
                  }}>
                    <Hand cards={seat.hand.cards}
                      label={seat.splitHand ? 'HAND 1' : (store.activeSeatIndices.length > 1 ? `SEAT ${si + 1}` : 'YOUR HAND')}
                      active={isCurrentSeat && store.phase === 'player_turn' && store.currentHandIndex === 0}
                      showValue={seat.hand.cards.length > 0} skinId={skinId} />
                  </div>
                  {/* Split hand -- clearly separated below */}
                  {seat.splitHand && (
                    <div className="mt-4" style={{
                      opacity: store.currentHandIndex === 0 ? 0.5 : 1,
                      transition: 'opacity 0.3s',
                    }}>
                      <Hand cards={seat.splitHand.cards} label="HAND 2"
                        active={isCurrentSeat && store.phase === 'split_turn' && store.currentHandIndex === 1}
                        showValue={true} skinId={skinId} />
                    </div>
                  )}
                </div>
              )
            }

            // Non-center seats: position near their table seat
            if (!seatPos?.visible) return null
            return (
              <div key={si} className="absolute" style={{
                left: `${seatPos.x}px`,
                top: `${Math.min(seatPos.y - 60, 400)}px`,
                transform: 'translate(-50%, 0) scale(0.75)',
                opacity: isCurrentSeat ? 1 : 0.8,
              }}>
                <Hand cards={seat.hand.cards} label={`SEAT ${si + 1}`}
                  active={isCurrentSeat && store.phase === 'player_turn'}
                  showValue={seat.hand.cards.length > 0} skinId={skinId} />
              </div>
            )
          })}

        </div>
      </div>

      {/* === CONTROLS === */}
      <div className="px-2 md:px-8 py-3 md:py-4 relative z-20"
        style={{ background: 'linear-gradient(0deg, rgba(0,0,0,0.9), transparent)' }}>

        {/* BETTING PHASE -- chips and circles are on the table (BettingLayout), this is just the DEAL bar */}
        {store.phase === 'betting' && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-center gap-3 flex-wrap">
            {/* Bet display */}
            <div className="text-center px-4">
              <p className="text-[8px] uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.4)', fontFamily: "'Cinzel', serif" }}>YOUR BET</p>
              <p className="font-mono text-lg md:text-2xl font-bold" style={{ color: store.gameMode === 'sc' ? 'var(--win)' : 'var(--gold)' }}>
                {store.betAmount.toLocaleString()} <span className="text-xs">{store.gameMode === 'sc' ? 'SC' : 'GC'}</span>
              </p>
              {/* Guidance messages */}
              {store.betAmount === 0 && (
                <p className="text-[9px] mt-1" style={{ color: '#ffb300' }}>Tap a chip to place your bet</p>
              )}
              {store.betAmount > 0 && store.betAmount < store.config.minBet && (
                <p className="text-[9px] mt-1" style={{ color: '#ff5252' }}>Minimum bet: {store.config.minBet} {store.gameMode === 'sc' ? 'SC' : 'GC'}</p>
              )}
              {store.betAmount > (store.gameMode === 'sc' ? store.player.sweepsCoins : store.player.chips) && (
                <p className="text-[9px] mt-1" style={{ color: '#ff5252' }}>Not enough chips! Claim free chips or lower your bet</p>
              )}
              {store.betAmount >= store.config.minBet && store.betAmount <= (store.gameMode === 'sc' ? store.player.sweepsCoins : store.player.chips) && (
                <p className="text-[9px] mt-1" style={{ color: 'rgba(255,255,255,0.25)' }}>
                  Table: {store.config.minBet}-{store.config.maxBet.toLocaleString()} {store.gameMode === 'sc' ? 'SC' : 'GC'}
                </p>
              )}
            </div>

            {/* Compact action row: CLEAR | REBET | 2x | MAX | DEAL */}
            <div className="flex gap-1.5 md:gap-2 items-center justify-center flex-wrap">
              <button onClick={() => {
                store.setBet(0)
                // Also clear all side bets
                if (store.sideBets.perfectPairs.active) store.toggleSideBet('perfectPairs', 0)
                if (store.sideBets.luckyLadies.active) store.toggleSideBet('luckyLadies', 0)
                if (store.sideBets.progressive.active) store.toggleSideBet('progressive', 0)
              }}
                className="text-[10px] md:text-xs px-2 md:px-3 py-1.5 rounded-lg"
                style={{ background: 'rgba(255,45,85,0.08)', color: 'var(--loss)', border: '1px solid rgba(255,45,85,0.2)' }}>
                CLEAR
              </button>
              {lastBet > 0 && (
                <button onClick={handleRebet}
                  className="text-[10px] md:text-xs px-2 md:px-3 py-1.5 rounded-lg"
                  style={{ background: 'rgba(201,168,76,0.08)', color: '#c9a84c', border: '1px solid rgba(201,168,76,0.2)' }}>
                  REBET
                </button>
              )}
              <button onClick={() => store.setBet(Math.min(store.betAmount * 2, store.player.chips, store.config.maxBet))}
                className="text-[10px] md:text-xs px-2 md:px-3 py-1.5 rounded-lg"
                style={{ background: 'rgba(88,166,255,0.08)', color: '#58a6ff', border: '1px solid rgba(88,166,255,0.2)' }}>
                2x
              </button>
              <button onClick={() => store.setBet(Math.min(store.player.chips, store.config.maxBet))}
                className="text-[10px] md:text-xs px-2 md:px-3 py-1.5 rounded-lg"
                style={{ background: 'rgba(255,255,255,0.04)', color: 'var(--text-tertiary)', border: '1px solid rgba(255,255,255,0.1)' }}>
                MAX
              </button>
              <motion.button onClick={handleDeal}
                className="px-6 md:px-10 py-2 md:py-2.5 text-xs md:text-sm tracking-widest font-bold rounded-xl"
                style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif", letterSpacing: '2px', boxShadow: '0 0 15px rgba(201,168,76,0.4)' }}
                whileHover={{ boxShadow: '0 0 25px rgba(201,168,76,0.7)', y: -1 }}
                whileTap={{ scale: 0.97 }}
                disabled={store.betAmount <= 0 || store.betAmount < store.config.minBet || store.betAmount * store.activeSeatIndices.length > store.player.chips}>
                {store.activeSeatIndices.length > 1 ? `DEAL (${store.activeSeatIndices.length})` : 'DEAL'}
              </motion.button>
            </div>
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
            className="flex flex-col items-center gap-2">
            {/* Current seat indicator */}
            {store.activeSeatIndices.length > 1 && (
              <p className="text-[10px] uppercase tracking-widest" style={{
                color: 'var(--gold)', fontFamily: "'Cinzel', serif", letterSpacing: '2px',
              }}>
                SEAT {store.currentSeatIndex + 1} &mdash; YOUR ACTION
              </p>
            )}
            <div className="flex items-center justify-center gap-2 md:gap-3 flex-wrap">
            <motion.button onClick={handleHit}
              className="px-6 md:px-8 py-2 md:py-2.5 text-xs md:text-sm tracking-widest font-bold rounded-xl"
              style={{ background: 'rgba(39,174,96,0.9)', color: '#fff', fontFamily: "'Cinzel', serif" }}
              whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              HIT
            </motion.button>
            <motion.button onClick={handleStand}
              className="px-6 md:px-8 py-2 md:py-2.5 text-xs md:text-sm tracking-widest font-bold rounded-xl"
              style={{ background: 'rgba(231,76,60,0.9)', color: '#fff', fontFamily: "'Cinzel', serif" }}
              whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              STAND
            </motion.button>
            {/* Double Down Madness: available if player has ANY chips left */}
            {store.mainHand.cards.length >= 2 && store.player.chips > 0 && (() => {
              const canFullDouble = store.player.chips >= store.mainHand.bet
              const doubleAmount = Math.min(store.mainHand.bet, store.player.chips)
              return (
                <motion.button onClick={handleDouble}
                  className="px-4 md:px-6 py-2 md:py-2.5 text-[10px] md:text-xs tracking-widest font-bold rounded-xl"
                  style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif", boxShadow: '0 0 15px rgba(201,168,76,0.4)' }}
                  whileHover={{ scale: 1.05, boxShadow: '0 0 25px rgba(201,168,76,0.6)' }} whileTap={{ scale: 0.95 }}>
                  {canFullDouble
                    ? `DOUBLE (${store.mainHand.bet} \u2192 ${store.mainHand.bet * 2})`
                    : `DOUBLE FOR LESS (+${doubleAmount})`}
                </motion.button>
              )
            })()}
            {canSplit && (
              <motion.button onClick={handleSplit}
                className="px-5 md:px-8 py-2 md:py-2.5 text-xs md:text-sm tracking-widest font-bold rounded-xl"
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
            </div>
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

        {/* SETTLED -- per-seat results + auto-reset */}
        {store.phase === 'settled' && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="text-center py-2">
            {/* Multi-seat result breakdown */}
            {store.seatResults.length > 1 && (
              <div className="flex justify-center gap-3 mb-2">
                {store.seatResults.map((r, i) => {
                  const isWin = r.outcome === 'win' || r.outcome === 'blackjack' || r.outcome === 'charlie'
                  const isPush = r.outcome === 'push'
                  const color = isWin ? 'var(--win)' : isPush ? '#58a6ff' : 'var(--loss)'
                  return (
                    <div key={i} className="glass px-3 py-1.5 rounded-lg">
                      <p className="text-[8px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                        Seat {r.seatIndex + 1}
                      </p>
                      <p className="text-xs font-bold uppercase" style={{ color }}>{r.outcome}</p>
                      <p className="text-[10px] font-mono" style={{ color }}>
                        {r.payout > 0 ? `+${r.payout.toLocaleString()}` : r.payout === 0 ? 'PUSH' : `-${store.betAmount}`}
                      </p>
                    </div>
                  )
                })}
              </div>
            )}
            <p className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>Next hand in a moment...</p>
          </motion.div>
        )}
      </div>

      {/* === OVERLAY PANELS === */}
      <PlayerProfilePanel isOpen={showProfile} onClose={() => setShowProfile(false)}
        stats={store.player} unlockedAchievements={store.player.unlockedAchievements}
        onOpenAvatar={() => { setShowProfile(false); setShowAvatarBuilder(true) }}
        onLogout={() => console.log('logout')}
        settings={{
          soundEnabled: store.voiceEnabled,
          musicEnabled: store.musicEnabled,
          voiceEnabled: store.voiceEnabled,
          autoRebet: store.autoRebet,
          onToggle: (key, value) => {
            if (key === 'music') useBlackjackStore.setState({ musicEnabled: value })
            else if (key === 'voice') useBlackjackStore.setState({ voiceEnabled: value })
            else if (key === 'sound') useBlackjackStore.setState({ voiceEnabled: value })
            else if (key === 'autorebet') useBlackjackStore.setState({ autoRebet: value })
          },
        }}
      />

      <AvatarBuilder isOpen={showAvatarBuilder} onClose={() => setShowAvatarBuilder(false)}
        currentAvatar={avatar} onSave={setAvatar} />

      <VantarisBoutique isOpen={showBoutique} onClose={() => setShowBoutique(false)}
        chips={store.player.chips} gems={store.player.gems}
        ownedItems={store.player.ownedItems}
        equippedItems={{ outfit: store.player.equippedOutfit, aura: store.player.equippedAura, deck: store.player.equippedDeckSkin, card_back: store.player.equippedCardBack }}
        onPurchase={(item, currency) => {
          const p = store.player
          if (currency === 'chips' && p.chips >= item.priceChips) {
            useBlackjackStore.setState({ player: { ...p, chips: p.chips - item.priceChips, ownedItems: [...p.ownedItems, item.id] } })
            toastWin('Purchased!', `${item.name} is now yours.`)
          } else if (currency === 'gems' && p.gems >= item.priceGems) {
            useBlackjackStore.setState({ player: { ...p, gems: p.gems - item.priceGems, ownedItems: [...p.ownedItems, item.id] } })
            toastWin('Purchased!', `${item.name} is now yours.`)
          }
        }}
        onEquip={(item) => {
          const p = store.player
          const updates: Record<string, string> = {}
          if (item.category === 'outfit') updates.equippedOutfit = item.id
          else if (item.category === 'aura') updates.equippedAura = item.id
          else if (item.category === 'card_back') updates.equippedCardBack = item.id
          else if (item.category === 'table_felt') updates.equippedFelt = item.id
          useBlackjackStore.setState({ player: { ...p, ...updates } })
          recalculatePresence()
          toastInfo('Equipped', `${item.name} equipped!`)
        }}
      />

      <GemStore isOpen={showGemStore} onClose={() => setShowGemStore(false)}
        currentGems={store.player.gems}
        onPurchase={(packageId) => {
          const packs: Record<string, { gems: number; bonus: number; gc: number }> = {
            starter: { gems: 100, bonus: 0, gc: 500 },
            player: { gems: 500, bonus: 100, gc: 2500 },
            high_roller: { gems: 1200, bonus: 300, gc: 5000 },
            vip_bundle: { gems: 3000, bonus: 1000, gc: 15000 },
            casino_boss: { gems: 7000, bonus: 3000, gc: 50000 },
          }
          const pack = packs[packageId]
          if (pack) {
            const p = store.player
            useBlackjackStore.setState({
              player: { ...p, gems: p.gems + pack.gems + pack.bonus, chips: p.chips + pack.gc }
            })
            toastWin('Gems Credited!', `+${pack.gems + pack.bonus} gems and +${pack.gc.toLocaleString()} GC`)
          }
          setShowGemStore(false)
        }}
      />

      <FreeChips isOpen={showFreeChips} onClose={() => setShowFreeChips(false)}
        refillsRemaining={adRefills} currentStreak={store.player.currentStreak}
        onWatchAd={() => {
          if (adRefills > 0) {
            const p = store.player
            useBlackjackStore.setState({ player: { ...p, chips: p.chips + 100 } })
            setAdRefills(prev => prev - 1)
            localStorage.setItem('vantaris_ad_refills', JSON.stringify({ count: adRefills - 1, date: new Date().toDateString() }))
            toastWin('+100 GC', 'Ad reward claimed!')
          }
        }}
        onClaimDaily={() => {
          if (!dailyClaimed) {
            const p = store.player
            const streakBonus = Math.min(p.currentStreak * 10, 200)
            const reward = 100 + streakBonus
            useBlackjackStore.setState({ player: { ...p, chips: p.chips + reward } })
            setDailyClaimed(true)
            localStorage.setItem('vantaris_daily', new Date().toDateString())
            toastWin(`+${reward} GC`, `Daily bonus! ${streakBonus > 0 ? `(+${streakBonus} streak bonus)` : ''}`)
          }
        }}
        dailyClaimed={dailyClaimed}
      />

      <Leaderboard isOpen={showLeaderboard} onClose={() => setShowLeaderboard(false)}
        playerStats={{
          name: localStorage.getItem('vantaris_player_name') || 'Player',
          tier: store.player.rank,
          chipsWon: store.player.biggestWin,
          hands: store.player.handsPlayed,
          winRate: store.player.handsPlayed > 0 ? (store.player.handsWon / store.player.handsPlayed) * 100 : 0,
        }}
      />
    </div>
  )
}
