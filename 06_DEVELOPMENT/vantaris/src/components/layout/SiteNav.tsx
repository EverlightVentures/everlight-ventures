'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const NAV_ITEMS = [
  { label: 'Publishing', href: '/publishing' },
  { label: 'Casino', href: '/vantaris' },
  { label: 'Onyx', href: '/onyx' },
  { label: 'Hive Mind', href: '/hivemind' },
  { label: 'HIM Loadout', href: '/him-loadout' },
  { label: 'Logistics', href: '/logistics' },
  { label: 'We Buy Houses', href: '/sell' },
]

// Hide nav on game pages (games have their own HUD)
const HIDDEN_ON = ['/play/blackjack', '/play/crash', '/play/dice', '/play/mines', '/play/plinko', '/play/roulette']

export function SiteNav() {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)

  if (HIDDEN_ON.some(p => pathname?.startsWith(p))) return null

  return (
    <nav className="sticky top-0 z-50 border-b"
      style={{ background: 'rgba(10,10,10,0.95)', backdropFilter: 'blur(12px)', borderColor: '#2A2A2A' }}>
      <div className="max-w-6xl mx-auto px-4 md:px-6">
        <div className="flex items-center justify-between h-14">

          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <span className="text-base font-bold tracking-widest"
              style={{ fontFamily: "'Cormorant Garamond', serif", color: '#D4AF37' }}>
              EVERLIGHT
            </span>
            <span className="text-[9px] uppercase tracking-wider hidden md:inline" style={{ color: '#8A8A8A' }}>Ventures</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            <Link href="/" className="px-3 py-2 text-xs tracking-wider rounded-lg transition-colors hover:bg-white/5"
              style={{ color: pathname === '/' ? '#D4AF37' : '#8A8A8A' }}>
              Home
            </Link>
            {NAV_ITEMS.map(item => (
              <Link key={item.label} href={item.href}
                className="px-3 py-2 text-xs tracking-wider rounded-lg transition-colors hover:bg-white/5"
                style={{ color: pathname === item.href ? '#D4AF37' : '#8A8A8A' }}>
                {item.label}
              </Link>
            ))}
          </div>

          {/* Mobile hamburger */}
          <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden text-lg px-2 py-1" style={{ color: '#8A8A8A' }}>
            {mobileOpen ? '\u2715' : '\u2630'}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="md:hidden overflow-hidden border-t"
            style={{ borderColor: '#2A2A2A', background: 'rgba(10,10,10,0.98)' }}>
            <div className="px-4 py-3 space-y-1">
              <Link href="/" onClick={() => setMobileOpen(false)}
                className="block py-2 text-sm" style={{ color: '#8A8A8A' }}>Home</Link>
              {NAV_ITEMS.map(item => (
                <Link key={item.label} href={item.href} onClick={() => setMobileOpen(false)}
                  className="block py-2 text-sm" style={{ color: '#8A8A8A' }}>
                  {item.label}
                </Link>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  )
}
