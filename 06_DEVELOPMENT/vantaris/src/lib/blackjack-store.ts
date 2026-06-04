/**
 * Vantaris Blackjack State Store (Zustand)
 *
 * Single source of truth for ALL blackjack game state.
 * The UI reads from this store. Actions dispatch through the engine.
 *
 * This replaces the scattered useState calls in the page component.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type {
  Card, GamePhase, Outcome, HandState, SideBetState,
  LightningState, TableConfig, DealEvent, DealerDrawEvent,
} from './blackjack-engine'
import {
  createShoe, needsReshuffle, evaluateHand,
  hit, doubleDown, split, surrender,
  takeInsurance, playDealer, settleHand, getAvailableActions,
  evaluatePerfectPairs, evaluate21Plus3, evaluateLuckyLadies,
  evaluateBadBuster, evaluateProgressive,
  generateLightning, calculateXP, createTableConfig,
  // THE B-CARDD BET -- core is already built + unit-tested in the engine.
  // We REUSE these; do not reimplement. Spec:
  // 01_BUSINESSES/Everlight_Ventures/Everlight_Gaming/Blackjack/BCARDD_BET_SPEC.md
  shouldDealBCard, makeBCard, bcardPayout,
} from './blackjack-engine'

// ============================================================
// THE B-CARDD BET -- Phase 1 (for-fun chips, VIP/Spanish 21 table only)
// ============================================================
//
// BETA_MODE: when true, shouldDealBCard() forces the B-Card every 50 cards BUT
// ONLY for the owner account (1m.rich.gee@gmail.com) -- other testers/players see
// the real 1-in-1,854,799 odds. The owner-email gate lives inside shouldDealBCard()
// in the engine, so flipping this flag is safe.
//
// HOW TO FLIP FOR BETA TESTING:
//   1. Set BCARD_BETA_MODE = true below (this line).
//   2. Sign in as 1m.rich.gee@gmail.com (Supabase Google auth).
//   3. Enter the VIP Lounge table from /vantaris/blackjack, then play.
//   4. Every 50th card dealt to your hand becomes the B-Card -> the choice UI fires.
//
// PRODUCTION = leave this false. With it false, the every-50 path is never taken
// (double-gated) and the only trigger is the genuine 1/1,854,799 RNG roll per card.
const BCARD_BETA_MODE = true   // BETA: owner-gated (only 1m.rich.gee@gmail.com gets every-50). Flip to false for full production.

// ============================================================
// STORE TYPES
// ============================================================

interface DealerPersona {
  id: string
  name: string
  title: string
  vip: boolean
  voiceId: string
  color: string
}

interface BotPlayer {
  name: string
  chips: number
  hand: Card[]
  bet: number
  outcome: string | null
  sittingOut: boolean
  color: string
  seat: number
}

interface PlayerState {
  chips: number          // Gold Coins (GC) -- purchased, social play, NOT redeemable
  gems: number           // Premium currency for cosmetics
  sweepsCoins: number    // Sweep Chips (SC) -- never sold, bonus only, redeemable for cash
  xp: number
  rank: string
  handsPlayed: number
  handsWon: number
  blackjacks: number
  currentStreak: number
  bestStreak: number
  biggestWin: number
  presenceMultiplier: number
  unlockedAchievements: string[]
  ownedItems: string[]
  equippedOutfit: string
  equippedAura: string
  equippedDeckSkin: string
  equippedCardBack: string
  equippedFelt: string
  // Sweepstakes tracking
  scPlaythroughRequired: number  // total SC that must be wagered before redemption
  scPlaythroughWagered: number   // SC wagered so far
  kycVerified: boolean           // KYC verification status

  // ---- QTD average bet (B-CARDD BET payout basis) ----
  // Phase 1: a simple per-player chip-bet average over the current quarter, computed
  // client-side. The spec marks Gold/Sweeps-split + SERVER-AUTHORITATIVE avg as a
  // Phase 2 requirement (immutable hand log on the edge fn). See the TODO in
  // recordBetForQtd() below. For now we sum chip wagers + count hands this quarter.
  qtdBetSum: number              // sum of chip bets logged this quarter
  qtdBetCount: number            // number of chip bets logged this quarter
  qtdQuarterKey: string          // e.g. "2026-Q2"; when it changes we reset the average
}

// Game mode: GC (social, no cash value) or SC (sweepstakes, redeemable)
export type GameMode = 'gc' | 'sc'

// ============================================================
// MULTI-SEAT: Each seat the player occupies is independent
// ============================================================

interface SeatState {
  index: number           // 0-4 (table position)
  active: boolean         // player is occupying this seat
  bet: number
  hand: HandState
  splitHand: HandState | null
  sideBets: SideBetState
  outcome: Outcome | null
  payout: number
  currentHandIndex: number // 0 = main, 1 = split (within this seat)
}

interface BlackjackStore {
  // Game state
  phase: GamePhase
  shoe: Card[]
  config: TableConfig
  betAmount: number
  selectedChip: number

  // Multi-seat model
  seats: SeatState[]           // all 5 table seats
  activeSeatIndices: number[]  // which seats the player occupies (e.g. [1, 2, 3])
  currentSeatIndex: number     // which seat is currently acting (during player_turn)

  // Legacy single-hand accessors (computed from current seat for backward compat)
  mainHand: HandState
  splitHand: HandState | null
  dealerHand: HandState
  currentHandIndex: number
  availableActions: string[]

  // Side bets (for the CURRENT seat being bet on)
  sideBets: SideBetState
  lightning: LightningState

  // Deal animation queue
  dealQueue: DealEvent[]
  dealerDrawQueue: DealerDrawEvent[]

  // Outcome (summary of all seats)
  outcome: Outcome | null       // primary outcome (first seat or worst)
  winAmount: number             // total across all seats
  xpEarned: number
  seatResults: { seatIndex: number; outcome: Outcome; payout: number }[]

  // Dealer
  activeDealer: DealerPersona
  dealerLine: string
  speaking: boolean

  // Bots
  bots: BotPlayer[]

  // Player
  player: PlayerState

  // UI state
  showBoutique: boolean
  showGemStore: boolean
  showFreeChips: boolean
  showProfile: boolean
  showLeaderboard: boolean
  showAvatarBuilder: boolean
  showDealerSelect: boolean
  musicEnabled: boolean
  voiceEnabled: boolean
  autoRebet: boolean
  gameMode: GameMode  // 'gc' for social play, 'sc' for sweepstakes

  // ---- THE B-CARDD BET (Phase 1, VIP/Spanish 21 table, for-fun chips) ----
  playerEmail: string | null   // authenticated email, fed to shouldDealBCard's beta gate
  cardsDealt: number           // running count of cards dealt this session (per-card B-Card odds)
  bcardActive: boolean         // the player drew the B-Card this round + is choosing/has chosen
  bcardChoice: 'take' | 'ride' | null  // which option they picked
  bcardAvgBet: number          // QTD-average bet used as the payout basis for the current event
  bcardPayoutAmount: number    // chips credited (or to be credited) for the current event
  goldenHandPending: boolean   // they chose RIDE -> the NEXT hand is the Golden Hand
  goldenHandActive: boolean    // the current round IS the Golden Hand (beat dealer for 200x)
  goldenHandAvgBet: number     // avg-bet basis frozen at RIDE time, used for the 200x payout

  // Timers
  resultTimer: number | null

  // Actions
  setBet: (amount: number) => void
  selectChip: (value: number) => void
  toggleSeat: (seatIndex: number) => void   // activate/deactivate a seat
  resetToHomeSeat: () => void                // drop all extra seats, keep only the home seat
  deal: () => void
  playerHit: () => void
  playerDoubleHit: () => void  // Double Down Madness: double bet then hit (can repeat)
  playerStand: () => void
  playerDouble: () => void
  playerSplit: () => void
  playerSurrender: () => void
  playerInsurance: (take: boolean) => void
  newRound: () => void
  setDealer: (dealer: DealerPersona) => void
  togglePanel: (panel: string) => void
  setDealerLine: (line: string) => void
  toggleSideBet: (bet: 'perfectPairs' | 'twentyOnePlus3' | 'luckyLadies' | 'progressive', amount: number) => void
  setTableVariant: (variant: string) => void
  // THE B-CARDD BET
  setPlayerEmail: (email: string | null) => void
  bcardTake: () => void   // TAKE IT: auto-win current hand at 100x avg bet (chips)
  bcardRide: () => void   // RIDE IT: B-Card plays as 8, next hand = Golden Hand (200x if you beat dealer)
}

// ============================================================
// INITIAL HAND STATE
// ============================================================

const EMPTY_HAND: HandState = {
  cards: [],
  value: 0,
  softValue: 0,
  isSoft: false,
  isBust: false,
  isBlackjack: false,
  isCharlie: false,
  bet: 0,
  outcome: null,
  payout: 0,
  doubled: false,
  surrendered: false,
  insured: false,
  insuranceBet: 0,
  insurancePayout: 0,
}

function createEmptySeat(index: number, active = false): SeatState {
  return {
    index,
    active,
    bet: 0,
    hand: { ...EMPTY_HAND },
    splitHand: null,
    sideBets: { ...EMPTY_SIDE_BETS },
    outcome: null,
    payout: 0,
    currentHandIndex: 0,
  }
}

function createInitialSeats(): SeatState[] {
  // 5 seats. Player starts at seat 2 (center).
  return [0, 1, 2, 3, 4].map(i => createEmptySeat(i, i === HOME_SEAT))
}

// The human's permanent home seat (bottom-center). Bots never sit here. Every new
// round resets the player to exactly this ONE seat, so playing extra hands never
// carries over -- you can drop back to a single hand freely, every round.
const HOME_SEAT = 2

// Canonical deal / turn order: first base (the dealer's LEFT = the table's far-RIGHT
// seat) acts first, then clockwise, dealer last -- standard US casino. We keep
// activeSeatIndices stored in THIS order so dealing, the turn loop, settlement and the
// card render all agree (one source of truth, no scattered per-seat logic). The human's
// center seat is dealt 3rd either way, so this only sets the bot-seat sequence.
// To put first base on the LEFT instead, change this to [0, 1, 2, 3, 4].
const SEAT_DEAL_ORDER = [4, 3, 2, 1, 0]
const orderActive = (active: number[]): number[] => SEAT_DEAL_ORDER.filter(i => active.includes(i))

const EMPTY_SIDE_BETS: SideBetState = {
  perfectPairs: { active: false, bet: 0, result: null, payout: 0 },
  twentyOnePlus3: { active: false, bet: 0, result: null, payout: 0 },
  luckyLadies: { active: false, bet: 0, result: null, payout: 0 },
  progressive: { active: false, bet: 0, result: null, payout: 0 },
}

const EMPTY_LIGHTNING: LightningState = {
  active: false,
  fee: 0,
  multipliedTotal: null,
  multiplier: 1,
}

// ============================================================
// DEFAULT DEALERS
// ============================================================

const DEFAULT_DEALERS: DealerPersona[] = [
  { id: 'aria', name: 'Aria Sinclair', title: 'House Dealer', vip: false, voiceId: 'EXAVITQu4vr4xnSDxMaL', color: '#c9a84c' },
  { id: 'marcus', name: 'Marcus Vega', title: 'High Roller', vip: false, voiceId: 'onwK4e9ZLuTAKqWW03F9', color: '#ff6b35' },
  { id: 'kanisha', name: 'Kanisha Thompson', title: 'VIP Lounge', vip: true, voiceId: 'XrExE9yKIg1WjnnlVkGX', color: '#e91e63' },
  { id: 'bacardi', name: 'Bacardi Ice', title: 'VIP Elite', vip: true, voiceId: 'DwwuoY7Uz8AP8zrY5TAo', color: '#00bcd4' },
]

// ============================================================
// CREATE STORE
// ============================================================

// Fresh player defaults (for first-time visitors)
const FRESH_PLAYER: PlayerState = {
  chips: 1000, gems: 10, sweepsCoins: 5.00, xp: 0, rank: 'Bronze',
  handsPlayed: 0, handsWon: 0, blackjacks: 0, currentStreak: 0,
  bestStreak: 0, biggestWin: 0, presenceMultiplier: 1.0,
  unlockedAchievements: [],
  ownedItems: ['default_suit'],
  equippedOutfit: 'default_suit',
  equippedAura: 'none',
  equippedDeckSkin: 'classic',
  equippedCardBack: 'classic_navy',
  equippedFelt: 'default',
  // Sweepstakes
  scPlaythroughRequired: 0,
  scPlaythroughWagered: 0,
  kycVerified: false,
  // QTD average bet (B-CARDD BET basis)
  qtdBetSum: 0,
  qtdBetCount: 0,
  qtdQuarterKey: '',
}

// ============================================================
// QTD AVERAGE BET HELPERS (B-CARDD BET payout basis)
// ============================================================

/** Calendar-quarter key, e.g. "2026-Q2". Resets the average each quarter (spec: PLAYER RATING). */
function currentQuarterKey(d: Date = new Date()): string {
  return `${d.getFullYear()}-Q${Math.floor(d.getMonth() / 3) + 1}`
}

/**
 * Fold one chip bet into the player's QTD average-bet tally. Resets the tally when
 * the calendar quarter rolls over. Returns the updated QTD fields to merge into player.
 *
 * Phase 1 = chip bets only (for-fun). TODO(Phase 2): move this to a server-authoritative
 * immutable hand log on the edge fn (blackjack-api) and track Gold + Sweeps averages
 * separately per the spec's "tracked PER CURRENCY" requirement -- the client value here
 * is spoofable and must NOT gate any real-money (SC) payout.
 */
function recordBetForQtd(p: PlayerState, bet: number): Pick<PlayerState, 'qtdBetSum' | 'qtdBetCount' | 'qtdQuarterKey'> {
  const qk = currentQuarterKey()
  const rolledOver = p.qtdQuarterKey !== qk
  const sum = (rolledOver ? 0 : p.qtdBetSum) + Math.max(0, bet || 0)
  const count = (rolledOver ? 0 : p.qtdBetCount) + 1
  return { qtdBetSum: sum, qtdBetCount: count, qtdQuarterKey: qk }
}

/**
 * The QTD average bet used as the B-CARDD BET multiplier basis.
 * Spec PLAYER RATING + new-player fallback: under 20 logged hands this quarter, the
 * basis = the larger of (their average so far) or the table minimum bet, so a hand-1
 * B-Card cannot produce a junk average.
 */
function qtdAvgBet(p: PlayerState, tableMinBet: number): number {
  const MIN_HANDS = 20  // tunable threshold (spec)
  const avgSoFar = p.qtdBetCount > 0 ? p.qtdBetSum / p.qtdBetCount : 0
  if (p.qtdBetCount < MIN_HANDS) {
    return Math.max(avgSoFar, tableMinBet)
  }
  return avgSoFar
}

// ============================================================
// B-CARD DRAW INTERCEPT (VIP / Spanish 21 table only)
// ============================================================
//
// There is no single "draw a card" function in the engine -- the store pulls cards
// directly (shoe.pop() / shoe[0]). This helper is the ONE interception point: every
// card drawn TO THE PLAYER on the VIP table runs through here. It keeps the running
// cardsDealt counter, asks the engine's shouldDealBCard() per card, and swaps in
// makeBCard() (which scores as 8 via cardValue(), so Spanish 21 eval is unaffected)
// when the trigger fires. All other tables/draws bypass this and deal normally.

interface DrawResult { card: Card; shoe: Card[]; cardsDealt: number; bcard: boolean }

/**
 * Draw the next card for a PLAYER hand on the VIP table, with B-Card interception.
 * @param fromTop  true = shoe[0] (hit/double/split use the top); false = shoe.pop() (initial deal)
 * Non-VIP tables must NOT call this; they keep dealing normally so nothing else changes.
 */
function drawPlayerCard(
  shoe: Card[],
  cardsDealt: number,
  isVipTable: boolean,
  playerEmail: string | null,
  fromTop: boolean,
): DrawResult {
  const nextCount = cardsDealt + 1
  // Only the VIP (Spanish 21) table runs the B-CARDD BET. Other tables: never inject.
  if (isVipTable && shouldDealBCard({ betaMode: BCARD_BETA_MODE, playerEmail: playerEmail ?? undefined, cardsDealt: nextCount })) {
    // Inject the B-Card instead of the next shoe card; the shoe is NOT consumed so
    // the card count of the shoe is preserved (the B-Card is an overlay, not a 53rd
    // physical card being removed from the 48-card Spanish deck).
    return { card: makeBCard(), shoe, cardsDealt: nextCount, bcard: true }
  }
  const card = fromTop
    ? { ...shoe[0], faceDown: false }
    : { ...shoe[shoe.length - 1], faceDown: false }
  const newShoe = fromTop ? shoe.slice(1) : shoe.slice(0, -1)
  return { card, shoe: newShoe, cardsDealt: nextCount, bcard: false }
}

/** True when the player is sitting at the existing VIP (Spanish 21) lobby table. */
function isVip(config: TableConfig): boolean {
  return config.tableType === 'vip'
}

export const useBlackjackStore = create<BlackjackStore>()(
  persist(
    (set, get) => ({
  // Initial state
  phase: 'betting' as GamePhase,
  shoe: createShoe(6),
  config: createTableConfig('classic'),
  betAmount: 100,
  selectedChip: 100,

  // Multi-seat state
  seats: createInitialSeats(),
  activeSeatIndices: [2],      // player starts at center seat
  currentSeatIndex: 2,

  // Legacy accessors (point to current seat for backward compat)
  mainHand: { ...EMPTY_HAND },
  splitHand: null,
  dealerHand: { ...EMPTY_HAND },
  currentHandIndex: 0,
  availableActions: [],

  sideBets: { ...EMPTY_SIDE_BETS },
  lightning: { ...EMPTY_LIGHTNING },

  dealQueue: [],
  dealerDrawQueue: [],

  outcome: null,
  winAmount: 0,
  xpEarned: 0,
  seatResults: [],

  activeDealer: DEFAULT_DEALERS[0],
  dealerLine: 'Take your time. The cards are patient.',
  speaking: false,

  bots: (() => {
    // 36 diverse NPC names (from V4 GDD spec)
    const pool = [
      'Marcus', 'DeShawn', 'Aaliyah', 'Jaylen', 'Keisha', 'Darius', 'Imani',
      'Tremaine', 'Latoya', 'Malik', 'Brianna', 'Jamal', 'Tanisha', 'Elijah',
      'Monique', 'Xavier', 'Shanice', 'Devon', 'Kamila', 'Tyrone', 'Destiny',
      'Isaiah', 'Nadia', 'Quinton', 'Zara', 'Reginald', 'Tamara', 'Calvin',
      'Precious', 'Derrick', 'Amara', 'Jordan', 'Simone', 'Anthony', 'Crystal',
    ]
    const shuffled = pool.sort(() => Math.random() - 0.5).slice(0, 4)
    // Weighted starting chip stacks (from V4: $50-$500 range)
    const chipTiers = [50, 75, 100, 150, 200, 300, 500]
    const chipWeights = [0.10, 0.15, 0.30, 0.20, 0.15, 0.07, 0.03]
    function npcChips() {
      const r = Math.random()
      let c = 0
      for (let i = 0; i < chipTiers.length; i++) {
        c += chipWeights[i]
        if (r <= c) return chipTiers[i] * 10 // scale to GC
      }
      return 1000
    }
    return shuffled.map((name, i) => ({
      name, chips: npcChips(),
      hand: [] as Card[], bet: 0, outcome: null,
      sittingOut: Math.random() < 0.15,
      color: ['#27ae60', '#e74c3c', '#9b59b6', '#e67e22'][i],
      seat: [0, 1, 3, 4][i],
    }))
  })(),

  player: { ...FRESH_PLAYER },

  showBoutique: false,
  showGemStore: false,
  showFreeChips: false,
  showProfile: false,
  showLeaderboard: false,
  showAvatarBuilder: false,
  showDealerSelect: false,
  musicEnabled: true,
  voiceEnabled: true,
  autoRebet: false,
  gameMode: 'gc' as GameMode,

  // THE B-CARDD BET (Phase 1)
  playerEmail: null,
  cardsDealt: 0,
  bcardActive: false,
  bcardChoice: null,
  bcardAvgBet: 0,
  bcardPayoutAmount: 0,
  goldenHandPending: false,
  goldenHandActive: false,
  goldenHandAvgBet: 0,

  resultTimer: null,

  // ============================================================
  // ACTIONS
  // ============================================================

  // Helper: get current balance based on game mode
  // (not exported, used internally by all actions)

  setBet: (amount) => set({ betAmount: amount }),
  selectChip: (value) => {
    const state = get()
    const bal = state.gameMode === 'sc' ? state.player.sweepsCoins : state.player.chips
    const newBet = Math.min(state.betAmount + value, bal, state.config.maxBet)
    set({ selectedChip: value, betAmount: newBet })
  },

  toggleSeat: (seatIndex: number) => {
    const state = get()
    if (state.phase !== 'betting') return
    const seats = [...state.seats]
    const seat = seats[seatIndex]

    // If a bot is at this seat, remove the bot (player takes priority)
    const bots = [...state.bots]
    const botIdx = bots.findIndex(b => b.seat === seatIndex)
    if (botIdx >= 0 && !seat.active) {
      bots[botIdx] = { ...bots[botIdx], sittingOut: true }
    }

    seats[seatIndex] = { ...seat, active: !seat.active }
    const active = orderActive(seats.filter(s => s.active).map(s => s.index))
    if (active.length === 0) return // must have at least one seat
    set({ seats, activeSeatIndices: active, bots })
  },

  // Drop every seat except the home seat. Powers the CLEAR control so the player can
  // go from N hands back to a single hand mid-round, without having to deal first.
  resetToHomeSeat: () => {
    const state = get()
    if (state.phase !== 'betting') return
    const seats = state.seats.map(s => ({ ...s, active: s.index === HOME_SEAT, bet: 0 }))
    set({ seats, activeSeatIndices: [HOME_SEAT], currentSeatIndex: HOME_SEAT })
  },

  deal: () => {
    const state = get()
    if (state.phase !== 'betting') return
    if (state.betAmount < state.config.minBet) return

    const activeSeats = state.activeSeatIndices
    const totalBet = state.betAmount * activeSeats.length
    const sideBetTotal = Object.values(state.sideBets).reduce((sum, sb) => sum + (sb.active ? sb.bet : 0), 0) * activeSeats.length
    const isScMode = state.gameMode === 'sc'
    const balance = isScMode ? state.player.sweepsCoins : state.player.chips
    if (totalBet + sideBetTotal > balance) return

    let shoe = state.shoe
    if (needsReshuffle(shoe)) shoe = createShoe(state.config.deckCount)

    // ---- THE B-CARDD BET: VIP/Spanish 21 table only ----
    // Intercept PLAYER card draws (single-seat play, the normal case) so the running
    // cardsDealt counter + per-card 1/1,854,799 odds (or beta every-50 for the owner)
    // can swap in the B-Card. Dealer cards + multi-seat deal normally (see TODO below).
    const vip = isVip(state.config)
    const singleSeat = activeSeats.length === 1
    let cardsDealt = state.cardsDealt
    let drewBCard = false

    // Deal to each active seat + dealer
    const seats = [...state.seats]
    const dealerCards: Card[] = [shoe.pop()!, shoe.pop()!]
    dealerCards[1] = { ...dealerCards[1], faceDown: true }
    const dealerEvalEarly = evaluateHand(dealerCards)

    for (const si of activeSeats) {
      let pCards: Card[]
      // B-Card interception only on VIP single-seat play. TODO(Phase 2): extend the
      // intercept to multi-seat + dealer draws once the deal moves server-side.
      if (vip && singleSeat) {
        const d1 = drawPlayerCard(shoe, cardsDealt, true, state.playerEmail, false)
        shoe = d1.shoe; cardsDealt = d1.cardsDealt; if (d1.bcard) drewBCard = true
        const d2 = drawPlayerCard(shoe, cardsDealt, true, state.playerEmail, false)
        shoe = d2.shoe; cardsDealt = d2.cardsDealt; if (d2.bcard) drewBCard = true
        pCards = [d1.card, d2.card]
      } else {
        pCards = [shoe.pop()!, shoe.pop()!]
        if (vip) cardsDealt += 2  // still count cards on VIP multi-seat for odds continuity
      }
      const ev = evaluateHand(pCards)
      seats[si] = {
        ...seats[si],
        bet: state.betAmount,
        hand: {
          ...EMPTY_HAND,
          cards: pCards,
          value: ev.value, softValue: ev.softValue, isSoft: ev.isSoft,
          isBust: ev.isBust, isBlackjack: ev.isBlackjack, isCharlie: ev.isCharlie,
          bet: state.betAmount,
        },
        splitHand: null,
        sideBets: { ...state.sideBets },
        outcome: null,
        payout: 0,
        currentHandIndex: 0,
      }

      // Evaluate ALL side bets for this seat
      if (seats[si].sideBets.perfectPairs.active) {
        const pp = evaluatePerfectPairs(pCards[0], pCards[1])
        seats[si].sideBets.perfectPairs.result = pp.result
        seats[si].sideBets.perfectPairs.payout = pp.result ? seats[si].sideBets.perfectPairs.bet * pp.multiplier : 0
      }
      if (seats[si].sideBets.twentyOnePlus3.active) {
        const t3 = evaluate21Plus3(pCards[0], pCards[1], dealerCards[0])
        seats[si].sideBets.twentyOnePlus3.result = t3.result
        seats[si].sideBets.twentyOnePlus3.payout = t3.result ? seats[si].sideBets.twentyOnePlus3.bet * t3.multiplier : 0
      }
      // luckyLadies slot = BAD BUSTER (evaluated at settlement, not deal)
      // Bad Buster needs dealer's final hand to check if dealer busted
      // Progressive side bet (evaluated on deal -- poker hands from first 2 + dealer upcard)
      if (seats[si].sideBets.progressive.active) {
        const prog = evaluateProgressive(pCards, dealerCards[0])
        seats[si].sideBets.progressive.result = prog.result
        seats[si].sideBets.progressive.payout = prog.result
          ? (prog.isJackpot ? 0 : seats[si].sideBets.progressive.bet * prog.multiplier) // jackpot paid from pool
          : 0
      }
    }

    const dealerEval = evaluateHand(dealerCards)
    const dealerHand: HandState = {
      ...EMPTY_HAND,
      cards: dealerCards,
      value: dealerEval.value, softValue: dealerEval.softValue,
      isSoft: dealerEval.isSoft, isBust: dealerEval.isBust,
      isBlackjack: dealerEval.isBlackjack,
    }

    // Lightning
    let lightning = { ...EMPTY_LIGHTNING }
    if (state.config.lightningEnabled) {
      lightning = generateLightning()
      lightning.fee = state.betAmount
    }

    // First active seat becomes current (for legacy mainHand compat)
    const firstSeat = activeSeats[0]
    // Deduct from correct currency based on game mode
    const newChips = isScMode ? state.player.chips : state.player.chips - totalBet - sideBetTotal
    const newSC = isScMode ? state.player.sweepsCoins - totalBet - sideBetTotal : state.player.sweepsCoins
    // Track SC wagers for playthrough
    const newSCWagered = isScMode
      ? state.player.scPlaythroughWagered + totalBet + sideBetTotal
      : state.player.scPlaythroughWagered

    // QTD average-bet log (B-CARDD BET basis). Record the per-seat chip bet for each
    // active seat this round, rolling over the quarter as needed. Phase 1: chip bets.
    let qtd: Pick<PlayerState, 'qtdBetSum' | 'qtdBetCount' | 'qtdQuarterKey'> = {
      qtdBetSum: state.player.qtdBetSum,
      qtdBetCount: state.player.qtdBetCount,
      qtdQuarterKey: state.player.qtdQuarterKey,
    }
    for (let i = 0; i < activeSeats.length; i++) {
      qtd = recordBetForQtd({ ...state.player, ...qtd }, state.betAmount)
    }

    set({
      phase: 'dealing',
      shoe,
      seats,
      dealerHand,
      mainHand: seats[firstSeat].hand,
      splitHand: null,
      currentSeatIndex: firstSeat,
      currentHandIndex: 0,
      cardsDealt,
      outcome: null,
      winAmount: 0,
      xpEarned: 0,
      seatResults: [],
      sideBets: seats[firstSeat].sideBets,
      lightning,
      dealQueue: [],
      player: { ...state.player, chips: newChips, sweepsCoins: newSC, scPlaythroughWagered: newSCWagered, ...qtd },
    })

    // After deal animation (~1200ms), start seat-by-seat play
    setTimeout(() => {
      const s = get()
      const firstActive = s.activeSeatIndices[0]
      const firstSeatHand = s.seats[firstActive].hand

      // ---- THE B-CARDD BET: B-Card landed in the opening deal ----
      // Pause the hand and present TAKE IT (100x) vs RIDE IT (200x golden hand).
      // Freeze the QTD-average-bet basis now so the displayed/credited payout is stable.
      if (drewBCard) {
        const basis = qtdAvgBet(s.player, s.config.minBet)
        set({
          phase: 'bcard_choice',
          currentSeatIndex: firstActive,
          mainHand: firstSeatHand,
          splitHand: null,
          availableActions: [],
          bcardActive: true,
          bcardChoice: null,
          bcardAvgBet: basis,
          bcardPayoutAmount: 0,
          dealQueue: [],
        })
        return
      }

      // Check for natural blackjack on first seat
      if (firstSeatHand.isBlackjack && s.activeSeatIndices.length === 1) {
        // Single seat BJ: settle immediately
        const settled = settleHand(
          firstSeatHand,
          { ...s.dealerHand, cards: s.dealerHand.cards.map(c => ({ ...c, faceDown: false })) },
          s.config, s.player.presenceMultiplier,
          s.lightning.active && s.lightning.multipliedTotal === 21 ? s.lightning.multiplier : 1,
        )
        const xp = calculateXP(settled.outcome!)
        const sbPayout = Object.values(s.seats[firstActive].sideBets).reduce((sum, sb) => sum + (sb.active ? sb.payout : 0), 0)
        // Golden Hand bonus if this opening-BJ round was the armed Golden Hand. A
        // natural blackjack beats the dealer (unless dealer also has BJ = push).
        const bjBeatDealer = settled.outcome === 'blackjack'
        const bjGoldenBonus = s.goldenHandActive ? bcardPayout(s.goldenHandAvgBet, 'ride', bjBeatDealer) : 0
        const bjTotal = settled.payout + sbPayout + bjGoldenBonus
        set({
          phase: 'settled',
          mainHand: settled,
          dealerHand: { ...s.dealerHand, cards: s.dealerHand.cards.map(c => ({ ...c, faceDown: false })) },
          outcome: settled.outcome,
          winAmount: bjTotal,
          xpEarned: xp,
          seatResults: [{ seatIndex: firstActive, outcome: settled.outcome!, payout: bjTotal }],
          goldenHandActive: false,
          bcardPayoutAmount: bjGoldenBonus,
          player: {
            ...s.player,
            chips: s.gameMode === 'sc' ? s.player.chips : s.player.chips + bjTotal,
            sweepsCoins: s.gameMode === 'sc' ? s.player.sweepsCoins + bjTotal : s.player.sweepsCoins,
            xp: s.player.xp + xp,
            handsPlayed: s.player.handsPlayed + 1,
            handsWon: s.player.handsWon + 1,
            blackjacks: s.player.blackjacks + 1,
            currentStreak: s.player.currentStreak + 1,
            bestStreak: Math.max(s.player.bestStreak, s.player.currentStreak + 1),
            biggestWin: Math.max(s.player.biggestWin, settled.payout),
          },
        })
      } else {
        // Start player turn on first seat
        const dealerUpcard = s.dealerHand.cards[0]
        const nextPhase = dealerUpcard.rank === 'A' ? 'insurance' as GamePhase : 'player_turn' as GamePhase
        const actions = getAvailableActions(firstSeatHand, s.config, s.player.chips, dealerUpcard, false)

        set({
          phase: nextPhase,
          currentSeatIndex: firstActive,
          mainHand: firstSeatHand,
          splitHand: null,
          availableActions: actions,
          dealQueue: [],
        })
      }
    }, 1200)
  },

  playerHit: () => {
    const state = get()
    if (state.phase !== 'player_turn' && state.phase !== 'split_turn') return

    const isMainHand = state.currentHandIndex === 0
    const currentHand = isMainHand ? state.mainHand : state.splitHand!

    // ---- THE B-CARDD BET: intercept the hit draw on VIP single-seat play ----
    // We keep the tested engine hit() untouched -- if the B-Card should fire, we
    // prepend it to the shoe so hit() draws it as shoe[0] (it scores as 8). After the
    // hit, we detect the B-Card on the new card and pause into the choice UI.
    const vip = isVip(state.config)
    const singleSeat = state.activeSeatIndices.length === 1
    let workingShoe = state.shoe
    let newCardsDealt = state.cardsDealt
    let injectedBCard = false
    if (vip && singleSeat && !state.splitHand) {
      const d = drawPlayerCard(state.shoe, state.cardsDealt, true, state.playerEmail, true)
      newCardsDealt = d.cardsDealt
      if (d.bcard) {
        workingShoe = [d.card, ...state.shoe]  // hit() will draw the B-Card first; shoe not consumed
        injectedBCard = true
      }
    }

    const result = hit(currentHand, workingShoe)

    // Sync to seats array so card display updates
    const seats = [...state.seats]
    const seatData = { ...seats[state.currentSeatIndex] }
    if (isMainHand) {
      seatData.hand = result.hand
    } else {
      seatData.splitHand = result.hand
    }
    seats[state.currentSeatIndex] = seatData

    const update: Partial<BlackjackStore> = {
      shoe: result.shoe,
      seats: seats as any,
      cardsDealt: newCardsDealt,
    }

    if (isMainHand) {
      update.mainHand = result.hand
    } else {
      update.splitHand = result.hand
    }

    // ---- THE B-CARDD BET: the hit drew the B-Card -> pause for the choice ----
    // The B-Card is now in the hand (as an 8). Even if that 8 happens to bust the
    // hand, the player still gets the optional jackpot choice before settling.
    if (injectedBCard) {
      const basis = qtdAvgBet(state.player, state.config.minBet)
      set({
        ...(update as any),
        phase: 'bcard_choice',
        availableActions: [],
        bcardActive: true,
        bcardChoice: null,
        bcardAvgBet: basis,
        bcardPayoutAmount: 0,
      })
      return
    }

    if (result.autoBust) {
      // Handle bust
      if (state.splitHand && isMainHand) {
        // Bust on main hand, move to split hand
        update.currentHandIndex = 1
        update.phase = 'split_turn'
        update.mainHand = { ...result.hand, outcome: 'bust', payout: 0 }
      } else {
        // Bust on this seat -- save and advance to next seat via playerStand
        const hand = result.hand
        if (isMainHand) {
          update.mainHand = { ...hand, outcome: 'bust', payout: 0 }
        } else {
          update.splitHand = { ...hand, outcome: 'bust', payout: 0 }
        }
        // Apply update first, then trigger stand to advance to next seat
        set(update as any)
        setTimeout(() => get().playerStand(), 100)
        return
      }
    } else if (result.autoCharlie && state.config.sixCardCharlie) {
      // Six Card Charlie -- auto-win, advance to next seat via playerStand
      const hand = result.hand
      if (isMainHand) {
        update.mainHand = { ...hand, outcome: 'charlie', payout: hand.bet * 2 }
      } else {
        update.splitHand = { ...hand, outcome: 'charlie', payout: hand.bet * 2 }
      }
      // Sync to seats then advance
      const charlieSeats = [...state.seats]
      const charlieSeat = { ...charlieSeats[state.currentSeatIndex] }
      if (isMainHand) charlieSeat.hand = { ...hand, outcome: 'charlie', payout: hand.bet * 2 }
      else charlieSeat.splitHand = { ...hand, outcome: 'charlie', payout: hand.bet * 2 }
      charlieSeats[state.currentSeatIndex] = charlieSeat
      update.seats = charlieSeats as any
      set(update as any)
      setTimeout(() => get().playerStand(), 100)
      return
    }

    // Update available actions
    const activeHand = isMainHand ? (update.mainHand || state.mainHand) : (update.splitHand || state.splitHand!)
    if (!result.autoBust && !result.autoCharlie) {
      update.availableActions = getAvailableActions(
        activeHand, state.config, state.player.chips, state.dealerHand.cards[0], !!state.splitHand,
      )
    }

    set(update as any)
  },

  // DOUBLE DOWN MADNESS: double current bet then hit (can repeat every card)
  playerDoubleHit: () => {
    const state = get()
    if (state.phase !== 'player_turn' && state.phase !== 'split_turn') return

    const isMainHand = state.currentHandIndex === 0
    const currentHand = isMainHand ? state.mainHand : state.splitHand!

    // Double for less: use whatever the player can afford, up to the full double
    const fullDoubleCost = currentHand.bet
    const isScMode = state.gameMode === 'sc'
    const balance = isScMode ? state.player.sweepsCoins : state.player.chips
    if (balance <= 0) return // completely broke
    const doubleCost = Math.min(fullDoubleCost, balance) // double for less if needed

    // Add the double amount to the hand's bet
    const doubledHand: HandState = { ...currentHand, bet: currentHand.bet + doubleCost, doubled: true }

    // Deduct the additional bet
    const playerUpdate = isScMode
      ? { sweepsCoins: state.player.sweepsCoins - doubleCost, scPlaythroughWagered: state.player.scPlaythroughWagered + doubleCost }
      : { chips: state.player.chips - doubleCost }

    // Now hit
    const result = hit(doubledHand, state.shoe)

    // Sync to both root state AND seats array
    const seats = [...state.seats]
    const seatData = { ...seats[state.currentSeatIndex] }
    if (isMainHand) {
      seatData.hand = result.hand
    } else {
      seatData.splitHand = result.hand
    }
    seats[state.currentSeatIndex] = seatData

    const update: any = {
      shoe: result.shoe,
      seats,
      player: { ...state.player, ...playerUpdate },
    }

    if (isMainHand) {
      update.mainHand = result.hand
    } else {
      update.splitHand = result.hand
    }

    // If bust, advance to next seat
    if (result.autoBust) {
      if (isMainHand) {
        update.mainHand = { ...result.hand, outcome: 'bust', payout: 0 }
        seats[state.currentSeatIndex] = { ...seatData, hand: { ...result.hand, outcome: 'bust', payout: 0 } }
      } else {
        update.splitHand = { ...result.hand, outcome: 'bust', payout: 0 }
      }
      update.seats = seats
      set(update)
      setTimeout(() => get().playerStand(), 100)
      return
    }

    // Update available actions (still allow another doubleHit)
    const activeHand = result.hand
    update.availableActions = getAvailableActions(
      activeHand, state.config, (state.player.chips - (isScMode ? 0 : doubleCost)), state.dealerHand.cards[0], !!state.splitHand,
    )

    set(update)
  },

  playerStand: () => {
    const state = get()
    if (state.phase !== 'player_turn' && state.phase !== 'split_turn') return

    // If split hand active, move to split first
    if (state.splitHand && state.currentHandIndex === 0) {
      set({ currentHandIndex: 1, phase: 'split_turn' })
      return
    }

    // Save current seat state back to seats array
    const seats = [...state.seats]
    seats[state.currentSeatIndex] = {
      ...seats[state.currentSeatIndex],
      hand: state.mainHand,
      splitHand: state.splitHand,
    }

    // Find next active seat
    const activeSeats = state.activeSeatIndices
    const currentIdx = activeSeats.indexOf(state.currentSeatIndex)
    const nextIdx = currentIdx + 1

    if (nextIdx < activeSeats.length) {
      // Move to next seat
      const nextSeat = activeSeats[nextIdx]
      const nextHand = seats[nextSeat].hand
      const dealerUpcard = state.dealerHand.cards[0]

      // Skip seats with natural blackjack
      if (nextHand.isBlackjack) {
        seats[nextSeat] = { ...seats[nextSeat], outcome: 'blackjack' }
        set({ seats, currentSeatIndex: nextSeat, mainHand: nextHand, splitHand: null })
        // Recurse to skip to next
        setTimeout(() => get().playerStand(), 100)
        return
      }

      const actions = getAvailableActions(nextHand, state.config, state.player.chips, dealerUpcard, false)
      set({
        seats,
        currentSeatIndex: nextSeat,
        mainHand: nextHand,
        splitHand: seats[nextSeat].splitHand,
        currentHandIndex: 0,
        availableActions: actions,
        phase: 'player_turn',
      })
      return
    }

    // ALL seats done -- dealer plays
    set({ seats, phase: 'dealer_turn' })

    setTimeout(() => {
      const s = get()
      const dealerResult = playDealer(s.dealerHand, s.shoe, s.config)

      set({
        dealerHand: dealerResult.hand,
        dealerDrawQueue: dealerResult.draws,
        shoe: dealerResult.shoe,
      })

      const totalDrawTime = dealerResult.draws.length > 0
        ? dealerResult.draws[dealerResult.draws.length - 1].delayMs + 600
        : 300

      setTimeout(() => {
        const s2 = get()
        const allSeats = [...s2.seats]
        let totalPayout = 0
        let totalXp = 0
        let handsWon = 0
        let bjCount = 0
        const results: { seatIndex: number; outcome: Outcome; payout: number }[] = []

        // Settle ALL active seats against dealer
        for (const si of s2.activeSeatIndices) {
          const seat = allSeats[si]
          const lightningMult = s2.lightning.active && s2.lightning.multipliedTotal
            ? (seat.hand.value === s2.lightning.multipliedTotal ? s2.lightning.multiplier : 1)
            : 1

          const settledMain = settleHand(seat.hand, s2.dealerHand, s2.config, s2.player.presenceMultiplier, lightningMult)
          let settledSplit: HandState | null = null
          if (seat.splitHand) {
            settledSplit = settleHand(seat.splitHand, s2.dealerHand, s2.config, s2.player.presenceMultiplier, 1)
          }

          // Evaluate Bad Buster NOW (needs dealer's final hand to check bust)
          if (seat.sideBets.luckyLadies.active && s2.dealerHand.isBust) {
            const bb = evaluateBadBuster(s2.dealerHand)
            seat.sideBets.luckyLadies.result = bb.result
            seat.sideBets.luckyLadies.payout = bb.result ? seat.sideBets.luckyLadies.bet * bb.multiplier : 0
          }
          const sbPayout = Object.values(seat.sideBets).reduce((sum, sb) => sum + (sb.active ? sb.payout : 0), 0)
          const seatPayout = settledMain.payout + (settledSplit?.payout || 0) + sbPayout
          const seatOutcome = settledMain.outcome!
          const isWin = seatOutcome === 'win' || seatOutcome === 'blackjack' || seatOutcome === 'charlie'

          allSeats[si] = { ...seat, hand: settledMain, splitHand: settledSplit, outcome: seatOutcome, payout: seatPayout }
          results.push({ seatIndex: si, outcome: seatOutcome, payout: seatPayout })

          totalPayout += seatPayout
          totalXp += calculateXP(seatOutcome)
          if (isWin) handsWon++
          if (seatOutcome === 'blackjack') bjCount++
        }

        // Primary outcome = most dramatic result
        const primaryOutcome = results.find(r => r.outcome === 'blackjack')?.outcome
          || results.find(r => r.outcome === 'win')?.outcome
          || results.find(r => r.outcome === 'charlie')?.outcome
          || results.find(r => r.outcome === 'push')?.outcome
          || results[0]?.outcome || 'loss'

        // ---- THE B-CARDD BET: Golden Hand resolution (RIDE IT, 200x) ----
        // If this round was armed as the Golden Hand, the player collects 200x their
        // (frozen) avg bet ONLY if they beat the dealer (win/blackjack/charlie). Push,
        // loss, or bust = 0 (the gambled-away guaranteed 100x is gone). Chips only.
        let goldenBonus = 0
        if (s2.goldenHandActive) {
          const beatDealer = handsWon > 0  // any active seat that won = beat the dealer
          goldenBonus = bcardPayout(s2.goldenHandAvgBet, 'ride', beatDealer)  // 200x, capped 888
        }
        const grandPayout = totalPayout + goldenBonus

        set({
          phase: 'settled',
          seats: allSeats,
          mainHand: allSeats[s2.activeSeatIndices[0]].hand,
          splitHand: allSeats[s2.activeSeatIndices[0]].splitHand,
          outcome: primaryOutcome,
          winAmount: grandPayout,
          xpEarned: totalXp,
          seatResults: results,
          dealerDrawQueue: [],
          // Golden Hand consumed this round; surface the bonus for the UI.
          goldenHandActive: false,
          bcardPayoutAmount: goldenBonus,
          player: {
            ...s2.player,
            // Add winnings to correct currency based on game mode (+ any golden bonus)
            chips: s2.gameMode === 'sc' ? s2.player.chips : s2.player.chips + grandPayout,
            sweepsCoins: s2.gameMode === 'sc' ? s2.player.sweepsCoins + grandPayout : s2.player.sweepsCoins,
            xp: s2.player.xp + totalXp,
            handsPlayed: s2.player.handsPlayed + s2.activeSeatIndices.length,
            handsWon: s2.player.handsWon + handsWon,
            blackjacks: s2.player.blackjacks + bjCount,
            currentStreak: handsWon > 0 ? s2.player.currentStreak + 1 : 0,
            bestStreak: handsWon > 0 ? Math.max(s2.player.bestStreak, s2.player.currentStreak + 1) : s2.player.bestStreak,
            biggestWin: Math.max(s2.player.biggestWin, grandPayout),
          },
        })
      }, totalDrawTime)
    }, 300)
  },

  playerDouble: () => {
    const state = get()
    if (state.phase !== 'player_turn' && state.phase !== 'split_turn') return
    const isScMode = state.gameMode === 'sc'
    const bal = isScMode ? state.player.sweepsCoins : state.player.chips
    if (bal < state.betAmount) return

    const isMainHand = state.currentHandIndex === 0
    const currentHand = isMainHand ? state.mainHand : state.splitHand!

    const result = doubleDown(currentHand, state.shoe)

    set({
      shoe: result.shoe,
      mainHand: isMainHand ? result.hand : state.mainHand,
      splitHand: isMainHand ? state.splitHand : result.hand,
      player: {
        ...state.player,
        chips: isScMode ? state.player.chips : state.player.chips - state.betAmount,
        sweepsCoins: isScMode ? state.player.sweepsCoins - state.betAmount : state.player.sweepsCoins,
        scPlaythroughWagered: isScMode ? state.player.scPlaythroughWagered + state.betAmount : state.player.scPlaythroughWagered,
      },
    })

    // After double, auto-stand (or bust)
    setTimeout(() => {
      const s = get()
      const hand = isMainHand ? s.mainHand : s.splitHand!
      if (hand.isBust) {
        if (s.splitHand && isMainHand) {
          set({ currentHandIndex: 1, phase: 'split_turn', mainHand: { ...hand, outcome: 'bust', payout: 0 } })
        } else {
          set({ phase: 'settled', outcome: 'bust', winAmount: hand.bet, mainHand: isMainHand ? { ...hand, outcome: 'bust', payout: 0 } : s.mainHand })
        }
      } else {
        get().playerStand()
      }
    }, 500)
  },

  playerSplit: () => {
    const state = get()
    if (state.phase !== 'player_turn') return
    const isScMode = state.gameMode === 'sc'
    const bal = isScMode ? state.player.sweepsCoins : state.player.chips
    if (bal < state.betAmount) return

    const result = split(state.mainHand, state.shoe)

    // Update both root-level AND per-seat splitHand
    const seats = [...state.seats]
    seats[state.currentSeatIndex] = {
      ...seats[state.currentSeatIndex],
      hand: result.mainHand,
      splitHand: result.splitHand,
    }

    set({
      mainHand: result.mainHand,
      splitHand: result.splitHand,
      seats,
      shoe: result.shoe,
      currentHandIndex: 0,
      player: {
        ...state.player,
        chips: isScMode ? state.player.chips : state.player.chips - state.betAmount,
        sweepsCoins: isScMode ? state.player.sweepsCoins - state.betAmount : state.player.sweepsCoins,
        scPlaythroughWagered: isScMode ? state.player.scPlaythroughWagered + state.betAmount : state.player.scPlaythroughWagered,
      },
      availableActions: getAvailableActions(result.mainHand, state.config, bal - state.betAmount, state.dealerHand.cards[0], true),
    })
  },

  playerSurrender: () => {
    const state = get()
    if (state.phase !== 'player_turn') return

    const result = surrender(state.mainHand)
    const xp = calculateXP('surrender')

    set({
      phase: 'settled',
      mainHand: result,
      outcome: 'surrender',
      winAmount: result.payout,
      xpEarned: xp,
      player: {
        ...state.player,
        chips: state.gameMode === 'sc' ? state.player.chips : state.player.chips + result.payout,
        sweepsCoins: state.gameMode === 'sc' ? state.player.sweepsCoins + result.payout : state.player.sweepsCoins,
        xp: state.player.xp + xp,
        handsPlayed: state.player.handsPlayed + 1,
      },
    })
  },

  playerInsurance: (take) => {
    const state = get()
    if (state.phase !== 'insurance') return
    const isScMode = state.gameMode === 'sc'

    if (take) {
      const insured = takeInsurance(state.mainHand)
      const cost = insured.insuranceBet
      const newBal = isScMode
        ? state.player.sweepsCoins - cost
        : state.player.chips - cost

      // DEALER PEEK: check if dealer has blackjack
      const dealerHand = state.dealerHand
      const revealedDealer = { ...dealerHand, cards: dealerHand.cards.map(c => ({ ...c, faceDown: false })) }
      const dealerEval = evaluateHand(revealedDealer.cards)

      if (dealerEval.isBlackjack) {
        const insurancePayout = insured.insuranceBet * 3
        set({
          phase: 'settled',
          mainHand: { ...insured, outcome: 'loss', payout: insurancePayout },
          dealerHand: revealedDealer,
          outcome: 'loss',
          winAmount: insurancePayout,
          xpEarned: 2,
          player: {
            ...state.player,
            chips: isScMode ? state.player.chips : newBal + insurancePayout,
            sweepsCoins: isScMode ? newBal + insurancePayout : state.player.sweepsCoins,
            handsPlayed: state.player.handsPlayed + 1,
          },
        })
        return
      }

      // Dealer does NOT have blackjack -- continue to player turn
      set({
        mainHand: insured,
        phase: 'player_turn',
        player: {
          ...state.player,
          chips: isScMode ? state.player.chips : newBal,
          sweepsCoins: isScMode ? newBal : state.player.sweepsCoins,
        },
        availableActions: getAvailableActions(insured, state.config, newBal, state.dealerHand.cards[0], false),
      })
    } else {
      // Declined insurance -- still peek
      const dealerHand = state.dealerHand
      const dealerEval = evaluateHand(dealerHand.cards)

      if (dealerEval.isBlackjack) {
        // Dealer has BJ -- reveal and settle (player loses, no insurance)
        const revealedDealer = { ...dealerHand, cards: dealerHand.cards.map(c => ({ ...c, faceDown: false })) }
        set({
          phase: 'settled',
          dealerHand: revealedDealer,
          outcome: 'loss',
          winAmount: 0,
          xpEarned: 2,
          player: {
            ...state.player,
            handsPlayed: state.player.handsPlayed + 1,
          },
        })
        return
      }

      set({
        phase: 'player_turn',
        availableActions: getAvailableActions(state.mainHand, state.config, state.player.chips, state.dealerHand.cards[0], false),
      })
    }
  },

  newRound: () => {
    const state = get()
    let shoe = state.shoe
    if (needsReshuffle(shoe)) shoe = createShoe(state.config.deckCount)

    // Reset to the SINGLE home seat every round. Extra hands (multi-seat) are opt-in
    // PER ROUND and must never carry over -- otherwise playing 2 hands once would lock
    // you into 2 forever with no way back to 1. The player re-adds extra seats freely.
    const seats = state.seats.map(s => createEmptySeat(s.index, s.index === HOME_SEAT))

    // ---- THE B-CARDD BET: promote a pending Golden Hand into the upcoming round ----
    // If the player chose RIDE IT last round, THIS new round is the Golden Hand:
    // play it normally at the current bet; beat the dealer for the 200x payout.
    const goldenHandActive = state.goldenHandPending

    set({
      phase: 'betting',
      shoe,
      seats,
      mainHand: { ...EMPTY_HAND },
      splitHand: null,
      dealerHand: { ...EMPTY_HAND },
      currentHandIndex: 0,
      currentSeatIndex: HOME_SEAT,
      activeSeatIndices: [HOME_SEAT],
      availableActions: [],
      sideBets: { ...EMPTY_SIDE_BETS },
      lightning: { ...EMPTY_LIGHTNING },
      dealQueue: [],
      dealerDrawQueue: [],
      outcome: null,
      winAmount: 0,
      xpEarned: 0,
      seatResults: [],
      betAmount: state.autoRebet ? state.betAmount : state.selectedChip,
      // B-Card per-round flags reset; Golden Hand status carried forward once.
      bcardActive: false,
      bcardChoice: null,
      bcardAvgBet: 0,
      bcardPayoutAmount: 0,
      goldenHandPending: false,
      goldenHandActive,
    })
  },

  setDealer: (dealer) => {
    // Always use the latest voiceId from DEFAULT_DEALERS
    const canonical = DEFAULT_DEALERS.find(d => d.id === dealer.id) || dealer
    set({ activeDealer: canonical, showDealerSelect: false })
    // Persist dealer selection
    if (typeof window !== 'undefined') {
      localStorage.setItem('vantaris_dealer', dealer.id)
    }
  },
  setDealerLine: (line) => {
    set({ dealerLine: line, speaking: true })
    // Auto-stop speaking indicator after 2.5s
    setTimeout(() => {
      if (get().dealerLine === line) set({ speaking: false })
    }, 2500)
  },

  togglePanel: (panel) => {
    const key = `show${panel.charAt(0).toUpperCase() + panel.slice(1)}` as keyof BlackjackStore
    set({ [key]: !get()[key] } as any)
  },

  toggleSideBet: (bet, amount) => {
    const state = get()
    const sideBets = { ...state.sideBets }
    const current = sideBets[bet]

    if (amount === 0) {
      // Clear this side bet (called when user long-presses or wants to remove)
      sideBets[bet] = { ...current, active: false, bet: 0 }
    } else if (current.active) {
      // Already active -- ADD more chips to it (stack bets)
      const bal = state.gameMode === 'sc' ? state.player.sweepsCoins : state.player.chips
      const totalBets = state.betAmount + Object.values(sideBets).reduce((sum, sb) => sum + sb.bet, 0)
      if (bal >= totalBets + amount) {
        sideBets[bet] = { ...current, bet: current.bet + amount }
      }
    } else {
      // Turn on -- place initial bet
      const bal = state.gameMode === 'sc' ? state.player.sweepsCoins : state.player.chips
      const totalBets = state.betAmount + Object.values(sideBets).reduce((sum, sb) => sum + sb.bet, 0)
      if (bal >= totalBets + amount) {
        sideBets[bet] = { ...current, active: true, bet: amount }
      }
    }
    set({ sideBets })
  },

  setTableVariant: (variant) => {
    set({
      config: createTableConfig(variant),
      shoe: createShoe(createTableConfig(variant).deckCount),
      phase: 'betting' as GamePhase,
      mainHand: { ...EMPTY_HAND },
      splitHand: null,
      dealerHand: { ...EMPTY_HAND },
      sideBets: { ...EMPTY_SIDE_BETS },
      lightning: { ...EMPTY_LIGHTNING },
    })
  },

  // ============================================================
  // THE B-CARDD BET ACTIONS
  // ============================================================

  setPlayerEmail: (email) => set({ playerEmail: email }),

  // TAKE IT: guaranteed auto-WIN of the current hand at 100x the QTD average bet.
  // Resolve immediately, credit bcardPayout(avgBet, 'take') in CHIPS (capped at 888).
  bcardTake: () => {
    const state = get()
    if (state.phase !== 'bcard_choice') return
    const jackpot = bcardPayout(state.bcardAvgBet, 'take')  // 100x, capped at 888
    // "House-staked, player risks nothing": return their staked bet (deducted at deal)
    // on top of the jackpot, since the hand auto-wins.
    const payout = jackpot + state.mainHand.bet
    const reveal = { ...state.dealerHand, cards: state.dealerHand.cards.map(c => ({ ...c, faceDown: false })) }
    const wonHand: HandState = { ...state.mainHand, outcome: 'win', payout }
    const seats = [...state.seats]
    seats[state.currentSeatIndex] = { ...seats[state.currentSeatIndex], hand: wonHand, outcome: 'win', payout }

    set({
      phase: 'settled',
      mainHand: wonHand,
      dealerHand: reveal,
      seats,
      outcome: 'win',
      winAmount: payout,
      xpEarned: calculateXP('win'),
      seatResults: [{ seatIndex: state.currentSeatIndex, outcome: 'win', payout }],
      bcardActive: true,
      bcardChoice: 'take',
      bcardPayoutAmount: jackpot,
      // Phase 1 = chips only. TODO(Phase 2): pay SC in sweeps mode + log via edge fn
      // bcard-resolve (server-authoritative avg bet + 888 cap on the redeemable side).
      player: {
        ...state.player,
        chips: state.gameMode === 'sc' ? state.player.chips : state.player.chips + payout,
        sweepsCoins: state.gameMode === 'sc' ? state.player.sweepsCoins + payout : state.player.sweepsCoins,
        xp: state.player.xp + calculateXP('win'),
        handsPlayed: state.player.handsPlayed + 1,
        handsWon: state.player.handsWon + 1,
        currentStreak: state.player.currentStreak + 1,
        bestStreak: Math.max(state.player.bestStreak, state.player.currentStreak + 1),
        biggestWin: Math.max(state.player.biggestWin, payout),
      },
    })
  },

  // RIDE IT: the B-Card stays as the 8 in the current hand; the player keeps playing
  // at their current bet. The NEXT hand becomes the Golden Hand (200x if they beat the
  // dealer). Freeze the avg-bet basis NOW so the 200x is computed off this quarter.
  bcardRide: () => {
    const state = get()
    if (state.phase !== 'bcard_choice') return
    // Arm the Golden Hand for the NEXT round and freeze the avg-bet basis now.
    const dealerUpcard = state.dealerHand.cards[0]
    const handEval = evaluateHand(state.mainHand.cards)
    set({
      bcardActive: true,
      bcardChoice: 'ride',
      goldenHandPending: true,
      goldenHandAvgBet: state.bcardAvgBet,
    })
    // Resume normal play of the current hand (the B-Card already sits in it as an 8).
    if (handEval.isBust || handEval.isCharlie) {
      // The B-Card 8 ended the hand -> settle this round, Golden Hand still armed.
      const busted = handEval.isBust
      const seats = [...state.seats]
      seats[state.currentSeatIndex] = {
        ...seats[state.currentSeatIndex],
        hand: { ...state.mainHand, outcome: busted ? 'bust' : 'charlie', payout: busted ? 0 : state.mainHand.bet * 2 },
      }
      set({ seats, mainHand: seats[state.currentSeatIndex].hand, phase: 'player_turn' })
      setTimeout(() => get().playerStand(), 100)
      return
    }
    const actions = getAvailableActions(state.mainHand, state.config, state.player.chips, dealerUpcard, !!state.splitHand)
    set({ phase: 'player_turn', availableActions: actions })
  },
}),
    {
      name: 'vantaris-player',
      // Only persist player data + settings. NEVER persist game state (shoe, hands, phase).
      partialize: (state) => ({
        player: state.player,
        musicEnabled: state.musicEnabled,
        voiceEnabled: state.voiceEnabled,
        autoRebet: state.autoRebet,
        gameMode: state.gameMode,
        selectedChip: state.selectedChip,
        betAmount: state.betAmount,
      }),
      // Merge persisted data with fresh defaults on hydration
      merge: (persisted: any, current) => {
        if (!persisted) return current
        // ALWAYS restore dealer from DEFAULT_DEALERS (source of truth for voice IDs)
        // Check both localStorage key and persisted state for dealer ID
        let activeDealer = current.activeDealer
        const savedId = (typeof window !== 'undefined' ? localStorage.getItem('vantaris_dealer') : null)
          || persisted?.activeDealer?.id
        if (savedId) {
          const found = DEFAULT_DEALERS.find(d => d.id === savedId)
          if (found) activeDealer = found // Always uses latest voice IDs
        }
        // One-time test deposit: 10K chips if below 100
        const mergedPlayer = { ...FRESH_PLAYER, ...(persisted.player || {}) }
        if (mergedPlayer.chips < 100) {
          mergedPlayer.chips += 10000
        }
        // One-time SC test deposit
        if (mergedPlayer.sweepsCoins < 100) {
          mergedPlayer.sweepsCoins += 1000
        }
        return {
          ...current,
          player: mergedPlayer,
          musicEnabled: persisted.musicEnabled ?? true,
          voiceEnabled: persisted.voiceEnabled ?? true,
          autoRebet: persisted.autoRebet ?? false,
          gameMode: (persisted as any).gameMode ?? 'gc',
          selectedChip: persisted.selectedChip ?? 100,
          betAmount: persisted.betAmount ?? 100,
          activeDealer,
        }
      },
    },
  ),
)
