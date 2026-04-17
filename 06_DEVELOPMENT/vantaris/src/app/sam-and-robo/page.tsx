'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { PageHero } from '@/components/shared/PageHero'
import { GlassCard } from '@/components/shared/GlassCard'
import { SectionDivider } from '@/components/shared/SectionDivider'
import { EmailCapture } from '@/components/shared/EmailCapture'
import { BOOKS, createCheckout, formatPrice } from '@/lib/stripe-products'

const C = '#E8B84B'

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.1 } } }

const BOOK_LIST = [
  { key: 'sam1' as const, num: 1, title: "Sam's First Superpower", theme: 'Emotional Intelligence', desc: 'Sam discovers a glowing book under an old oak tree. Out pops Robo -- a small robot with kind eyes. Together they learn that understanding your feelings is the first superpower.' },
  { key: 'sam2' as const, num: 2, title: "Sam's Second Superpower", theme: 'Science & Curiosity', desc: 'Sam and Robo explore a science lab full of wonders. They learn that curiosity is the engine that drives everything worth knowing.' },
  { key: 'sam3' as const, num: 3, title: "Sam's Third Superpower", theme: 'Problem Solving', desc: 'A challenge that looks impossible teaches Sam and Robo that breaking big problems into small steps is a superpower anyone can learn.' },
  { key: 'sam4' as const, num: 4, title: "Sam's Fourth Superpower", theme: 'Environmental Awareness', desc: 'Sam and Robo discover that taking care of the world around you is not just good -- it is necessary.' },
  { key: 'sam5' as const, num: 5, title: "Sam's Fifth Superpower", theme: 'Teamwork', desc: 'The greatest superpower of all is the one you share with others. Nobody builds anything worth building alone.' },
]

export default function SamAndRoboPage() {
  return (
    <main className="min-h-screen" style={{ background: 'linear-gradient(180deg, #08080c 0%, #0c0c12 50%, #0a0a10 100%)' }}>

      <PageHero
        overline="Everlight Kids"
        title="Sam & Robo"
        subtitle="Every word is a door. And every door is an adventure."
        description="Ages 3-8 | Phonics-Based | Interactive Coloring Hybrid | 5 Complete Books | Full Audiobooks | 60+ Illustrations"
        color={C} />

      <SectionDivider color={C} />

      {/* Books */}
      <section className="py-28 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.p variants={fadeUp} className="text-[15px] mb-12" style={{ color: '#999' }}>
            Five books. Five superpowers. Each complete with manuscript, 12 paired illustrations, full audiobook, EPUB, and KDP-ready files.
          </motion.p>

          <div className="space-y-4">
            {BOOK_LIST.map(b => (
              <motion.div key={b.key} variants={fadeUp}>
                <GlassCard color={C}><div className="p-7">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <span className="text-[10px] uppercase tracking-[0.2em]" style={{ color: '#666' }}>Book {b.num}</span>
                      <h3 className="text-base font-bold mt-1 mb-1" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>{b.title}</h3>
                      <p className="text-[10px] uppercase tracking-[0.15em] mb-3" style={{ color: '#5DAE72' }}>Theme: {b.theme}</p>
                      <p className="text-[13px] leading-[1.8]" style={{ color: '#888' }}>{b.desc}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-lg font-bold" style={{ color: '#f0f0f5' }}>{formatPrice(BOOKS[b.key].amount)}</p>
                      <motion.button
                        onClick={() => createCheckout(BOOKS[b.key].priceId)}
                        className="mt-2 px-4 py-2 rounded-full text-[10px] font-semibold tracking-[0.15em] uppercase"
                        style={{ border: `1px solid ${C}40`, color: C }}
                        whileHover={{ background: `${C}10`, borderColor: `${C}70` }}
                        whileTap={{ scale: 0.97 }}>
                        Buy Digital
                      </motion.button>
                    </div>
                  </div>
                </div></GlassCard>
              </motion.div>
            ))}
          </div>

          {/* Bundle */}
          <motion.div variants={fadeUp} className="mt-8">
            <GlassCard color={C} hover={false}><div className="p-8 text-center">
              <p className="text-[10px] uppercase tracking-[0.3em] mb-2" style={{ color: C }}>COMPLETE SERIES</p>
              <h3 className="text-xl font-bold" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>All 5 Adventures</h3>
              <p className="text-3xl font-bold my-4" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#f0f0f5' }}>
                {formatPrice(BOOKS.samBundle.amount)} <span className="text-sm font-light" style={{ color: '#666' }}>save $5</span>
              </p>
              <motion.button
                onClick={() => createCheckout(BOOKS.samBundle.priceId)}
                className="px-8 py-3 rounded-full text-xs font-semibold tracking-[0.2em] uppercase"
                style={{ background: C, color: '#0A0A0A' }}
                whileHover={{ scale: 1.03, boxShadow: `0 0 30px ${C}30` }}
                whileTap={{ scale: 0.97 }}>
                Buy the Bundle
              </motion.button>
            </div></GlassCard>
          </motion.div>
        </motion.div>
      </section>

      <SectionDivider color={C} />

      {/* For Parents */}
      <section className="py-20 px-6">
        <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="max-w-3xl mx-auto">
          <p className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>For Parents & Teachers</p>
          <div className="text-[14px] leading-[1.9] space-y-3" style={{ color: '#888' }}>
            <p>Each book introduces a new phonics progression. CVC words build to blends, digraphs, and fluency.</p>
            <p>Left page: B/W illustration for coloring. Right page: full color. Story time and activity time in one product.</p>
            <p>Aligned with the Science of Reading framework.</p>
          </div>
        </motion.div>
      </section>

      <SectionDivider color={C} />

      {/* Free Coloring Pages */}
      <section className="py-20 px-6 text-center">
        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
          <p className="text-[10px] uppercase tracking-[0.4em] font-medium mb-4" style={{ color: C }}>Free Download</p>
          <p className="text-sm mb-6" style={{ color: '#888' }}>Five free coloring pages -- one from each adventure.</p>
          <div className="max-w-md mx-auto">
            <EmailCapture source="consulting" color={C} buttonText="DOWNLOAD" successTitle="Check your email!" successDesc="5 free coloring pages incoming." />
          </div>
        </motion.div>
      </section>

      <section className="py-8 px-6 text-center">
        <Link href="/publishing" className="text-[11px] tracking-[0.15em]" style={{ color: '#555' }}>&larr; Back to Publishing</Link>
      </section>
    </main>
  )
}
