'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { useBlackjackStore } from '@/lib/blackjack-store'

/**
 * Settings -- Account, Audio, Responsible Gambling
 */

export default function SettingsPage() {
  const store = useBlackjackStore()
  const [depositLimit, setDepositLimit] = useState('none')
  const [sessionLimit, setSessionLimit] = useState('none')

  return (
    <div className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>
      <div className="px-6 py-4 border-b flex items-center gap-4" style={{ borderColor: 'var(--vanta-border)' }}>
        <Link href="/lobby"><button className="text-sm" style={{ color: 'var(--text-tertiary)' }}>{'\u2190'} Back</button></Link>
        <h1 className="text-xl font-bold tracking-widest" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>SETTINGS</h1>
      </div>

      <div className="max-w-xl mx-auto px-6 py-6 space-y-6">
        {/* Audio */}
        <section>
          <h2 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>Audio</h2>
          <div className="space-y-3">
            {[
              { label: 'Music', key: 'musicEnabled', value: store.musicEnabled },
              { label: 'Dealer Voice', key: 'voiceEnabled', value: store.voiceEnabled },
              { label: 'Auto-Rebet', key: 'autoRebet', value: store.autoRebet },
            ].map(s => (
              <div key={s.key} className="flex justify-between items-center p-3 rounded-lg" style={{ background: 'var(--vanta-surface)' }}>
                <span className="text-sm">{s.label}</span>
                <button onClick={() => useBlackjackStore.setState({ [s.key]: !s.value } as any)}
                  className="w-11 h-6 rounded-full relative transition-colors"
                  style={{ background: s.value ? 'var(--gold)' : 'rgba(255,255,255,0.15)' }}>
                  <div className="w-5 h-5 rounded-full bg-white absolute top-0.5 transition-all"
                    style={{ left: s.value ? '22px' : '2px' }} />
                </button>
              </div>
            ))}
          </div>
        </section>

        {/* Game Mode */}
        <section>
          <h2 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>Game Mode</h2>
          <div className="flex gap-3">
            {(['gc', 'sc'] as const).map(mode => (
              <button key={mode} onClick={() => useBlackjackStore.setState({ gameMode: mode })}
                className="flex-1 py-3 rounded-xl text-sm font-bold"
                style={{
                  background: store.gameMode === mode ? (mode === 'sc' ? 'rgba(0,230,118,0.1)' : 'rgba(201,168,76,0.1)') : 'var(--vanta-surface)',
                  color: store.gameMode === mode ? (mode === 'sc' ? 'var(--win)' : 'var(--gold)') : 'var(--text-tertiary)',
                  border: `1px solid ${store.gameMode === mode ? (mode === 'sc' ? 'rgba(0,230,118,0.3)' : 'rgba(201,168,76,0.3)') : 'var(--vanta-border)'}`,
                }}>
                {mode === 'gc' ? 'Gold Coins (Social)' : 'Sweep Chips (Redeemable)'}
              </button>
            ))}
          </div>
        </section>

        {/* Responsible Gambling */}
        <section>
          <h2 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: '#ff5252' }}>Responsible Play</h2>
          <div className="space-y-3">
            <div className="p-3 rounded-lg" style={{ background: 'var(--vanta-surface)' }}>
              <p className="text-sm mb-2">Daily Deposit Limit</p>
              <div className="flex gap-2">
                {['none', '50', '100', '500'].map(v => (
                  <button key={v} onClick={() => setDepositLimit(v)}
                    className="text-xs px-3 py-1.5 rounded-lg"
                    style={{
                      background: depositLimit === v ? 'rgba(255,82,82,0.1)' : 'transparent',
                      color: depositLimit === v ? '#ff5252' : 'var(--text-tertiary)',
                      border: `1px solid ${depositLimit === v ? 'rgba(255,82,82,0.3)' : 'var(--vanta-border)'}`,
                    }}>
                    {v === 'none' ? 'No Limit' : `$${v}`}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-3 rounded-lg" style={{ background: 'var(--vanta-surface)' }}>
              <p className="text-sm mb-2">Session Time Limit</p>
              <div className="flex gap-2">
                {['none', '30m', '1h', '2h'].map(v => (
                  <button key={v} onClick={() => setSessionLimit(v)}
                    className="text-xs px-3 py-1.5 rounded-lg"
                    style={{
                      background: sessionLimit === v ? 'rgba(255,82,82,0.1)' : 'transparent',
                      color: sessionLimit === v ? '#ff5252' : 'var(--text-tertiary)',
                      border: `1px solid ${sessionLimit === v ? 'rgba(255,82,82,0.3)' : 'var(--vanta-border)'}`,
                    }}>
                    {v === 'none' ? 'No Limit' : v}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-4 rounded-xl" style={{ background: 'rgba(255,82,82,0.05)', border: '1px solid rgba(255,82,82,0.15)' }}>
              <p className="text-sm font-bold mb-1" style={{ color: '#ff5252' }}>Self-Exclusion</p>
              <p className="text-xs mb-3" style={{ color: 'var(--text-tertiary)' }}>
                If you need a break, you can exclude yourself for 24 hours, 7 days, 30 days, or permanently.
              </p>
              <button className="text-xs px-4 py-2 rounded-lg"
                style={{ background: 'rgba(255,82,82,0.1)', color: '#ff5252', border: '1px solid rgba(255,82,82,0.3)' }}>
                Self-Exclude
              </button>
            </div>

            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
              National Problem Gambling Helpline: <span style={{ color: 'var(--gold)' }}>1-800-522-4700</span>
            </p>
          </div>
        </section>

        {/* Account */}
        <section>
          <h2 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>Account</h2>
          <div className="space-y-2">
            <Link href="/auth">
              <button className="w-full py-3 rounded-xl text-sm text-left px-4" style={{ background: 'var(--vanta-surface)', border: '1px solid var(--vanta-border)' }}>
                Change Password
              </button>
            </Link>
            <Link href="/rules">
              <button className="w-full py-3 rounded-xl text-sm text-left px-4" style={{ background: 'var(--vanta-surface)', border: '1px solid var(--vanta-border)' }}>
                Sweepstakes Rules
              </button>
            </Link>
            <Link href="/fairness">
              <button className="w-full py-3 rounded-xl text-sm text-left px-4" style={{ background: 'var(--vanta-surface)', border: '1px solid var(--vanta-border)' }}>
                Provably Fair
              </button>
            </Link>
            <button className="w-full py-3 rounded-xl text-sm text-left px-4"
              style={{ background: 'rgba(255,82,82,0.05)', color: 'var(--loss)', border: '1px solid rgba(255,82,82,0.2)' }}>
              Delete Account
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}
