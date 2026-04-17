'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

/**
 * SiteNav -- Unified top navigation for the entire Everlight Ventures site
 *
 * Shows on all pages EXCEPT in-game pages (blackjack, crash, etc.)
 * where the game has its own HUD.
 *
 * Sections:
 * - Home / About
 * - Casino (Vantaris)
 * - Products (Alley Kingz, Onyx, Hive Mind)
 * - Publishing (Books)
 * - Services (Logistics, Wholesale)
 */

const NAV_ITEMS = [
  {
    label: 'Casino',
    href: '/lobby',
    children: [
      { label: 'Lobby', href: '/lobby' },
      { label: 'Blackjack', href: '/play/blackjack' },
      { label: 'Crash', href: '/play/crash' },
      { label: 'Rewards', href: '/rewards' },
      { label: 'Wallet', href: '/wallet' },
    ],
  },
  {
    label: 'Products',
    href: '/alley-kingz',
    children: [
      { label: 'Alley Kingz', href: '/alley-kingz' },
      { label: 'Onyx POS', href: '/onyx' },
      { label: 'Hive Mind AI', href: '/hivemind' },
      { label: 'HIM Loadout', href: '/him-loadout' },
    ],
  },
  {
    label: 'Publishing',
    href: '/publishing',
    children: [
      { label: 'All Books', href: '/publishing' },
      { label: 'Beyond the Veil', href: '/beyond-the-veil' },
      { label: 'Sam & Robo', href: '/sam-and-robo' },
    ],
  },
  {
    label: 'Services',
    href: '/logistics',
    children: [
      { label: 'Logistics', href: '/logistics' },
      { label: 'Wholesale', href: '/wholesale' },
      { label: 'AI Consulting', href: '/sell' },
    ],
  },
]

// Pages where the nav should be HIDDEN (games have their own HUD)
const HIDDEN_ON = ['/play/blackjack', '/play/crash', '/play/dice', '/play/mines', '/play/plinko', '/play/roulette']

export function SiteNav() {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [hoveredMenu, setHoveredMenu] = useState<string | null>(null)

  // Hide nav on game pages
  if (HIDDEN_ON.some(p => pathname?.startsWith(p))) return null

  return (
    <nav className="sticky top-0 z-50 border-b"
      style={{ background: 'rgba(4,4,10,0.95)', backdropFilter: 'blur(12px)', borderColor: 'var(--vanta-border)' }}>
      <div className="max-w-7xl mx-auto px-4 md:px-6">
        <div className="flex items-center justify-between h-14 md:h-16">

          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <span className="text-base md:text-lg font-bold tracking-widest"
              style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #c9a84c, #e8c55a)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              EVERLIGHT
            </span>
            <span className="text-[9px] uppercase tracking-wider hidden md:inline" style={{ color: 'var(--text-tertiary)' }}>Ventures</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            <Link href="/" className="px-3 py-2 text-xs uppercase tracking-wider rounded-lg transition-colors hover:bg-white/5"
              style={{ color: pathname === '/' ? 'var(--gold)' : 'var(--text-secondary)' }}>
              Home
            </Link>

            {NAV_ITEMS.map(item => (
              <div key={item.label} className="relative"
                onMouseEnter={() => setHoveredMenu(item.label)}
                onMouseLeave={() => setHoveredMenu(null)}>
                <Link href={item.href}
                  className="px-3 py-2 text-xs uppercase tracking-wider rounded-lg transition-colors hover:bg-white/5"
                  style={{ color: pathname?.startsWith(item.href) || item.children?.some(c => pathname === c.href) ? 'var(--gold)' : 'var(--text-secondary)' }}>
                  {item.label}
                </Link>

                {/* Dropdown */}
                <AnimatePresence>
                  {hoveredMenu === item.label && item.children && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      transition={{ duration: 0.15 }}
                      className="absolute top-full left-0 mt-1 py-2 rounded-xl min-w-[160px]"
                      style={{ background: 'rgba(10,10,20,0.97)', border: '1px solid var(--vanta-border)', backdropFilter: 'blur(12px)' }}>
                      {item.children.map(child => (
                        <Link key={child.href} href={child.href}
                          className="block px-4 py-2 text-xs transition-colors hover:bg-white/5"
                          style={{ color: pathname === child.href ? 'var(--gold)' : 'var(--text-secondary)' }}>
                          {child.label}
                        </Link>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}

            <Link href="/auth"
              className="ml-2 px-4 py-1.5 text-xs uppercase tracking-wider rounded-lg font-semibold"
              style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif" }}>
              Sign In
            </Link>
          </div>

          {/* Mobile hamburger */}
          <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden text-lg px-2 py-1" style={{ color: 'var(--text-secondary)' }}>
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
            style={{ borderColor: 'var(--vanta-border)', background: 'rgba(4,4,10,0.98)' }}>
            <div className="px-4 py-3 space-y-1">
              <Link href="/" onClick={() => setMobileOpen(false)}
                className="block py-2 text-sm" style={{ color: 'var(--text-secondary)' }}>Home</Link>
              {NAV_ITEMS.map(item => (
                <div key={item.label}>
                  <p className="text-[9px] uppercase tracking-wider mt-3 mb-1" style={{ color: 'var(--text-tertiary)' }}>{item.label}</p>
                  {item.children?.map(child => (
                    <Link key={child.href} href={child.href} onClick={() => setMobileOpen(false)}
                      className="block py-1.5 pl-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
                      {child.label}
                    </Link>
                  ))}
                </div>
              ))}
              <Link href="/auth" onClick={() => setMobileOpen(false)}
                className="block mt-3 py-2 text-center text-sm font-semibold rounded-lg"
                style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000' }}>
                Sign In
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  )
}
