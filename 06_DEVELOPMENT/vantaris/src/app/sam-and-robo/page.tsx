'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const BOOKS_IN_SERIES = [
  { title: 'Sam & Robo: First Friends', desc: 'Sam finds a broken robot in his garage and brings it to life. The beginning of a beautiful friendship.' },
  { title: 'Sam & Robo: The Big Adventure', desc: 'Sam and Robo explore the neighborhood and learn that the world is bigger than they thought.' },
  { title: 'Sam & Robo: Feelings Are Hard', desc: 'Robo tries to understand human emotions. Sam learns that being different is what makes you special.' },
]

export default function SamAndRoboPage() {
  return (
    <main className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>

      <section className="min-h-[80vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger} className="max-w-3xl">
          <motion.p variants={fadeUp} className="text-xs uppercase tracking-widest mb-4" style={{ color: '#58a6ff', letterSpacing: '4px' }}>
            EVERLIGHT LITERATURE
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-5xl md:text-7xl font-bold"
            style={{ fontFamily: "'Playfair Display', serif", background: 'linear-gradient(135deg, #58a6ff, #8ec5ff, #58a6ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Sam &amp; Robo
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-2 text-sm uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
            A Children's Book Series -- Ages 4-8
          </motion.p>
          <motion.p variants={fadeUp} className="mt-6 text-lg leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            A heartwarming series about a young boy named Sam and his AI robot best friend Robo. Together they learn about friendship, technology, kindness, and what it really means to be human.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 flex gap-4 justify-center flex-wrap">
            <a href="https://www.amazon.com/s?k=sam+and+robo+everlight" target="_blank" rel="noopener noreferrer">
              <motion.button className="px-8 py-3 rounded-xl text-sm font-bold tracking-widest"
                style={{ background: 'linear-gradient(135deg, #58a6ff, #8ec5ff)', color: '#000', fontFamily: "'Cinzel', serif" }}
                whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                READ ON AMAZON
              </motion.button>
            </a>
            <Link href="/publishing">
              <motion.button className="px-8 py-3 rounded-xl text-sm font-bold tracking-widest"
                style={{ background: 'rgba(255,255,255,0.06)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)' }}
                whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                ALL BOOKS
              </motion.button>
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* Books in series */}
      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <motion.h2 variants={fadeUp} className="text-2xl font-bold text-center mb-8" style={{ fontFamily: "'Playfair Display', serif", color: '#58a6ff' }}>
            Books in the Series
          </motion.h2>
          <div className="space-y-4">
            {BOOKS_IN_SERIES.map((b, i) => (
              <motion.div key={b.title} variants={fadeUp} className="p-6 rounded-2xl"
                style={{ background: 'rgba(88,166,255,0.05)', border: '1px solid rgba(88,166,255,0.15)' }}>
                <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Book {i + 1}</span>
                <h3 className="text-sm font-bold mt-1 mb-2" style={{ color: '#58a6ff', fontFamily: "'Playfair Display', serif" }}>{b.title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{b.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-2xl mx-auto text-center">
          <motion.h2 variants={fadeUp} className="text-xl font-bold mb-4" style={{ fontFamily: "'Playfair Display', serif", color: '#58a6ff' }}>
            For Parents
          </motion.h2>
          <motion.p variants={fadeUp} className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Sam &amp; Robo teaches kids about technology, empathy, and friendship in a way that feels natural. No screen time guilt -- these are real books with real illustrations. Each story is designed to spark conversation about what makes us human in an age of AI.
          </motion.p>
        </motion.div>
      </section>
    </main>
  )
}
