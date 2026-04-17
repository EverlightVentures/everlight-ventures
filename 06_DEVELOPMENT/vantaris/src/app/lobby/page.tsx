'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useBlackjackStore } from '@/lib/blackjack-store'

/**
 * Vantaris Casino Lobby
 *
 * The casino floor. Always-visible sidebar (Stake pattern).
 * Predictive game ordering (most played first).
 * Live feed of wins scrolling at bottom (social proof).
 * Jackpot ticker pulsing at top.
 *
 * Layout:
 * [Sidebar] [Main Content                        ]
 * [Nav    ] [Jackpot Banner                       ]
 * [Games  ] [Game Grid                            ]
 * [Wallet ] [Live Win Feed                        ]
 * [Social ] [                                     ]
 */

// Game data
const GAMES = [
  {
    id: 'blackjack',
    name: 'Blackjack',
    tagline: 'Classic 21. Beat the dealer.',
    color: '#c9a84c',
    gradient: 'linear-gradient(135deg, #c9a84c20, #0a0a1005)',
    icon: '\u2660', // spade
    hot: true,
    players: 1247,
  },
  {
    id: 'crash',
    name: 'Crash',
    tagline: 'How high do you dare?',
    color: '#00e676',
    gradient: 'linear-gradient(135deg, #00e67620, #0a0a1005)',
    icon: '\u2191', // up arrow
    hot: true,
    players: 3891,
  },
  {
    id: 'roulette',
    name: 'Roulette',
    tagline: 'Where fortune meets obsidian.',
    color: '#ff2d55',
    gradient: 'linear-gradient(135deg, #ff2d5520, #0a0a1005)',
    icon: '\u25CF', // circle
    hot: false,
    players: 892,
  },
  {
    id: 'dice',
    name: 'Dice',
    tagline: 'Roll the obsidian.',
    color: '#58a6ff',
    gradient: 'linear-gradient(135deg, #58a6ff20, #0a0a1005)',
    icon: '\u2684', // die
    hot: false,
    players: 654,
  },
  {
    id: 'plinko',
    name: 'Plinko',
    tagline: 'Watch it fall. Pray it lands.',
    color: '#ff6b35',
    gradient: 'linear-gradient(135deg, #ff6b3520, #0a0a1005)',
    icon: '\u25BD', // down triangle
    hot: false,
    players: 421,
  },
  {
    id: 'mines',
    name: 'Mines',
    tagline: 'Every tap could be your fortune.',
    color: '#00ff41',
    gradient: 'linear-gradient(135deg, #00ff4120, #0a0a1005)',
    icon: '\u2B23', // hexagon
    hot: true,
    players: 1832,
  },
]

// Simulated live win feed
const LIVE_WINS = [
  { player: 'ShadowKing', game: 'Crash', amount: 4250, multiplier: 12.4, currency: 'GC' },
  { player: 'NightOwl22', game: 'Mines', amount: 890, multiplier: 3.2, currency: 'SC' },
  { player: 'xVenus', game: 'Blackjack', amount: 15000, multiplier: 2.5, currency: 'GC' },
  { player: 'CryptoWolf', game: 'Roulette', amount: 7200, multiplier: 35, currency: 'BTC' },
  { player: 'LuckyAce', game: 'Dice', amount: 2100, multiplier: 4.8, currency: 'GC' },
  { player: 'Phantom_x', game: 'Crash', amount: 28000, multiplier: 87.3, currency: 'GC' },
]

// Tier badge component
function TierBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    Ember: '#ff6b35',
    Shadow: '#6a5acd',
    Eclipse: '#9966ff',
    Supernova: '#c9a84c',
    'Vanta Black': '#ffffff',
  }
  return (
    <span
      className="text-xs font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider"
      style={{
        color: colors[tier] || '#888',
        background: `${colors[tier] || '#888'}15`,
        border: `1px solid ${colors[tier] || '#888'}30`,
      }}
    >
      {tier}
    </span>
  )
}

// Sidebar component
function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const player = useBlackjackStore(s => s.player)
  const playerName = typeof window !== 'undefined' ? localStorage.getItem('vantaris_player_name') || 'Player' : 'Player'

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/60 z-30 md:hidden" onClick={onClose} />
      )}
      <aside
        className={`fixed left-0 top-0 bottom-0 w-64 flex flex-col z-40 border-r transition-transform duration-300 ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}
        style={{
          background: 'var(--vanta-abyss)',
          borderColor: 'var(--vanta-border)',
        }}
      >
      {/* Logo */}
      <div className="p-6 border-b" style={{ borderColor: 'var(--vanta-border)' }}>
        <h1
          className="font-display text-xl font-bold tracking-widest"
          style={{
            background: 'linear-gradient(135deg, #c9a84c, #e8c55a)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          VANTARIS
        </h1>
        <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
          The darkest star burns brightest.
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        {[
          { label: 'Casino', href: '/lobby', icon: '\u2605', active: true },
          { label: 'Wallet', href: '/wallet', icon: '\u2668' },
          { label: 'Rewards', href: '/rewards', icon: '\u2B50' },
          { label: 'Profile', href: '/profile', icon: '\u263A' },
          { label: 'Redeem SC', href: '/redeem', icon: '\u2714' },
          { label: 'Settings', href: '/settings', icon: '\u2699' },
          { label: 'Fairness', href: '/fairness', icon: '\u2696' },
          { label: 'Support', href: '/support', icon: '\u2753' },
          { label: 'Rules', href: '/rules', icon: '\u2706' },
        ].map((item) => (
          <Link key={item.label} href={item.href}>
            <div
              className="flex items-center gap-3 px-6 py-3 text-sm cursor-pointer transition-all duration-200"
              style={{
                color: item.active ? 'var(--gold)' : 'var(--text-secondary)',
                background: item.active ? 'var(--gold-glow)' : 'transparent',
                borderRight: item.active ? '2px solid var(--gold)' : 'none',
              }}
            >
              <span className="text-base">{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </div>
          </Link>
        ))}
      </nav>

      {/* Wallet Summary */}
      <div
        className="p-4 border-t cursor-pointer"
        style={{ borderColor: 'var(--vanta-border)' }}
        onClick={() => {}}
      >
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
            Wallet
          </span>
          <TierBadge tier="Shadow" />
        </div>
        <div className="font-mono text-lg font-bold" style={{ color: 'var(--gold)' }}>
          {player.chips.toLocaleString()} GC
        </div>
        <div className="font-mono text-sm" style={{ color: 'var(--win)' }}>
          {player.sweepsCoins.toFixed(2)} SC
        </div>
        <div className="font-mono text-xs" style={{ color: '#58a6ff' }}>
          {player.gems} Gems
        </div>
      </div>

      {/* Profile */}
      <div className="p-4 border-t flex items-center gap-3" style={{ borderColor: 'var(--vanta-border)' }}>
        <div
          className="w-8 h-8 rounded-full"
          style={{ background: 'linear-gradient(135deg, #6a5acd, #c9a84c)' }}
        />
        <div>
          <div className="text-sm font-medium">{playerName}</div>
          <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            {player.rank} &middot; {player.xp.toLocaleString()} XP
          </div>
        </div>
      </div>
    </aside>
    </>
  )
}

// Live win ticker at bottom
function LiveWinTicker() {
  return (
    <div
      className="fixed bottom-0 left-0 md:left-64 right-0 h-10 flex items-center overflow-hidden z-10 border-t"
      style={{
        background: 'var(--vanta-abyss)',
        borderColor: 'var(--vanta-border)',
      }}
    >
      <motion.div
        className="flex gap-8 whitespace-nowrap"
        animate={{ x: [0, -1500] }}
        transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
      >
        {[...LIVE_WINS, ...LIVE_WINS, ...LIVE_WINS].map((win, i) => (
          <span key={i} className="text-xs flex items-center gap-2">
            <span style={{ color: 'var(--text-secondary)' }}>{win.player}</span>
            <span style={{ color: 'var(--text-tertiary)' }}>won</span>
            <span className="font-mono font-semibold" style={{ color: 'var(--win)' }}>
              {win.amount.toLocaleString()} {win.currency}
            </span>
            <span style={{ color: 'var(--text-tertiary)' }}>on {win.game}</span>
            <span className="font-mono" style={{ color: 'var(--gold)' }}>
              {win.multiplier}x
            </span>
          </span>
        ))}
      </motion.div>
    </div>
  )
}

// Jackpot banner
function JackpotBanner() {
  return (
    <motion.div
      className="glass-elevated p-6 rounded-2xl mb-8 text-center relative overflow-hidden"
      animate={{
        boxShadow: [
          '0 0 20px rgba(201, 168, 76, 0.1)',
          '0 0 40px rgba(201, 168, 76, 0.2)',
          '0 0 20px rgba(201, 168, 76, 0.1)',
        ],
      }}
      transition={{ duration: 3, repeat: Infinity }}
    >
      <p className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-tertiary)' }}>
        Vantaris Jackpot
      </p>
      <p
        className="font-mono text-4xl md:text-5xl font-bold"
        style={{
          background: 'linear-gradient(135deg, #c9a84c, #e8c55a, #c9a84c)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}
      >
        127,450 GC
      </p>
      <p className="text-xs mt-2" style={{ color: 'var(--text-tertiary)' }}>
        Grows with every bet. Could hit any moment.
      </p>
    </motion.div>
  )
}

// Game card in the lobby grid
function LobbyGameCard({ game }: { game: typeof GAMES[0] }) {
  return (
    <Link href={`/play/${game.id}`}>
      <motion.div
        className="relative rounded-2xl overflow-hidden cursor-pointer group"
        style={{
          background: game.gradient,
          border: `1px solid ${game.color}15`,
        }}
        whileHover={{
          scale: 1.02,
          borderColor: `${game.color}40`,
          boxShadow: `0 0 30px ${game.color}15`,
        }}
        transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="p-6 md:p-8">
          {/* Hot badge */}
          {game.hot && (
            <div
              className="absolute top-4 right-4 text-xs font-semibold px-2 py-1 rounded-full"
              style={{ background: '#ff2d5520', color: '#ff2d55', border: '1px solid #ff2d5530' }}
            >
              HOT
            </div>
          )}

          {/* Icon */}
          <div
            className="text-4xl mb-4 opacity-60 group-hover:opacity-100 transition-opacity"
            style={{ color: game.color }}
          >
            {game.icon}
          </div>

          {/* Name */}
          <h3 className="font-display text-xl md:text-2xl font-bold mb-1">
            {game.name}
          </h3>

          {/* Tagline */}
          <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
            {game.tagline}
          </p>

          {/* Live players */}
          <div className="flex items-center gap-2">
            <div
              className="w-2 h-2 rounded-full animate-pulse"
              style={{ background: game.color }}
            />
            <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
              {game.players.toLocaleString()} playing
            </span>
          </div>
        </div>
      </motion.div>
    </Link>
  )
}

export default function LobbyPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>
      {/* Mobile hamburger */}
      <button onClick={() => setSidebarOpen(true)}
        className="fixed top-4 left-4 z-50 md:hidden w-10 h-10 rounded-lg flex items-center justify-center"
        style={{ background: 'var(--vanta-surface)', border: '1px solid var(--vanta-border)' }}>
        <span className="text-lg">{'\u2630'}</span>
      </button>

      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <LiveWinTicker />

      {/* Main content area (offset by sidebar) */}
      <main className="ml-0 md:ml-64 pb-16 px-4 md:px-8 pt-16 md:pt-8">
        {/* Jackpot */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <JackpotBanner />
        </motion.div>

        {/* Game Grid */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-display text-2xl font-bold">Games</h2>
            <div className="flex gap-2">
              {['All', 'Table', 'Instant', 'PvP'].map((filter) => (
                <button
                  key={filter}
                  className="text-xs px-3 py-1.5 rounded-full transition-all"
                  style={{
                    background: filter === 'All' ? 'var(--gold-glow)' : 'transparent',
                    color: filter === 'All' ? 'var(--gold)' : 'var(--text-tertiary)',
                    border: `1px solid ${filter === 'All' ? 'var(--gold)' : 'var(--vanta-border)'}`,
                  }}
                >
                  {filter}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {GAMES.map((game, i) => (
              <motion.div
                key={game.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * i, duration: 0.5 }}
              >
                <LobbyGameCard game={game} />
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Provably Fair Banner */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mt-12 glass p-8 rounded-2xl text-center"
        >
          <p className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-tertiary)' }}>
            Every game. Every outcome.
          </p>
          <p className="font-display text-xl md:text-2xl">
            <span style={{ color: 'var(--gold)' }}>Provably fair.</span>{' '}
            Verify any hand yourself.
          </p>
          <Link href="/fairness">
            <button className="btn-ghost mt-4 text-xs">
              Learn how it works
            </button>
          </Link>
        </motion.div>
      </main>
    </div>
  )
}
