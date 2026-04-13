'use client'

import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import Link from 'next/link'

/**
 * Vantaris Rewards Center
 *
 * Daily login calendar, missions, battle pass tiers.
 * Everlight Ventures / Vantaris Casino branded.
 */

const DAILY_REWARDS = [
  { day: 1, reward: 100, type: 'GC' },
  { day: 2, reward: 150, type: 'GC' },
  { day: 3, reward: 5, type: 'Gems' },
  { day: 4, reward: 250, type: 'GC' },
  { day: 5, reward: 10, type: 'Gems' },
  { day: 6, reward: 500, type: 'GC' },
  { day: 7, reward: 1000, type: 'GC', bonus: '+ 25 Gems' },
]

const MISSIONS = [
  { id: 'm1', name: 'Play 10 Hands', desc: 'Play 10 blackjack hands', reward: 200, type: 'GC', target: 10, icon: '\uD83C\uDCCF' },
  { id: 'm2', name: 'Win 5 Hands', desc: 'Win 5 hands in any game', reward: 300, type: 'GC', target: 5, icon: '\uD83C\uDFC6' },
  { id: 'm3', name: 'Hit Blackjack', desc: 'Get a natural 21', reward: 500, type: 'GC', target: 1, icon: '\u2B50' },
  { id: 'm4', name: '3-Win Streak', desc: 'Win 3 hands in a row', reward: 15, type: 'Gems', target: 1, icon: '\uD83D\uDD25' },
  { id: 'm5', name: 'Double Down Win', desc: 'Win a doubled hand', reward: 400, type: 'GC', target: 1, icon: '\uD83D\uDCAA' },
  { id: 'm6', name: 'Play All Tables', desc: 'Play on 3 different table variants', reward: 25, type: 'Gems', target: 3, icon: '\uD83C\uDFB0' },
]

const BATTLE_PASS = [
  { tier: 1, xp: 0, reward: '200 GC', free: true },
  { tier: 2, xp: 500, reward: '5 Gems', free: true },
  { tier: 3, xp: 1200, reward: 'Neon Card Back', free: false },
  { tier: 4, xp: 2000, reward: '500 GC', free: true },
  { tier: 5, xp: 3000, reward: 'Gold Tux Outfit', free: false },
  { tier: 6, xp: 4500, reward: '1,000 GC', free: true },
  { tier: 7, xp: 6000, reward: '25 Gems', free: true },
  { tier: 8, xp: 8000, reward: 'Fire Aura', free: false },
  { tier: 9, xp: 10000, reward: '2,500 GC', free: true },
  { tier: 10, xp: 15000, reward: 'Legend Title + 50 Gems', free: false },
]

export default function RewardsPage() {
  const [activeTab, setActiveTab] = useState<'daily' | 'missions' | 'battlepass'>('daily')
  const [loginStreak, setLoginStreak] = useState(0)
  const [claimedDays, setClaimedDays] = useState<number[]>([])

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('vantaris_daily_rewards') || '{}')
      if (saved.streak) setLoginStreak(saved.streak)
      if (saved.claimed) setClaimedDays(saved.claimed)
    } catch {}
  }, [])

  const handleClaimDaily = (day: number) => {
    if (claimedDays.includes(day) || day > loginStreak + 1) return
    const newClaimed = [...claimedDays, day]
    const newStreak = Math.max(loginStreak, day)
    setClaimedDays(newClaimed)
    setLoginStreak(newStreak)
    localStorage.setItem('vantaris_daily_rewards', JSON.stringify({ streak: newStreak, claimed: newClaimed }))
  }

  return (
    <div className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>
      {/* Header */}
      <div className="px-6 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--vanta-border)' }}>
        <div className="flex items-center gap-4">
          <Link href="/lobby">
            <button className="text-sm" style={{ color: 'var(--text-tertiary)' }}>{'\u2190'} Back</button>
          </Link>
          <h1 className="text-xl font-bold tracking-widest" style={{
            fontFamily: "'Cinzel', serif",
            background: 'linear-gradient(135deg, #c9a84c, #e8c55a)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>
            REWARDS CENTER
          </h1>
        </div>
        <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>By Everlight Ventures</p>
      </div>

      {/* Tabs */}
      <div className="flex border-b px-6" style={{ borderColor: 'var(--vanta-border)' }}>
        {(['daily', 'missions', 'battlepass'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className="px-6 py-3 text-sm uppercase tracking-wider"
            style={{
              color: activeTab === tab ? 'var(--gold)' : 'var(--text-tertiary)',
              borderBottom: activeTab === tab ? '2px solid var(--gold)' : '2px solid transparent',
              fontFamily: "'Cinzel', serif",
            }}>
            {tab === 'battlepass' ? 'BATTLE PASS' : tab}
          </button>
        ))}
      </div>

      <div className="px-6 py-8 max-w-4xl mx-auto">

        {/* DAILY LOGIN */}
        {activeTab === 'daily' && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <p className="text-sm mb-6" style={{ color: 'var(--text-secondary)' }}>
              Log in daily to earn rewards. Streak resets if you miss a day.
              Current streak: <span style={{ color: 'var(--gold)' }}>{loginStreak} days</span>
            </p>
            <div className="grid grid-cols-7 gap-3">
              {DAILY_REWARDS.map(day => {
                const claimed = claimedDays.includes(day.day)
                const available = day.day <= loginStreak + 1 && !claimed
                return (
                  <motion.div key={day.day}
                    onClick={() => available && handleClaimDaily(day.day)}
                    className={`p-4 rounded-xl text-center ${available ? 'cursor-pointer' : ''}`}
                    style={{
                      background: claimed ? 'rgba(0,230,118,0.08)' : available ? 'rgba(201,168,76,0.1)' : 'var(--vanta-surface)',
                      border: `1px solid ${claimed ? 'rgba(0,230,118,0.3)' : available ? 'rgba(201,168,76,0.3)' : 'var(--vanta-border)'}`,
                      opacity: claimed ? 0.6 : 1,
                    }}
                    whileHover={available ? { scale: 1.05 } : {}}
                    whileTap={available ? { scale: 0.95 } : {}}
                  >
                    <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: 'var(--text-tertiary)' }}>Day {day.day}</p>
                    <p className="text-lg font-bold font-mono" style={{ color: claimed ? 'var(--win)' : 'var(--gold)' }}>
                      {day.reward}
                    </p>
                    <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>{day.type}</p>
                    {day.bonus && <p className="text-[8px] mt-1" style={{ color: 'var(--gold)' }}>{day.bonus}</p>}
                    {claimed && <p className="text-[8px] mt-1" style={{ color: 'var(--win)' }}>{'\u2713'} Claimed</p>}
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        )}

        {/* MISSIONS */}
        {activeTab === 'missions' && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
            <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
              Complete missions to earn bonus chips and gems. Resets daily.
            </p>
            {MISSIONS.map(m => (
              <div key={m.id} className="flex items-center gap-4 p-4 rounded-xl"
                style={{ background: 'var(--vanta-surface)', border: '1px solid var(--vanta-border)' }}>
                <span className="text-2xl">{m.icon}</span>
                <div className="flex-1">
                  <p className="text-sm font-semibold">{m.name}</p>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{m.desc}</p>
                  {/* Progress bar */}
                  <div className="mt-2 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                    <div className="h-full rounded-full" style={{ width: '0%', background: 'var(--gold)' }} />
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-mono text-sm font-bold" style={{ color: 'var(--gold)' }}>{m.reward}</p>
                  <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>{m.type}</p>
                </div>
              </div>
            ))}
          </motion.div>
        )}

        {/* BATTLE PASS */}
        {activeTab === 'battlepass' && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center justify-between mb-6">
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Season 1 -- Earn XP by playing to unlock tiers
              </p>
              <button className="px-4 py-2 rounded-lg text-xs font-bold"
                style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif" }}>
                UPGRADE TO PREMIUM
              </button>
            </div>
            <div className="space-y-2">
              {BATTLE_PASS.map(tier => (
                <div key={tier.tier} className="flex items-center gap-4 p-3 rounded-xl"
                  style={{
                    background: tier.free ? 'var(--vanta-surface)' : 'rgba(201,168,76,0.05)',
                    border: `1px solid ${tier.free ? 'var(--vanta-border)' : 'rgba(201,168,76,0.2)'}`,
                  }}>
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                    style={{ background: 'rgba(201,168,76,0.15)', color: 'var(--gold)' }}>
                    {tier.tier}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold">{tier.reward}</p>
                    <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>{tier.xp.toLocaleString()} XP</p>
                  </div>
                  {!tier.free && (
                    <span className="text-[8px] px-2 py-0.5 rounded-full font-bold"
                      style={{ background: 'rgba(201,168,76,0.2)', color: '#c9a84c' }}>PREMIUM</span>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
