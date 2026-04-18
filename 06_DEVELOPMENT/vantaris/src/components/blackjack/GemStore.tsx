'use client'

import { motion, AnimatePresence } from 'framer-motion'

/**
 * Vantaris Casino Shop -- Chip & Gem Packages
 *
 * Competitive pricing based on Chumba, Stake.us, WOW Vegas, Pulsz.
 * Industry standard: $9.99 is the best first-purchase hook (60-70% off),
 * higher tiers give progressively better "bonus" percentages.
 *
 * Pricing strategy:
 * - Show "original" crossed-out price to create urgency
 * - Highlight bonus % ("200% BONUS!")
 * - "BEST VALUE" and "MOST POPULAR" badges
 * - First-purchase welcome offer at deep discount
 * - $0.99 starter to get card on file (low friction)
 */

interface ShopPackage {
  id: string
  slug: string           // Stripe slug (maps to PRICE_MAP)
  name: string
  chips: number          // Gold Coins received
  bonusChips: number     // Extra GC (shown as "bonus")
  gems: number           // Gems received
  price: number          // USD
  originalPrice: number  // "Was" price (crossed out)
  bonusPct: number       // "200% BONUS" badge
  badge: string | null   // "BEST VALUE", "MOST POPULAR", etc.
  featured: boolean
  color: string
}

const CHIP_PACKAGES: ShopPackage[] = [
  {
    id: 'starter', slug: 'chips-500',
    name: 'Starter Stack',
    chips: 2000, bonusChips: 3000, gems: 10,
    price: 0.99, originalPrice: 2.99, bonusPct: 250,
    badge: 'TRY IT', featured: false, color: '#27ae60',
  },
  {
    id: 'player', slug: 'chips-500',
    name: 'Player Pack',
    chips: 5000, bonusChips: 5000, gems: 25,
    price: 4.99, originalPrice: 9.99, bonusPct: 200,
    badge: null, featured: false, color: '#3498db',
  },
  {
    id: 'high_roller', slug: 'chips-3000',
    name: 'High Roller',
    chips: 15000, bonusChips: 15000, gems: 75,
    price: 9.99, originalPrice: 24.99, bonusPct: 200,
    badge: 'MOST POPULAR', featured: true, color: '#c9a84c',
  },
  {
    id: 'vip_bundle', slug: 'chips-3000',
    name: 'VIP Bundle',
    chips: 40000, bonusChips: 40000, gems: 200,
    price: 19.99, originalPrice: 49.99, bonusPct: 200,
    badge: 'BEST VALUE', featured: false, color: '#9b59b6',
  },
  {
    id: 'whale', slug: 'chips-8000',
    name: 'Casino Boss',
    chips: 100000, bonusChips: 150000, gems: 500,
    price: 49.99, originalPrice: 149.99, bonusPct: 250,
    badge: 'WHALE TIER', featured: false, color: '#e74c3c',
  },
  {
    id: 'mogul', slug: 'chips-8000',
    name: 'Mogul Package',
    chips: 250000, bonusChips: 500000, gems: 1500,
    price: 99.99, originalPrice: 299.99, bonusPct: 300,
    badge: 'ULTIMATE', featured: false, color: '#f39c12',
  },
]

const GEM_PACKAGES: ShopPackage[] = [
  {
    id: 'gem_starter', slug: 'gems-100',
    name: 'Gem Pouch',
    chips: 500, bonusChips: 0, gems: 100,
    price: 0.99, originalPrice: 1.99, bonusPct: 0,
    badge: null, featured: false, color: '#58a6ff',
  },
  {
    id: 'gem_case', slug: 'gems-600',
    name: 'Gem Case',
    chips: 2500, bonusChips: 0, gems: 600,
    price: 4.99, originalPrice: 8.99, bonusPct: 20,
    badge: null, featured: false, color: '#58a6ff',
  },
  {
    id: 'gem_vault', slug: 'gems-1500',
    name: 'Gem Vault',
    chips: 5000, bonusChips: 0, gems: 1500,
    price: 9.99, originalPrice: 19.99, bonusPct: 50,
    badge: 'POPULAR', featured: true, color: '#58a6ff',
  },
  {
    id: 'gem_treasury', slug: 'gems-4000',
    name: 'Gem Treasury',
    chips: 15000, bonusChips: 0, gems: 4000,
    price: 24.99, originalPrice: 49.99, bonusPct: 60,
    badge: 'BEST VALUE', featured: false, color: '#58a6ff',
  },
]

function PackageCard({ pkg, onPurchase }: { pkg: ShopPackage; onPurchase: (slug: string) => void }) {
  const discount = Math.round((1 - pkg.price / pkg.originalPrice) * 100)
  const totalChips = pkg.chips + pkg.bonusChips

  return (
    <motion.div
      className="rounded-xl p-3 relative overflow-hidden"
      style={{
        background: pkg.featured
          ? 'linear-gradient(135deg, rgba(201,168,76,0.08), rgba(201,168,76,0.02))'
          : 'rgba(255,255,255,0.02)',
        border: `1px solid ${pkg.featured ? 'rgba(201,168,76,0.3)' : 'rgba(255,255,255,0.06)'}`,
      }}
      whileHover={{ borderColor: pkg.color + '50', y: -1 }}
    >
      {/* Badge */}
      {pkg.badge && (
        <div className="absolute top-0 right-0 text-[7px] px-2 py-0.5 font-bold tracking-wider"
          style={{
            background: pkg.featured ? '#c9a84c' : pkg.color + '30',
            color: pkg.featured ? '#000' : pkg.color,
            borderBottomLeftRadius: 8,
          }}>
          {pkg.badge}
        </div>
      )}

      {/* Discount badge */}
      {discount > 0 && (
        <div className="absolute top-0 left-0 text-[7px] px-1.5 py-0.5 font-bold"
          style={{ background: '#e74c3c', color: '#fff', borderBottomRightRadius: 8 }}>
          -{discount}%
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-bold mb-0.5">{pkg.name}</p>

          {/* Chips amount */}
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-sm font-mono font-bold" style={{ color: '#c9a84c' }}>
              {totalChips.toLocaleString()} GC
            </span>
            {pkg.bonusChips > 0 && (
              <span className="text-[8px] px-1.5 py-0.5 rounded-full font-bold"
                style={{ background: '#27ae6020', color: '#27ae60' }}>
                +{pkg.bonusPct}% BONUS
              </span>
            )}
          </div>

          {/* Gems */}
          {pkg.gems > 0 && (
            <span className="text-[9px] font-mono" style={{ color: '#58a6ff' }}>
              +{pkg.gems.toLocaleString()} Gems
            </span>
          )}
        </div>

        {/* Price */}
        <div className="flex flex-col items-end gap-0.5 ml-2">
          <span className="text-[9px] line-through opacity-30">
            ${pkg.originalPrice.toFixed(2)}
          </span>
          <motion.button
            onClick={() => onPurchase(pkg.slug)}
            className="px-4 py-1.5 rounded-lg text-sm font-bold"
            style={{
              background: pkg.featured
                ? 'linear-gradient(135deg, #c9a84c, #e8c55a)'
                : `${pkg.color}20`,
              color: pkg.featured ? '#000' : pkg.color,
              border: pkg.featured ? 'none' : `1px solid ${pkg.color}30`,
            }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            ${pkg.price.toFixed(2)}
          </motion.button>
        </div>
      </div>
    </motion.div>
  )
}

export function GemStore({
  isOpen,
  onClose,
  currentGems,
  currentChips,
  onPurchase,
}: {
  isOpen: boolean
  onClose: () => void
  currentGems: number
  currentChips?: number
  onPurchase: (slug: string) => void
}) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-3"
          style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(16px)' }}
          onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
        >
          <motion.div
            initial={{ scale: 0.95, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, y: 20 }}
            className="w-full max-w-md rounded-2xl overflow-hidden"
            style={{ background: '#0a0a15', border: '1px solid rgba(201,168,76,0.15)' }}
          >
            {/* Header */}
            <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
              <div>
                <h2 className="text-base font-bold" style={{ fontFamily: "'Cinzel', serif", color: '#c9a84c' }}>
                  Vantaris Shop
                </h2>
                <p className="text-[9px] uppercase tracking-widest opacity-30">
                  Limited time bonus on all packages
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px]"
                  style={{ background: 'rgba(201,168,76,0.1)', border: '1px solid rgba(201,168,76,0.15)' }}>
                  <span style={{ color: '#c9a84c' }}>{(currentChips || 0).toLocaleString()} GC</span>
                </div>
                <div className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px]"
                  style={{ background: 'rgba(88,166,255,0.1)', border: '1px solid rgba(88,166,255,0.15)' }}>
                  <span style={{ color: '#58a6ff' }}>{currentGems} Gems</span>
                </div>
                <button onClick={onClose} className="text-lg opacity-30 hover:opacity-60">&times;</button>
              </div>
            </div>

            {/* Sale banner */}
            <div className="px-4 py-2 text-center" style={{ background: 'linear-gradient(135deg, rgba(231,76,60,0.1), rgba(201,168,76,0.05))' }}>
              <p className="text-[10px] font-bold tracking-wider" style={{ color: '#e74c3c' }}>
                GRAND OPENING SALE -- UP TO 300% BONUS ON ALL PACKAGES
              </p>
            </div>

            <div className="p-3 space-y-4 max-h-[55vh] overflow-y-auto">
              {/* Chip Packages */}
              <div>
                <p className="text-[9px] uppercase tracking-widest opacity-30 mb-2 px-1">Gold Coin Packages</p>
                <div className="space-y-2">
                  {CHIP_PACKAGES.map((pkg) => (
                    <PackageCard key={pkg.id} pkg={pkg} onPurchase={onPurchase} />
                  ))}
                </div>
              </div>

              {/* Gem Packages */}
              <div>
                <p className="text-[9px] uppercase tracking-widest opacity-30 mb-2 px-1">Gem Packages (Cosmetics + Bonus GC)</p>
                <div className="space-y-2">
                  {GEM_PACKAGES.map((pkg) => (
                    <PackageCard key={pkg.id} pkg={pkg} onPurchase={onPurchase} />
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t text-center" style={{ borderColor: 'rgba(255,255,255,0.04)' }}>
              <p className="text-[8px] opacity-20">
                Gold Coins (GC) are for entertainment only and have no cash value. Gems unlock cosmetic items.
                All purchases are final. Must be 18+.
              </p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
