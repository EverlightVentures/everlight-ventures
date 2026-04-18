'use client'

import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import Link from 'next/link'

/**
 * Vantaris Table Lobby -- LIVE
 *
 * Fetches real table data from Supabase via the blackjack-dealer
 * edge function. Shows live player counts, real table IDs, and
 * links to the multiplayer game page.
 */

const DEALER_URL = 'https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-dealer'

interface LiveTable {
  id: string
  name: string
  variant: string
  min_bet: number
  max_bet: number
  max_seats: number
  status: string
  phase: string
  felt_color: string
  dealer_name: string
  dealer_avatar: string
  players_count: number
}

const VARIANT_COLORS: Record<string, string> = {
  classic: '#27ae60',
  lightning: '#f1c40f',
  speed: '#e74c3c',
  switch: '#9b59b6',
  highroller: '#c9a84c',
}

const DEALER_COLORS: Record<string, string> = {
  aria: '#c9a84c',
  marcus: '#ff6b35',
  kanisha: '#e91e63',
  bacardi: '#00bcd4',
}

const VARIANT_LABELS: Record<string, string> = {
  classic: 'Classic',
  lightning: 'Lightning',
  speed: 'Speed',
  switch: 'Switch',
  highroller: 'High Roller',
}

const DESCRIPTIONS: Record<string, string> = {
  classic: 'Standard blackjack. 6-deck shoe. 3:2 payouts.',
  lightning: 'Random 2x-25x multipliers each round. 100% lightning fee.',
  speed: 'Fastest decision acts first. 30% faster rounds.',
  switch: 'Two hands. Swap top cards between them. BJ pays even money.',
  highroller: 'VIP only. Lightning + side bets. The inner circle.',
}

const VARIANT_FILTERS = ['All', 'Classic', 'Lightning', 'Speed', 'Switch', 'High Roller']

function TableCard({ table }: { table: LiveTable }) {
  const variantColor = VARIANT_COLORS[table.variant] || '#27ae60'
  const dealerColor = DEALER_COLORS[table.dealer_avatar] || '#c9a84c'
  const isVip = table.variant === 'highroller'
  const isFull = table.players_count >= table.max_seats
  const isHot = table.players_count >= Math.floor(table.max_seats * 0.6)

  return (
    <Link href={`/play/blackjack/multi?table=${table.id}`}>
      <motion.div
        className="rounded-2xl overflow-hidden cursor-pointer relative"
        style={{
          background: 'var(--vanta-abyss, #0a0a15)',
          border: `1px solid ${isVip ? 'rgba(201,168,76,0.3)' : 'rgba(255,255,255,0.06)'}`,
        }}
        whileHover={{
          borderColor: dealerColor + '60',
          boxShadow: `0 0 20px ${dealerColor}15`,
          y: -3,
        }}
        transition={{ duration: 0.25 }}
      >
        {/* Felt preview strip */}
        <div className="h-2" style={{ background: table.felt_color }} />

        {/* Badges */}
        <div className="absolute top-4 right-4 flex gap-1.5">
          {isHot && (
            <span className="text-[9px] font-bold px-2 py-0.5 rounded-full" style={{ background: '#ff2d5520', color: '#ff2d55' }}>
              HOT
            </span>
          )}
          {isVip && (
            <span className="text-[9px] font-bold px-2 py-0.5 rounded-full" style={{ background: 'rgba(201,168,76,0.15)', color: 'var(--gold, #c9a84c)' }}>
              VIP
            </span>
          )}
          {table.status === 'active' && (
            <span className="text-[9px] font-bold px-2 py-0.5 rounded-full" style={{ background: '#27ae6020', color: '#27ae60' }}>
              LIVE
            </span>
          )}
          <span className="text-[9px] font-semibold px-2 py-0.5 rounded-full" style={{ background: variantColor + '15', color: variantColor }}>
            {VARIANT_LABELS[table.variant] || table.variant}
          </span>
        </div>

        <div className="p-5">
          {/* Dealer */}
          <div className="flex items-center gap-3 mb-3">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold"
              style={{ background: dealerColor + '25', color: dealerColor, border: `1px solid ${dealerColor}40` }}
            >
              {table.dealer_name[0]}
            </div>
            <div>
              <p className="text-sm font-semibold">{table.name}</p>
              <p className="text-[10px]" style={{ color: 'var(--text-tertiary, rgba(255,255,255,0.4))' }}>
                {table.dealer_name}
              </p>
            </div>
          </div>

          {/* Description */}
          <p className="text-xs mb-3 line-clamp-2" style={{ color: 'var(--text-secondary, rgba(255,255,255,0.6))' }}>
            {DESCRIPTIONS[table.variant] || 'Multiplayer blackjack.'}
          </p>

          {/* Stakes + players */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary, rgba(255,255,255,0.4))' }}>Stakes</p>
              <p className="font-mono text-sm font-bold">
                {table.min_bet.toLocaleString()} - {table.max_bet.toLocaleString()}
              </p>
            </div>
            <div className="text-right">
              <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary, rgba(255,255,255,0.4))' }}>Players</p>
              <div className="flex items-center gap-1.5">
                <div className="flex -space-x-1">
                  {Array.from({ length: Math.min(table.players_count, 4) }).map((_, i) => (
                    <div
                      key={i}
                      className="w-4 h-4 rounded-full border border-black"
                      style={{ background: ['#27ae60', '#e74c3c', '#9b59b6', '#e67e22'][i] + '80' }}
                    />
                  ))}
                </div>
                <span className="text-xs font-mono" style={{
                  color: isFull ? 'var(--loss, #e74c3c)' : 'var(--text-secondary, rgba(255,255,255,0.6))',
                }}>
                  {table.players_count}/{table.max_seats}
                </span>
              </div>
            </div>
          </div>

          {/* Seat indicator dots */}
          <div className="flex gap-1 mt-3 justify-center">
            {Array.from({ length: table.max_seats }).map((_, i) => (
              <div
                key={i}
                className="w-2 h-2 rounded-full"
                style={{
                  background: i < table.players_count ? dealerColor : 'rgba(255,255,255,0.08)',
                  boxShadow: i < table.players_count ? `0 0 4px ${dealerColor}40` : 'none',
                }}
              />
            ))}
          </div>
        </div>

        {/* Action button */}
        <div className="px-5 pb-4">
          <motion.button
            className="w-full py-2 rounded-xl text-xs font-bold tracking-widest"
            style={{
              background: isVip
                ? 'linear-gradient(135deg, #c9a84c, #e8c55a)'
                : 'rgba(255,255,255,0.05)',
              color: isVip ? '#000' : 'var(--text-primary, #fff)',
              border: isVip ? 'none' : '1px solid rgba(255,255,255,0.08)',
            }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {isFull ? 'SPECTATE' : isVip ? 'ENTER VIP' : 'JOIN TABLE'}
          </motion.button>
        </div>
      </motion.div>
    </Link>
  )
}

export default function TableLobbyPage() {
  const [filter, setFilter] = useState('All')
  const [tables, setTables] = useState<LiveTable[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTables()
    // Refresh every 10 seconds
    const interval = setInterval(fetchTables, 10000)
    return () => clearInterval(interval)
  }, [])

  async function fetchTables() {
    try {
      const res = await fetch(DEALER_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'get-tables' }),
      })
      const data = await res.json()
      if (data.success && data.tables) {
        setTables(data.tables)
      }
    } catch (err) {
      console.warn('[lobby] Failed to fetch tables:', err)
    } finally {
      setLoading(false)
    }
  }

  const filtered = filter === 'All'
    ? tables
    : tables.filter((t) => (VARIANT_LABELS[t.variant] || t.variant) === filter)

  return (
    <div className="min-h-screen" style={{ background: 'var(--vanta-void, #050510)' }}>
      {/* Header */}
      <div className="px-6 md:px-12 pt-8 pb-4">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold, #c9a84c)' }}>
              Blackjack Tables
            </h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-tertiary, rgba(255,255,255,0.4))' }}>
              Choose your table. Choose your destiny.
              {tables.length > 0 && (
                <span className="ml-2 text-[10px] opacity-50">
                  ({tables.reduce((sum, t) => sum + t.players_count, 0)} players online)
                </span>
              )}
            </p>
          </div>
          <Link href="/lobby">
            <button className="text-xs px-4 py-2 rounded-lg" style={{
              border: '1px solid rgba(255,255,255,0.08)',
              color: 'rgba(255,255,255,0.5)',
            }}>
              BACK TO LOBBY
            </button>
          </Link>
        </div>

        {/* Filters */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {VARIANT_FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className="text-xs px-4 py-2 rounded-full whitespace-nowrap transition-all"
              style={{
                background: filter === f ? 'rgba(201,168,76,0.1)' : 'transparent',
                color: filter === f ? 'var(--gold, #c9a84c)' : 'var(--text-tertiary, rgba(255,255,255,0.4))',
                border: `1px solid ${filter === f ? 'var(--gold, #c9a84c)' : 'rgba(255,255,255,0.08)'}`,
              }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Quick Join */}
      {tables.length > 0 && (
        <div className="px-6 md:px-12 mb-6">
          <motion.div
            className="p-4 rounded-xl flex items-center justify-between"
            style={{
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.06)',
            }}
            whileHover={{ borderColor: 'rgba(201,168,76,0.3)' }}
          >
            <div>
              <p className="text-sm font-semibold">Quick Join</p>
              <p className="text-xs" style={{ color: 'var(--text-tertiary, rgba(255,255,255,0.4))' }}>
                Jump into the first table with an open seat.
              </p>
            </div>
            <Link href={`/play/blackjack/multi?table=${tables.find((t) => t.players_count < t.max_seats)?.id || tables[0]?.id}`}>
              <motion.button
                className="px-8 py-2 text-xs tracking-widest rounded-xl font-bold"
                style={{
                  background: 'linear-gradient(135deg, #c9a84c, #e8c55a)',
                  color: '#000',
                }}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
              >
                PLAY NOW
              </motion.button>
            </Link>
          </motion.div>
        </div>
      )}

      {/* Table grid */}
      <div className="px-6 md:px-12 pb-12">
        {loading ? (
          <div className="flex justify-center py-20">
            <motion.span
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="text-sm"
              style={{ color: 'var(--gold, #c9a84c)' }}
            >
              Loading tables...
            </motion.span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 opacity-40">
            <p>No tables found for this filter.</p>
          </div>
        ) : (
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
        )}
      </div>
    </div>
  )
}
