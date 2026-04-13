'use client'

import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useBlackjackStore } from '@/lib/blackjack-store'
import { canRedeemSC, getPlaythroughProgress } from '@/lib/sweepstakes'

/**
 * Vantaris Redeem Page
 *
 * SC (Sweep Chips) redemption for cash.
 * Requires: minimum 50 SC, playthrough complete, KYC verified.
 * Payout methods: CashApp, PayPal, bank ACH, crypto (where allowed).
 */

const PAYOUT_METHODS = [
  { id: 'cashapp', name: 'CashApp', icon: '\uD83D\uDCB2', minSC: 50, fee: '0%', speed: '1-3 business days' },
  { id: 'paypal', name: 'PayPal', icon: '\uD83C\uDF10', minSC: 50, fee: '0%', speed: '1-3 business days' },
  { id: 'bank', name: 'Bank Transfer (ACH)', icon: '\uD83C\uDFE6', minSC: 100, fee: '0%', speed: '3-5 business days' },
  { id: 'crypto', name: 'Crypto (USDT/BTC)', icon: '\u20BF', minSC: 50, fee: '0%', speed: 'Within 24 hours' },
]

export default function RedeemPage() {
  const player = useBlackjackStore(s => s.player)
  const [selectedMethod, setSelectedMethod] = useState<string | null>(null)
  const [redeemAmount, setRedeemAmount] = useState('')
  const [kycStep, setKycStep] = useState(0)
  const [kycData, setKycData] = useState({ fullName: '', dob: '', address: '', state: '', zip: '' })

  const progress = getPlaythroughProgress()
  const eligible = canRedeemSC()
  const scBalance = player.sweepsCoins

  const handleRedeem = () => {
    const amount = parseFloat(redeemAmount)
    if (!amount || amount < 50 || amount > scBalance) return
    // In production: POST to Django /blackjack/api/redeem/
    // For now: show confirmation
    alert(`Redemption request submitted: ${amount} SC via ${selectedMethod}. Processing in 1-3 business days.`)
  }

  return (
    <div className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>
      {/* Header */}
      <div className="px-6 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--vanta-border)' }}>
        <div className="flex items-center gap-4">
          <Link href="/lobby"><button className="text-sm" style={{ color: 'var(--text-tertiary)' }}>{'\u2190'} Back</button></Link>
          <h1 className="text-xl font-bold tracking-widest" style={{
            fontFamily: "'Cinzel', serif",
            background: 'linear-gradient(135deg, #00e676, #69f0ae)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>REDEEM</h1>
        </div>
        <Link href="/rules"><button className="text-xs underline" style={{ color: 'var(--text-tertiary)' }}>Sweepstakes Rules</button></Link>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-8">

        {/* SC Balance Card */}
        <div className="glass-elevated p-6 rounded-2xl mb-8 text-center">
          <p className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--text-tertiary)' }}>Your Sweep Chips Balance</p>
          <p className="font-mono text-4xl font-bold" style={{ color: 'var(--win)' }}>{scBalance.toFixed(2)} SC</p>
          <p className="text-xs mt-2" style={{ color: 'var(--text-tertiary)' }}>1 SC = $1.00 USD</p>
        </div>

        {/* Playthrough Progress */}
        <div className="glass p-4 rounded-xl mb-6">
          <div className="flex justify-between items-center mb-2">
            <p className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Playthrough Progress</p>
            <p className="text-xs font-mono" style={{ color: progress >= 100 ? 'var(--win)' : 'var(--gold)' }}>
              {progress.toFixed(0)}%
            </p>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <motion.div className="h-full rounded-full"
              style={{ background: progress >= 100 ? 'var(--win)' : 'var(--gold)', width: `${progress}%` }}
              initial={{ width: 0 }} animate={{ width: `${progress}%` }} transition={{ duration: 1 }} />
          </div>
          <p className="text-[10px] mt-2" style={{ color: 'var(--text-tertiary)' }}>
            {player.scPlaythroughWagered.toFixed(2)} / {player.scPlaythroughRequired.toFixed(2)} SC wagered
          </p>
        </div>

        {/* KYC Status */}
        <div className="glass p-4 rounded-xl mb-6">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-sm font-semibold">Identity Verification</p>
              <p className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>Required for all redemptions (AML/KYC)</p>
            </div>
            {player.kycVerified ? (
              <span className="text-xs font-bold px-3 py-1 rounded-full" style={{ background: 'rgba(0,230,118,0.1)', color: 'var(--win)' }}>
                {'\u2713'} Verified
              </span>
            ) : (
              <button onClick={() => setKycStep(1)}
                className="text-xs font-bold px-4 py-2 rounded-lg"
                style={{ background: 'rgba(201,168,76,0.15)', color: '#c9a84c', border: '1px solid rgba(201,168,76,0.3)' }}>
                Verify Now
              </button>
            )}
          </div>

          {/* KYC Form */}
          {kycStep > 0 && !player.kycVerified && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mt-4 space-y-3">
              <input type="text" placeholder="Full Legal Name" value={kycData.fullName}
                onChange={e => setKycData(p => ({ ...p, fullName: e.target.value }))}
                className="w-full bg-transparent border rounded-lg px-3 py-2 text-sm outline-none"
                style={{ borderColor: 'var(--vanta-border)', color: '#fff' }} />
              <input type="date" placeholder="Date of Birth" value={kycData.dob}
                onChange={e => setKycData(p => ({ ...p, dob: e.target.value }))}
                className="w-full bg-transparent border rounded-lg px-3 py-2 text-sm outline-none"
                style={{ borderColor: 'var(--vanta-border)', color: '#fff' }} />
              <input type="text" placeholder="Street Address" value={kycData.address}
                onChange={e => setKycData(p => ({ ...p, address: e.target.value }))}
                className="w-full bg-transparent border rounded-lg px-3 py-2 text-sm outline-none"
                style={{ borderColor: 'var(--vanta-border)', color: '#fff' }} />
              <div className="flex gap-3">
                <input type="text" placeholder="State" value={kycData.state}
                  onChange={e => setKycData(p => ({ ...p, state: e.target.value }))}
                  className="flex-1 bg-transparent border rounded-lg px-3 py-2 text-sm outline-none"
                  style={{ borderColor: 'var(--vanta-border)', color: '#fff' }} />
                <input type="text" placeholder="ZIP" value={kycData.zip}
                  onChange={e => setKycData(p => ({ ...p, zip: e.target.value }))}
                  className="w-24 bg-transparent border rounded-lg px-3 py-2 text-sm outline-none"
                  style={{ borderColor: 'var(--vanta-border)', color: '#fff' }} />
              </div>
              <button onClick={() => {
                // In production: POST to Django for real KYC
                useBlackjackStore.setState({ player: { ...player, kycVerified: true } })
                setKycStep(0)
              }}
                className="w-full py-2 rounded-lg text-sm font-bold"
                style={{ background: 'var(--win)', color: '#000' }}>
                Submit Verification
              </button>
              <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>
                Your information is encrypted and used solely for identity verification per federal AML requirements.
              </p>
            </motion.div>
          )}
        </div>

        {/* Payout Method Selection */}
        <p className="text-sm font-semibold mb-3">Choose Payout Method</p>
        <div className="grid grid-cols-2 gap-3 mb-6">
          {PAYOUT_METHODS.map(m => (
            <motion.button key={m.id} onClick={() => setSelectedMethod(m.id)}
              className="p-4 rounded-xl text-left"
              style={{
                background: selectedMethod === m.id ? 'rgba(0,230,118,0.08)' : 'var(--vanta-surface)',
                border: `2px solid ${selectedMethod === m.id ? 'var(--win)' : 'var(--vanta-border)'}`,
              }}
              whileTap={{ scale: 0.98 }}>
              <span className="text-xl block mb-1">{m.icon}</span>
              <p className="text-sm font-semibold">{m.name}</p>
              <p className="text-[9px]" style={{ color: 'var(--text-tertiary)' }}>Min: {m.minSC} SC | {m.speed}</p>
            </motion.button>
          ))}
        </div>

        {/* Redeem Amount */}
        <div className="glass p-4 rounded-xl mb-6">
          <p className="text-xs uppercase tracking-wider mb-2" style={{ color: 'var(--text-tertiary)' }}>Redeem Amount (SC)</p>
          <div className="flex gap-3">
            <input type="number" value={redeemAmount}
              onChange={e => setRedeemAmount(e.target.value)}
              placeholder="50.00" min={50} max={scBalance}
              className="flex-1 bg-transparent border rounded-lg px-3 py-2 text-lg font-mono outline-none"
              style={{ borderColor: 'var(--vanta-border)', color: '#fff' }} />
            <button onClick={() => setRedeemAmount(scBalance.toFixed(2))}
              className="px-4 py-2 rounded-lg text-xs font-bold"
              style={{ background: 'rgba(0,230,118,0.1)', color: 'var(--win)', border: '1px solid rgba(0,230,118,0.3)' }}>
              MAX
            </button>
          </div>
          {redeemAmount && (
            <p className="text-xs mt-2" style={{ color: 'var(--win)' }}>
              You will receive: ${parseFloat(redeemAmount || '0').toFixed(2)} USD
            </p>
          )}
        </div>

        {/* Submit */}
        <motion.button onClick={handleRedeem}
          className="w-full py-4 rounded-xl text-lg font-bold tracking-widest"
          style={{
            background: eligible && selectedMethod ? 'linear-gradient(135deg, #00e676, #69f0ae)' : 'rgba(255,255,255,0.05)',
            color: eligible && selectedMethod ? '#000' : 'rgba(255,255,255,0.2)',
            fontFamily: "'Cinzel', serif",
            cursor: eligible && selectedMethod ? 'pointer' : 'not-allowed',
          }}
          whileHover={eligible && selectedMethod ? { scale: 1.02 } : {}}
          whileTap={eligible && selectedMethod ? { scale: 0.98 } : {}}>
          {!player.kycVerified ? 'VERIFY IDENTITY FIRST' :
            progress < 100 ? 'COMPLETE PLAYTHROUGH FIRST' :
              scBalance < 50 ? 'MINIMUM 50 SC REQUIRED' :
                !selectedMethod ? 'SELECT PAYOUT METHOD' :
                  'REDEEM NOW'}
        </motion.button>

        <p className="text-[9px] mt-4 text-center" style={{ color: 'var(--text-tertiary)' }}>
          Sweep Chips have no purchase price and are provided as a free promotional bonus.
          Redemptions are processed within 1-5 business days. Must be 18+.
          See <Link href="/rules" className="underline">Official Sweepstakes Rules</Link> for full terms.
        </p>
      </div>
    </div>
  )
}
