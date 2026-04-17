'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } },
}
const stagger = { visible: { transition: { staggerChildren: 0.12 } } }

export default function BeyondTheVeilPage() {
  return (
    <main className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>

      <section className="min-h-[80vh] flex flex-col items-center justify-center px-6 text-center">
        <motion.div initial="hidden" animate="visible" variants={stagger} className="max-w-3xl">
          <motion.p variants={fadeUp} className="text-xs uppercase tracking-widest mb-4" style={{ color: '#9b59b6', letterSpacing: '4px' }}>
            EVERLIGHT LITERATURE
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-5xl md:text-7xl font-bold"
            style={{ fontFamily: "'Playfair Display', serif", background: 'linear-gradient(135deg, #9b59b6, #c39bd3, #9b59b6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Beyond the Veil
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-2 text-sm uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
            A Supernatural Thriller
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 p-8 rounded-2xl text-left" style={{ background: 'rgba(155,89,182,0.05)', border: '1px solid rgba(155,89,182,0.15)' }}>
            <p className="text-base leading-relaxed italic" style={{ color: 'var(--text-secondary)', fontFamily: "'Playfair Display', serif" }}>
              Detective Marcus Cole doesn't believe in ghosts. He believes in evidence, procedure, and closing cases. But when a string of impossible murders rocks his city -- victims found dead in locked rooms, security cameras showing empty hallways, witnesses describing shadows that move against the light -- Marcus is forced to confront something his training never prepared him for.
            </p>
            <p className="text-base leading-relaxed italic mt-4" style={{ color: 'var(--text-secondary)', fontFamily: "'Playfair Display', serif" }}>
              The veil between the living and the dead is thinner than anyone imagined. And something on the other side wants to come through.
            </p>
          </motion.div>
          <motion.div variants={fadeUp} className="mt-8 flex gap-4 justify-center flex-wrap">
            <a href="https://www.amazon.com/s?k=beyond+the+veil+everlight+ventures" target="_blank" rel="noopener noreferrer">
              <motion.button className="px-8 py-3 rounded-xl text-sm font-bold tracking-widest"
                style={{ background: 'linear-gradient(135deg, #9b59b6, #c39bd3)', color: '#000', fontFamily: "'Cinzel', serif" }}
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

      <section className="py-20 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={stagger} className="max-w-3xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { label: 'Genre', value: 'Supernatural Thriller' },
              { label: 'Pages', value: '320' },
              { label: 'Format', value: 'Kindle, Paperback, Hardcover' },
            ].map(d => (
              <motion.div key={d.label} variants={fadeUp} className="p-4 rounded-xl text-center" style={{ background: 'rgba(155,89,182,0.05)', border: '1px solid rgba(155,89,182,0.15)' }}>
                <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>{d.label}</p>
                <p className="text-sm font-bold mt-1" style={{ color: '#9b59b6' }}>{d.value}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>
    </main>
  )
}
