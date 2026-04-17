'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { PageHero } from '@/components/shared/PageHero'
import { GlassCard } from '@/components/shared/GlassCard'
import { SectionDivider } from '@/components/shared/SectionDivider'

const C = '#7B5EA7'

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.1 } } }

export default function PublishingPage() {
  return (
    <main className="min-h-screen" style={{ background: 'linear-gradient(180deg, #08080c 0%, #0c0c12 50%, #0a0a10 100%)' }}>

      <PageHero
        overline="Everlight Publishing"
        title="Stories Built to Last."
        description="We do not publish content. We finish books. Every title has a complete manuscript, professional illustrations, a full audiobook, and distribution-ready files."
        color={C} />

      <SectionDivider color={C} />

      {/* Everlight Kids */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: '#E8B84B' }}>Everlight Kids</motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl md:text-4xl font-bold mb-6" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
            Adventures with Sam & Robo
          </motion.h2>
          <motion.p variants={fadeUp} className="text-[15px] leading-[1.9] mb-8" style={{ color: '#999' }}>
            A curious boy. A robot with a heart. Five adventures that teach kids ages 3 to 8 how to read while teaching them how to think. Phonics-based. Interactive coloring hybrid. Two books in one.
          </motion.p>
          <motion.div variants={fadeUp}>
            <Link href="/sam-and-robo">
              <motion.button className="px-8 py-3 rounded-full text-xs font-semibold tracking-[0.2em] uppercase"
                style={{ border: `1px solid ${C}50`, color: C }}
                whileHover={{ background: `${C}10`, borderColor: `${C}80` }} whileTap={{ scale: 0.97 }}>
                View the Series
              </motion.button>
            </Link>
          </motion.div>
        </motion.div>
      </section>

      <SectionDivider color="#D4871C" />

      {/* Adult Fiction */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.p variants={fadeUp} className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: '#D4871C' }}>Adult Fiction</motion.p>

          <motion.div variants={fadeUp} className="mb-6">
            <GlassCard color="#D4871C"><div className="p-8">
              <span className="text-[9px] font-bold uppercase tracking-[0.15em] px-2 py-1 rounded-full inline-block mb-4" style={{ background: '#D4871C12', color: '#D4871C', border: '1px solid #D4871C20' }}>COMING 2026</span>
              <h3 className="text-2xl font-bold mb-1" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4871C' }}>Beyond the Veil</h3>
              <p className="text-[11px] uppercase tracking-[0.15em] mb-4" style={{ color: '#666' }}>The Hailey Pink Chronicles | Quantum Western Thriller</p>
              <p className="text-[14px] leading-[1.8] mb-4" style={{ color: '#999' }}>
                100,000 words. 11 chapters. Full audiobook. Hidden ciphers in every chapter. A deputy in a dying Western town who escapes through astral projection discovers something is following her between dimensions.
              </p>
              <p className="text-sm mb-4" style={{ color: '#eee' }}>Digital: $6.99</p>
              <Link href="/beyond-the-veil" className="text-[11px] font-semibold uppercase tracking-[0.15em]" style={{ color: '#D4871C' }}>Read More &rarr;</Link>
            </div></GlassCard>
          </motion.div>

          <motion.div variants={fadeUp}>
            <GlassCard color="#4A6FA5"><div className="p-8">
              <span className="text-[9px] font-bold uppercase tracking-[0.15em] px-2 py-1 rounded-full inline-block mb-4" style={{ background: '#4A6FA512', color: '#4A6FA5', border: '1px solid #4A6FA520' }}>IN DEVELOPMENT</span>
              <h3 className="text-2xl font-bold mb-1" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#4A6FA5' }}>The Silent Witness</h3>
              <p className="text-[11px] uppercase tracking-[0.15em] mb-4" style={{ color: '#666' }}>Detective Kiara Estrella | Mystery Thriller</p>
              <p className="text-[14px] leading-[1.8]" style={{ color: '#999' }}>
                A decorated Chicago homicide detective catches a case that leads to the most protected office in the city. Corruption, community, and the cost of doing what is right.
              </p>
            </div></GlassCard>
          </motion.div>
        </motion.div>
      </section>

      <SectionDivider color={C} />

      {/* For Educators */}
      <section className="py-20 px-6 text-center">
        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="max-w-xl mx-auto">
          <p className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>For Educators</p>
          <p className="text-[14px] leading-[1.8]" style={{ color: '#888' }}>
            Our children's books are built on the Science of Reading. Phonics progressions, decodable text, and vocabulary scaffolding woven into every story.
          </p>
        </motion.div>
      </section>
    </main>
  )
}
