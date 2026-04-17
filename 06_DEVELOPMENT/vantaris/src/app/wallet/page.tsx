'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import Link from 'next/link'
import { useBlackjackStore } from '@/lib/blackjack-store'
import { GC_PACKAGES, purchaseGCPackage } from '@/lib/sweepstakes'

/**
 * Vantaris Wallet -- Deposit, Withdraw, Transaction History
 */

export default function WalletPage() {
  const player = useBlackjackStore(s => s.player)
  const gameMode = useBlackjackStore(s => s.gameMode)
  const [tab, setTab] = useState<'overview' | 'deposit' | 'history'>('overview')

  // Mock transaction history
  const transactions = [
    { id: 1, type: 'win', desc: 'Blackjack win', amount: 250, currency: 'GC', time: '2 min ago' },
    { id: 2, type: 'bet', desc: 'Blackjack bet', amount: -100, currency: 'GC', time: '3 min ago' },
    { id: 3, type: 'bonus', desc: 'Daily login', amount: 100, currency: 'GC', time: '1 hour ago' },
    { id: 4, type: 'bonus', desc: 'Free SC bonus', amount: 0.30, currency: 'SC', time: '1 hour ago' },
    { id: 5, type: 'purchase', desc: 'Starter Pack', amount: 10000, currency: 'GC', time: 'Yesterday' },
  ]

  return (
    <div className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>
      <div className="px-6 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--vanta-border)' }}>
        <div className="flex items-center gap-4">
          <Link href="/lobby"><button className="text-sm" style={{ color: 'var(--text-tertiary)' }}>{'\u2190'} Back</button></Link>
          <h1 className="text-xl font-bold tracking-widest" style={{
            fontFamily: "'Cinzel', serif",
            background: 'linear-gradient(135deg, #c9a84c, #e8c55a)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>WALLET</h1>
        </div>
      </div>

      {/* Balances */}
      <div className="max-w-2xl mx-auto px-6 py-6">
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="glass p-4 rounded-xl text-center">
            <p className="text-[9px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Gold Coins</p>
            <p className="font-mono text-2xl font-bold" style={{ color: 'var(--gold)' }}>{player.chips.toLocaleString()}</p>
            <p className="text-[8px]" style={{ color: 'var(--text-tertiary)' }}>No cash value</p>
          </div>
          <div className="glass p-4 rounded-xl text-center">
            <p className="text-[9px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Sweep Chips</p>
            <p className="font-mono text-2xl font-bold" style={{ color: 'var(--win)' }}>{player.sweepsCoins.toFixed(2)}</p>
            <p className="text-[8px]" style={{ color: 'var(--text-tertiary)' }}>1 SC = $1 USD</p>
          </div>
          <div className="glass p-4 rounded-xl text-center">
            <p className="text-[9px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Gems</p>
            <p className="font-mono text-2xl font-bold" style={{ color: '#58a6ff' }}>{player.gems}</p>
            <p className="text-[8px]" style={{ color: 'var(--text-tertiary)' }}>Cosmetics</p>
          </div>
        </div>

        {/* Quick actions */}
        <div className="flex gap-3 mb-6">
          <Link href="/redeem" className="flex-1">
            <button className="w-full py-3 rounded-xl text-sm font-bold"
              style={{ background: 'rgba(0,230,118,0.1)', color: 'var(--win)', border: '1px solid rgba(0,230,118,0.3)' }}>
              REDEEM SC
            </button>
          </Link>
          <button onClick={() => setTab('deposit')} className="flex-1 py-3 rounded-xl text-sm font-bold"
            style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000' }}>
            BUY GC
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b mb-4" style={{ borderColor: 'var(--vanta-border)' }}>
          {(['overview', 'deposit', 'history'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className="flex-1 py-2 text-xs uppercase tracking-wider"
              style={{ color: tab === t ? 'var(--gold)' : 'var(--text-tertiary)', borderBottom: tab === t ? '2px solid var(--gold)' : '2px solid transparent', fontFamily: "'Cinzel', serif" }}>
              {t}
            </button>
          ))}
        </div>

        {tab === 'overview' && (
          <div className="space-y-3">
            <div className="flex justify-between p-3 rounded-lg" style={{ background: 'var(--vanta-surface)' }}>
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Rank</span>
              <span className="text-xs font-bold" style={{ color: 'var(--gold)' }}>{player.rank}</span>
            </div>
            <div className="flex justify-between p-3 rounded-lg" style={{ background: 'var(--vanta-surface)' }}>
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>XP</span>
              <span className="text-xs font-mono font-bold">{player.xp.toLocaleString()}</span>
            </div>
            <div className="flex justify-between p-3 rounded-lg" style={{ background: 'var(--vanta-surface)' }}>
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Presence Multiplier</span>
              <span className="text-xs font-mono font-bold" style={{ color: 'var(--gold)' }}>{player.presenceMultiplier}x</span>
            </div>
            <div className="flex justify-between p-3 rounded-lg" style={{ background: 'var(--vanta-surface)' }}>
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>SC Playthrough</span>
              <span className="text-xs font-mono">{player.scPlaythroughWagered.toFixed(2)} / {player.scPlaythroughRequired.toFixed(2)}</span>
            </div>
          </div>
        )}

        {tab === 'deposit' && (
          <div className="space-y-3">
            <p className="text-xs mb-2" style={{ color: 'var(--text-tertiary)' }}>
              Purchase Gold Coins for social play. Free Sweep Chips included as bonus.
              <br />No purchase necessary to obtain SC. See <Link href="/rules" className="underline">rules</Link>.
            </p>
            {GC_PACKAGES.map(pkg => (
              <motion.button key={pkg.id} onClick={() => purchaseGCPackage(pkg.id)}
                className="w-full p-4 rounded-xl flex items-center justify-between"
                style={{
                  background: pkg.featured ? 'rgba(201,168,76,0.08)' : 'var(--vanta-surface)',
                  border: `1px solid ${pkg.featured ? 'rgba(201,168,76,0.3)' : 'var(--vanta-border)'}`,
                }}
                whileTap={{ scale: 0.98 }}>
                <div className="text-left">
                  <p className="text-sm font-semibold">{pkg.name}</p>
                  <p className="text-xs" style={{ color: 'var(--gold)' }}>{pkg.gcAmount.toLocaleString()} GC</p>
                  <p className="text-[9px]" style={{ color: 'var(--win)' }}>+ {pkg.scBonus.toFixed(2)} SC free</p>
                  {pkg.gemsBonus > 0 && <p className="text-[9px]" style={{ color: '#58a6ff' }}>+ {pkg.gemsBonus} Gems</p>}
                </div>
                <div className="text-right">
                  <p className="font-bold text-lg" style={{ color: 'var(--gold)' }}>${pkg.priceUSD.toFixed(2)}</p>
                  {pkg.featured && <span className="text-[7px] bg-yellow-500 text-black font-bold px-1.5 py-0.5 rounded">BEST VALUE</span>}
                </div>
              </motion.button>
            ))}
          </div>
        )}

        {tab === 'history' && (
          <div className="space-y-2">
            {transactions.map(tx => (
              <div key={tx.id} className="flex items-center justify-between p-3 rounded-lg" style={{ background: 'var(--vanta-surface)' }}>
                <div>
                  <p className="text-xs font-semibold">{tx.desc}</p>
                  <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>{tx.time}</p>
                </div>
                <p className="font-mono text-sm font-bold" style={{ color: tx.amount >= 0 ? 'var(--win)' : 'var(--loss)' }}>
                  {tx.amount >= 0 ? '+' : ''}{tx.amount.toLocaleString()} {tx.currency}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
