/**
 * Vantaris Casino Engine
 *
 * Shared RNG + payout math + round persistence for the instant-bet games
 * (dice, mines, plinko, roulette). Every single-player game calls these
 * helpers so winnings bank to Supabase consistently and the leaderboard
 * finally has real data to rank.
 *
 * RNG note: uses the browser CSPRNG (crypto.getRandomValues) today, but is
 * structured for a provably-fair upgrade (server-seed / client-seed / nonce,
 * HMAC-SHA256) to honor the promise on /fairness. When that lands, only
 * randomFloat() changes; every game keeps working untouched.
 */

import {
  supabase,
  getPlayerProfile,
} from './supabase'

// ============================================================
// RNG (provably-fair-ready)
// ============================================================

/** Uniform float in [0, 1) from the CSPRNG. */
export function randomFloat(): number {
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    const buf = new Uint32Array(1)
    crypto.getRandomValues(buf)
    return buf[0] / 0x100000000
  }
  // SSR / non-secure fallback (never the betting path; UI only)
  return Math.random()
}

/** Integer in [min, max] inclusive. */
export function randomInt(min: number, max: number): number {
  return min + Math.floor(randomFloat() * (max - min + 1))
}

/** Classic dice roll: 0.00 to 99.99 (two decimals). */
export function rollDice(): number {
  return Math.floor(randomFloat() * 10000) / 100
}

export const HOUSE_EDGE = 0.01 // 1%

// ============================================================
// DICE PAYOUT MATH
// ============================================================

/** Win probability (percent) for a target + direction. */
export function diceWinChance(target: number, direction: 'over' | 'under'): number {
  const chance = direction === 'over' ? 100 - target : target
  return Math.max(0.01, Math.min(99.99, chance))
}

/** Payout multiplier after house edge. fair = 100 / chance. */
export function diceMultiplier(target: number, direction: 'over' | 'under'): number {
  const chance = diceWinChance(target, direction)
  return (100 / chance) * (1 - HOUSE_EDGE)
}

export function diceIsWin(roll: number, target: number, direction: 'over' | 'under'): boolean {
  return direction === 'over' ? roll > target : roll < target
}

// ============================================================
// MINES PAYOUT MATH
// Reveal safe tiles; each pick raises the multiplier. Hit a mine, lose it all.
// ============================================================

/** Fair multiplier after revealing `picks` safe tiles, with house edge. */
export function minesMultiplier(tiles: number, mines: number, picks: number): number {
  if (picks <= 0) return 1
  let m = 1
  for (let i = 0; i < picks; i++) {
    m *= (tiles - i) / (tiles - mines - i)
  }
  return Math.round(m * (1 - HOUSE_EDGE) * 100) / 100
}

/** Random distinct mine positions on a `tiles`-cell board. */
export function placeMines(tiles: number, mines: number): number[] {
  const positions = new Set<number>()
  while (positions.size < mines && positions.size < tiles) {
    positions.add(randomInt(0, tiles - 1))
  }
  return [...positions]
}

// ============================================================
// ROULETTE (European single-zero, 0-36)
// The single zero IS the house edge (2.7%), so HOUSE_EDGE is NOT applied here.
// ============================================================

export const ROULETTE_RED = new Set([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36])

export function spinRoulette(): number {
  return randomInt(0, 36)
}

export type RouletteBet =
  | { type: 'red' | 'black' | 'even' | 'odd' | 'low' | 'high' }
  | { type: 'dozen' | 'column'; index: 0 | 1 | 2 }
  | { type: 'straight'; n: number }

/** Total return multiplier (stake included) on a win, else 0. */
export function roulettePayout(bet: RouletteBet, result: number): number {
  const red = ROULETTE_RED.has(result)
  let win = false
  switch (bet.type) {
    case 'red': win = result !== 0 && red; break
    case 'black': win = result !== 0 && !red; break
    case 'even': win = result !== 0 && result % 2 === 0; break
    case 'odd': win = result % 2 === 1; break
    case 'low': win = result >= 1 && result <= 18; break
    case 'high': win = result >= 19 && result <= 36; break
    case 'dozen': win = result >= bet.index * 12 + 1 && result <= bet.index * 12 + 12; break
    case 'column': win = result !== 0 && (result - 1) % 3 === bet.index; break
    case 'straight': win = result === bet.n; break
  }
  if (!win) return 0
  if (bet.type === 'straight') return 36 // 35:1
  if (bet.type === 'dozen' || bet.type === 'column') return 3 // 2:1
  return 2 // 1:1
}

// ============================================================
// PLINKO
// Ball bounces L/R through `rows` pegs into one of rows+1 buckets.
// Multipliers are derived from the binomial distribution so expected value
// equals (1 - HOUSE_EDGE) exactly for any rows/risk. Honest by construction.
// ============================================================

function binomP(n: number, k: number): number {
  let c = 1
  for (let i = 0; i < k; i++) c = (c * (n - i)) / (i + 1)
  return c / Math.pow(2, n)
}

export function plinkoMultipliers(rows: number, risk: 'low' | 'medium' | 'high'): number[] {
  const skew = risk === 'low' ? 2.0 : risk === 'medium' ? 4.0 : 7.0
  const center = rows / 2
  const shape: number[] = []
  for (let k = 0; k <= rows; k++) {
    const dist = Math.abs(k - center) / center // 0 center, 1 edge
    shape.push(Math.pow(1 + dist * skew, 2))
  }
  let expected = 0
  for (let k = 0; k <= rows; k++) expected += binomP(rows, k) * shape[k]
  const scale = (1 - HOUSE_EDGE) / expected
  return shape.map((s) => Math.round(s * scale * 100) / 100)
}

/** Drop a ball: returns the L/R path (0=left,1=right) and the landing bucket. */
export function dropPlinko(rows: number): { path: number[]; bucket: number } {
  const path: number[] = []
  let bucket = 0
  for (let i = 0; i < rows; i++) {
    const right = randomFloat() < 0.5 ? 0 : 1
    path.push(right)
    bucket += right
  }
  return { path, bucket }
}

// ============================================================
// CHIPS
// Source of truth = Supabase casino_players.gold_coins when authed.
// Guests get a local-storage balance so the game is always playable.
// ============================================================

export type ChipState = { balance: number; playerId: string | null; authed: boolean; displayName?: string }

const GUEST_START = 1000
const GUEST_KEY = 'vanta_guest_chips'

export async function loadChips(): Promise<ChipState> {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (user) {
      const profile = await getPlayerProfile(user.id)
      return {
        balance: typeof profile?.gold_coins === 'number' ? profile.gold_coins : GUEST_START,
        playerId: profile?.id ?? null,
        authed: true,
        displayName: profile?.display_name ?? 'Player',
      }
    }
  } catch {
    // fall through to guest mode
  }
  let local = NaN
  if (typeof window !== 'undefined') local = Number(window.localStorage.getItem(GUEST_KEY))
  return {
    balance: Number.isFinite(local) && local > 0 ? local : GUEST_START,
    playerId: null,
    authed: false,
    displayName: 'Guest',
  }
}

export function saveGuestChips(balance: number): void {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(GUEST_KEY, String(Math.max(0, Math.floor(balance))))
  }
}

// ============================================================
// PERSIST A FINISHED ROUND (no-op-safe for guests, never throws)
// ============================================================

export async function persistRound(opts: {
  state: ChipState
  game: string
  bet: number
  win: number // total returned (0 on a loss)
  multiplier: number
  gameData: unknown
  newBalance: number
}): Promise<void> {
  const { state, game, bet, win, multiplier, gameData, newBalance } = opts

  if (!state.authed) {
    saveGuestChips(newBalance)
    return
  }

  // Signed-in: persist server-side via the game-event edge function (the browser
  // is RLS-blocked from the game tables). It logs the round to player_events,
  // records the arcade high score, and updates chip_balance. Best-effort; a
  // failure never blocks play (local fallback keeps the balance correct).
  try {
    await supabase.functions.invoke('game-event', {
      body: {
        type: 'game_round',
        game,
        bet,
        win,
        net: win - bet,
        multiplier,
        gameData,
        playerId: state.playerId,
        displayName: state.displayName ?? 'Player',
        newBalance: Math.max(0, Math.floor(newBalance)),
      },
    })
  } catch (e) {
    console.warn('[casino-engine] persistRound (edge) failed (non-fatal):', e)
    saveGuestChips(newBalance)
  }
}
