'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { EmailCapture } from '@/components/shared/EmailCapture'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

export default function BeyondTheVeilPage() {
  return (
    <main className="min-h-screen" style={{ background: '#0A0A0A' }}>

      <section className="min-h-[80vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger} className="max-w-3xl">
          <motion.p variants={fadeUp} className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full inline-block mb-4" style={{ background: '#D4871C15', color: '#D4871C' }}>COMING 2026</motion.p>
          <motion.h1 variants={fadeUp} className="text-5xl md:text-7xl font-bold"
            style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4871C' }}>
            Beyond the Veil
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-2 text-sm uppercase tracking-wider" style={{ color: '#8A8A8A' }}>
            The Hailey Pink Chronicles
          </motion.p>
          <motion.p variants={fadeUp} className="mt-6 text-xl italic" style={{ color: '#E5E5E5', fontFamily: "'Cormorant Garamond', serif" }}>
            She escapes her bruises every night by leaving her body behind.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 p-8 rounded-xl text-left" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
            <p className="text-sm leading-relaxed" style={{ color: '#8A8A8A' }}>
              Deputy Hailey Pink is trapped in a dying Western town where the sheriff dismisses her warnings, and the man waiting for her at home speaks with his fists before his words. But when Hailey closes her eyes and sleeps, she flies. In the astral realm she is untouchable -- soaring over floating islands of liquid light, swimming ancient oceans alongside creatures older than memory.
            </p>
            <p className="text-sm leading-relaxed mt-4" style={{ color: '#8A8A8A' }}>
              But something is following her there. A shadow. A presence. A dark and ancient rage that does not belong to this world, or any other she has ever known.
            </p>
            <p className="text-sm leading-relaxed mt-4" style={{ color: '#8A8A8A' }}>
              The truth is stranger than any ghost story: the entity is not a monster. It is a man in another dimension who does not even know he is doing it. His unresolved anger, his consciousness leaking across the quantum web, poisoning her world like a slow and invisible plague.
            </p>
            <p className="text-sm leading-relaxed mt-4" style={{ color: '#E5E5E5' }}>
              To stop him, Hailey will have to become something the frontier has never seen -- a warrior of the mind, a healer of broken dimensions, and a woman willing to pay the ultimate price.
            </p>
            <p className="text-sm italic mt-4" style={{ color: '#D4871C' }}>
              "The real battle will be fought inside you."
            </p>
          </motion.div>
        </motion.div>
      </section>

      {/* The World */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-8" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4871C' }}>The World</motion.h2>
          <div className="space-y-4">
            {[
              { title: 'QUANTUM WESTERN', desc: 'A genre that does not exist yet. The frontier meets the astral plane. Saloons and cosmic oceans. Deputy badges and interdimensional warfare.' },
              { title: 'CIPHER SYSTEM', desc: 'Hidden encrypted messages are woven into every chapter. Find the cipher. Decode the message. Unlock a layer of the story most readers will never see.' },
              { title: 'DUAL DIMENSIONS', desc: 'The story operates in two worlds simultaneously. What happens in one bleeds into the other. The rules of physics bend at the boundary.' },
            ].map(w => (
              <motion.div key={w.title} variants={fadeUp} className="p-6 rounded-xl" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
                <h3 className="text-xs font-bold tracking-wider mb-2" style={{ color: '#D4871C' }}>{w.title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: '#8A8A8A' }}>{w.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Buy */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-md mx-auto text-center">
          <motion.p variants={fadeUp} className="text-lg font-bold" style={{ color: '#E5E5E5' }}>Digital: $6.99</motion.p>
          <motion.p variants={fadeUp} className="text-sm mt-4 mb-6" style={{ color: '#8A8A8A' }}>Or join the waitlist for the print edition and audiobook bundle.</motion.p>
          <motion.div variants={fadeUp}>
            <EmailCapture source="consulting" color="#D4871C" buttonText="JOIN WAITLIST" successTitle="You're on the list." successDesc="We'll notify you at launch." />
          </motion.div>
          <motion.div variants={fadeUp} className="mt-4">
            <Link href="/publishing" className="text-xs" style={{ color: '#8A8A8A' }}>
              &larr; Back to Publishing
            </Link>
          </motion.div>
        </motion.div>
      </section>
    </main>
  )
}
