'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'

/**
 * Gem Store -- Premium Currency Purchase
 *
 * Gems are the legacy premium currency from the Everlight era.
 * In the Vantaris platform, Gems still exist for cosmetic purchases.
 * GC (Gold Coins) = sweepstakes play currency
 * SC (Sweeps Coins) = redeemable cash currency
 * Gems = cosmetics-only premium currency (Stripe)
 *
 * Gem packages include bonus GC and free SC (sweepstakes compliance).
 */

const GEM_PACKAGES = [
  { id: 'starter', name: 'Starter', gems: 100, bonusGems: 0, bonusGC: 500, bonusSC: 0.50, price: 0.99, featured: false },
  { id: 'player', name: 'Player', gems: 500, bonusGems: 100, bonusGC: 2500, bonusSC: 2.50, price: 4.99, featured: false },
  { id: 'high_roller', name: 'High Roller', gems: 1200, bonusGems: 300, bonusGC: 5000, bonusSC: 5.00, price: 9.99, featured: true },
  { id: 'vip', name: 'VIP Bundle', gems: 3000, bonusGems: 1000, bonusGC: 15000, bonusSC: 15.00, price: 24.99, featured: false },
  { id: 'whale', name: 'Casino Boss', gems: 7000, bonusGems: 3000, bonusGC: 50000, bonusSC: 55.00, price: 49.99, featured: false },
]

export function GemStore({
  isOpen,
  onClose,
  currentGems,
  onPurchase,
}: {
  isOpen: boolean
  onClose: () => void
  currentGems: number
  onPurchase: (packageId: string) => void
}) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(16px)' }}
          onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
        >
          <motion.div
            initial={{ scale: 0.95, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, y: 20 }}
            className="w-full max-w-lg rounded-2xl overflow-hidden"
            style={{ background: 'var(--vanta-abyss)', border: '1px solid var(--vanta-border)' }}
          >
            {/* Header */}
            <div className="px-6 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--vanta-border)' }}>
              <div>
                <h2 className="font-display text-xl font-bold" style={{ color: '#58a6ff' }}>
                  Gem Store
                </h2>
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  Premium currency for cosmetics + bonus Gold Coins
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 px-2 py-1 rounded-full text-xs" style={{ background: 'var(--vanta-surface)', border: '1px solid var(--vanta-border)' }}>
                  <span>&#x1F48E;</span>
                  <span className="font-mono font-bold" style={{ color: '#58a6ff' }}>{currentGems}</span>
                </div>
                <button onClick={onClose} className="text-lg" style={{ color: 'var(--text-tertiary)' }}>&times;</button>
              </div>
            </div>

            {/* Packages */}
            <div className="p-4 space-y-3 max-h-[60vh] overflow-y-auto">
              {GEM_PACKAGES.map((pkg) => (
                <motion.div
                  key={pkg.id}
                  className="rounded-xl p-4 flex items-center justify-between relative overflow-hidden"
                  style={{
                    background: pkg.featured ? 'linear-gradient(135deg, rgba(201,168,76,0.08), rgba(201,168,76,0.02))' : 'var(--vanta-surface)',
                    border: `1px solid ${pkg.featured ? 'rgba(201,168,76,0.3)' : 'var(--vanta-border)'}`,
                  }}
                  whileHover={{ borderColor: 'rgba(88,166,255,0.3)' }}
                >
                  {pkg.featured && (
                    <div className="absolute top-0 right-0 text-[8px] px-2 py-0.5 font-bold"
                      style={{ background: 'var(--gold)', color: 'var(--vanta-void)', borderBottomLeftRadius: '8px' }}>
                      BEST VALUE
                    </div>
                  )}

                  <div>
                    <p className="text-sm font-semibold">{pkg.name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs font-mono" style={{ color: '#58a6ff' }}>
                        {(pkg.gems + pkg.bonusGems).toLocaleString()} Gems
                      </span>
                      {pkg.bonusGems > 0 && (
                        <span className="text-[9px] px-1 rounded" style={{ background: '#58a6ff15', color: '#58a6ff' }}>
                          +{pkg.bonusGems} bonus
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] font-mono" style={{ color: 'var(--gold)' }}>
                        +{pkg.bonusGC.toLocaleString()} GC
                      </span>
                      <span className="text-[10px] font-mono" style={{ color: 'var(--win)' }}>
                        +{pkg.bonusSC} FREE SC
                      </span>
                    </div>
                  </div>

                  <motion.button
                    onClick={() => onPurchase(pkg.id)}
                    className="px-4 py-2 rounded-xl text-sm font-bold"
                    style={{
                      background: pkg.featured ? 'var(--gold-gradient)' : 'var(--vanta-elevated)',
                      color: pkg.featured ? 'var(--vanta-void)' : 'var(--text-primary)',
                      border: pkg.featured ? 'none' : '1px solid var(--vanta-border)',
                    }}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    ${pkg.price.toFixed(2)}
                  </motion.button>
                </motion.div>
              ))}
            </div>

            {/* Footer */}
            <div className="px-6 py-3 border-t text-center" style={{ borderColor: 'var(--vanta-border)' }}>
              <p className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                Gems are for cosmetic purchases only. SC are free and redeemable for cash prizes.
                Gold Coins have no cash value.
              </p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
