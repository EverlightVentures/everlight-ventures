'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import Link from 'next/link'

/**
 * Vantaris Table Lobby
 *
 * Browse and join blackjack tables. Multiple variants,
 * stake levels, dealers, and themes.
 *
 * This is the first thing a player sees when they click
 * "Blackjack" in the casino lobby. Pick your table, pick
 * your seat, play.
 */

const TABLES = [
  {
    id: 'classic-1',
    name: 'The Floor',
    variant: 'Classic',
    variantColor: '#27ae60',
    dealer: { name: 'Aria Sinclair', title: 'House Dealer', initial: 'A', color: '#c9a84c' },
    minBet: 10,
    maxBet: 5000,
    players: 4,
    maxPlayers: 7,
    felt: '#0d5c2e',
    hot: false,
    vip: false,
    description: 'Standard blackjack. 6-deck shoe. 3:2 payouts.',
  },
  {
    id: 'classic-2',
    name: 'The Parlor',
    variant: 'Classic',
    variantColor: '#27ae60',
    dealer: { name: 'Aria Sinclair', title: 'House Dealer', initial: 'A', color: '#c9a84c' },
    minBet: 25,
    maxBet: 10000,
    players: 6,
    maxPlayers: 7,
    felt: '#0d5c2e',
    hot: true,
    vip: false,
    description: 'Mid-stakes classic. Side bets available.',
  },
  {
    id: 'lightning-1',
    name: 'Lightning Lounge',
    variant: 'Lightning',
    variantColor: '#f1c40f',
    dealer: { name: 'Marcus Vega', title: 'High Roller', initial: 'M', color: '#ff6b35' },
    minBet: 50,
    maxBet: 25000,
    players: 5,
    maxPlayers: 7,
    felt: '#1a0a2e',
    hot: true,
    vip: false,
    description: 'Random 2x-25x multipliers each round. 100% lightning fee.',
  },
  {
    id: 'speed-1',
    name: 'Velocity',
    variant: 'Speed',
    variantColor: '#e74c3c',
    dealer: { name: 'Kanisha Thompson', title: 'VIP Lounge', initial: 'K', color: '#e91e63' },
    minBet: 25,
    maxBet: 10000,
    players: 3,
    maxPlayers: 7,
    felt: '#0a1520',
    hot: false,
    vip: false,
    description: 'Fastest decision acts first. 30% faster rounds.',
  },
  {
    id: 'switch-1',
    name: 'The Switch',
    variant: 'Switch',
    variantColor: '#9b59b6',
    dealer: { name: 'Aria Sinclair', title: 'House Dealer', initial: 'A', color: '#c9a84c' },
    minBet: 100,
    maxBet: 25000,
    players: 2,
    maxPlayers: 7,
    felt: '#150a20',
    hot: false,
    vip: false,
    description: 'Two hands. Swap top cards between them. BJ pays even money.',
  },
  {
    id: 'highroller-1',
    name: 'Vanta Black',
    variant: 'High Roller',
    variantColor: '#c9a84c',
    dealer: { name: 'Bacardi Ice', title: 'VIP Elite', initial: 'B', color: '#00bcd4' },
    minBet: 500,
    maxBet: 50000,
    players: 2,
    maxPlayers: 5,
    felt: '#050507',
    hot: false,
    vip: true,
    description: 'Diamond+ only. Lightning + side bets. The inner circle.',
  },
  {
    id: 'tournament-1',
    name: 'Weekly Championship',
    variant: 'Tournament',
    variantColor: '#e67e22',
    dealer: { name: 'Bacardi Ice', title: 'VIP Elite', initial: 'B', color: '#00bcd4' },
    minBet: 0,
    maxBet: 0,
    players: 0,
    maxPlayers: 64,
    felt: '#0a0a10',
    hot: false,
    vip: false,
    description: 'Buy-in: 1,000 GC. Elimination rounds. Top 3 win prizes.',
    tournament: { buyIn: 1000, status: 'registering', startsIn: '2h 14m' },
  },
]

const VARIANT_FILTERS = ['All', 'Classic', 'Lightning', 'Speed', 'Switch', 'High Roller', 'Tournament']

function TableCard({ table }: { table: typeof TABLES[0] }) {
  const isTournament = table.variant === 'Tournament'

  return (
    <Link href={isTournament ? '#' : `/play/blackjack?table=${table.id}`}>
      <motion.div
        className="rounded-2xl overflow-hidden cursor-pointer relative"
        style={{
          background: 'var(--vanta-abyss)',
          border: `1px solid ${table.vip ? 'rgba(201,168,76,0.3)' : 'var(--vanta-border)'}`,
        }}
        whileHover={{
          borderColor: table.dealer.color + '60',
          boxShadow: `0 0 20px ${table.dealer.color}15`,
          y: -3,
        }}
        transition={{ duration: 0.25 }}
      >
        {/* Felt preview strip */}
        <div className="h-2" style={{ background: table.felt }} />

        {/* Badges */}
        <div className="absolute top-4 right-4 flex gap-1.5">
          {table.hot && (
            <span className="text-[9px] font-bold px-2 py-0.5 rounded-full" style={{ background: '#ff2d5520', color: '#ff2d55' }}>
              HOT
            </span>
          )}
          {table.vip && (
            <span className="text-[9px] font-bold px-2 py-0.5 rounded-full" style={{ background: 'rgba(201,168,76,0.15)', color: 'var(--gold)' }}>
              VIP
            </span>
          )}
          <span className="text-[9px] font-semibold px-2 py-0.5 rounded-full" style={{ background: table.variantColor + '15', color: table.variantColor }}>
            {table.variant}
          </span>
        </div>

        <div className="p-5">
          {/* Dealer */}
          <div className="flex items-center gap-3 mb-3">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold"
              style={{ background: table.dealer.color + '25', color: table.dealer.color, border: `1px solid ${table.dealer.color}40` }}
            >
              {table.dealer.initial}
            </div>
            <div>
              <p className="text-sm font-semibold">{table.name}</p>
              <p className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                {table.dealer.name} -- {table.dealer.title}
              </p>
            </div>
          </div>

          {/* Description */}
          <p className="text-xs mb-3 line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
            {table.description}
          </p>

          {/* Stakes + players */}
          <div className="flex items-center justify-between">
            {isTournament ? (
              <>
                <div>
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Buy-in</p>
                  <p className="font-mono text-sm font-bold" style={{ color: 'var(--gold)' }}>
                    {table.tournament?.buyIn.toLocaleString()} GC
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Starts in</p>
                  <p className="text-sm font-semibold" style={{ color: 'var(--warning, #ff6b35)' }}>
                    {table.tournament?.startsIn}
                  </p>
                </div>
              </>
            ) : (
              <>
                <div>
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Stakes</p>
                  <p className="font-mono text-sm font-bold">
                    {table.minBet.toLocaleString()} - {table.maxBet.toLocaleString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Players</p>
                  <div className="flex items-center gap-1.5">
                    <div className="flex -space-x-1">
                      {Array.from({ length: Math.min(table.players, 4) }).map((_, i) => (
                        <div
                          key={i}
                          className="w-4 h-4 rounded-full border border-black"
                          style={{ background: ['#27ae60', '#e74c3c', '#9b59b6', '#e67e22'][i] + '80' }}
                        />
                      ))}
                    </div>
                    <span className="text-xs font-mono" style={{ color: table.players >= table.maxPlayers - 1 ? 'var(--loss)' : 'var(--text-secondary)' }}>
                      {table.players}/{table.maxPlayers}
                    </span>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Seat indicator dots */}
          {!isTournament && (
            <div className="flex gap-1 mt-3 justify-center">
              {Array.from({ length: table.maxPlayers }).map((_, i) => (
                <div
                  key={i}
                  className="w-2 h-2 rounded-full"
                  style={{
                    background: i < table.players ? table.dealer.color : 'var(--vanta-border)',
                    boxShadow: i < table.players ? `0 0 4px ${table.dealer.color}40` : 'none',
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Action button */}
        <div className="px-5 pb-4">
          <motion.button
            className="w-full py-2 rounded-xl text-xs font-bold tracking-widest"
            style={{
              background: table.vip
                ? 'linear-gradient(135deg, #c9a84c, #e8c55a)'
                : isTournament
                  ? table.variantColor + '20'
                  : 'rgba(255,255,255,0.05)',
              color: table.vip ? '#000' : isTournament ? table.variantColor : 'var(--text-primary)',
              border: table.vip ? 'none' : `1px solid ${table.vip ? 'transparent' : 'var(--vanta-border)'}`,
            }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {table.vip ? 'ENTER VIP' : isTournament ? 'REGISTER' : table.players >= table.maxPlayers ? 'FULL' : 'JOIN TABLE'}
          </motion.button>
        </div>
      </motion.div>
    </Link>
  )
}

export default function TableLobbyPage() {
  const [filter, setFilter] = useState('All')

  const filtered = filter === 'All' ? TABLES : TABLES.filter(t => t.variant === filter)

  return (
    <div className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>
      {/* Header */}
      <div className="px-6 md:px-12 pt-8 pb-4">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
              Blackjack Tables
            </h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-tertiary)' }}>
              Choose your table. Choose your destiny.
            </p>
          </div>
          <Link href="/lobby">
            <button className="btn-ghost text-xs px-4 py-2">BACK TO LOBBY</button>
          </Link>
        </div>

        {/* Filters */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {VARIANT_FILTERS.map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className="text-xs px-4 py-2 rounded-full whitespace-nowrap transition-all"
              style={{
                background: filter === f ? 'var(--gold-glow)' : 'transparent',
                color: filter === f ? 'var(--gold)' : 'var(--text-tertiary)',
                border: `1px solid ${filter === f ? 'var(--gold)' : 'var(--vanta-border)'}`,
              }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Quick Join */}
      <div className="px-6 md:px-12 mb-6">
        <motion.div
          className="glass-elevated p-4 rounded-xl flex items-center justify-between"
          whileHover={{ borderColor: 'rgba(201,168,76,0.3)' }}
        >
          <div>
            <p className="text-sm font-semibold">Quick Join</p>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
              Jump into the next available seat at a Classic table.
            </p>
          </div>
          <Link href="/play/blackjack?table=classic-1&quickjoin=true">
            <motion.button
              className="btn-primary px-8 py-2 text-xs tracking-widest"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              PLAY NOW
            </motion.button>
          </Link>
        </motion.div>
      </div>

      {/* Table grid */}
      <div className="px-6 md:px-12 pb-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((table, i) => (
            <motion.div
              key={table.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
            >
              <TableCard table={table} />
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}
