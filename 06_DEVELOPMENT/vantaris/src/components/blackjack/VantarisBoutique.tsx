'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'

/**
 * Vantaris Boutique (Cosmetics Store)
 *
 * Full-screen overlay panel. Replaces "Everlight Boutique".
 * Sells: Outfits, Auras, Card Backs, Table Felts, Titles, Accessories, Emotes, Frames
 * Currencies: Chips (GC) or Gems (legacy premium)
 *
 * In the Vantaris casino platform:
 * - GC = Gold Coins (play money, also sweepstakes GC)
 * - Gems = Legacy premium currency (from Stripe purchases)
 * - SC = Sweeps Coins (never used for cosmetics -- only for cash redemption)
 *
 * The boutique uses GC and Gems. SC is purely for the sweepstakes cashout flow.
 */

export interface CosmeticItem {
  id: string
  name: string
  category: 'outfit' | 'aura' | 'card_back' | 'table_felt' | 'title' | 'accessory' | 'emote' | 'frame' | 'dealer_skin'
  rarity: 'common' | 'rare' | 'epic' | 'legendary'
  priceChips: number
  priceGems: number
  rankRequired: string
  isVipOnly: boolean
  isLimited: boolean
  description: string
  visual: string // emoji or icon ref
  presenceScore?: number
}

// Full catalog (merged from Django seed_blackjack.py + FashionStore.tsx)
const CATALOG: CosmeticItem[] = [
  // OUTFITS
  { id: 'default_suit', name: 'Classic Suit', category: 'outfit', rarity: 'common', priceChips: 0, priceGems: 0, rankRequired: 'Bronze', isVipOnly: false, isLimited: false, description: 'The default look. Clean and classic.', visual: '\uD83D\uDC54', presenceScore: 1.0 },
  { id: 'gold_tux', name: 'Gold Tuxedo', category: 'outfit', rarity: 'rare', priceChips: 5000, priceGems: 0, rankRequired: 'Silver', isVipOnly: false, isLimited: false, description: 'A tuxedo that says you belong at the high roller table.', visual: '\uD83E\uDD35', presenceScore: 1.15 },
  { id: 'diamond_blazer', name: 'Diamond Blazer', category: 'outfit', rarity: 'epic', priceChips: 15000, priceGems: 0, rankRequired: 'Gold', isVipOnly: false, isLimited: false, description: 'Embedded with micro-crystals. Catches every light in the room.', visual: '\uD83D\uDC8E', presenceScore: 1.25 },
  { id: 'neon_suit', name: 'Neon Synthwave Suit', category: 'outfit', rarity: 'rare', priceChips: 0, priceGems: 50, rankRequired: 'Bronze', isVipOnly: false, isLimited: false, description: 'Retrowave vibes. Glows under the neon lights.', visual: '\uD83C\uDF1F', presenceScore: 1.20 },
  { id: 'royal_robe', name: 'Royal Robe', category: 'outfit', rarity: 'epic', priceChips: 0, priceGems: 120, rankRequired: 'Platinum', isVipOnly: false, isLimited: false, description: 'Fit for royalty. The velvet catches the candlelight.', visual: '\uD83D\uDC51', presenceScore: 1.35 },
  { id: 'legendary_drip', name: 'Legend Drip', category: 'outfit', rarity: 'legendary', priceChips: 0, priceGems: 300, rankRequired: 'Legend', isVipOnly: false, isLimited: true, description: 'The outfit that legends are made of. One of a kind.', visual: '\uD83D\uDD25', presenceScore: 1.50 },

  // AURAS
  { id: 'golden_glow', name: 'Golden Glow', category: 'aura', rarity: 'common', priceChips: 2000, priceGems: 0, rankRequired: 'Bronze', isVipOnly: false, isLimited: false, description: 'A warm golden aura. Subtle but commanding.', visual: '\u2728', presenceScore: 1.05 },
  { id: 'hologram_blue', name: 'Hologram Aura', category: 'aura', rarity: 'rare', priceChips: 0, priceGems: 40, rankRequired: 'Silver', isVipOnly: false, isLimited: false, description: 'Blue holographic shimmer. Future meets fortune.', visual: '\uD83D\uDCA0', presenceScore: 1.10 },
  { id: 'fire_aura', name: 'Fire Aura', category: 'aura', rarity: 'epic', priceChips: 0, priceGems: 80, rankRequired: 'Gold', isVipOnly: false, isLimited: false, description: 'Flames dance around your seat. Hot streak energy.', visual: '\uD83D\uDD25', presenceScore: 1.15 },
  { id: 'legend_aura', name: 'Legend Aura', category: 'aura', rarity: 'legendary', priceChips: 0, priceGems: 200, rankRequired: 'Legend', isVipOnly: false, isLimited: true, description: 'The cosmos swirls around you. Only legends wear this.', visual: '\uD83C\uDF0C', presenceScore: 1.25 },

  // CARD BACKS
  { id: 'card_dragon', name: 'Dragon Card Back', category: 'card_back', rarity: 'rare', priceChips: 3000, priceGems: 0, rankRequired: 'Bronze', isVipOnly: false, isLimited: false, description: 'Embossed dragon design. Fierce.', visual: '\uD83D\uDC32' },
  { id: 'card_gold', name: 'Gold Foil', category: 'card_back', rarity: 'epic', priceChips: 0, priceGems: 60, rankRequired: 'Gold', isVipOnly: false, isLimited: false, description: 'Pure gold foil finish. Every flip is luxurious.', visual: '\uD83E\uDD47' },
  { id: 'card_space', name: 'Deep Space', category: 'card_back', rarity: 'epic', priceChips: 0, priceGems: 75, rankRequired: 'Silver', isVipOnly: false, isLimited: false, description: 'Nebula and stars. The universe is in your cards.', visual: '\uD83C\uDF0C' },
  { id: 'card_vantaris', name: 'Vantaris Black', category: 'card_back', rarity: 'legendary', priceChips: 0, priceGems: 250, rankRequired: 'Diamond', isVipOnly: true, isLimited: true, description: 'Vantablack finish. The cards absorb all light.', visual: '\u2B1B' },

  // TABLE FELTS
  { id: 'felt_crimson', name: 'Crimson Felt', category: 'table_felt', rarity: 'rare', priceChips: 4000, priceGems: 0, rankRequired: 'Silver', isVipOnly: false, isLimited: false, description: 'Deep red felt. Casino royalty.', visual: '\uD83D\uDD34' },
  { id: 'felt_midnight', name: 'Midnight Blue', category: 'table_felt', rarity: 'epic', priceChips: 0, priceGems: 90, rankRequired: 'Gold', isVipOnly: false, isLimited: false, description: 'Navy felt with gold trim. The VIP experience.', visual: '\uD83D\uDD35' },
  { id: 'felt_legend', name: 'Legend Black', category: 'table_felt', rarity: 'legendary', priceChips: 0, priceGems: 250, rankRequired: 'Legend', isVipOnly: false, isLimited: true, description: 'Black felt with holographic trim. The final table.', visual: '\u26AB' },

  // ACCESSORIES
  { id: 'acc_sunglasses', name: 'Gold Aviators', category: 'accessory', rarity: 'common', priceChips: 1500, priceGems: 0, rankRequired: 'Bronze', isVipOnly: false, isLimited: false, description: 'Classic aviator sunglasses. Gold-rimmed.', visual: '\uD83D\uDD76' },
  { id: 'acc_cigar', name: 'Lucky Cigar', category: 'accessory', rarity: 'rare', priceChips: 0, priceGems: 30, rankRequired: 'Silver', isVipOnly: false, isLimited: false, description: 'A cigar for the winners. Unlit but distinguished.', visual: '\uD83D\uDEAC' },
  { id: 'acc_crown', name: 'Platinum Crown', category: 'accessory', rarity: 'epic', priceChips: 0, priceGems: 100, rankRequired: 'Platinum', isVipOnly: false, isLimited: false, description: 'A crown for the table. You earned it.', visual: '\uD83D\uDC51' },

  // TITLES
  { id: 'title_high_roller', name: 'High Roller', category: 'title', rarity: 'rare', priceChips: 0, priceGems: 0, rankRequired: 'Bronze', isVipOnly: false, isLimited: false, description: 'Win 10,000+ chips in one hand.', visual: '\uD83C\uDFB0' },
  { id: 'title_the_shark', name: 'The Shark', category: 'title', rarity: 'epic', priceChips: 0, priceGems: 0, rankRequired: 'Bronze', isVipOnly: false, isLimited: false, description: '60%+ win rate over 100 hands.', visual: '\uD83E\uDD88' },
  { id: 'title_casino_king', name: 'Casino King', category: 'title', rarity: 'legendary', priceChips: 0, priceGems: 0, rankRequired: 'Legend', isVipOnly: false, isLimited: false, description: 'Reach Legend rank.', visual: '\uD83D\uDC51' },

  // EMOTES
  { id: 'emote_fire', name: 'Fire', category: 'emote', rarity: 'common', priceChips: 0, priceGems: 0, rankRequired: 'Bronze', isVipOnly: false, isLimited: false, description: 'Express yourself.', visual: '\uD83D\uDD25' },
  { id: 'emote_crown', name: 'Crown', category: 'emote', rarity: 'rare', priceChips: 0, priceGems: 25, rankRequired: 'Gold', isVipOnly: false, isLimited: false, description: 'Crown energy. For big wins only.', visual: '\uD83D\uDC51' },
  { id: 'emote_money', name: 'Money', category: 'emote', rarity: 'rare', priceChips: 0, priceGems: 25, rankRequired: 'Bronze', isVipOnly: false, isLimited: false, description: 'Show them what you won.', visual: '\uD83D\uDCB0' },
  { id: 'emote_rocket', name: 'Rocket', category: 'emote', rarity: 'epic', priceChips: 0, priceGems: 100, rankRequired: 'Diamond', isVipOnly: false, isLimited: false, description: 'To the moon.', visual: '\uD83D\uDE80' },
]

const RARITY_COLORS: Record<string, string> = {
  common: '#8b8b9e',
  rare: '#1E90FF',
  epic: '#7C3AED',
  legendary: '#c9a84c',
}

const CATEGORY_LABELS: Record<string, string> = {
  all: 'All',
  outfit: 'Outfits',
  aura: 'Auras',
  card_back: 'Cards',
  table_felt: 'Tables',
  accessory: 'Accessories',
  title: 'Titles',
  emote: 'Emotes',
}

export function VantarisBoutique({
  isOpen,
  onClose,
  chips,
  gems,
  ownedItems,
  equippedItems,
  onPurchase,
  onEquip,
}: {
  isOpen: boolean
  onClose: () => void
  chips: number
  gems: number
  ownedItems: string[]
  equippedItems: Record<string, string>
  onPurchase: (item: CosmeticItem, currency: 'chips' | 'gems') => void
  onEquip: (item: CosmeticItem) => void
}) {
  const [filter, setFilter] = useState('all')
  const [confirmItem, setConfirmItem] = useState<CosmeticItem | null>(null)

  const filtered = filter === 'all'
    ? CATALOG
    : CATALOG.filter(i => i.category === filter)

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(12px)' }}
          onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
        >
          <motion.div
            initial={{ scale: 0.95, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, y: 20 }}
            className="w-full max-w-2xl max-h-[85vh] rounded-2xl overflow-hidden flex flex-col"
            style={{ background: 'var(--vanta-abyss)', border: '1px solid var(--vanta-border)' }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: 'var(--vanta-border)' }}>
              <div>
                <h2 className="font-display text-xl font-bold" style={{ color: 'var(--gold)' }}>
                  Vantaris Boutique
                </h2>
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  Customize your presence at the table.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1 px-2 py-1 rounded-full text-xs" style={{ background: 'var(--vanta-surface)', border: '1px solid var(--vanta-border)' }}>
                  <span>&#x1FA99;</span>
                  <span className="font-mono font-bold" style={{ color: 'var(--gold)' }}>{chips.toLocaleString()}</span>
                </div>
                <div className="flex items-center gap-1 px-2 py-1 rounded-full text-xs" style={{ background: 'var(--vanta-surface)', border: '1px solid var(--vanta-border)' }}>
                  <span>&#x1F48E;</span>
                  <span className="font-mono font-bold" style={{ color: '#58a6ff' }}>{gems}</span>
                </div>
                <button onClick={onClose} className="text-lg" style={{ color: 'var(--text-tertiary)' }}>&times;</button>
              </div>
            </div>

            {/* Filters */}
            <div className="flex gap-1 px-6 py-3 overflow-x-auto border-b" style={{ borderColor: 'var(--vanta-border)' }}>
              {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setFilter(key)}
                  className="text-xs px-3 py-1.5 rounded-full whitespace-nowrap transition-all"
                  style={{
                    background: filter === key ? 'var(--gold-glow)' : 'transparent',
                    color: filter === key ? 'var(--gold)' : 'var(--text-tertiary)',
                    border: `1px solid ${filter === key ? 'var(--gold)' : 'var(--vanta-border)'}`,
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Items grid */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {filtered.map((item) => {
                  const owned = ownedItems.includes(item.id)
                  const equipped = Object.values(equippedItems).includes(item.id)
                  const canAffordChips = item.priceChips > 0 && chips >= item.priceChips
                  const canAffordGems = item.priceGems > 0 && gems >= item.priceGems
                  const isFree = item.priceChips === 0 && item.priceGems === 0

                  return (
                    <motion.div
                      key={item.id}
                      className="rounded-xl p-3 relative cursor-pointer transition-all"
                      style={{
                        background: equipped ? `${RARITY_COLORS[item.rarity]}10` : 'var(--vanta-surface)',
                        border: `1px solid ${equipped ? RARITY_COLORS[item.rarity] + '40' : 'var(--vanta-border)'}`,
                      }}
                      whileHover={{ scale: 1.02, borderColor: RARITY_COLORS[item.rarity] + '60' }}
                      onClick={() => {
                        if (owned || isFree) onEquip(item)
                        else setConfirmItem(item)
                      }}
                    >
                      {/* Rarity badge */}
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[9px] uppercase tracking-wider font-semibold" style={{ color: RARITY_COLORS[item.rarity] }}>
                          {item.rarity}
                        </span>
                        {item.isLimited && (
                          <span className="text-[8px] px-1.5 py-0.5 rounded" style={{ background: '#ff2d5520', color: '#ff2d55' }}>LIMITED</span>
                        )}
                        {item.isVipOnly && (
                          <span className="text-[8px] px-1.5 py-0.5 rounded bg-yellow-500 text-black font-bold">VIP</span>
                        )}
                      </div>

                      {/* Visual */}
                      <div className="text-3xl text-center mb-2">{item.visual}</div>

                      {/* Name */}
                      <p className="text-xs font-semibold text-center truncate">{item.name}</p>

                      {/* Price / Status */}
                      <div className="text-center mt-2">
                        {equipped ? (
                          <span className="text-[10px] font-bold" style={{ color: 'var(--win)' }}>EQUIPPED</span>
                        ) : owned || isFree ? (
                          <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>Owned - Tap to equip</span>
                        ) : item.priceChips > 0 ? (
                          <span className="text-[10px] font-mono" style={{ color: canAffordChips ? 'var(--gold)' : 'var(--loss)' }}>
                            {item.priceChips.toLocaleString()} GC
                          </span>
                        ) : (
                          <span className="text-[10px] font-mono" style={{ color: canAffordGems ? '#58a6ff' : 'var(--loss)' }}>
                            {item.priceGems} Gems
                          </span>
                        )}
                      </div>

                      {/* Presence score */}
                      {item.presenceScore && item.presenceScore > 1.0 && (
                        <div className="text-center mt-1">
                          <span className="text-[9px] font-mono" style={{ color: 'var(--gold)' }}>
                            {item.presenceScore.toFixed(2)}x presence
                          </span>
                        </div>
                      )}
                    </motion.div>
                  )
                })}
              </div>
            </div>

            {/* Purchase confirmation */}
            <AnimatePresence>
              {confirmItem && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 20 }}
                  className="absolute bottom-0 left-0 right-0 p-6 glass-elevated rounded-t-2xl"
                >
                  <p className="text-sm font-semibold mb-1">Purchase {confirmItem.name}?</p>
                  <p className="text-xs mb-4" style={{ color: 'var(--text-tertiary)' }}>{confirmItem.description}</p>
                  <div className="flex gap-2">
                    {confirmItem.priceChips > 0 && (
                      <button
                        onClick={() => { onPurchase(confirmItem, 'chips'); setConfirmItem(null) }}
                        className="btn-primary px-6 py-2 text-xs"
                        disabled={chips < confirmItem.priceChips}
                      >
                        Buy for {confirmItem.priceChips.toLocaleString()} GC
                      </button>
                    )}
                    {confirmItem.priceGems > 0 && (
                      <button
                        onClick={() => { onPurchase(confirmItem, 'gems'); setConfirmItem(null) }}
                        className="px-6 py-2 text-xs rounded-xl font-semibold"
                        style={{ background: '#58a6ff20', color: '#58a6ff', border: '1px solid #58a6ff30' }}
                        disabled={gems < confirmItem.priceGems}
                      >
                        Buy for {confirmItem.priceGems} Gems
                      </button>
                    )}
                    <button
                      onClick={() => setConfirmItem(null)}
                      className="btn-ghost px-6 py-2 text-xs"
                    >
                      Cancel
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
