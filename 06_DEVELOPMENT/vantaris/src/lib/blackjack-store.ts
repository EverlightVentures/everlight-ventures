/**
 * Vantaris Blackjack State Store (Zustand)
 *
 * Single source of truth for ALL blackjack game state.
 * The UI reads from this store. Actions dispatch through the engine.
 *
 * This replaces the scattered useState calls in the page component.
 */

import { create } from 'zustand'
import type {
  Card, GamePhase, Outcome, HandState, SideBetState,
  LightningState, TableConfig, DealEvent, DealerDrawEvent,
} from './blackjack-engine'
import {
  createShoe, needsReshuffle, evaluateHand,
  generateDealSequence, hit, doubleDown, split, surrender,
  takeInsurance, playDealer, settleHand, getAvailableActions,
  evaluatePerfectPairs, evaluate21Plus3, evaluateLuckyLadies,
  generateLightning, calculateXP, createTableConfig,
} from './blackjack-engine'

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
  chips: number
  gems: number
  sweepsCoins: number
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
  equippedDeckSkin: string
  equippedCardBack: string
}

interface BlackjackStore {
  // Game state
  phase: GamePhase
  shoe: Card[]
  config: TableConfig
  betAmount: number
  selectedChip: number

  // Hands
  mainHand: HandState
  splitHand: HandState | null
  dealerHand: HandState
  currentHandIndex: number
  availableActions: string[]

  // Side bets
  sideBets: SideBetState
  lightning: LightningState

  // Deal animation queue
  dealQueue: DealEvent[]
  dealerDrawQueue: DealerDrawEvent[]

  // Outcome
  outcome: Outcome | null
  winAmount: number
  xpEarned: number

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

  // Timers
  resultTimer: number | null

  // Actions
  setBet: (amount: number) => void
  selectChip: (value: number) => void
  deal: () => void
  playerHit: () => void
  playerStand: () => void
  playerDouble: () => void
  playerSplit: () => void
  playerSurrender: () => void
  playerInsurance: (take: boolean) => void
  newRound: () => void
  setDealer: (dealer: DealerPersona) => void
  togglePanel: (panel: string) => void
  setDealerLine: (line: string) => void
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
  { id: 'bacardi', name: 'Bacardi Ice', title: 'VIP Elite', vip: true, voiceId: 'onwK4e9ZLuTAKqWW03F9', color: '#00bcd4' },
]

// ============================================================
// CREATE STORE
// ============================================================

export const useBlackjackStore = create<BlackjackStore>((set, get) => ({
  // Initial state
  phase: 'betting',
  shoe: createShoe(6),
  config: createTableConfig('classic'),
  betAmount: 100,
  selectedChip: 100,

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

  activeDealer: DEFAULT_DEALERS[0],
  dealerLine: 'Take your time. The cards are patient.',
  speaking: false,

  bots: ['Vegas Vic', 'Lucky Lou', 'Miss Fortune', 'Big Stack Bobby'].map((name, i) => ({
    name, chips: 800 + Math.floor(Math.random() * 4000),
    hand: [], bet: 0, outcome: null,
    sittingOut: Math.random() < 0.2,
    color: ['#27ae60', '#e74c3c', '#9b59b6', '#e67e22'][i],
    seat: [0, 1, 3, 4][i],
  })),

  player: {
    chips: 12450, gems: 45, sweepsCoins: 24.50, xp: 3200, rank: 'Gold',
    handsPlayed: 87, handsWon: 41, blackjacks: 6, currentStreak: 0,
    bestStreak: 7, biggestWin: 5000, presenceMultiplier: 1.25,
    unlockedAchievements: ['first_win'],
    equippedDeckSkin: 'classic',
    equippedCardBack: 'classic_navy',
  },

  showBoutique: false,
  showGemStore: false,
  showFreeChips: false,
  showProfile: false,
  showLeaderboard: false,
  showAvatarBuilder: false,
  showDealerSelect: false,
  musicEnabled: false,
  voiceEnabled: false,

  resultTimer: null,

  // ============================================================
  // ACTIONS
  // ============================================================

  setBet: (amount) => set({ betAmount: amount }),
  selectChip: (value) => set({ selectedChip: value, betAmount: value }),

  deal: () => {
    const state = get()
    if (state.phase !== 'betting') return
    if (state.betAmount < state.config.minBet) return
    if (state.betAmount > state.player.chips) return

    // Reshuffle if needed
    let shoe = state.shoe
    if (needsReshuffle(shoe)) shoe = createShoe(state.config.deckCount)

    // Deduct bet
    const newChips = state.player.chips - state.betAmount

    // Generate deal sequence
    const { events, remainingShoe } = generateDealSequence(shoe)

    // Build initial hands from deal events
    const playerCards = events.filter(e => e.target === 'player').map(e => e.card)
    const dealerCards = events.filter(e => e.target === 'dealer').map(e => e.card)

    const playerEval = evaluateHand(playerCards)
    const dealerEval = evaluateHand(dealerCards)

    // Lightning
    let lightning = { ...EMPTY_LIGHTNING }
    if (state.config.lightningEnabled) {
      lightning = generateLightning()
      lightning.fee = state.betAmount // 100% fee
    }

    // Side bets evaluation (if any are active)
    const sideBets = { ...state.sideBets }
    if (sideBets.perfectPairs.active) {
      const pp = evaluatePerfectPairs(playerCards[0], playerCards[1])
      sideBets.perfectPairs.result = pp.result
      sideBets.perfectPairs.payout = pp.result ? sideBets.perfectPairs.bet * pp.multiplier : 0
    }
    if (sideBets.twentyOnePlus3.active) {
      const dealerUpcard = dealerCards[0]
      const t3 = evaluate21Plus3(playerCards[0], playerCards[1], dealerUpcard)
      sideBets.twentyOnePlus3.result = t3.result
      sideBets.twentyOnePlus3.payout = t3.result ? sideBets.twentyOnePlus3.bet * t3.multiplier : 0
    }

    const mainHand: HandState = {
      ...EMPTY_HAND,
      cards: playerCards,
      value: playerEval.value,
      softValue: playerEval.softValue,
      isSoft: playerEval.isSoft,
      isBust: playerEval.isBust,
      isBlackjack: playerEval.isBlackjack,
      isCharlie: playerEval.isCharlie,
      bet: state.betAmount,
    }

    const dealerHand: HandState = {
      ...EMPTY_HAND,
      cards: dealerCards,
      value: dealerEval.value,
      softValue: dealerEval.softValue,
      isSoft: dealerEval.isSoft,
      isBust: dealerEval.isBust,
      isBlackjack: dealerEval.isBlackjack,
      isCharlie: false,
    }

    set({
      phase: 'dealing',
      shoe: remainingShoe,
      mainHand,
      splitHand: null,
      dealerHand,
      dealQueue: events,
      outcome: null,
      winAmount: 0,
      xpEarned: 0,
      sideBets,
      lightning,
      currentHandIndex: 0,
      player: { ...state.player, chips: newChips },
    })

    // After deal animation completes (~1200ms), check for blackjack or move to player turn
    setTimeout(() => {
      const s = get()
      if (s.mainHand.isBlackjack) {
        // Natural blackjack -- settle immediately
        const settled = settleHand(
          s.mainHand, { ...s.dealerHand, cards: s.dealerHand.cards.map(c => ({ ...c, faceDown: false })) },
          s.config, s.player.presenceMultiplier,
          s.lightning.active && s.lightning.multipliedTotal === 21 ? s.lightning.multiplier : 1,
        )
        const xp = calculateXP(settled.outcome!)
        set({
          phase: 'settled',
          mainHand: settled,
          dealerHand: { ...s.dealerHand, cards: s.dealerHand.cards.map(c => ({ ...c, faceDown: false })) },
          outcome: settled.outcome,
          winAmount: settled.payout,
          xpEarned: xp,
          player: {
            ...s.player,
            chips: s.player.chips + settled.payout,
            xp: s.player.xp + xp,
            handsPlayed: s.player.handsPlayed + 1,
            handsWon: s.player.handsWon + 1,
            blackjacks: s.player.blackjacks + 1,
            currentStreak: s.player.currentStreak + 1,
            bestStreak: Math.max(s.player.bestStreak, s.player.currentStreak + 1),
            biggestWin: Math.max(s.player.biggestWin, settled.payout),
          },
          dealQueue: [],
        })
      } else {
        // Check if dealer shows Ace (insurance opportunity)
        const dealerUpcard = s.dealerHand.cards[0]
        const nextPhase = dealerUpcard.rank === 'A' ? 'insurance' as GamePhase : 'player_turn' as GamePhase
        const actions = getAvailableActions(s.mainHand, s.config, s.player.chips, dealerUpcard, false)

        set({
          phase: nextPhase,
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

    const result = hit(currentHand, state.shoe)

    const update: Partial<BlackjackStore> = {
      shoe: result.shoe,
    }

    if (isMainHand) {
      update.mainHand = result.hand
    } else {
      update.splitHand = result.hand
    }

    if (result.autoBust) {
      // Handle bust
      if (state.splitHand && isMainHand) {
        // Bust on main hand, move to split hand
        update.currentHandIndex = 1
        update.phase = 'split_turn'
        update.mainHand = { ...result.hand, outcome: 'bust', payout: 0 }
      } else {
        // Final bust -- settle
        const hand = result.hand
        update.phase = 'settled'
        update.outcome = 'bust'
        update.winAmount = hand.bet
        update.xpEarned = calculateXP('bust')
        if (isMainHand) {
          update.mainHand = { ...hand, outcome: 'bust', payout: 0 }
        } else {
          update.splitHand = { ...hand, outcome: 'bust', payout: 0 }
        }
      }
    } else if (result.autoCharlie && state.config.sixCardCharlie) {
      // Six Card Charlie -- auto-win
      const hand = result.hand
      if (isMainHand) {
        update.mainHand = { ...hand, outcome: 'charlie', payout: hand.bet * 2 }
      } else {
        update.splitHand = { ...hand, outcome: 'charlie', payout: hand.bet * 2 }
      }
      // Move to next hand or dealer
      if (state.splitHand && isMainHand) {
        update.currentHandIndex = 1
        update.phase = 'split_turn'
      } else {
        update.phase = 'dealer_turn'
      }
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

  playerStand: () => {
    const state = get()
    if (state.phase !== 'player_turn' && state.phase !== 'split_turn') return

    if (state.splitHand && state.currentHandIndex === 0) {
      // Standing on main hand, move to split hand
      set({ currentHandIndex: 1, phase: 'split_turn' })
      return
    }

    // All player hands done -- dealer plays
    set({ phase: 'dealer_turn' })

    // 300ms anticipation gap before dealer reveal
    setTimeout(() => {
      const s = get()
      const dealerResult = playDealer(s.dealerHand, s.shoe, s.config)

      set({
        dealerHand: dealerResult.hand,
        dealerDrawQueue: dealerResult.draws,
        shoe: dealerResult.shoe,
      })

      // After dealer draws complete, settle
      const totalDrawTime = dealerResult.draws.length > 0
        ? dealerResult.draws[dealerResult.draws.length - 1].delayMs + 600
        : 300

      setTimeout(() => {
        const s2 = get()
        const lightningMult = s2.lightning.active && s2.lightning.multipliedTotal
          ? (s2.mainHand.value === s2.lightning.multipliedTotal ? s2.lightning.multiplier : 1)
          : 1

        const settledMain = settleHand(s2.mainHand, s2.dealerHand, s2.config, s2.player.presenceMultiplier, lightningMult)
        let settledSplit: HandState | null = null
        if (s2.splitHand) {
          settledSplit = settleHand(s2.splitHand, s2.dealerHand, s2.config, s2.player.presenceMultiplier, 1)
        }

        const totalPayout = settledMain.payout + (settledSplit?.payout || 0)
        const mainOutcome = settledMain.outcome!
        const xp = calculateXP(mainOutcome)
        const isWin = mainOutcome === 'win' || mainOutcome === 'blackjack' || mainOutcome === 'charlie'

        set({
          phase: 'settled',
          mainHand: settledMain,
          splitHand: settledSplit,
          outcome: mainOutcome,
          winAmount: totalPayout,
          xpEarned: xp,
          dealerDrawQueue: [],
          player: {
            ...s2.player,
            chips: s2.player.chips + totalPayout,
            xp: s2.player.xp + xp,
            handsPlayed: s2.player.handsPlayed + 1,
            handsWon: s2.player.handsWon + (isWin ? 1 : 0),
            currentStreak: isWin ? s2.player.currentStreak + 1 : 0,
            bestStreak: isWin ? Math.max(s2.player.bestStreak, s2.player.currentStreak + 1) : s2.player.bestStreak,
            biggestWin: Math.max(s2.player.biggestWin, totalPayout),
          },
        })
      }, totalDrawTime)
    }, 300) // THE anticipation gap
  },

  playerDouble: () => {
    const state = get()
    if (state.phase !== 'player_turn' && state.phase !== 'split_turn') return
    if (state.player.chips < state.betAmount) return

    const isMainHand = state.currentHandIndex === 0
    const currentHand = isMainHand ? state.mainHand : state.splitHand!

    const result = doubleDown(currentHand, state.shoe)

    set({
      shoe: result.shoe,
      mainHand: isMainHand ? result.hand : state.mainHand,
      splitHand: isMainHand ? state.splitHand : result.hand,
      player: { ...state.player, chips: state.player.chips - state.betAmount },
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
    if (state.player.chips < state.betAmount) return

    const result = split(state.mainHand, state.shoe)

    set({
      mainHand: result.mainHand,
      splitHand: result.splitHand,
      shoe: result.shoe,
      currentHandIndex: 0,
      player: { ...state.player, chips: state.player.chips - state.betAmount },
      availableActions: getAvailableActions(result.mainHand, state.config, state.player.chips - state.betAmount, state.dealerHand.cards[0], true),
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
        chips: state.player.chips + result.payout,
        xp: state.player.xp + xp,
        handsPlayed: state.player.handsPlayed + 1,
      },
    })
  },

  playerInsurance: (take) => {
    const state = get()
    if (state.phase !== 'insurance') return

    if (take) {
      const insured = takeInsurance(state.mainHand)
      set({
        mainHand: insured,
        phase: 'player_turn',
        player: { ...state.player, chips: state.player.chips - insured.insuranceBet },
        availableActions: getAvailableActions(insured, state.config, state.player.chips - insured.insuranceBet, state.dealerHand.cards[0], false),
      })
    } else {
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

    set({
      phase: 'betting',
      shoe,
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
      betAmount: state.selectedChip,
    })
  },

  setDealer: (dealer) => set({ activeDealer: dealer, showDealerSelect: false }),
  setDealerLine: (line) => set({ dealerLine: line }),

  togglePanel: (panel) => {
    const key = `show${panel.charAt(0).toUpperCase() + panel.slice(1)}` as keyof BlackjackStore
    set({ [key]: !get()[key] } as any)
  },
}))
