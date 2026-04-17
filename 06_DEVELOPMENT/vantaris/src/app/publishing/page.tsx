'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

export default function PublishingPage() {
  return (
    <main className="min-h-screen" style={{ background: '#0A0A0A' }}>

      <section className="min-h-[60vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.h1 variants={fadeUp} className="text-4xl md:text-6xl font-bold"
            style={{ fontFamily: "'Cormorant Garamond', serif", color: '#7B5EA7' }}>
            EVERLIGHT PUBLISHING
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-2 text-lg" style={{ color: '#7B5EA7' }}>Stories Built to Last</motion.p>
          <motion.p variants={fadeUp} className="mt-4 text-sm max-w-2xl mx-auto leading-relaxed" style={{ color: '#8A8A8A' }}>
            We do not publish content. We finish books. Every title in this catalog has a complete manuscript, professional illustrations, a full audiobook, and distribution-ready files. Independent publishing done right.
          </motion.p>
        </motion.div>
      </section>

      {/* Everlight Kids */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-2" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#E8B84B' }}>Everlight Kids</motion.h2>
          <motion.p variants={fadeUp} className="text-sm mb-6" style={{ color: '#E5E5E5' }}>Adventures with Sam & Robo -- 5 Books Available Now</motion.p>
          <motion.p variants={fadeUp} className="text-sm leading-relaxed mb-4" style={{ color: '#8A8A8A' }}>
            A curious boy. A robot with a heart. Five adventures that teach kids ages 3 to 8 how to read while teaching them how to think. Each book follows a phonics progression built on the Science of Reading. Each one is an interactive coloring hybrid -- left page black and white for coloring, right page in full color. Two books in one.
          </motion.p>
          <motion.div variants={fadeUp} className="flex gap-3 flex-wrap">
            <Link href="/sam-and-robo">
              <motion.button className="px-6 py-2 rounded-lg text-xs font-bold tracking-wider" style={{ background: '#E8B84B', color: '#0A0A0A' }}
                whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                VIEW THE SERIES
              </motion.button>
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* Adult Fiction */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold mb-8" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4871C' }}>Adult Fiction</motion.h2>

          {/* Beyond the Veil */}
          <motion.div variants={fadeUp} className="p-6 rounded-xl mb-4" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
            <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full" style={{ background: '#D4871C15', color: '#D4871C' }}>COMING 2026</span>
            <h3 className="text-lg font-bold mt-3 mb-1" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4871C' }}>Beyond the Veil</h3>
            <p className="text-xs uppercase tracking-wider mb-3" style={{ color: '#8A8A8A' }}>The Hailey Pink Chronicles | A Quantum Western Thriller</p>
            <p className="text-sm leading-relaxed mb-3" style={{ color: '#8A8A8A' }}>
              100,000 words. 11 chapters. Full audiobook. Hidden ciphers woven into every chapter. A deputy in a dying Western town escapes her bruises every night by leaving her body behind. The astral realm is not a dream. The worlds are connected. And something is crossing over.
            </p>
            <p className="text-sm" style={{ color: '#E5E5E5' }}>Digital: $6.99</p>
            <Link href="/beyond-the-veil" className="text-xs font-semibold uppercase tracking-wider mt-2 inline-block" style={{ color: '#D4871C' }}>Read More &rarr;</Link>
          </motion.div>

          {/* The Silent Witness */}
          <motion.div variants={fadeUp} className="p-6 rounded-xl" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
            <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full" style={{ background: '#4A6FA515', color: '#4A6FA5' }}>IN DEVELOPMENT</span>
            <h3 className="text-lg font-bold mt-3 mb-1" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#4A6FA5' }}>The Silent Witness</h3>
            <p className="text-xs uppercase tracking-wider mb-3" style={{ color: '#8A8A8A' }}>A Detective Kiara Estrella Novel | A Mystery Thriller</p>
            <p className="text-sm leading-relaxed" style={{ color: '#8A8A8A' }}>
              A decorated Chicago homicide detective catches a case that leads straight to the most protected office in the city. Corruption, community, and the cost of doing what is right.
            </p>
          </motion.div>
        </motion.div>
      </section>

      {/* For Educators */}
      <section className="py-16 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto text-center">
          <motion.h2 variants={fadeUp} className="text-xl font-bold mb-4" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#7B5EA7' }}>For Educators</motion.h2>
          <motion.p variants={fadeUp} className="text-sm leading-relaxed" style={{ color: '#8A8A8A' }}>
            Our children's books are built on the Science of Reading. Phonics progressions, decodable text, and vocabulary scaffolding are woven directly into the stories. Download our Educator Guide for classroom use, lesson alignment, and discussion prompts.
          </motion.p>
        </motion.div>
      </section>
    </main>
  )
}
