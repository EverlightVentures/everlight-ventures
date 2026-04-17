/**
 * Stripe Product & Price Catalog
 * All Everlight Ventures products wired to live Stripe price IDs.
 *
 * Checkout flow: client calls createCheckout() -> redirects to Stripe
 * -> Stripe redirects back to /success or /cancel
 */

const SUPABASE_URL = 'https://jdqqmsmwmbsnlnstyavl.supabase.co'
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww'

// ============================================================
// BOOKS
// ============================================================
export const BOOKS = {
  sam1: { name: "Sam's First Superpower", priceId: 'price_1T86XVGd8n4Fz3nAs7ubL82A', amount: 699 },
  sam2: { name: "Sam's Second Superpower", priceId: 'price_1T86XVGd8n4Fz3nACgflduDO', amount: 699 },
  sam3: { name: "Sam's Third Superpower", priceId: 'price_1T86XWGd8n4Fz3nAqwJsmpjJ', amount: 699 },
  sam4: { name: "Sam's Fourth Superpower", priceId: 'price_1T86XXGd8n4Fz3nABRzxEp33', amount: 699 },
  sam5: { name: "Sam's Fifth Superpower", priceId: 'price_1T86XYGd8n4Fz3nAI0vnzdv8', amount: 699 },
  samBundle: { name: 'Sam & Robo Complete Bundle', priceId: 'price_1T86XZGd8n4Fz3nAnYniGGZq', amount: 2999 },
  beyondTheVeil: { name: 'Beyond the Veil (Digital)', priceId: 'price_1T86XaGd8n4Fz3nAksUXrOkU', amount: 699 },
}

// ============================================================
// ARCADE (lives, passes, VIP)
// ============================================================
export const ARCADE = {
  lives1: { name: '3 Lives (Tier 1)', priceId: 'price_1T86XbGd8n4Fz3nA2Dku9288', amount: 25 },
  lives2: { name: '3 Lives (Tier 2)', priceId: 'price_1T86XcGd8n4Fz3nAAfe2DqpT', amount: 50 },
  lives3: { name: '3 Lives (Tier 3)', priceId: 'price_1T86XcGd8n4Fz3nAn9DuNkfk', amount: 100 },
  dayPass: { name: 'Day Pass', priceId: 'price_1T86XdGd8n4Fz3nAEmjFNQcS', amount: 299 },
  vipMonthly: { name: 'VIP Monthly', priceId: 'price_1T86XfGd8n4Fz3nAPsmaVqPS', amount: 499, recurring: true },
  seasonPass: { name: 'Season Pass', priceId: 'price_1T86XgGd8n4Fz3nA06V8zK8m', amount: 799 },
}

// ============================================================
// GEMS
// ============================================================
export const GEMS = {
  starter: { name: '100 Gems', priceId: 'price_1T86XiGd8n4Fz3nAsJk2s93y', amount: 99 },
  standard: { name: '600 Gems', priceId: 'price_1T86XjGd8n4Fz3nASyIVCA70', amount: 499 },
  premium: { name: '1,500 Gems', priceId: 'price_1T86XkGd8n4Fz3nAjXXz9pcI', amount: 999 },
  ultra: { name: '4,000 Gems', priceId: 'price_1T86XlGd8n4Fz3nAHfTgPqih', amount: 1999 },
}

// ============================================================
// GAME PASSES
// ============================================================
export const GAME_PASSES = {
  alleyKingz: { name: 'Alley Kingz Pass', priceId: 'price_1T9CPLGd8n4Fz3nA52PnZRgm', amount: 499, recurring: true },
  blackjack: { name: 'Blackjack Pass', priceId: 'price_1T9CPMGd8n4Fz3nAXyX7odXJ', amount: 499, recurring: true },
  masterPass: { name: 'Master Pass (All Games)', priceId: 'price_1T9CPMGd8n4Fz3nAVlfEbWGv', amount: 999, recurring: true },
}

// ============================================================
// CASINO (GC packages -- sweepstakes model)
// ============================================================
export const CASINO_PACKS = {
  starter: { name: 'Starter Pack', priceId: 'price_1TN5NsGd8n4Fz3nAohDXKsrQ', amount: 99, gc: 10000, scBonus: 1, gems: 0 },
  player: { name: 'Player Pack', priceId: 'price_1TN5NtGd8n4Fz3nAMSYyYMFW', amount: 499, gc: 50000, scBonus: 5, gems: 10 },
  highRoller: { name: 'High Roller', priceId: 'price_1TN5NuGd8n4Fz3nAygL0m0BD', amount: 999, gc: 120000, scBonus: 15, gems: 30 },
  vip: { name: 'VIP Bundle', priceId: 'price_1TN5NuGd8n4Fz3nAp7pPQKQ0', amount: 2499, gc: 300000, scBonus: 50, gems: 100 },
  casinoBoss: { name: 'Casino Boss', priceId: 'price_1TN5NvGd8n4Fz3nAowxalCQ2', amount: 4999, gc: 750000, scBonus: 150, gems: 300 },
}

// ============================================================
// HIVE MIND SaaS
// ============================================================
export const HIVE_MIND = {
  spark: { name: 'Hive Mind Spark', priceId: 'price_1TCoRYGd8n4Fz3nA57DzNT7u', amount: 4900, recurring: true },
  hive: { name: 'Hive Mind Hive', priceId: 'price_1TCoRZGd8n4Fz3nA4cGEuOH7', amount: 12900, recurring: true },
  enterprise: { name: 'Hive Mind Enterprise', priceId: 'price_1TCoRZGd8n4Fz3nAtm7T01d7', amount: 39900, recurring: true },
}

// ============================================================
// CHECKOUT HELPER
// ============================================================

export function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(cents % 100 === 0 ? 0 : 2)}`
}

/**
 * Redirect to Stripe Checkout.
 * For production, this should go through a Supabase edge function
 * that creates the session server-side. For now, we use the
 * create-checkout edge function if it exists, otherwise payment links.
 */
export async function createCheckout(priceId: string, mode: 'payment' | 'subscription' = 'payment'): Promise<void> {
  try {
    const res = await fetch(`${SUPABASE_URL}/functions/v1/create-checkout`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        priceId,
        mode,
        successUrl: `${window.location.origin}/success`,
        cancelUrl: window.location.href,
      }),
    })

    const data = await res.json()
    if (data.url) {
      window.location.href = data.url
    }
  } catch {
    // Fallback: direct Stripe payment link would go here
    console.error('[stripe] Checkout creation failed')
  }
}
