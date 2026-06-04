'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useBlackjackStore } from '@/lib/blackjack-store'
import { CasinoLoader } from '@/components/shared/CasinoLoader'

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.1 } } }

const TABLES = [
  {
    id: 'classic',
    name: 'Classic Table',
    desc: 'Standard rules. Dealer hits soft 17. 8-deck shoe. Perfect for getting started.',
    minBet: 100,
    maxBet: 10000,
    color: '#27ae60',
    feltColor: '#0d5c2e',
    features: ['3:2 Blackjack', 'Soft 17 Hit', 'Split Pairs', 'Double Any Card'],
    hot: false,
  },
  {
    id: 'vip',
    name: 'VIP Lounge',
    desc: 'High stakes. Higher rewards. Side bets enabled. Lucky Lucky, Bad Buster, Progressive.',
    minBet: 1000,
    maxBet: 100000,
    color: '#D4AF37',
    feltColor: '#0a0a0a',
    features: ['All Side Bets', 'Progressive Jackpot', 'Double Any Card', 'VIP Dealers'],
    hot: true,
  },
  {
    id: 'lightning',
    name: 'Lightning',
    desc: 'Fast rounds. Auto-deal. Multiplied payouts on random hands. For players who move fast.',
    minBet: 500,
    maxBet: 50000,
    color: '#58a6ff',
    feltColor: '#0d1a5c',
    features: ['Random Multipliers', 'Fast Deal', 'Auto Stand on 17+', 'Lightning Payouts'],
    hot: true,
  },
  {
    id: 'midnight',
    name: 'Midnight Table',
    desc: 'Dark felt. Minimal UI. Just you and the cards. For players who want zero distractions.',
    minBet: 100,
    maxBet: 25000,
    color: '#9b59b6',
    feltColor: '#0d1a5c',
    features: ['Minimal UI', 'No Side Bets', 'Clean Layout', 'Focus Mode'],
    hot: false,
  },
  {
    id: 'high_roller',
    name: 'High Roller Suite',
    desc: 'Minimum bet: 5,000. Maximum: 500,000. This table is not for tourists.',
    minBet: 5000,
    maxBet: 500000,
    color: '#e74c3c',
    feltColor: '#5c0d0d',
    features: ['500K Max Bet', 'All Side Bets', 'Progressive Jackpot', 'Exclusive Dealers'],
    hot: false,
  },
]

const DEALERS = [
  { id: 'aria', name: 'Aria Sinclair', title: 'House Dealer', voiceId: 'EXAVITQu4vr4xnSDxMaL', color: '#c9a84c', desc: 'Warm. Professional. The default.' },
  { id: 'marcus', name: 'Marcus Vega', title: 'High Roller', voiceId: 'onwK4e9ZLuTAKqWW03F9', color: '#ff6b35', desc: 'Smooth talker. Loves the action.' },
  { id: 'kanisha', name: 'Kanisha Thompson', title: 'VIP Lounge', voiceId: 'XrExE9yKIg1WjnnlVkGX', color: '#e91e63', desc: 'Sharp. No nonsense. Respects the game.' },
  { id: 'bacardi', name: 'Bacardi Ice', title: 'VIP Elite', voiceId: 'DwwuoY7Uz8AP8zrY5TAo', color: '#00bcd4', desc: 'Cold. Calculated. The final boss.' },
]

export default function BlackjackTablesPage() {
  const router = useRouter()
  const { setDealer } = useBlackjackStore()
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [selectedDealer, setSelectedDealer] = useState<string>('aria')
  const [launching, setLaunching] = useState(false)

  const handleLaunch = useCallback(() => {
    const dealer = DEALERS.find(d => d.id === selectedDealer)
    if (dealer) setDealer(dealer as any)

    const table = TABLES.find(t => t.id === selectedTable)
    if (table) {
      useBlackjackStore.setState({
        config: {
          ...useBlackjackStore.getState().config,
          minBet: table.minBet,
          maxBet: table.maxBet,
          // Carry the lobby table identity into the play screen. THE B-CARDD BET only
          // fires when tableType === 'vip' (the existing VIP Lounge / Spanish 21 table).
          tableType: table.id,
        },
      })
      if (table.feltColor) {
        useBlackjackStore.setState({
          player: {
            ...useBlackjackStore.getState().player,
            equippedFelt: table.id === 'vip' ? 'felt_legend' : table.id === 'midnight' ? 'felt_midnight' : table.id === 'high_roller' ? 'felt_crimson' : 'felt_default',
          },
        })
      }
    }

    setLaunching(true)
  }, [selectedTable, selectedDealer, setDealer])

  const onLoaderComplete = useCallback(() => {
    router.push('/play/blackjack')
  }, [router])

  return (
    <main className="min-h-screen relative" style={{ background: 'linear-gradient(180deg, #08080c 0%, #0c0c12 50%, #0a0a10 100%)' }}>

      {/* Casino entry animation */}
      {launching && <CasinoLoader onComplete={onLoaderComplete} />}

      {/* Casino lobby video background */}
      <video autoPlay muted loop playsInline className="fixed inset-0 w-full h-full object-cover pointer-events-none" style={{ opacity: 0.08, zIndex: 0 }}>
        <source src="/videos/casino-lobby.mp4" type="video/mp4" />
      </video>

      <div className="relative z-10 max-w-6xl mx-auto px-6 py-16">

        {/* Header */}
        <motion.div initial="hidden" animate="visible" variants={stagger} className="mb-16">
          <motion.a variants={fadeUp} href="/vantaris" className="text-[11px] tracking-[0.2em] mb-6 inline-block" style={{ color: '#555' }}>
            &larr; Back to Lobby
          </motion.a>
          <motion.h1 variants={fadeUp} className="text-4xl md:text-6xl font-bold"
            style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            Blackjack
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-3 text-[15px]" style={{ color: '#777' }}>
            Pick your table. Pick your dealer. The cards are waiting.
          </motion.p>
        </motion.div>

        {/* Table Selection */}
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-6" style={{ color: '#D4AF37' }}>
            Choose Your Table
          </motion.p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-16">
            {TABLES.map(t => (
              <motion.div key={t.id} variants={fadeUp}
                onClick={() => setSelectedTable(t.id)}
                className="group relative rounded-2xl overflow-hidden cursor-pointer"
                style={{
                  background: 'linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015))',
                  backdropFilter: 'blur(40px)',
                  border: selectedTable === t.id ? `2px solid ${t.color}` : '1px solid rgba(255,255,255,0.06)',
                  boxShadow: selectedTable === t.id ? `0 0 30px ${t.color}15` : 'inset 0 1px 0 rgba(255,255,255,0.06)',
                }}>

                {/* Top glow */}
                <div className="h-1 w-full" style={{ background: `linear-gradient(90deg, transparent, ${t.color}, transparent)`, opacity: selectedTable === t.id ? 0.6 : 0.15 }} />

                {t.hot && (
                  <span className="absolute top-4 right-4 text-[9px] font-bold px-2 py-0.5 rounded-full animate-pulse"
                    style={{ background: '#ff2d5520', color: '#ff2d55' }}>HOT</span>
                )}

                <div className="p-7">
                  <h3 className="text-lg font-bold mb-2" style={{ color: selectedTable === t.id ? t.color : '#eee' }}>{t.name}</h3>
                  <p className="text-[13px] leading-[1.7] mb-4" style={{ color: '#888' }}>{t.desc}</p>

                  {/* Features */}
                  <div className="flex flex-wrap gap-1 mb-4">
                    {t.features.map(f => (
                      <span key={f} className="text-[9px] px-2 py-0.5 rounded-full"
                        style={{ background: `${t.color}10`, color: t.color, border: `1px solid ${t.color}20` }}>{f}</span>
                    ))}
                  </div>

                  {/* Bet range */}
                  <div className="flex justify-between items-center pt-3" style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                    <span className="text-[10px] uppercase tracking-wider" style={{ color: '#555' }}>Min: {t.minBet.toLocaleString()} GC</span>
                    <span className="text-[10px] uppercase tracking-wider" style={{ color: '#555' }}>Max: {t.maxBet.toLocaleString()} GC</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Dealer Selection -- only shows after table is picked */}
        <AnimatePresence>
          {selectedTable && (
            <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 30 }}>
              <p className="text-[10px] uppercase tracking-[0.4em] font-medium mb-6" style={{ color: '#D4AF37' }}>
                Choose Your Dealer
              </p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-16">
                {DEALERS.map(d => (
                  <motion.div key={d.id}
                    onClick={() => setSelectedDealer(d.id)}
                    className="rounded-2xl overflow-hidden cursor-pointer text-center p-6"
                    style={{
                      background: 'linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015))',
                      border: selectedDealer === d.id ? `2px solid ${d.color}` : '1px solid rgba(255,255,255,0.06)',
                      boxShadow: selectedDealer === d.id ? `0 0 20px ${d.color}15` : 'none',
                    }}
                    whileHover={{ y: -2 }}
                    transition={{ duration: 0.3 }}>

                    {/* Dealer avatar placeholder */}
                    <div className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center text-2xl"
                      style={{ background: `${d.color}15`, border: `1px solid ${d.color}30` }}>
                      {d.id === 'bacardi' ? '\u2744' : d.id === 'aria' ? '\u2666' : d.id === 'marcus' ? '\u2660' : '\u2665'}
                    </div>

                    <h4 className="text-sm font-bold mb-1" style={{ color: selectedDealer === d.id ? d.color : '#eee' }}>{d.name}</h4>
                    <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: '#555' }}>{d.title}</p>
                    <p className="text-[11px]" style={{ color: '#777' }}>{d.desc}</p>
                  </motion.div>
                ))}
              </div>

              {/* Launch button */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center">
                <motion.button
                  onClick={handleLaunch}
                  className="px-12 py-4 rounded-full text-sm font-bold tracking-[0.25em] uppercase"
                  style={{ background: 'linear-gradient(135deg, #D4AF37, #E8D48B)', color: '#0A0A0A' }}
                  whileHover={{ scale: 1.03, boxShadow: '0 0 40px rgba(212,175,55,0.3)' }}
                  whileTap={{ scale: 0.97 }}>
                  Take Your Seat
                </motion.button>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  )
}
