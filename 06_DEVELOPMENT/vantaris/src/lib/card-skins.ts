/**
 * Vantaris Card Skin System
 *
 * TCG-level card customization applied to blackjack.
 * Nothing like this exists in any online casino.
 *
 * Three layers:
 * 1. DECK SKINS -- change how all cards look (theme)
 * 2. CARD RARITY -- individual cards have rarity tiers with visual effects
 * 3. CARD XP -- cards level up with use, gaining visual evolution
 *
 * Visual effects reference:
 * - Pokemon: holographic rainbow foil, full-art bleed, gold stamped
 * - Magic: mythic orange shimmer, foil sweep diagonal
 * - Yu-Gi-Oh: ghost rare (spectral white), starlight prismatic
 * - Gambit: kinetic energy charge, pink/magenta particle trails
 */

// ============================================================
// DECK SKINS (applied to entire deck)
// ============================================================

export interface DeckSkin {
  id: string
  name: string
  description: string
  // Card face styling
  cardBg: string           // background color/gradient
  cardBorder: string       // border color
  redSuitColor: string     // hearts/diamonds
  blackSuitColor: string   // spades/clubs
  rankFont: string         // font family for rank text
  faceCardStyle: 'standard' | 'illustrated' | 'minimal' | 'neon' | 'void'
  // Card back styling
  backBg: string           // back gradient
  backBorder: string
  backIcon: string         // center icon (unicode or svg ref)
  backIconColor: string
  // Effects
  dealTrail: string | null   // particle color on deal
  hoverGlow: string | null   // glow color on hover
  winBurst: string | null    // particle color on win
  // Meta
  rarity: 'common' | 'rare' | 'epic' | 'legendary'
  price: { gc: number; gems: number }
  unlockRequirement: string | null
}

export const DECK_SKINS: DeckSkin[] = [
  {
    id: 'classic',
    name: 'Classic',
    description: 'The standard deck. Clean and timeless.',
    cardBg: 'linear-gradient(160deg, #ffffff, #f8f6f0)',
    cardBorder: '#ddd',
    redSuitColor: '#c0392b',
    blackSuitColor: '#111111',
    rankFont: "'Cinzel', serif",
    faceCardStyle: 'standard',
    backBg: 'linear-gradient(135deg, #1a3a6b, #0d1f3c)',
    backBorder: '#c9a84c',
    backIcon: '\u2666',
    backIconColor: '#c9a84c',
    dealTrail: null,
    hoverGlow: null,
    winBurst: null,
    rarity: 'common',
    price: { gc: 0, gems: 0 },
    unlockRequirement: null,
  },
  {
    id: 'neon_noir',
    name: 'Neon Noir',
    description: 'Dark cards with electric neon suit outlines. The city never sleeps.',
    cardBg: 'linear-gradient(160deg, #0a0a0a, #1a1a2e)',
    cardBorder: '#333',
    redSuitColor: '#ff2d55',
    blackSuitColor: '#00e5ff',
    rankFont: "'JetBrains Mono', monospace",
    faceCardStyle: 'neon',
    backBg: 'linear-gradient(135deg, #0a0a1a, #1a0a2e)',
    backBorder: '#00e5ff',
    backIcon: '\u26A1',
    backIconColor: '#00e5ff',
    dealTrail: '#00e5ff',
    hoverGlow: '#ff2d55',
    winBurst: '#00e5ff',
    rarity: 'rare',
    price: { gc: 5000, gems: 0 },
    unlockRequirement: null,
  },
  {
    id: 'royal_court',
    name: 'Royal Court',
    description: 'Illustrated face cards with gold filigree borders. Fit for royalty.',
    cardBg: 'linear-gradient(160deg, #faf8f2, #f0ece0)',
    cardBorder: '#c9a84c',
    redSuitColor: '#8b0000',
    blackSuitColor: '#1a1a1a',
    rankFont: "'Playfair Display', serif",
    faceCardStyle: 'illustrated',
    backBg: 'linear-gradient(135deg, #2a1505, #1a0d08)',
    backBorder: '#c9a84c',
    backIcon: '\u2654',
    backIconColor: '#c9a84c',
    dealTrail: '#c9a84c',
    hoverGlow: '#c9a84c',
    winBurst: '#c9a84c',
    rarity: 'epic',
    price: { gc: 0, gems: 100 },
    unlockRequirement: null,
  },
  {
    id: 'voidwalker',
    name: 'Voidwalker',
    description: 'Minimalist geometry on pure darkness. The void stares back.',
    cardBg: 'linear-gradient(160deg, #0d0815, #050308)',
    cardBorder: '#6a5acd40',
    redSuitColor: '#9b59b6',
    blackSuitColor: '#6a5acd',
    rankFont: "'Inter', sans-serif",
    faceCardStyle: 'void',
    backBg: 'linear-gradient(135deg, #0d0815, #1a0a2e)',
    backBorder: '#6a5acd',
    backIcon: '\u25C8',
    backIconColor: '#6a5acd',
    dealTrail: '#6a5acd',
    hoverGlow: '#9b59b6',
    winBurst: '#6a5acd',
    rarity: 'epic',
    price: { gc: 0, gems: 150 },
    unlockRequirement: null,
  },
  {
    id: 'sakura',
    name: 'Sakura',
    description: 'Watercolor painted cards with cherry blossom pips. Wabi-sabi.',
    cardBg: 'linear-gradient(160deg, #fff5f5, #fce4ec)',
    cardBorder: '#e8a0b0',
    redSuitColor: '#c0392b',
    blackSuitColor: '#2c3e50',
    rankFont: "'Playfair Display', serif",
    faceCardStyle: 'illustrated',
    backBg: 'linear-gradient(135deg, #fce4ec, #f8bbd0)',
    backBorder: '#e8a0b0',
    backIcon: '\u2740',
    backIconColor: '#c0392b',
    dealTrail: '#f48fb1',
    hoverGlow: '#e8a0b0',
    winBurst: '#f48fb1',
    rarity: 'epic',
    price: { gc: 0, gems: 200 },
    unlockRequirement: null,
  },
  {
    id: 'vantaris_black',
    name: 'Vantaris Black',
    description: 'Cards that absorb light. The darkest deck ever made. Legend only.',
    cardBg: 'linear-gradient(160deg, #050507, #0a0a10)',
    cardBorder: '#c9a84c30',
    redSuitColor: '#c9a84c',
    blackSuitColor: '#c9a84c',
    rankFont: "'Cinzel', serif",
    faceCardStyle: 'minimal',
    backBg: 'linear-gradient(135deg, #020203, #050507)',
    backBorder: '#c9a84c',
    backIcon: '\u2605',
    backIconColor: '#c9a84c',
    dealTrail: '#c9a84c',
    hoverGlow: '#c9a84c',
    winBurst: '#c9a84c',
    rarity: 'legendary',
    price: { gc: 0, gems: 0 },
    unlockRequirement: 'Legend rank',
  },
  {
    id: 'gambit',
    name: 'Gambit',
    description: 'Kinetic energy charges every card. Pink fire on every play.',
    cardBg: 'linear-gradient(160deg, #1a0515, #0d020a)',
    cardBorder: '#ff2d7740',
    redSuitColor: '#ff2d77',
    blackSuitColor: '#cc1166',
    rankFont: "'Cinzel', serif",
    faceCardStyle: 'neon',
    backBg: 'linear-gradient(135deg, #2a0520, #1a0315)',
    backBorder: '#ff2d77',
    backIcon: '\u2660',
    backIconColor: '#ff2d77',
    dealTrail: '#ff2d77',
    hoverGlow: '#ff69b4',
    winBurst: '#ff2d77',
    rarity: 'legendary',
    price: { gc: 0, gems: 0 },
    unlockRequirement: 'Legendary drop only',
  },
]

// ============================================================
// CARD RARITY SYSTEM
// ============================================================

export interface CardRarityEffect {
  tier: 'common' | 'uncommon' | 'rare' | 'mythic' | 'legendary'
  name: string
  // CSS effects applied to the card element
  borderEffect: string | null        // border animation
  shimmerEffect: string | null       // shimmer/foil overlay
  glowEffect: string | null          // outer glow
  particleColor: string | null       // ambient particles around card
  soundOnDeal: string | null         // audio cue
  // Animation configs
  shimmerSpeed: number               // seconds per shimmer cycle
  shimmerAngle: number               // degrees
}

export const CARD_RARITY_EFFECTS: CardRarityEffect[] = [
  {
    tier: 'common',
    name: 'Standard',
    borderEffect: null,
    shimmerEffect: null,
    glowEffect: null,
    particleColor: null,
    soundOnDeal: null,
    shimmerSpeed: 0,
    shimmerAngle: 0,
  },
  {
    tier: 'uncommon',
    name: 'Silver Foil',
    borderEffect: 'silver_pulse',    // silver border fades in/out
    shimmerEffect: null,
    glowEffect: '0 0 8px rgba(192,192,192,0.3)',
    particleColor: null,
    soundOnDeal: null,
    shimmerSpeed: 3,
    shimmerAngle: 0,
  },
  {
    tier: 'rare',
    name: 'Gold Press',
    borderEffect: 'gold_pulse',      // gold border breathing
    shimmerEffect: 'diagonal_sweep', // diagonal light sweep across card face
    glowEffect: '0 0 12px rgba(201,168,76,0.3)',
    particleColor: '#c9a84c',
    soundOnDeal: 'metallic_clink',
    shimmerSpeed: 4,
    shimmerAngle: 135,
  },
  {
    tier: 'mythic',
    name: 'Prismatic',
    borderEffect: 'rainbow_cycle',   // border color cycles through spectrum
    shimmerEffect: 'holographic',    // rainbow holographic overlay (tilt-reactive)
    glowEffect: '0 0 20px rgba(201,168,76,0.4)',
    particleColor: '#e8c55a',
    soundOnDeal: 'crystal_chime',
    shimmerSpeed: 3,
    shimmerAngle: 45,
  },
  {
    tier: 'legendary',
    name: 'Celestial',
    borderEffect: 'fire_edges',      // edges emit soft fire particles
    shimmerEffect: 'full_spectrum',   // entire card shifts through spectrum on movement
    glowEffect: '0 0 30px rgba(201,168,76,0.5), 0 0 60px rgba(201,168,76,0.2)',
    particleColor: '#fff',
    soundOnDeal: 'epic_reveal',
    shimmerSpeed: 2,
    shimmerAngle: 0,
  },
]

// ============================================================
// CARD XP SYSTEM
// ============================================================

export interface CardXPLevel {
  level: number
  name: string
  xpRequired: number
  // Visual evolution
  glowColor: string | null
  glowIntensity: number
  particleTrail: boolean
  borderTreatment: string | null
}

export const CARD_XP_LEVELS: CardXPLevel[] = [
  { level: 0, name: 'Base',          xpRequired: 0,    glowColor: null,      glowIntensity: 0,   particleTrail: false, borderTreatment: null },
  { level: 1, name: 'Touched',       xpRequired: 10,   glowColor: '#cd7f32', glowIntensity: 0.1,  particleTrail: false, borderTreatment: null },
  { level: 2, name: 'Bronze Aura',   xpRequired: 50,   glowColor: '#cd7f32', glowIntensity: 0.25, particleTrail: false, borderTreatment: 'bronze_edge' },
  { level: 3, name: 'Silver Forge',  xpRequired: 150,  glowColor: '#c0c0c0', glowIntensity: 0.35, particleTrail: false, borderTreatment: 'silver_edge' },
  { level: 4, name: 'Gold Tempered', xpRequired: 500,  glowColor: '#c9a84c', glowIntensity: 0.5,  particleTrail: true,  borderTreatment: 'gold_edge' },
  { level: 5, name: 'Mythic Bound',  xpRequired: 1500, glowColor: '#e8c55a', glowIntensity: 0.7,  particleTrail: true,  borderTreatment: 'mythic_edge' },
]

export function getCardXPLevel(xp: number): CardXPLevel {
  let level = CARD_XP_LEVELS[0]
  for (const l of CARD_XP_LEVELS) {
    if (xp >= l.xpRequired) level = l
  }
  return level
}

// ============================================================
// GAMBIT ENERGY EFFECT
// ============================================================

/**
 * Gambit effect config -- applied when a card is played (Hit, Double, Split).
 *
 * Sequence:
 * 1. Card vibrates at 8Hz, 3px amplitude for 400ms
 * 2. Pink/magenta particle burst from card corners (radial, 0.4s)
 * 3. Inner glow pulses outward from card center (bloom, 0.6s)
 * 4. Card launches with trailing particle streak (motion blur)
 * 5. Sound: crackling static + bass thud on land
 */
export const GAMBIT_EFFECT = {
  vibrate: { frequency: 8, amplitude: 3, duration: 400 },
  particles: {
    count: 24,
    colors: ['#ff2d77', '#cc1166', '#ff69b4', '#ff1493'],
    speed: 4,
    lifetime: 0.4,
    origin: 'corners', // emit from card corners
  },
  innerGlow: {
    color: '#ff2d77',
    maxRadius: 40,
    duration: 600,
    easing: 'easeOut',
  },
  trail: {
    color: '#ff2d77',
    length: 80,    // pixels of trail
    fadeTime: 300,  // ms to fade
    blur: 4,       // motion blur radius
  },
  sound: {
    charge: 'crackle_static',   // plays during vibrate
    release: 'bass_thud',       // plays on card land
  },
}

// ============================================================
// CARD BACK DESIGNS
// ============================================================

export interface CardBackDesign {
  id: string
  name: string
  background: string
  borderColor: string
  centerIcon: string
  iconColor: string
  pattern: string | null      // repeating pattern overlay
  rarity: string
  price: { gc: number; gems: number }
}

export const CARD_BACKS: CardBackDesign[] = [
  {
    id: 'classic_navy',
    name: 'Classic Navy',
    background: 'linear-gradient(135deg, #1a3a6b, #0d1f3c)',
    borderColor: '#c9a84c',
    centerIcon: '\u2666',
    iconColor: '#c9a84c',
    pattern: null,
    rarity: 'common',
    price: { gc: 0, gems: 0 },
  },
  {
    id: 'dragon',
    name: 'Dragon',
    background: 'linear-gradient(135deg, #2a0505, #0d0202)',
    borderColor: '#ff4444',
    centerIcon: '\uD83D\uDC32',
    iconColor: '#ff4444',
    pattern: 'scales',
    rarity: 'rare',
    price: { gc: 3000, gems: 0 },
  },
  {
    id: 'gold_foil',
    name: 'Gold Foil',
    background: 'linear-gradient(135deg, #c9a84c, #8a7333, #c9a84c)',
    borderColor: '#e8c55a',
    centerIcon: '\u2605',
    iconColor: '#1a1a1a',
    pattern: null,
    rarity: 'epic',
    price: { gc: 0, gems: 60 },
  },
  {
    id: 'deep_space',
    name: 'Deep Space',
    background: 'linear-gradient(135deg, #0a001a, #1a0a3a, #0a001a)',
    borderColor: '#6a5acd',
    centerIcon: '\u2734',
    iconColor: '#9b59b6',
    pattern: 'stars',
    rarity: 'epic',
    price: { gc: 0, gems: 75 },
  },
  {
    id: 'vantaris_seal',
    name: 'Vantaris Seal',
    background: 'linear-gradient(135deg, #020203, #050507, #020203)',
    borderColor: '#c9a84c',
    centerIcon: '\u2605',
    iconColor: '#c9a84c',
    pattern: null,
    rarity: 'legendary',
    price: { gc: 0, gems: 0 },
  },
]

// ============================================================
// HELPERS
// ============================================================

export function getSkin(id: string): DeckSkin {
  return DECK_SKINS.find(s => s.id === id) || DECK_SKINS[0]
}

export function getCardBack(id: string): CardBackDesign {
  return CARD_BACKS.find(b => b.id === id) || CARD_BACKS[0]
}

export function getRarityEffect(tier: string): CardRarityEffect {
  return CARD_RARITY_EFFECTS.find(r => r.tier === tier) || CARD_RARITY_EFFECTS[0]
}
