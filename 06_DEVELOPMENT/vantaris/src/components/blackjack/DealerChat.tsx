'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useBlackjackStore } from '@/lib/blackjack-store'
import { getPlayerProfile } from '@/lib/supabase'

/**
 * DealerChat -- the table's dealer + strategy coach.
 *
 * TWO tiers:
 *  - FREE (everyone): instant static basic-strategy hints (the `dealer-chat`
 *    action + the local fallback). No AI tokens, $0. This stays free so no player
 *    is ever required to pay for help -- a compliance anchor for the sweepstakes.
 *  - PRO COACHING (premium): a conversational AI dealer that answers anything and
 *    explains WHY. Paid in GOLD COINS only (never Sweeps Coins). Each reply costs
 *    Gold = 3x its token cost (floored), OR is free under an active Coaching Pass.
 *    All metering is server-side (blackjack-api `dealer-ai` / `buy-coaching-pass`).
 *
 * Gated by PRO_COACHING_ENABLED until the metering edge fn is deployed; until then
 * the chat behaves exactly as before (free static hints only).
 */

const API_URL = 'https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api'
const API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww'

// Premium AI coaching. OFF until the blackjack-api dealer-ai/buy-coaching-pass
// actions are deployed (+ the coaching_pass_until column migration applied).
// Flip to true post-deploy; the free static hints work regardless.
const PRO_COACHING_ENABLED = false
const COACHING_PASS_GC = 250  // display only; server is source of truth

// Premium AI ask: server meters Gold + runs the LLM. Returns reply + what it cost.
async function getPremiumResponse(
  playerId: string,
  message: string,
  gameState: Record<string, unknown>,
): Promise<{ reply?: string; chargedGold?: number; goldBalance?: number; passActive?: boolean; error?: string; neededGold?: number }> {
  try {
    const res = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'apikey': API_KEY, 'Authorization': `Bearer ${API_KEY}` },
      body: JSON.stringify({ action: 'dealer-ai', player_id: playerId, message, game_state: gameState }),
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok && data.success) {
      return { reply: data.reply, chargedGold: data.charged_gold, goldBalance: data.gold_balance, passActive: data.pass_active }
    }
    return { error: data.error || 'coach_error', neededGold: data.needed_gold }
  } catch {
    return { error: 'coach_error' }
  }
}

async function buyCoachingPass(playerId: string): Promise<{ ok: boolean; until?: string; goldBalance?: number; error?: string; neededGold?: number }> {
  try {
    const res = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'apikey': API_KEY, 'Authorization': `Bearer ${API_KEY}` },
      body: JSON.stringify({ action: 'buy-coaching-pass', player_id: playerId }),
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok && data.success) return { ok: true, until: data.coaching_pass_until, goldBalance: data.gold_balance }
    return { ok: false, error: data.error || 'error', neededGold: data.needed_gold }
  } catch {
    return { ok: false, error: 'error' }
  }
}

interface ChatMessage {
  id: number
  type: 'player' | 'dealer' | 'coach'
  name: string
  text: string
  timestamp: number
}

let msgId = 0

async function getDealerResponse(message: string, gameState: Record<string, unknown>): Promise<string> {
  try {
    const res = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': API_KEY,
        'Authorization': `Bearer ${API_KEY}`,
      },
      body: JSON.stringify({
        action: 'dealer-chat',
        player_id: 'local_player',
        message,
        display_name: typeof window !== 'undefined' ? localStorage.getItem('vantaris_player_name') || 'Player' : 'Player',
        table_id: 'vantaris_main',
        game_state: gameState,
      }),
    })
    if (res.ok) {
      const data = await res.json()
      return data.reply || data.message || 'Good play. Keep it up.'
    }
  } catch { /* fall through */ }
  return getLocalStrategyHint(gameState)
}

function getLocalStrategyHint(gs: Record<string, unknown>): string {
  const total = (gs.player_total as number) || 0
  const dealer = (gs.dealer_upcard as number) || 0
  if (!total) return 'Ask me about your hand and I will break down the strategy.'
  if (total >= 17) return `Stand on ${total}. Let the dealer take the risk.`
  if (total <= 11) return `Hit on ${total}. You cannot bust.`
  if (total >= 13 && total <= 16 && dealer >= 2 && dealer <= 6) return `Stand on ${total} vs dealer ${dealer}. Dealer is likely to bust.`
  if (total === 12 && dealer >= 4 && dealer <= 6) return `Stand on 12 vs dealer ${dealer}. Small risk of busting.`
  return `With ${total} vs dealer ${dealer}, basic strategy says Hit. The odds favor drawing.`
}

// Safe text rendering: only convert bold markers and newlines (no arbitrary HTML)
function formatDealerText(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*.*?\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} style={{ color: '#c9a84c' }}>{part.slice(2, -2)}</strong>
    }
    // Split on newlines
    const lines = part.split('\n')
    return lines.map((line, j) => (
      <span key={`${i}-${j}`}>{j > 0 && <br />}{line}</span>
    ))
  })
}

export function DealerChat() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [typing, setTyping] = useState(false)
  const [proMode, setProMode] = useState(false)         // premium AI tutor on/off
  const [playerId, setPlayerId] = useState<string | null>(null)  // resolved when signed in
  const [passActive, setPassActive] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const phase = useBlackjackStore(s => s.phase)
  const outcome = useBlackjackStore(s => s.outcome)
  const mainHand = useBlackjackStore(s => s.mainHand)
  const dealerHand = useBlackjackStore(s => s.dealerHand)
  const activeDealer = useBlackjackStore(s => s.activeDealer)

  // Resolve the signed-in player's id once (premium AI needs a real account).
  useEffect(() => {
    if (!PRO_COACHING_ENABLED || !isOpen || playerId) return
    getPlayerProfile('').then((p: any) => p?.player_id && setPlayerId(p.player_id)).catch(() => {})
  }, [isOpen, playerId])

  // System line helper for the chat (coach/info notices).
  const sysMsg = (text: string) =>
    setMessages(prev => [...prev, { id: msgId++, type: 'coach', name: 'Coaching', text, timestamp: Date.now() }])

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages])

  // Welcome on first open
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([{
        id: msgId++, type: 'dealer', name: activeDealer.name,
        text: `Welcome to the table! I'm ${activeDealer.name}. Ask me anything about your hand or basic strategy. I can see your cards and help you make the best play.`,
        timestamp: Date.now(),
      }])
    }
  }, [isOpen])

  // Auto-coach after each hand + bot chatter
  useEffect(() => {
    if (!outcome || !isOpen) return

    // Bot chat messages (random 1-2 bots react in chat)
    const bots = useBlackjackStore.getState().bots.filter(b => !b.sittingOut)
    const chatBots = bots.sort(() => Math.random() - 0.5).slice(0, Math.random() < 0.4 ? 1 : 2)
    const botWinLines = ['Nice hand!', 'GG!', 'Big money!', 'Let\'s go!', 'You\'re on fire']
    const botLossLines = ['Tough luck', 'Next one', 'Happens to the best', 'The cards will turn', 'Keep playing']
    const botBJLines = ['BLACKJACK! Wow!', 'That\'s insane!', 'Legend status!', 'No way!', 'Unreal!']

    chatBots.forEach((bot, i) => {
      setTimeout(() => {
        const isPlayerWin = outcome === 'win' || outcome === 'blackjack' || outcome === 'charlie'
        const pool = outcome === 'blackjack' ? botBJLines : isPlayerWin ? botWinLines : botLossLines
        setMessages(prev => [...prev, {
          id: msgId++, type: 'player' as const, name: bot.name,
          text: pool[Math.floor(Math.random() * pool.length)],
          timestamp: Date.now(),
        }])
      }, 800 + i * 1500)
    })

    // Dealer coaching (after bots chat)
    setTimeout(() => {
      setTyping(true)
      const gs = {
        player_total: mainHand.value,
        dealer_upcard: dealerHand.cards[0]?.rank,
        dealer_total: dealerHand.value,
        last_result: outcome,
        phase: 'result',
      }
      getDealerResponse('how was that hand?', gs).then(reply => {
        setTyping(false)
        setMessages(prev => [...prev, {
          id: msgId++, type: 'coach', name: 'Coach',
          text: reply, timestamp: Date.now(),
        }])
      })
    }, 1500 + chatBots.length * 1500)
  }, [outcome])

  const handleSend = async () => {
    const text = input.trim()
    if (!text) return
    setInput('')
    setMessages(prev => [...prev, {
      id: msgId++, type: 'player',
      name: typeof window !== 'undefined' ? localStorage.getItem('vantaris_player_name') || 'You' : 'You',
      text, timestamp: Date.now(),
    }])

    setTyping(true)
    const gs = {
      player_cards: mainHand.cards.map(c => ({ value: c.rank, suit: c.suit })),
      dealer_upcard: dealerHand.cards[0]?.rank,
      player_total: mainHand.value,
      dealer_total: phase === 'settled' ? dealerHand.value : undefined,
      phase,
      last_result: outcome,
    }

    // PRO COACHING -- server-metered AI tutor (Gold-funded). Free static path below.
    if (PRO_COACHING_ENABLED && proMode) {
      if (!playerId) { setTyping(false); sysMsg('Sign in to unlock Pro Coaching -- your live AI strategy tutor.'); return }
      const r = await getPremiumResponse(playerId, text, gs)
      setTyping(false)
      if (r.reply) {
        if (typeof r.goldBalance === 'number') useBlackjackStore.setState(s => ({ player: { ...s.player, chips: r.goldBalance! } }))
        setPassActive(!!r.passActive)
        setMessages(prev => [...prev, {
          id: msgId++, type: 'dealer', name: activeDealer.name,
          text: r.reply + (r.chargedGold ? `\n\n**-${r.chargedGold} Gold**` : ''), timestamp: Date.now(),
        }])
      } else if (r.error === 'insufficient_gold') {
        sysMsg(`You're low on Gold for live coaching. Add Gold, or unlock the Coaching Pass (${COACHING_PASS_GC} Gold) for a full day of unlimited AI coaching.`)
      } else if (r.error === 'sign_in_required') {
        sysMsg('Sign in to use Pro Coaching.')
      } else {
        const hint = await getDealerResponse(text, gs)  // graceful fallback to the free hint
        setMessages(prev => [...prev, { id: msgId++, type: 'dealer', name: activeDealer.name, text: hint, timestamp: Date.now() }])
      }
      return
    }

    const reply = await getDealerResponse(text, gs)
    setTyping(false)
    setMessages(prev => [...prev, {
      id: msgId++, type: 'dealer', name: activeDealer.name,
      text: reply, timestamp: Date.now(),
    }])

    // Random bot might respond to player chat (30% chance)
    const allBots = useBlackjackStore.getState().bots.filter(b => !b.sittingOut)
    if (allBots.length > 0 && Math.random() < 0.3) {
      const bot = allBots[Math.floor(Math.random() * allBots.length)]
      const botResponses = [
        'For real!', 'I agree', 'Haha', 'Good point', 'Same here',
        'True that', 'Yep', 'No doubt', 'Facts', 'Right?',
        'lol', 'I feel that', '100%', 'Big mood', 'Say less',
      ]
      setTimeout(() => {
        setMessages(prev => [...prev, {
          id: msgId++, type: 'player' as const, name: bot.name,
          text: botResponses[Math.floor(Math.random() * botResponses.length)],
          timestamp: Date.now(),
        }])
      }, 1000 + Math.random() * 2000)
    }
  }

  const handleBuyPass = async () => {
    if (!playerId) { sysMsg('Sign in to unlock the Coaching Pass.'); return }
    sysMsg('Unlocking your Coaching Pass...')
    const r = await buyCoachingPass(playerId)
    if (r.ok) {
      setPassActive(true)
      if (typeof r.goldBalance === 'number') useBlackjackStore.setState(s => ({ player: { ...s.player, chips: r.goldBalance! } }))
      sysMsg('Coaching Pass active -- unlimited AI coaching for the next 24 hours. Ask me anything.')
    } else if (r.error === 'insufficient_gold') {
      sysMsg(`Not enough Gold for the Coaching Pass (need ${COACHING_PASS_GC}). Add Gold and try again.`)
    } else {
      sysMsg('Could not unlock the pass right now. Try again in a moment.')
    }
  }

  return (
    <>
      {/* Chat toggle */}
      <motion.button
        data-chat-toggle="true"
        onClick={() => setIsOpen(!isOpen)}
        className="absolute bottom-[100px] right-2 md:right-4 z-20 w-10 h-10 rounded-full flex items-center justify-center glass"
        style={{
          border: isOpen ? '1px solid rgba(201,168,76,0.4)' : '1px solid rgba(255,255,255,0.1)',
          boxShadow: isOpen ? '0 0 12px rgba(201,168,76,0.2)' : 'none',
        }}
        whileTap={{ scale: 0.9 }}
      >
        {'\uD83D\uDCAC'}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
            className="absolute bottom-[150px] right-2 md:right-4 z-20 w-[280px] md:w-[320px] rounded-xl overflow-hidden flex flex-col"
            style={{ background: 'rgba(0,0,0,0.92)', border: '1px solid rgba(201,168,76,0.2)', maxHeight: '360px' }}
          >
            <div className="px-3 py-2 flex items-center gap-2" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
              <span className="text-xs">{'\uD83C\uDCCF'}</span>
              <span className="text-xs font-semibold" style={{ color: '#c9a84c', fontFamily: "'Cinzel', serif" }}>TABLE CHAT</span>
              {PRO_COACHING_ENABLED && (
                <button
                  onClick={() => setProMode(v => !v)}
                  className="ml-auto text-[9px] px-2 py-0.5 rounded-full font-bold"
                  style={{
                    color: proMode ? '#0a0a0a' : '#c9a84c',
                    background: proMode ? '#c9a84c' : 'rgba(201,168,76,0.12)',
                    border: '1px solid rgba(201,168,76,0.4)',
                  }}
                  title="Pro Coaching -- live AI strategy tutor, powered by Gold"
                >
                  {passActive ? '✦ PRO · PASS' : proMode ? '✦ PRO ON' : '✦ PRO'}
                </button>
              )}
              <span className={`text-[9px] ${PRO_COACHING_ENABLED ? '' : 'ml-auto'}`} style={{ color: 'rgba(255,255,255,0.4)' }}>{activeDealer.name}</span>
            </div>

            {/* Pro Coaching hint bar (premium mode, no active pass) */}
            {PRO_COACHING_ENABLED && proMode && !passActive && (
              <div className="px-3 py-1.5 flex items-center gap-2 text-[9px]"
                style={{ background: 'rgba(201,168,76,0.06)', borderBottom: '1px solid rgba(201,168,76,0.15)', color: 'rgba(255,255,255,0.55)' }}>
                <span>Live AI coaching &middot; Gold per question</span>
                <button onClick={handleBuyPass}
                  className="ml-auto px-2 py-0.5 rounded-full font-bold"
                  style={{ color: '#c9a84c', background: 'rgba(201,168,76,0.15)', border: '1px solid rgba(201,168,76,0.35)' }}>
                  Coaching Pass &middot; {COACHING_PASS_GC} Gold
                </button>
              </div>
            )}

            <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-2 space-y-2" style={{ maxHeight: '240px' }}>
              {messages.map(m => (
                <div key={m.id} className={`flex gap-2 items-start ${m.type === 'player' ? 'justify-end' : ''}`}>
                  {m.type !== 'player' && (
                    <span className="text-sm flex-shrink-0 mt-0.5">
                      {m.type === 'coach' ? '\uD83C\uDFC6' : '\uD83C\uDCCF'}
                    </span>
                  )}
                  <div className={`rounded-xl px-3 py-2 max-w-[85%] ${
                    m.type === 'player' ? 'bg-[#1a3a6b]'
                      : m.type === 'coach' ? 'bg-[#1a2a1a] border border-[#2a3a2a]'
                      : 'bg-[#1a1a1a] border border-[#2a2a2a]'
                  }`}>
                    <span className="text-[9px] font-bold block mb-0.5" style={{
                      color: m.type === 'player' ? '#58a6ff' : m.type === 'coach' ? '#27ae60' : '#c9a84c',
                    }}>{m.name}</span>
                    <p className="text-[11px] leading-relaxed" style={{ color: '#e5e5e5' }}>
                      {formatDealerText(m.text)}
                    </p>
                  </div>
                </div>
              ))}

              {typing && (
                <div className="flex gap-2 items-center">
                  <span className="text-sm">{'\uD83C\uDCCF'}</span>
                  <motion.div className="flex gap-1 px-3 py-2 rounded-xl bg-[#1a1a1a]"
                    animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 1.2, repeat: Infinity }}>
                    {[0,1,2].map(i => <div key={i} className="w-1.5 h-1.5 rounded-full bg-[#c9a84c]" />)}
                  </motion.div>
                </div>
              )}
            </div>

            <div className="px-2 py-2 flex gap-2" style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
              <input
                type="text" value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                placeholder={PRO_COACHING_ENABLED && proMode ? 'Ask your AI coach...' : 'Ask the dealer...'}
                className="flex-1 bg-transparent text-xs outline-none px-2 py-1.5 rounded-lg"
                style={{ border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }}
              />
              <button onClick={handleSend}
                className="px-3 py-1.5 rounded-lg text-xs font-bold"
                style={{ background: 'rgba(201,168,76,0.2)', color: '#c9a84c', border: '1px solid rgba(201,168,76,0.3)' }}>
                Send
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
