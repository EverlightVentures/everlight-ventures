'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

const BOOKS = [
  {
    title: 'Beyond the Veil',
    series: 'Standalone Thriller',
    desc: 'A gripping supernatural thriller that explores the thin boundary between the living and the dead. When a skeptical detective is forced to investigate a series of impossible murders, he discovers that the veil between worlds is thinner than anyone imagined.',
    color: '#9b59b6',
    href: '/beyond-the-veil',
    status: 'AVAILABLE',
  },
  {
    title: 'Sam & Robo',
    series: "Children's Series",
    desc: "A heartwarming children's series about a young boy named Sam and his AI robot best friend Robo. Together they learn about friendship, technology, and what it means to be human. Perfect for ages 4-8.",
    color: '#58a6ff',
    href: '/sam-and-robo',
    status: 'SERIES',
  },
  {
    title: 'The Streets Within',
    series: 'Urban Fiction',
    desc: 'Raw, unfiltered urban fiction. Stories from the streets that shaped us. Coming to Amazon KDP.',
    color: '#ff6b35',
    href: '#',
    status: 'COMING SOON',
  },
]

export default function PublishingPage() {
  return (
    <main className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>

      <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger}>
          <motion.p variants={fadeUp} className="text-xs uppercase tracking-widest mb-4" style={{ color: '#e91e63', letterSpacing: '4px' }}>
            EVERLIGHT LITERATURE
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-5xl md:text-7xl font-bold"
            style={{ fontFamily: "'Playfair Display', serif", background: 'linear-gradient(135deg, #e91e63, #ff6b8a, #e91e63)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Publishing
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-4 text-xl max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
            Independent books for independent minds. From supernatural thrillers to children's stories. Available on Amazon KDP and direct.
          </motion.p>
        </motion.div>
      </section>

      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-4xl mx-auto">
          <div className="space-y-6">
            {BOOKS.map(book => (
              <motion.div key={book.title} variants={fadeUp}>
                <Link href={book.href}>
                  <motion.div className="p-8 rounded-2xl cursor-pointer"
                    style={{ background: `${book.color}06`, border: `1px solid ${book.color}20` }}
                    whileHover={{ borderColor: `${book.color}40`, boxShadow: `0 0 30px ${book.color}10` }}>
                    <div className="flex items-start justify-between flex-wrap gap-4">
                      <div>
                        <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full" style={{ background: `${book.color}15`, color: book.color }}>{book.status}</span>
                        <h3 className="text-xl font-bold mt-3 mb-1" style={{ fontFamily: "'Playfair Display', serif", color: book.color }}>{book.title}</h3>
                        <p className="text-xs uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>{book.series}</p>
                        <p className="text-sm leading-relaxed max-w-xl" style={{ color: 'var(--text-secondary)' }}>{book.desc}</p>
                      </div>
                    </div>
                  </motion.div>
                </Link>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <section className="py-20 px-6 text-center">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger}>
          <motion.p variants={fadeUp} className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
            Everlight Literature -- a division of Everlight Ventures LLC
          </motion.p>
          <motion.p variants={fadeUp} className="mt-2 text-sm" style={{ color: 'var(--text-tertiary)' }}>
            Available on Amazon Kindle, paperback, and hardcover.
          </motion.p>
        </motion.div>
      </section>
    </main>
  )
}
