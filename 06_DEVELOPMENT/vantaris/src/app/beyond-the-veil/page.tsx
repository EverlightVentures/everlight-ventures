'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { PageHero } from '@/components/shared/PageHero'
import { GlassCard } from '@/components/shared/GlassCard'
import { SectionDivider } from '@/components/shared/SectionDivider'
import { EmailCapture } from '@/components/shared/EmailCapture'
import { BOOKS, createCheckout, formatPrice } from '@/lib/stripe-products'

const C = '#D4871C'

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.1 } } }

export default function BeyondTheVeilPage() {
  return (
    <main className="min-h-screen" style={{ background: 'linear-gradient(180deg, #08080c 0%, #0c0c12 50%, #0a0a10 100%)' }}>

      <PageHero
        overline="Everlight Publishing"
        title="Beyond the Veil"
        subtitle="The Hailey Pink Chronicles"
        color={C}>
        <p className="mt-6 text-xl italic font-light" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#eee' }}>
          She escapes her bruises every night by leaving her body behind.
        </p>
      </PageHero>

      <SectionDivider color={C} />

      {/* Synopsis */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.div variants={fadeUp}>
            <GlassCard color={C} hover={false}><div className="p-8 md:p-10">
              <div className="space-y-5 text-[15px] leading-[1.9]" style={{ color: '#999' }}>
                <p>Deputy Hailey Pink is trapped in a dying Western town where the sheriff dismisses her warnings, and the man waiting for her at home speaks with his fists before his words. But when Hailey closes her eyes and sleeps, she flies. In the astral realm she is untouchable -- soaring over floating islands of liquid light, swimming ancient oceans alongside creatures older than memory.</p>
                <p>But something is following her there. A shadow. A presence. A dark and ancient rage that does not belong to this world, or any other she has ever known.</p>
                <p>The truth is stranger than any ghost story: the entity is not a monster. It is a man in another dimension who does not even know he is doing it. His unresolved anger, his consciousness leaking across the quantum web, poisoning her world like a slow and invisible plague.</p>
                <p style={{ color: '#ddd' }}>To stop him, Hailey will have to become something the frontier has never seen -- a warrior of the mind, a healer of broken dimensions, and a woman willing to pay the ultimate price.</p>
              </div>
              <p className="mt-6 text-lg italic" style={{ fontFamily: "'Cormorant Garamond', serif", color: C }}>
                "The real battle will be fought inside you."
              </p>
            </div></GlassCard>
          </motion.div>
        </motion.div>
      </section>

      <SectionDivider color={C} />

      {/* The World */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={stagger} className="max-w-4xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>The World</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-4xl font-bold mb-12" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            What makes this different.
          </motion.h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { title: 'QUANTUM WESTERN', desc: 'A genre that does not exist yet. The frontier meets the astral plane. Saloons and cosmic oceans. Deputy badges and interdimensional warfare.' },
              { title: 'CIPHER SYSTEM', desc: 'Hidden encrypted messages are woven into every chapter. Find the cipher. Decode the message. Unlock a layer most readers will never see.' },
              { title: 'DUAL DIMENSIONS', desc: 'The story operates in two worlds simultaneously. What happens in one bleeds into the other. The rules of physics bend at the boundary.' },
            ].map(w => (
              <motion.div key={w.title} variants={fadeUp}>
                <GlassCard color={C}><div className="p-7">
                  <h3 className="text-[11px] font-bold tracking-[0.15em] mb-3" style={{ color: C }}>{w.title}</h3>
                  <p className="text-[13px] leading-[1.8]" style={{ color: '#888' }}>{w.desc}</p>
                </div></GlassCard>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <SectionDivider color={C} />

      {/* Buy */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-md mx-auto text-center">
          <motion.div variants={fadeUp}>
            <GlassCard color={C} hover={false}><div className="p-10">
              <p className="text-[10px] uppercase tracking-[0.3em] mb-2" style={{ color: C }}>DIGITAL EDITION</p>
              <p className="text-xs mb-4" style={{ color: '#666' }}>100,000 words | 11 chapters | Full audiobook</p>
              <p className="text-4xl font-bold my-6" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
                {formatPrice(BOOKS.beyondTheVeil.amount)}
              </p>
              <motion.button
                onClick={() => createCheckout(BOOKS.beyondTheVeil.priceId)}
                className="px-8 py-3 rounded-full text-xs font-semibold tracking-[0.2em] uppercase"
                style={{ background: C, color: '#0A0A0A' }}
                whileHover={{ scale: 1.03, boxShadow: `0 0 30px ${C}30` }}
                whileTap={{ scale: 0.97 }}>
                Buy Digital (EPUB)
              </motion.button>
            </div></GlassCard>
          </motion.div>

          <motion.div variants={fadeUp} className="mt-8">
            <p className="text-sm mb-4" style={{ color: '#666' }}>Or join the waitlist for print + audiobook bundle.</p>
            <EmailCapture source="consulting" color={C} buttonText="JOIN WAITLIST" successTitle="You're on the list." successDesc="We'll notify you at launch." />
          </motion.div>

          <motion.div variants={fadeUp} className="mt-8">
            <Link href="/publishing" className="text-[11px] tracking-[0.15em]" style={{ color: '#555' }}>&larr; Back to Publishing</Link>
          </motion.div>
        </motion.div>
      </section>
    </main>
  )
}
