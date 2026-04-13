'use client'

import Link from 'next/link'

/**
 * Vantaris Official Sweepstakes Rules
 *
 * Legal compliance page for the dual-currency model.
 * Required for sweepstakes casino operation.
 */

export default function RulesPage() {
  return (
    <div className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>
      <div className="px-6 py-4 border-b flex items-center gap-4" style={{ borderColor: 'var(--vanta-border)' }}>
        <Link href="/lobby"><button className="text-sm" style={{ color: 'var(--text-tertiary)' }}>{'\u2190'} Back</button></Link>
        <h1 className="text-lg font-bold tracking-widest" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
          OFFICIAL SWEEPSTAKES RULES
        </h1>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-8 space-y-8 text-sm" style={{ color: 'var(--text-secondary)' }}>

        <section>
          <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>1. OVERVIEW</h2>
          <p>Vantaris Casino, operated by Everlight Ventures LLC, offers a social casino platform featuring
            dual-currency gameplay. Gold Coins (GC) are purchased for entertainment purposes only.
            Sweep Chips (SC) are promotional sweepstakes entries provided at no additional cost.</p>
        </section>

        <section>
          <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>2. NO PURCHASE NECESSARY</h2>
          <p>No purchase is necessary to obtain Sweep Chips or to participate in sweepstakes games.
            Sweep Chips may be obtained through the following free methods:</p>
          <ul className="list-disc list-inside mt-2 space-y-1" style={{ color: 'var(--text-tertiary)' }}>
            <li>Daily login bonus (0.30 SC per day)</li>
            <li>Promotional giveaways and social media contests</li>
            <li>Mail-in request: Send a handwritten request including your full name, email address,
              and the words "Vantaris Sweepstakes Entry" to: Everlight Ventures LLC, Fairfield, CA 94534.
              Limit one request per day, 30 per calendar month.</li>
            <li>Referral bonuses for inviting new players</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>3. GOLD COINS (GC)</h2>
          <p>Gold Coins are virtual tokens purchased for social gameplay entertainment. Gold Coins have
            <strong style={{ color: '#fff' }}> NO CASH VALUE</strong> and cannot be redeemed, exchanged, or
            transferred for real money, goods, or services. Gold Coins are non-refundable.</p>
        </section>

        <section>
          <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>4. SWEEP CHIPS (SC)</h2>
          <p>Sweep Chips are promotional entries that can be used in eligible sweepstakes games.
            Sweep Chips are <strong style={{ color: '#fff' }}>never sold</strong> -- they are provided as
            complimentary bonuses with Gold Coin purchases and through no-purchase-necessary methods.</p>
          <p className="mt-2">Sweep Chips may be redeemed for cash prizes subject to the following conditions:</p>
          <ul className="list-disc list-inside mt-2 space-y-1" style={{ color: 'var(--text-tertiary)' }}>
            <li>Minimum redemption: 50 SC ($50.00 USD equivalent)</li>
            <li>Playthrough requirement: SC must be wagered at least 1x before redemption</li>
            <li>Identity verification (KYC) must be completed</li>
            <li>Player must be 18 years of age or older</li>
            <li>Player must be located in an eligible U.S. state or jurisdiction</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>5. ELIGIBILITY</h2>
          <p>Participants must be at least 18 years old and legally residing in the United States.
            Residents of the following states are NOT eligible to participate in sweepstakes games
            or redeem Sweep Chips:</p>
          <p className="mt-2 font-bold" style={{ color: '#ff5252' }}>Washington (WA), Idaho (ID), Nevada (NV), Montana (MT)</p>
          <p className="mt-2">Employees of Everlight Ventures LLC, their immediate families,
            and household members are not eligible.</p>
        </section>

        <section>
          <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>6. REDEMPTION</h2>
          <p>Sweep Chips may be redeemed for cash via the following methods:</p>
          <ul className="list-disc list-inside mt-2 space-y-1" style={{ color: 'var(--text-tertiary)' }}>
            <li>CashApp (1-3 business days)</li>
            <li>PayPal (1-3 business days)</li>
            <li>Bank transfer / ACH (3-5 business days)</li>
            <li>Cryptocurrency (USDT/BTC, within 24 hours, where permitted)</li>
          </ul>
          <p className="mt-2">Redemption value: 1 SC = $1.00 USD.</p>
        </section>

        <section>
          <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>7. PROVABLY FAIR</h2>
          <p>All games on Vantaris Casino use cryptographically committed random number generation.
            Game outcomes are determined by SHA-256 hashed seeds that are committed before each round
            and revealed after. Players may verify any game outcome independently.</p>
        </section>

        <section>
          <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>8. TAX OBLIGATIONS</h2>
          <p>Sweep Chip redemptions may be subject to federal and state income tax.
            Vantaris Casino will issue a 1099-MISC for any player who redeems $600 or more
            in a calendar year, as required by IRS regulations. Players are responsible for
            reporting and paying all applicable taxes.</p>
        </section>

        <section>
          <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>9. RESPONSIBLE PLAY</h2>
          <p>Vantaris Casino is committed to responsible gaming. Players may set deposit limits,
            session time limits, and self-exclusion periods through their account settings.
            If you or someone you know has a gambling problem, please contact:</p>
          <p className="mt-2" style={{ color: 'var(--gold)' }}>
            National Council on Problem Gambling: 1-800-522-4700
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>10. CONTACT</h2>
          <p>Everlight Ventures LLC<br />
            Fairfield, California 94534<br />
            support@everlightventures.io</p>
        </section>

        <p className="text-[10px] pt-4 border-t" style={{ borderColor: 'var(--vanta-border)', color: 'var(--text-tertiary)' }}>
          Last updated: April 13, 2026. These rules are subject to change.
          By participating, you agree to these Official Sweepstakes Rules and our Terms of Service.
        </p>
      </div>
    </div>
  )
}
