'use client'

import { motion } from 'framer-motion'

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6 } },
}

export default function PrivacyPage() {
  return (
    <main className="min-h-screen py-20 px-6" style={{ background: 'var(--vanta-void)' }}>
      <motion.div initial="hidden" animate="visible" variants={fadeUp} className="max-w-3xl mx-auto">
        <p className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--text-tertiary)' }}>LEGAL</p>
        <h1 className="text-3xl md:text-5xl font-bold mb-8" style={{ fontFamily: "'Cinzel', serif", color: 'var(--gold)' }}>
          Privacy Policy
        </h1>
        <div className="space-y-8 text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>1. Information We Collect</h2>
            <p>Everlight Ventures LLC ("we", "us") collects the following information when you use our services:</p>
            <ul className="list-disc pl-6 mt-2 space-y-1">
              <li>Account information: email address, display name, password (hashed)</li>
              <li>Payment information: processed securely through Stripe. We never store full card numbers.</li>
              <li>Usage data: game history, preferences, device type, IP address</li>
              <li>Cookies and local storage for session management and preferences</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>2. How We Use Your Information</h2>
            <ul className="list-disc pl-6 space-y-1">
              <li>To provide and maintain our services</li>
              <li>To process transactions and send related information</li>
              <li>To send promotional communications (with opt-out option)</li>
              <li>To detect, prevent, and address fraud or technical issues</li>
              <li>To comply with legal obligations</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>3. Data Sharing</h2>
            <p>We do not sell your personal information. We may share data with:</p>
            <ul className="list-disc pl-6 mt-2 space-y-1">
              <li>Payment processors (Stripe) to complete transactions</li>
              <li>Analytics providers to improve our services</li>
              <li>Law enforcement when required by law</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>4. Your Rights (CCPA)</h2>
            <p>California residents have the right to:</p>
            <ul className="list-disc pl-6 mt-2 space-y-1">
              <li>Know what personal information is collected</li>
              <li>Request deletion of personal information</li>
              <li>Opt out of the sale of personal information (we don't sell it)</li>
              <li>Non-discrimination for exercising these rights</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>5. Data Security</h2>
            <p>We implement industry-standard security measures including encryption in transit (TLS), hashed passwords, and secure cloud infrastructure. No method of transmission over the Internet is 100% secure, but we do our best.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold mb-3" style={{ color: '#fff' }}>6. Contact</h2>
            <p>For privacy questions: support@everlightventures.io</p>
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
