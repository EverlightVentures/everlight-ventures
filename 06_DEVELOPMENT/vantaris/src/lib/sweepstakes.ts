/**
 * Vantaris Sweepstakes Engine
 *
 * Dual-currency social casino model (Chumba/Stake.us pattern).
 *
 * GOLD COINS (GC):
 * - Purchased with real money via Stripe
 * - Used for social play ONLY
 * - Has NO cash value, cannot be redeemed
 *
 * SWEEP CHIPS (SC):
 * - NEVER sold directly
 * - Given as FREE BONUS with GC purchases
 * - Given via no-purchase-necessary methods (daily login, mail-in, promo)
 * - Can be played in sweepstakes-eligible games
 * - Redeemable for cash after playthrough + KYC verification
 *
 * Legal basis: removes "consideration" from the prize element,
 * making it a promotional sweepstakes, not gambling.
 */

import { useBlackjackStore, type GameMode } from './blackjack-store'
import { toastWin, toastInfo } from '@/components/blackjack/VantarisToast'
import { IS_PRODUCTION } from './django-sync'

// ============================================================
// GC PURCHASE PACKAGES (SC is always a bonus, never sold)
// ============================================================

export interface GCPackage {
  id: string
  name: string
  gcAmount: number
  scBonus: number      // free SC bonus (never "sold")
  gemsBonus: number
  priceUSD: number
  featured: boolean
  stripePriceId: string // Stripe price ID for checkout
}

export const GC_PACKAGES: GCPackage[] = [
  { id: 'starter', name: 'Starter', gcAmount: 10000, scBonus: 1.00, gemsBonus: 0, priceUSD: 0.99, featured: false, stripePriceId: 'price_1TN5NsGd8n4Fz3nAohDXKsrQ' },
  { id: 'player', name: 'Player Pack', gcAmount: 50000, scBonus: 5.00, gemsBonus: 10, priceUSD: 4.99, featured: false, stripePriceId: 'price_1TN5NtGd8n4Fz3nAMSYyYMFW' },
  { id: 'high_roller', name: 'High Roller', gcAmount: 120000, scBonus: 15.00, gemsBonus: 30, priceUSD: 9.99, featured: true, stripePriceId: 'price_1TN5NuGd8n4Fz3nAygL0m0BD' },
  { id: 'vip', name: 'VIP Bundle', gcAmount: 300000, scBonus: 50.00, gemsBonus: 100, priceUSD: 24.99, featured: false, stripePriceId: 'price_1TN5NuGd8n4Fz3nAp7pPQKQ0' },
  { id: 'whale', name: 'Casino Boss', gcAmount: 750000, scBonus: 150.00, gemsBonus: 300, priceUSD: 49.99, featured: false, stripePriceId: 'price_1TN5NvGd8n4Fz3nAowxalCQ2' },
]

// ============================================================
// PURCHASE FLOW
// ============================================================

export async function purchaseGCPackage(packageId: string): Promise<void> {
  const pkg = GC_PACKAGES.find(p => p.id === packageId)
  if (!pkg) return

  // ALWAYS go through Stripe -- no free credits
  try {
    const { createCheckout } = await import('./supabase')
    // Map package to the Stripe slug
    const slugMap: Record<string, string> = {
      starter: 'chips-500',
      player: 'chips-500',
      high_roller: 'chips-3000',
      vip: 'chips-3000',
      whale: 'chips-8000',
    }
    const slug = slugMap[packageId] || 'chips-500'
    const result = await createCheckout(slug, '')
    if (result?.url) {
      window.location.href = result.url
      return
    }
    toastInfo('Checkout Error', 'Could not create payment session. Please try again.')
  } catch (err) {
    console.error('Stripe checkout error:', err)
    toastInfo('Checkout Error', 'Payment unavailable. Please try again.')
  }
}

// ============================================================
// FREE SC METHODS (no purchase necessary)
// ============================================================

export function claimDailySCBonus(): void {
  const state = useBlackjackStore.getState()
  const today = new Date().toDateString()
  const lastClaim = localStorage.getItem('vantaris_sc_daily')

  if (lastClaim === today) return // already claimed

  const scAmount = 0.30 // daily free SC
  useBlackjackStore.setState({
    player: {
      ...state.player,
      sweepsCoins: state.player.sweepsCoins + scAmount,
      scPlaythroughRequired: state.player.scPlaythroughRequired + scAmount,
    },
  })

  localStorage.setItem('vantaris_sc_daily', today)
  toastInfo('Daily SC Bonus', `+${scAmount} SC credited! No purchase necessary.`)
}

// ============================================================
// SC GAME PLAY (track wagers for playthrough)
// ============================================================

export function trackSCWager(amount: number): void {
  const state = useBlackjackStore.getState()
  useBlackjackStore.setState({
    player: {
      ...state.player,
      scPlaythroughWagered: state.player.scPlaythroughWagered + amount,
    },
  })
}

export function canRedeemSC(): boolean {
  const player = useBlackjackStore.getState().player
  return (
    player.sweepsCoins >= 50 && // minimum 50 SC
    player.scPlaythroughWagered >= player.scPlaythroughRequired && // playthrough met
    player.kycVerified // KYC verified
  )
}

export function getPlaythroughProgress(): number {
  const player = useBlackjackStore.getState().player
  if (player.scPlaythroughRequired === 0) return 100
  return Math.min(100, (player.scPlaythroughWagered / player.scPlaythroughRequired) * 100)
}

// ============================================================
// GEO-BLOCKING (restricted states)
// ============================================================

// States where sweepstakes casinos are restricted or banned
export const RESTRICTED_STATES = ['WA', 'ID', 'NV', 'MT']
// States with additional restrictions (may require extra compliance)
export const EXTRA_COMPLIANCE_STATES = ['NJ', 'NY']

export function isStateAllowed(stateCode: string): boolean {
  return !RESTRICTED_STATES.includes(stateCode.toUpperCase())
}

// ============================================================
// GAME MODE TOGGLE
// ============================================================

export function setGameMode(mode: GameMode): void {
  useBlackjackStore.setState({ gameMode: mode })
  toastInfo(
    mode === 'sc' ? 'Sweepstakes Mode' : 'Social Mode',
    mode === 'sc'
      ? 'Playing with Sweep Chips. Wins are redeemable!'
      : 'Playing with Gold Coins. Fun play, no cash value.'
  )
}

// Get current bet currency label
export function getCurrencyLabel(mode: GameMode): string {
  return mode === 'sc' ? 'SC' : 'GC'
}

// Get player balance for current mode
export function getModeBalance(mode: GameMode): number {
  const player = useBlackjackStore.getState().player
  return mode === 'sc' ? player.sweepsCoins : player.chips
}
