/**
 * Vantaris Blackjack Engine
 *
 * Pure game logic. No UI. No React. No DOM.
 * This module handles EVERYTHING about how blackjack works:
 *
 * - Shoe management (1/2/4/6/8 deck, auto-reshuffle)
 * - Card dealing (correct casino order: P1, D1, P2, D2-facedown)
 * - Hand evaluation (value, soft/hard, bust, blackjack, Charlie)
 * - Player actions (hit, stand, double, split, surrender, insurance)
 * - Split hands (independent play, re-split aces, double after split)
 * - Dealer play (hits to hard 17, soft 17 configurable)
 * - Settlement (all outcomes, presence multiplier, side bet payouts)
 * - Side bets (Perfect Pairs, 21+3, Lucky Ladies, progressive)
 * - Lightning multipliers (random 2x-25x per round)
 * - Six Card Charlie (6 cards <= 21 = auto-win)
 * - Multi-hand mode (2-3 simultaneous hands)
 *
 * The UI reads state from this engine. The engine never touches the DOM.
 */

// ============================================================
// TYPES
// ============================================================

export type Suit = 'spades' | 'hearts' | 'diamonds' | 'clubs'
export type Rank = 'A' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9' | '10' | 'J' | 'Q' | 'K'

export interface Card {
  rank: Rank
  suit: Suit
  faceDown: boolean
  skinId?: string      // visual skin override
  rarity?: CardRarity  // visual rarity tier
  xp?: number          // card XP (for leveling system)
}

export type CardRarity = 'common' | 'uncommon' | 'rare' | 'mythic' | 'legendary'

export type GamePhase =
  | 'betting'       // placing bets
  | 'dealing'       // cards being dealt (animated)
  | 'insurance'     // dealer shows Ace, insurance offered
  | 'player_turn'   // player making decisions
  | 'split_turn'    // playing split hand
  | 'dealer_turn'   // dealer revealing + drawing
  | 'settled'       // round complete, showing result

export type Outcome =
  | 'blackjack'     // natural 21
  | 'win'           // beat the dealer
  | 'loss'          // dealer wins
  | 'push'          // tie
  | 'bust'          // over 21
  | 'surrender'     // gave up half bet
  | 'charlie'       // 6-card charlie auto-win

export type PlayerAction = 'hit' | 'stand' | 'double' | 'split' | 'surrender' | 'insurance' | 'no_insurance'

export interface HandState {
  cards: Card[]
  value: number
  softValue: number   // value counting all aces as 11
  isSoft: boolean     // has a flexible ace
  isBust: boolean
  isBlackjack: boolean
  isCharlie: boolean  // 6+ cards without busting
  bet: number
  outcome: Outcome | null
  payout: number
  doubled: boolean
  surrendered: boolean
  insured: boolean
  insuranceBet: number
  insurancePayout: number
}

export interface SideBetState {
  perfectPairs: { active: boolean; bet: number; result: string | null; payout: number }
  twentyOnePlus3: { active: boolean; bet: number; result: string | null; payout: number }
  luckyLadies: { active: boolean; bet: number; result: string | null; payout: number }
  progressive: { active: boolean; bet: number; result: string | null; payout: number }
}

export interface LightningState {
  active: boolean
  fee: number           // 100% of base bet
  multipliedTotal: number | null  // which hand total gets boosted
  multiplier: number    // 2x-25x
}

export interface RoundState {
  phase: GamePhase
  mainHand: HandState
  splitHand: HandState | null
  dealerHand: HandState
  sideBets: SideBetState
  lightning: LightningState
  availableActions: PlayerAction[]
  currentHandIndex: number  // 0 = main, 1 = split
  streak: number
  xpEarned: number
}

export interface TableConfig {
  deckCount: number        // 1, 2, 4, 6, or 8
  minBet: number
  maxBet: number
  blackjackPays: '3:2' | '6:5'
  dealerHitsSoft17: boolean
  doubleAfterSplit: boolean
  resplitAces: boolean
  surrenderAllowed: boolean
  sixCardCharlie: boolean
  lightningEnabled: boolean
  sideBetsEnabled: boolean
  variant: 'classic' | 'lightning' | 'speed' | 'switch' | 'highroller'
}

// ============================================================
// CONSTANTS
// ============================================================

const ALL_SUITS: Suit[] = ['spades', 'hearts', 'diamonds', 'clubs']
const ALL_RANKS: Rank[] = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

const SUIT_COLORS: Record<Suit, 'red' | 'black'> = {
  spades: 'black', clubs: 'black', hearts: 'red', diamonds: 'red',
}

const LIGHTNING_MULTIPLIERS = [2, 5, 8, 10, 15, 20, 25]
const LIGHTNING_TOTALS = [17, 18, 19, 20, 21] // which totals can get multiplied

const DEFAULT_CONFIG: TableConfig = {
  deckCount: 6,
  minBet: 10,
  maxBet: 50000,
  blackjackPays: '3:2',
  dealerHitsSoft17: false,
  doubleAfterSplit: true,
  resplitAces: false,
  surrenderAllowed: true,
  sixCardCharlie: true,
  lightningEnabled: false,
  sideBetsEnabled: true,
  variant: 'classic',
}

// ============================================================
// SHOE (deck management)
// ============================================================

export function createShoe(deckCount: number = 6): Card[] {
  const shoe: Card[] = []
  for (let d = 0; d < deckCount; d++) {
    for (const suit of ALL_SUITS) {
      for (const rank of ALL_RANKS) {
        shoe.push({ rank, suit, faceDown: false })
      }
    }
  }
  return shuffleShoe(shoe)
}

export function shuffleShoe(shoe: Card[]): Card[] {
  const shuffled = [...shoe]
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }
  return shuffled
}

export function needsReshuffle(shoe: Card[], threshold: number = 15): boolean {
  return shoe.length < threshold
}

// ============================================================
// HAND EVALUATION
// ============================================================

export function cardValue(card: Card): number {
  if (['J', 'Q', 'K'].includes(card.rank)) return 10
  if (card.rank === 'A') return 11
  return parseInt(card.rank)
}

export function evaluateHand(cards: Card[]): {
  value: number; softValue: number; isSoft: boolean;
  isBust: boolean; isBlackjack: boolean; isCharlie: boolean
} {
  const visible = cards.filter(c => !c.faceDown)
  let total = 0
  let aces = 0
  let softTotal = 0

  for (const card of visible) {
    const val = cardValue(card)
    total += val
    softTotal += val
    if (card.rank === 'A') aces++
  }

  // Soft total = all aces at 11
  // Hard total = reduce aces as needed
  while (total > 21 && aces > 0) {
    total -= 10
    aces--
  }

  const isSoft = aces > 0 && total <= 21
  const isBlackjack = visible.length === 2 && total === 21
  const isCharlie = visible.length >= 6 && total <= 21

  return {
    value: total,
    softValue: softTotal,
    isSoft,
    isBust: total > 21,
    isBlackjack,
    isCharlie,
  }
}

// ============================================================
// DEALING (correct casino order)
// ============================================================

/**
 * Deal initial cards in correct casino order:
 * 1. Player card 1 (face up)
 * 2. Dealer card 1 (face up)
 * 3. Player card 2 (face up)
 * 4. Dealer card 2 (face DOWN)
 *
 * Returns an array of deal events with timing info
 * so the UI can animate them in sequence.
 */
export interface DealEvent {
  target: 'player' | 'dealer'
  card: Card
  faceDown: boolean
  delayMs: number  // ms from start of deal sequence
}

export function generateDealSequence(shoe: Card[]): {
  events: DealEvent[]
  remainingShoe: Card[]
} {
  const cards = shoe.slice(0, 4)
  const remaining = shoe.slice(4)

  const events: DealEvent[] = [
    { target: 'player', card: { ...cards[0], faceDown: false }, faceDown: false, delayMs: 0 },
    { target: 'dealer', card: { ...cards[1], faceDown: false }, faceDown: false, delayMs: 300 },
    { target: 'player', card: { ...cards[2], faceDown: false }, faceDown: false, delayMs: 600 },
    { target: 'dealer', card: { ...cards[3], faceDown: true },  faceDown: true,  delayMs: 900 },
  ]

  return { events, remainingShoe: remaining }
}

// ============================================================
// PLAYER ACTIONS
// ============================================================

export function getAvailableActions(
  hand: HandState,
  config: TableConfig,
  playerChips: number,
  dealerUpcard: Card,
  hasSplitHand: boolean,
): PlayerAction[] {
  const actions: PlayerAction[] = []
  const eval_ = evaluateHand(hand.cards)

  if (eval_.isBust || eval_.isBlackjack || eval_.isCharlie || hand.outcome) {
    return [] // no actions available
  }

  // Always can hit (unless 21)
  if (eval_.value < 21) actions.push('hit')

  // Always can stand
  actions.push('stand')

  // Double: only on first two cards, must have chips
  if (hand.cards.length === 2 && !hand.doubled && playerChips >= hand.bet) {
    actions.push('double')
  }

  // Split: first two cards same rank, must have chips, no existing split
  if (
    hand.cards.length === 2 &&
    !hasSplitHand &&
    hand.cards[0].rank === hand.cards[1].rank &&
    playerChips >= hand.bet
  ) {
    actions.push('split')
  }

  // Surrender: first two cards only, if allowed
  if (hand.cards.length === 2 && config.surrenderAllowed && !hand.doubled) {
    actions.push('surrender')
  }

  // Insurance: dealer shows Ace, first decision, not already insured
  if (
    dealerUpcard.rank === 'A' &&
    hand.cards.length === 2 &&
    !hand.insured &&
    playerChips >= Math.floor(hand.bet / 2)
  ) {
    actions.push('insurance')
    actions.push('no_insurance')
  }

  return actions
}

export function hit(hand: HandState, shoe: Card[]): {
  hand: HandState; shoe: Card[]; autoBust: boolean; autoCharlie: boolean
} {
  const card = { ...shoe[0], faceDown: false }
  const newCards = [...hand.cards, card]
  const eval_ = evaluateHand(newCards)
  const newShoe = shoe.slice(1)

  const newHand: HandState = {
    ...hand,
    cards: newCards,
    value: eval_.value,
    softValue: eval_.softValue,
    isSoft: eval_.isSoft,
    isBust: eval_.isBust,
    isBlackjack: eval_.isBlackjack,
    isCharlie: eval_.isCharlie,
  }

  return {
    hand: newHand,
    shoe: newShoe,
    autoBust: eval_.isBust,
    autoCharlie: eval_.isCharlie,
  }
}

export function doubleDown(hand: HandState, shoe: Card[]): {
  hand: HandState; shoe: Card[]
} {
  const card = { ...shoe[0], faceDown: false }
  const newCards = [...hand.cards, card]
  const eval_ = evaluateHand(newCards)
  const newShoe = shoe.slice(1)

  return {
    hand: {
      ...hand,
      cards: newCards,
      bet: hand.bet * 2,
      doubled: true,
      value: eval_.value,
      softValue: eval_.softValue,
      isSoft: eval_.isSoft,
      isBust: eval_.isBust,
      isBlackjack: eval_.isBlackjack,
      isCharlie: eval_.isCharlie,
    },
    shoe: newShoe,
  }
}

export function split(hand: HandState, shoe: Card[]): {
  mainHand: HandState; splitHand: HandState; shoe: Card[]
} {
  const card1 = { ...shoe[0], faceDown: false }
  const card2 = { ...shoe[1], faceDown: false }
  const newShoe = shoe.slice(2)

  const mainCards = [hand.cards[0], card1]
  const splitCards = [hand.cards[1], card2]
  const mainEval = evaluateHand(mainCards)
  const splitEval = evaluateHand(splitCards)

  const makeHand = (cards: Card[], eval_: ReturnType<typeof evaluateHand>): HandState => ({
    cards,
    value: eval_.value,
    softValue: eval_.softValue,
    isSoft: eval_.isSoft,
    isBust: eval_.isBust,
    isBlackjack: false, // split hands can't be natural blackjack
    isCharlie: eval_.isCharlie,
    bet: hand.bet, // each hand gets original bet
    outcome: null,
    payout: 0,
    doubled: false,
    surrendered: false,
    insured: hand.insured,
    insuranceBet: 0,
    insurancePayout: 0,
  })

  return {
    mainHand: makeHand(mainCards, mainEval),
    splitHand: makeHand(splitCards, splitEval),
    shoe: newShoe,
  }
}

export function surrender(hand: HandState): HandState {
  return {
    ...hand,
    surrendered: true,
    outcome: 'surrender',
    payout: Math.floor(hand.bet / 2),
  }
}

export function takeInsurance(hand: HandState): HandState {
  const insuranceBet = Math.floor(hand.bet / 2)
  return {
    ...hand,
    insured: true,
    insuranceBet,
  }
}

// ============================================================
// DEALER PLAY
// ============================================================

export interface DealerDrawEvent {
  card: Card
  newValue: number
  delayMs: number
}

export function playDealer(
  dealerHand: HandState,
  shoe: Card[],
  config: TableConfig,
): {
  hand: HandState
  draws: DealerDrawEvent[]
  shoe: Card[]
} {
  // Reveal hole card
  let cards = dealerHand.cards.map(c => ({ ...c, faceDown: false }))
  let currentShoe = [...shoe]
  const draws: DealerDrawEvent[] = []
  let drawIndex = 0

  let eval_ = evaluateHand(cards)

  // Dealer draws to 17 (or soft 17 if configured)
  while (eval_.value < 17 || (config.dealerHitsSoft17 && eval_.value === 17 && eval_.isSoft)) {
    const card = { ...currentShoe[0], faceDown: false }
    cards = [...cards, card]
    currentShoe = currentShoe.slice(1)
    eval_ = evaluateHand(cards)
    drawIndex++

    draws.push({
      card,
      newValue: eval_.value,
      delayMs: drawIndex * 600, // 600ms between each dealer draw
    })
  }

  return {
    hand: {
      ...dealerHand,
      cards,
      value: eval_.value,
      softValue: eval_.softValue,
      isSoft: eval_.isSoft,
      isBust: eval_.isBust,
      isBlackjack: eval_.isBlackjack,
      isCharlie: false,
    },
    draws,
    shoe: currentShoe,
  }
}

// ============================================================
// SETTLEMENT
// ============================================================

export function settleHand(
  playerHand: HandState,
  dealerHand: HandState,
  config: TableConfig,
  presenceMultiplier: number = 1.0,
  lightningMultiplier: number = 1,
): HandState {
  const pv = playerHand.value
  const dv = dealerHand.value

  if (playerHand.surrendered) {
    return playerHand // already settled
  }

  let outcome: Outcome
  let payout = 0

  // Six Card Charlie
  if (playerHand.isCharlie && config.sixCardCharlie) {
    outcome = 'charlie'
    payout = Math.floor(playerHand.bet * 2 * presenceMultiplier * lightningMultiplier)
  }
  // Player bust
  else if (playerHand.isBust) {
    outcome = 'bust'
    payout = 0
  }
  // Player blackjack
  else if (playerHand.isBlackjack) {
    if (dealerHand.isBlackjack) {
      outcome = 'push'
      payout = playerHand.bet
    } else {
      outcome = 'blackjack'
      const bjMultiplier = config.blackjackPays === '3:2' ? 2.5 : 2.2
      payout = Math.floor(playerHand.bet * bjMultiplier * presenceMultiplier * lightningMultiplier)
    }
  }
  // Dealer bust
  else if (dealerHand.isBust) {
    outcome = 'win'
    payout = Math.floor(playerHand.bet * 2 * presenceMultiplier * lightningMultiplier)
  }
  // Compare
  else if (pv > dv) {
    outcome = 'win'
    payout = Math.floor(playerHand.bet * 2 * presenceMultiplier * lightningMultiplier)
  }
  else if (pv < dv) {
    outcome = 'loss'
    payout = 0
  }
  else {
    outcome = 'push'
    payout = playerHand.bet
  }

  // Insurance payout (if dealer has blackjack)
  let insurancePayout = 0
  if (playerHand.insured) {
    if (dealerHand.isBlackjack) {
      insurancePayout = playerHand.insuranceBet * 3 // 2:1 + original bet back
    }
  }

  return {
    ...playerHand,
    outcome,
    payout,
    insurancePayout,
  }
}

// ============================================================
// SIDE BETS
// ============================================================

export function evaluatePerfectPairs(card1: Card, card2: Card): {
  result: string | null; multiplier: number
} {
  if (card1.rank !== card2.rank) return { result: null, multiplier: 0 }

  if (card1.suit === card2.suit) {
    return { result: 'perfect_pair', multiplier: 25 }
  }
  if (SUIT_COLORS[card1.suit] === SUIT_COLORS[card2.suit]) {
    return { result: 'colored_pair', multiplier: 12 }
  }
  return { result: 'mixed_pair', multiplier: 5 }
}

export function evaluate21Plus3(
  playerCard1: Card, playerCard2: Card, dealerUpcard: Card,
): { result: string | null; multiplier: number } {
  const cards = [playerCard1, playerCard2, dealerUpcard]
  const ranks = cards.map(c => cardValue(c)).sort((a, b) => a - b)
  const suits = cards.map(c => c.suit)
  const values = cards.map(c => {
    if (c.rank === 'A') return 1
    if (['J', 'Q', 'K'].includes(c.rank)) return [11, 12, 13][['J', 'Q', 'K'].indexOf(c.rank)]
    return parseInt(c.rank)
  }).sort((a, b) => a - b)

  const allSameSuit = suits[0] === suits[1] && suits[1] === suits[2]
  const allSameRank = cards[0].rank === cards[1].rank && cards[1].rank === cards[2].rank
  const isSequential = values[2] - values[1] === 1 && values[1] - values[0] === 1

  // Check for Ace-high straight (Q-K-A)
  const aceHighStraight = values.includes(1) && values.includes(12) && values.includes(13)

  const isStraight = isSequential || aceHighStraight

  if (allSameRank && allSameSuit) return { result: 'suited_trips', multiplier: 100 }
  if (isStraight && allSameSuit) return { result: 'straight_flush', multiplier: 40 }
  if (allSameRank) return { result: 'three_of_a_kind', multiplier: 30 }
  if (isStraight) return { result: 'straight', multiplier: 10 }
  if (allSameSuit) return { result: 'flush', multiplier: 5 }

  return { result: null, multiplier: 0 }
}

export function evaluateLuckyLadies(
  card1: Card, card2: Card, dealerHasBlackjack: boolean,
): { result: string | null; multiplier: number } {
  const total = cardValue(card1) + cardValue(card2)
  // Adjust for aces
  let adjustedTotal = total
  if (adjustedTotal > 21 && (card1.rank === 'A' || card2.rank === 'A')) {
    adjustedTotal -= 10
  }

  if (adjustedTotal !== 20) return { result: null, multiplier: 0 }

  // Queen of Hearts pair + dealer blackjack
  if (card1.rank === 'Q' && card1.suit === 'hearts' &&
      card2.rank === 'Q' && card2.suit === 'hearts' && dealerHasBlackjack) {
    return { result: 'qh_pair_dealer_bj', multiplier: 1000 }
  }
  // Queen of Hearts pair
  if (card1.rank === 'Q' && card1.suit === 'hearts' &&
      card2.rank === 'Q' && card2.suit === 'hearts') {
    return { result: 'qh_pair', multiplier: 125 }
  }
  // Matched 20 (same rank + suit)
  if (card1.rank === card2.rank && card1.suit === card2.suit) {
    return { result: 'matched_20', multiplier: 19 }
  }
  // Suited 20
  if (card1.suit === card2.suit) {
    return { result: 'suited_20', multiplier: 9 }
  }
  // Any 20
  return { result: 'any_20', multiplier: 4 }
}

// ============================================================
// BAD BUSTER SIDE BET
// Pays when the DEALER BUSTS. Higher payout for more cards.
// ============================================================

export function evaluateBadBuster(
  dealerHand: HandState,
): { result: string | null; multiplier: number } {
  if (!dealerHand.isBust) return { result: null, multiplier: 0 }

  const cardCount = dealerHand.cards.length
  // Payouts based on how many cards dealer busts with
  if (cardCount === 3) return { result: 'bust_3_cards', multiplier: 2 }    // 2:1
  if (cardCount === 4) return { result: 'bust_4_cards', multiplier: 4 }    // 4:1
  if (cardCount === 5) return { result: 'bust_5_cards', multiplier: 8 }    // 8:1
  if (cardCount === 6) return { result: 'bust_6_cards', multiplier: 15 }   // 15:1
  if (cardCount === 7) return { result: 'bust_7_cards', multiplier: 50 }   // 50:1
  if (cardCount >= 8) return { result: 'bust_8_plus', multiplier: 250 }    // 250:1
  return { result: 'bust', multiplier: 2 }
}

// ============================================================
// PROGRESSIVE SIDE BET
// Suited diamond 7-7-7 = full jackpot
// Other poker hands pay percentages
// ============================================================

export function evaluateProgressive(
  playerCards: Card[], dealerUpcard: Card,
): { result: string | null; multiplier: number; isJackpot: boolean } {
  const allCards = [...playerCards.slice(0, 2), dealerUpcard] // first 2 player + dealer up

  // Check for suited 7-7-7 (JACKPOT)
  const sevens = allCards.filter(c => c.rank === '7')
  if (sevens.length === 3 && sevens.every(c => c.suit === 'diamonds')) {
    return { result: 'suited_777_diamonds', multiplier: 0, isJackpot: true } // pays from progressive pool
  }

  // Suited 7-7-7 any suit
  if (sevens.length === 3 && sevens[0].suit === sevens[1].suit && sevens[1].suit === sevens[2].suit) {
    return { result: 'suited_777', multiplier: 500, isJackpot: false }
  }

  // Any 7-7-7
  if (sevens.length === 3) {
    return { result: 'any_777', multiplier: 100, isJackpot: false }
  }

  // Suited three of a kind
  if (allCards[0].rank === allCards[1].rank && allCards[1].rank === allCards[2].rank &&
      allCards[0].suit === allCards[1].suit && allCards[1].suit === allCards[2].suit) {
    return { result: 'suited_trips', multiplier: 200, isJackpot: false }
  }

  // Three of a kind
  if (allCards[0].rank === allCards[1].rank && allCards[1].rank === allCards[2].rank) {
    return { result: 'trips', multiplier: 30, isJackpot: false }
  }

  // Straight flush (3 cards in sequence, same suit)
  const vals = allCards.map(c => cardValue(c)).sort((a, b) => a - b)
  const sameSuit = allCards[0].suit === allCards[1].suit && allCards[1].suit === allCards[2].suit
  const isSequence = vals[2] - vals[1] === 1 && vals[1] - vals[0] === 1

  if (sameSuit && isSequence) return { result: 'straight_flush', multiplier: 40, isJackpot: false }
  if (isSequence) return { result: 'straight', multiplier: 10, isJackpot: false }
  if (sameSuit) return { result: 'flush', multiplier: 5, isJackpot: false }

  return { result: null, multiplier: 0, isJackpot: false }
}

// ============================================================
// LIGHTNING SYSTEM
// ============================================================

export function generateLightning(): LightningState {
  const multiplier = LIGHTNING_MULTIPLIERS[Math.floor(Math.random() * LIGHTNING_MULTIPLIERS.length)]
  const total = LIGHTNING_TOTALS[Math.floor(Math.random() * LIGHTNING_TOTALS.length)]

  return {
    active: true,
    fee: 0, // calculated as 100% of bet at bet time
    multipliedTotal: total,
    multiplier,
  }
}

// ============================================================
// XP CALCULATION
// ============================================================

export function calculateXP(outcome: Outcome): number {
  switch (outcome) {
    case 'blackjack': return 20
    case 'charlie': return 25
    case 'win': return 10
    case 'push': return 3
    case 'surrender': return 2
    case 'loss': return 2
    case 'bust': return 2
    default: return 1
  }
}

// ============================================================
// TABLE CONFIGS (presets for each variant)
// ============================================================

export const TABLE_PRESETS: Record<string, Partial<TableConfig>> = {
  classic: {
    variant: 'classic',
    deckCount: 6,
    minBet: 10,
    maxBet: 5000,
    blackjackPays: '3:2',
    lightningEnabled: false,
    dealerHitsSoft17: true,
  },
  lightning: {
    variant: 'lightning',
    deckCount: 8,
    minBet: 50,
    maxBet: 25000,
    blackjackPays: '3:2',
    lightningEnabled: true,
  },
  speed: {
    variant: 'speed',
    deckCount: 6,
    minBet: 25,
    maxBet: 10000,
    blackjackPays: '3:2',
    lightningEnabled: false,
  },
  switch: {
    variant: 'switch',
    deckCount: 6,
    minBet: 100,
    maxBet: 25000,
    blackjackPays: '6:5', // switch pays even money on BJ
  },
  highroller: {
    variant: 'highroller',
    deckCount: 8,
    minBet: 500,
    maxBet: 50000,
    blackjackPays: '3:2',
    lightningEnabled: true,
    sideBetsEnabled: true,
  },
}

export function createTableConfig(variant: string): TableConfig {
  return { ...DEFAULT_CONFIG, ...TABLE_PRESETS[variant] || {} }
}
