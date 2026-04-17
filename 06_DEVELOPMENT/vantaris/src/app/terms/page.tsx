'use client'

import { motion } from 'framer-motion'

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6 } },
}

export default function TermsPage() {
  return (
    <main className="min-h-screen py-20 px-6" style={{ background: 'var(--vanta-void)' }}>
      <motion.div initial="hidden" animate="visible" variants={fadeUp} className="max-w-3xl mx-auto">
        <p className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--text-tertiary)' }}>LEGAL</p>
        <h1 className="text-3xl md:text-5xl font-bold mb-8" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
          Terms of Service
        </h1>
        <div className="space-y-8 text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>1. Acceptance of Terms</h2>
            <p>By accessing or using any service operated by Everlight Ventures LLC ("Company"), including Vantaris Casino, Onyx POS, Hive Mind AI, Alley Kingz, and all related products, you agree to be bound by these Terms of Service.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>2. Eligibility</h2>
            <p>You must be at least 18 years of age to use our services. For casino features (Vantaris), you must be located in a jurisdiction where sweepstakes promotions are legal. Residents of Washington, Idaho, Nevada, and Montana are restricted from sweepstakes features.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>3. Sweepstakes Model</h2>
            <p>Vantaris Casino operates as a sweepstakes promotion, not a gambling platform.</p>
            <ul className="list-disc pl-6 mt-2 space-y-1">
              <li><strong>Gold Coins (GC)</strong> are purchased for entertainment. They have no cash value and cannot be redeemed.</li>
              <li><strong>Sweep Chips (SC)</strong> are given as a free bonus with GC purchases or through no-purchase-necessary methods (daily login, mail-in). SC may be redeemed for cash prizes after meeting playthrough requirements and identity verification.</li>
              <li>No purchase is necessary to receive SC or to participate in sweepstakes.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>4. Account Responsibility</h2>
            <p>You are responsible for maintaining the confidentiality of your account credentials. You agree to notify us immediately of any unauthorized use. We are not liable for losses arising from unauthorized access to your account.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>5. Prohibited Conduct</h2>
            <ul className="list-disc pl-6 space-y-1">
              <li>Using bots, scripts, or automated tools to interact with games</li>
              <li>Exploiting bugs or vulnerabilities (report them to support)</li>
              <li>Creating multiple accounts to abuse promotions</li>
              <li>Money laundering or fraudulent transactions</li>
              <li>Harassing other users or staff</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>6. Provably Fair Gaming</h2>
            <p>All Vantaris Casino games use provably fair RNG with SHA-256 cryptographic seeds. Server seeds are hashed before each round and revealed after. Players can independently verify every outcome. See our <a href="/fairness" className="underline" style={{ color: 'var(--gold)' }}>Provably Fair</a> page for details.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>7. Payments and Refunds</h2>
            <p>GC purchases are processed through Stripe. All sales are final. Refunds may be issued at our discretion for technical errors. SC redemptions require KYC verification and minimum balance of 50 SC.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>8. Limitation of Liability</h2>
            <p>Everlight Ventures LLC provides services "as is" without warranty. We are not liable for any indirect, incidental, or consequential damages. Our total liability shall not exceed the amount you paid us in the 12 months preceding the claim.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>9. Governing Law</h2>
            <p>These terms are governed by the laws of the State of California. Any disputes shall be resolved in the courts of Solano County, California.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>10. Contact</h2>
            <p>For questions: support@everlightventures.io</p>
            <p className="mt-2">Everlight Ventures LLC, Fairfield, California 94533</p>
          </section>

          <p className="text-xs pt-4" style={{ color: 'var(--text-tertiary)' }}>
            Last updated: April 2026
          </p>
        </div>
      </motion.div>
    </main>
  )
}
