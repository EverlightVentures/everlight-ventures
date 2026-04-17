'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { EmailCapture } from '@/components/shared/EmailCapture'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const BOOKS = [
  { num: 1, title: "Sam's First Superpower", theme: 'Emotional Intelligence', desc: 'Sam discovers a glowing book under an old oak tree. Out pops Robo -- a small robot with kind eyes and a glowing display screen. Together they learn that understanding your feelings is the first superpower.' },
  { num: 2, title: "Sam's Second Superpower", theme: 'Science & Curiosity', desc: 'Sam and Robo explore a science lab full of wonders. They learn to ask questions, test ideas, and discover that curiosity is the engine that drives everything worth knowing.' },
  { num: 3, title: "Sam's Third Superpower", theme: 'Problem Solving', desc: 'A challenge that looks impossible teaches Sam and Robo that breaking big problems into small steps is a superpower anyone can learn.' },
  { num: 4, title: "Sam's Fourth Superpower", theme: 'Environmental Awareness', desc: 'Sam and Robo discover that taking care of the world around you is not just good -- it is necessary. Small actions, big impact.' },
  { num: 5, title: "Sam's Fifth Superpower", theme: 'Teamwork', desc: 'The greatest superpower of all is the one you share with others. Sam and Robo learn that nobody builds anything worth building alone.' },
]

export default function SamAndRoboPage() {
  return (
    <main className="min-h-screen" style={{ background: '#0A0A0A' }}>

      <section className="min-h-[60vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger} className="max-w-3xl">
          <motion.h1 variants={fadeUp} className="text-5xl md:text-7xl font-bold"
            style={{ fontFamily: "'Cormorant Garamond', serif", color: '#E8B84B' }}>
            SAM &amp; ROBO
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 text-xl italic" style={{ color: '#E5E5E5', fontFamily: "'Cormorant Garamond', serif" }}>
            Every word is a door. And every door is an adventure.
          </motion.p>
          <motion.p variants={fadeUp} className="mt-4 text-sm" style={{ color: '#8A8A8A' }}>
            Ages 3-8 | Phonics-Based | Interactive Coloring Hybrid | 5 Complete Books | Full Audiobooks | 60+ Illustrations
          </motion.p>
        </motion.div>
      </section>

      {/* Books */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.p variants={fadeUp} className="text-sm mb-8" style={{ color: '#8A8A8A' }}>
            Five books. Five superpowers. Each one complete with manuscript, 12 paired illustrations, full audiobook, EPUB, and KDP-ready files.
          </motion.p>
          <div className="space-y-4">
            {BOOKS.map(b => (
              <motion.div key={b.num} variants={fadeUp} className="p-6 rounded-xl" style={{ background: '#1A1A1A', border: '1px solid #2A2A2A' }}>
                <span className="text-[10px] uppercase tracking-wider" style={{ color: '#8A8A8A' }}>Book {b.num}</span>
                <h3 className="text-base font-bold mt-1 mb-1" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#E8B84B' }}>{b.title}</h3>
                <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: '#5DAE72' }}>Theme: {b.theme}</p>
                <p className="text-xs leading-relaxed mb-3" style={{ color: '#8A8A8A' }}>{b.desc}</p>
                <p className="text-xs" style={{ color: '#E5E5E5' }}>Digital: $6.99</p>
              </motion.div>
            ))}
          </div>

          {/* Bundle */}
          <motion.div variants={fadeUp} className="mt-6 p-6 rounded-xl text-center" style={{ background: '#E8B84B08', border: '1px solid #E8B84B20' }}>
            <h3 className="text-base font-bold" style={{ color: '#E8B84B', fontFamily: "'Cormorant Garamond', serif" }}>Complete Series Bundle</h3>
            <p className="text-xs mt-1" style={{ color: '#8A8A8A' }}>All 5 Adventures with Sam & Robo</p>
            <p className="text-2xl font-bold mt-2" style={{ color: '#E5E5E5' }}>$29.99 <span className="text-xs font-normal" style={{ color: '#8A8A8A' }}>(save $5)</span></p>
          </motion.div>
        </motion.div>
      </section>

      {/* For Parents */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-xl font-bold mb-4" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#E8B84B' }}>For Parents & Teachers</motion.h2>
          <motion.div variants={fadeUp} className="text-sm leading-relaxed space-y-2" style={{ color: '#8A8A8A' }}>
            <p>Each book introduces a new phonics progression. CVC words build to blends, digraphs, and fluency. Vocabulary is age-appropriate for ages 3-8.</p>
            <p>Left page: B/W illustration for coloring. Right page: same scene in full color. Story time and activity time in one product.</p>
            <p>Aligned with the Science of Reading framework.</p>
          </motion.div>
        </motion.div>
      </section>

      {/* Free Coloring Pages */}
      <section className="py-20 px-6 text-center">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger}>
          <motion.h2 variants={fadeUp} className="text-xl font-bold mb-2" style={{ fontFamily: "'Cormorant Garamond', serif", color: '#E8B84B' }}>Free Coloring Pages</motion.h2>
          <motion.p variants={fadeUp} className="text-sm mb-6" style={{ color: '#8A8A8A' }}>Five free coloring pages -- one from each adventure. Download as a lead magnet.</motion.p>
          <motion.div variants={fadeUp} className="max-w-md mx-auto">
            <EmailCapture source="consulting" color="#E8B84B" buttonText="DOWNLOAD" successTitle="Check your email!" successDesc="5 free coloring pages on the way." />
          </motion.div>
        </motion.div>
      </section>

      <section className="py-8 px-6 text-center">
        <Link href="/publishing" className="text-xs" style={{ color: '#8A8A8A' }}>&larr; Back to Publishing</Link>
      </section>
    </main>
  )
}
