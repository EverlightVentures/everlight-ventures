'use client'

import Link from 'next/link'

/**
 * Support / FAQ Page
 */

const FAQ = [
  { q: 'What are Gold Coins (GC)?', a: 'Gold Coins are virtual tokens purchased for social gameplay entertainment. They have NO cash value and cannot be redeemed.' },
  { q: 'What are Sweep Chips (SC)?', a: 'Sweep Chips are promotional entries that can be redeemed for cash prizes. They are never sold -- only given as free bonuses with GC purchases and through no-purchase-necessary methods.' },
  { q: 'How do I get free Sweep Chips?', a: 'Daily login bonus (0.30 SC), promotional giveaways, social media contests, and mail-in requests. No purchase necessary.' },
  { q: 'How do I redeem Sweep Chips?', a: 'Go to the Redeem page. Minimum 50 SC, complete KYC verification, and meet the 1x playthrough requirement. Payouts via CashApp, PayPal, bank, or crypto.' },
  { q: 'Is the game fair?', a: 'Every game uses provably fair RNG with SHA-256 cryptographic seeds. You can verify any outcome yourself on our Fairness page.' },
  { q: 'What states are eligible?', a: 'All US states except Washington, Idaho, Nevada, and Montana. You must be 18+ to play.' },
  { q: 'How do I change my dealer?', a: 'Click the dealer portrait during gameplay to open the dealer selection panel. Choose from 4 unique dealers.' },
  { q: 'What is the Progressive Jackpot?', a: 'The progressive jackpot starts at 500,000 GC and grows with every bet. It hits when you get suited diamond 7-7-7 with the progressive bet active.' },
]

export default function SupportPage() {
  return (
    <div className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>
      <div className="px-6 py-4 border-b flex items-center gap-4" style={{ borderColor: 'var(--vanta-border)' }}>
        <Link href="/lobby"><button className="text-sm" style={{ color: 'var(--text-tertiary)' }}>{'\u2190'} Back</button></Link>
        <h1 className="text-xl font-bold tracking-widest" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>SUPPORT</h1>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-8">
        <h2 className="text-lg font-bold mb-6">Frequently Asked Questions</h2>
        <div className="space-y-3">
          {FAQ.map((item, i) => (
            <details key={i} className="glass rounded-xl overflow-hidden">
              <summary className="p-4 cursor-pointer text-sm font-semibold" style={{ color: 'var(--gold)' }}>{item.q}</summary>
              <div className="px-4 pb-4 text-xs" style={{ color: 'var(--text-secondary)' }}>{item.a}</div>
            </details>
          ))}
        </div>

        <div className="mt-8 glass p-6 rounded-xl text-center">
          <p className="text-sm font-bold mb-2">Need more help?</p>
          <p className="text-xs mb-4" style={{ color: 'var(--text-tertiary)' }}>Contact our support team.</p>
          <p className="text-sm" style={{ color: 'var(--gold)' }}>support@everlightventures.io</p>
        </div>
      </div>
    </div>
  )
}
