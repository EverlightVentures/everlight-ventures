'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useBlackjackStore } from '@/lib/blackjack-store'

/**
 * DealerChat -- AI Strategy Coach
 *
 * Chat panel where player talks to the dealer.
 * Dealer sees cards and teaches basic strategy via blackjack-api.
 * Auto-coaches after each hand.
 */

const API_URL = 'https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api'
const API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww'

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
  const scrollRef = useRef<HTMLDivElement>(null)
  const phase = useBlackjackStore(s => s.phase)
  const outcome = useBlackjackStore(s => s.outcome)
  const mainHand = useBlackjackStore(s => s.mainHand)
  const dealerHand = useBlackjackStore(s => s.dealerHand)
  const activeDealer = useBlackjackStore(s => s.activeDealer)

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

  // Auto-coach after each hand
  useEffect(() => {
    if (!outcome || !isOpen) return
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
    const reply = await getDealerResponse(text, gs)
    setTyping(false)
    setMessages(prev => [...prev, {
      id: msgId++, type: 'dealer', name: activeDealer.name,
      text: reply, timestamp: Date.now(),
    }])
  }

  return (
    <>
      {/* Chat toggle */}
      <motion.button
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
              <span className="text-xs font-semibold" style={{ color: '#c9a84c', fontFamily: "'Cinzel', serif" }}>DEALER CHAT</span>
              <span className="text-[9px] ml-auto" style={{ color: 'rgba(255,255,255,0.4)' }}>{activeDealer.name}</span>
            </div>

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
                placeholder="Ask the dealer..."
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
