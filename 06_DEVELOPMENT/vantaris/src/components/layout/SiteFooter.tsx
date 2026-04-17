'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

/**
 * SiteFooter -- Shared footer for the entire Everlight Ventures site
 *
 * Hidden on in-game pages (blackjack, crash, etc.)
 */

const HIDDEN_ON = ['/play/blackjack', '/play/crash', '/play/dice', '/play/mines', '/play/plinko', '/play/roulette']

export function SiteFooter() {
  const pathname = usePathname()
  if (HIDDEN_ON.some(p => pathname?.startsWith(p))) return null

  return (
    <footer className="border-t py-12 px-6" style={{ background: 'var(--vanta-abyss)', borderColor: 'var(--vanta-border)' }}>
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-8">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <h3 className="text-lg font-bold tracking-widest mb-2"
              style={{ fontFamily: "'Cinzel', serif", background: 'linear-gradient(135deg, #c9a84c, #e8c55a)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              EVERLIGHT
            </h3>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
              Innovation meets opportunity.
              <br />Fairfield, California
            </p>
          </div>

          {/* Casino */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--gold)' }}>Casino</h4>
            <div className="space-y-1.5">
              {[
                { label: 'Lobby', href: '/lobby' },
                { label: 'Blackjack', href: '/play/blackjack' },
                { label: 'Rewards', href: '/rewards' },
                { label: 'Wallet', href: '/wallet' },
                { label: 'Redeem', href: '/redeem' },
              ].map(link => (
                <Link key={link.href} href={link.href} className="block text-xs transition-colors hover:text-white" style={{ color: 'var(--text-tertiary)' }}>
                  {link.label}
                </Link>
              ))}
            </div>
          </div>

          {/* Products */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--gold)' }}>Products</h4>
            <div className="space-y-1.5">
              {[
                { label: 'Alley Kingz', href: '/alley-kingz' },
                { label: 'Onyx POS', href: '/onyx' },
                { label: 'Hive Mind AI', href: '/hivemind' },
                { label: 'HIM Loadout', href: '/him-loadout' },
              ].map(link => (
                <Link key={link.href} href={link.href} className="block text-xs transition-colors hover:text-white" style={{ color: 'var(--text-tertiary)' }}>
                  {link.label}
                </Link>
              ))}
            </div>
          </div>

          {/* Publishing */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--gold)' }}>Publishing</h4>
            <div className="space-y-1.5">
              {[
                { label: 'All Books', href: '/publishing' },
                { label: 'Beyond the Veil', href: '/beyond-the-veil' },
                { label: 'Sam & Robo', href: '/sam-and-robo' },
              ].map(link => (
                <Link key={link.href} href={link.href} className="block text-xs transition-colors hover:text-white" style={{ color: 'var(--text-tertiary)' }}>
                  {link.label}
                </Link>
              ))}
            </div>
          </div>

          {/* Legal */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--gold)' }}>Legal</h4>
            <div className="space-y-1.5">
              {[
                { label: 'Sweepstakes Rules', href: '/rules' },
                { label: 'Provably Fair', href: '/fairness' },
                { label: 'Support', href: '/support' },
                { label: 'Settings', href: '/settings' },
              ].map(link => (
                <Link key={link.href} href={link.href} className="block text-xs transition-colors hover:text-white" style={{ color: 'var(--text-tertiary)' }}>
                  {link.label}
                </Link>
              ))}
            </div>
          </div>
        </div>

        <div className="border-t pt-6 flex flex-col md:flex-row items-center justify-between gap-4" style={{ borderColor: 'var(--vanta-border)' }}>
          <p className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
            &copy; {new Date().getFullYear()} Everlight Ventures LLC. All rights reserved. 18+ only. Play responsibly.
          </p>
          <p className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
            Fairfield, California &middot; support@everlightventures.io
          </p>
        </div>
      </div>
    </footer>
  )
}
