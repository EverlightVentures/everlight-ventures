/**
 * Dealer Intelligence Engine
 *
 * Makes the table feel ALIVE. Three systems:
 *
 * 1. MOOD SYSTEM -- Dealers react to player streaks and milestones
 *    States: neutral | impressed | annoyed | excited
 *    Transitions based on win/loss streaks and hand count
 *
 * 2. IDLE CHATTER -- Dealers talk when nothing is happening
 *    Fires every 45-90s during betting phase
 *    Unique per dealer persona
 *
 * 3. ACHIEVEMENT ENGINE -- Checks unlock conditions after each hand
 *    9 achievements with GC rewards
 *    Fires toast notifications on unlock
 *
 * 4. HAND HISTORY -- Tracks last 20 hands for profile display
 */

import { useBlackjackStore } from './blackjack-store'
import {
  toast, toastAchievement, toastXP, toastRankUp, toastWarning, toastInfo,
} from '@/components/blackjack/VantarisToast'

// ============================================================
// MOOD SYSTEM
// ============================================================

export type DealerMood = 'neutral' | 'impressed' | 'annoyed' | 'excited'

const MOOD_LINES: Record<string, Record<DealerMood, string[]>> = {
  aria: {
    neutral: ['The table is yours.', 'Let the cards decide.'],
    impressed: ['You are making this look effortless.', 'The table is yours tonight. Truly.', 'I may need to call the pit boss. You are on a tear.'],
    annoyed: ['The cards will turn. They always do.', 'Patience is a virtue at this table.', 'Even the best players have cold streaks.'],
    excited: ['This is extraordinary! The table is electric!', 'I have not seen a run like this in ages.', 'The entire casino is watching you right now.'],
  },
  marcus: {
    neutral: ['Cards do not lie.', 'Let us see what you got.'],
    impressed: ['Alright, I see you. You came to play.', 'Not bad. Not bad at all.', 'You are making the house nervous. I respect that.'],
    annoyed: ['Tough run. The Shark has seen worse.', 'You going to keep bleeding or change it up?', 'The deck does not owe you anything.'],
    excited: ['Yo. This is getting DANGEROUS. I love it.', 'The Shark is actually sweating. That never happens.', 'You are about to break this table. For real.'],
  },
  kanisha: {
    neutral: ['The VIP lounge is yours, superstar!', 'Ready when you are!'],
    impressed: ['OH you are COOKING tonight!', 'The lounge is buzzing! Everyone sees you!', 'Somebody get this player a crown!'],
    annoyed: ['It happens to the best, sugar. Keep your head up!', 'The comeback is always more fun than the lead!', 'Shake it off! The next hand is yours!'],
    excited: ['I am SCREAMING! This is LEGENDARY!', 'The VIP lounge has NEVER seen anything like this!', 'History! You are making HISTORY right now!'],
  },
  bacardi: {
    neutral: [
      'The ice waits.', 'Play or leave.', 'Another hand. Another test.',
      'The table does not judge. I do.', 'Sit down. Or walk away. No in between.',
      'The frost has no opinion. But I do.', 'Silence means I am watching.',
      'Do not mistake my patience for approval.', 'I have seen ten thousand players. You are still being evaluated.',
      'The cards do not lie. Neither do I.', 'Every chip you place is a conversation with fate.',
    ],
    impressed: [
      'Interesting. You have earned my attention.', 'The ice respects strength. Continue.',
      'Few survive this long at the ice table.', 'You play like someone who has lost before and learned from it.',
      'That was not luck. That was instinct. I respect instinct.',
      'The frost bends for no one. But it noticed you.', 'Keep playing like that and I might actually remember your name.',
      'Cold precision. You understand this table.', 'I see calculation behind those bets. Good.',
      'You are not gambling. You are hunting. I can tell the difference.',
      'The temperature just shifted. That was you.',
    ],
    annoyed: [
      'The ice does not care about your feelings.', 'Weakness. The table smells it.',
      'Cold. Like your chip stack.', 'That bet was emotional. I can tell.',
      'You are chasing. The frost always catches chasers.',
      'Stop hoping. Start thinking.', 'I have watched empires crumble at this table. You are not special.',
      'Desperation has a sound. I hear it in your bets.',
      'The cards do not owe you anything.', 'You came to the ice table unprepared.',
      'Fear makes bad players worse. Control yourself.',
    ],
    excited: [
      'I have never said this before. You have impressed the Ice.',
      'The temperature is rising. That should not be possible here.',
      'Even Bacardi Ice must acknowledge greatness.',
      'In twenty years at this table, I can count on one hand the players who played like that.',
      'The frost is cracking. You are doing that. Nobody does that.',
      'Stand up. Look around. This is your moment. Own it.',
      'I am not easily moved. You moved me. Respect.',
      'The ice table has a new legend. The room will remember this.',
      'Perfection. Cold, calculated perfection. That is what I just witnessed.',
      'You did not beat the house. You became the house.',
    ],
  },
}

// Extra voice line categories
const DEALER_DRAW_LINES: Record<string, string[]> = {
  aria: ['Drawing...', 'Another card for the house.', 'The dealer must hit.'],
  marcus: ['The Shark draws.', 'Let us see what is under here.', 'House takes a card.'],
  kanisha: ['Dealer draws! Drama!', 'Ooh what is coming next?!', 'The suspense!'],
  bacardi: ['The ice draws.', 'Another card. Cold as always.', 'The house takes what it needs.', 'Drawing. Do not blink.', 'One more from the frost.', 'The deck answers to me.', 'Watch carefully.', 'The ice takes.'],
}

const DEALER_BUST_LINES: Record<string, string[]> = {
  aria: ['The house falls. Well played.', 'Dealer busts. The table wins.', 'Over 21 for the house. Fortune smiled on you.'],
  marcus: ['The Shark busted. Do not get used to it.', 'House goes over. Enjoy your chips.', 'That will not happen again.'],
  kanisha: ['DEALER BUSTED! The VIP lounge goes WILD!', 'The house is DOWN! Your chips, superstar!', 'OH NO the house busted! Tonight is YOUR night!'],
  bacardi: ['The ice cracked. Rare.', 'Dealer busts. It will not happen twice.', 'A flaw in the frost. Take your winnings.', 'Even glaciers break. Once.', 'The house fell. Savor it. It will not happen again.', 'A crack in the ice. Enjoy it while it lasts.', 'Bust. I will remember this hand. And so will you.'],
}

const LOW_CHIPS_LINES: Record<string, string[]> = {
  aria: ['Your stack is getting thin. Perhaps a more conservative approach?', 'Running low. The free chips are always there if you need them.'],
  marcus: ['You are almost tapped. Time to grind or go home.', 'Low stack. Either go big or claim those free chips.'],
  kanisha: ['Ooh, running a little low there! Hit that free chips button, superstar!', 'The lounge has free chips waiting for you, no shame in that!'],
  bacardi: ['Your stack is melting. Like ice in the sun.', 'Almost gone. The ice table does not give refunds.', 'Running dry. The frost has no sympathy.', 'Your chips are disappearing. The table is hungry.', 'Low funds. The ice smells blood.', 'The cold takes everything eventually.'],
}

const MILESTONE_LINES: Record<string, Record<number, string>> = {
  aria: {
    10: 'Ten hands already. You are settling in nicely.',
    25: 'Twenty-five hands. You belong at this table.',
    50: 'Fifty hands. A true regular.',
    100: 'One hundred hands. You have earned the respect of the house.',
  },
  marcus: {
    10: 'Ten deep. You are not just passing through.',
    25: 'Twenty-five. You got stamina. Respect.',
    50: 'Half a hundred. The Shark remembers faces like yours.',
    100: 'A hundred hands with The Shark. That is a story worth telling.',
  },
  kanisha: {
    10: 'Ten hands in the VIP! You are officially a regular!',
    25: 'Twenty-five! The lounge LOVES you!',
    50: 'FIFTY hands! You are VIP royalty now!',
    100: 'ONE HUNDRED HANDS! Somebody get this legend a plaque!',
  },
  bacardi: {
    10: 'Ten hands on the ice. Most do not last five.',
    25: 'Twenty-five. You are harder than I thought.',
    50: 'Fifty hands. The ice table has claimed you.',
    100: 'One hundred. In all my years, few have matched this.',
  },
}

// ============================================================
// IDLE CHATTER
// ============================================================

const IDLE_LINES: Record<string, string[]> = {
  aria: [
    'Take your time. The cards are patient.',
    'The felt remembers every hand. Make this one count.',
    'I have seen fortunes change in a single card.',
    'The best players know when to breathe.',
    'The chandelier has seen ten thousand hands. It still watches yours.',
  ],
  marcus: [
    'You going to play or just stare?',
    'Clock is ticking. The Shark does not wait forever.',
    'I have seen better. I have seen worse. Show me something.',
    'The table is getting cold. Heat it up.',
    'Every second you wait, the deck is plotting.',
  ],
  kanisha: [
    'The VIP lounge is waiting for its star!',
    'Take your time, superstar! The spotlight is not going anywhere!',
    'I can feel the next big hand coming. Can you?',
    'The lounge is quiet. Let us change that!',
    'Ready when you are, VIP!',
  ],
  bacardi: [
    'The ice waits for no one.',
    'Still here? Then play.',
    'Silence at the ice table. That is either wisdom or fear.',
    'The frost is patient. You should not be.',
    'Every moment of hesitation, the ice grows colder.',
    'I have watched players sit here for hours. Most of them lost.',
    'The table is not going anywhere. Your chips are.',
    'Think. Then act. That is how you survive the frost.',
    'Most dealers make small talk. I am not most dealers.',
    'The ice table does not forgive second guessing.',
    'You know what separates winners from losers at this table? Speed of decision.',
    'I do not fill silence with comfort. I fill it with pressure.',
    'The longer you wait, the more the ice knows about you.',
    'Breathe. Focus. The next hand will define the session.',
    'I respect players who sit in the silence. It means they are calculating.',
    'The chandelier above us has seen a thousand fortunes made and lost. It watches yours now.',
    'Nobody walks away from the ice table the same person they were when they sat down.',
    'This table was built for players who do not need encouragement.',
    'The cold sharpens the mind. That is why I keep it this way.',
    'I do not wish you luck. Luck is for the unprepared.',
  ],
}

let idleTimer: ReturnType<typeof setTimeout> | null = null

export function startIdleChatter() {
  stopIdleChatter()
  scheduleIdleChatter()
}

export function stopIdleChatter() {
  if (idleTimer) clearTimeout(idleTimer)
  idleTimer = null
}

function scheduleIdleChatter() {
  // 45-90 second random interval
  const delay = 45000 + Math.random() * 45000
  idleTimer = setTimeout(() => {
    const state = useBlackjackStore.getState()
    if (state.phase === 'betting') {
      const dealerId = state.activeDealer.id
      const lines = IDLE_LINES[dealerId] || IDLE_LINES.aria
      const line = lines[Math.floor(Math.random() * lines.length)]
      useBlackjackStore.setState({ dealerLine: line })
    }
    scheduleIdleChatter()
  }, delay)
}

// ============================================================
// MOOD ENGINE
// ============================================================

let currentMood: DealerMood = 'neutral'

function getDealerMood(): DealerMood {
  return currentMood
}

export function updateMoodAfterHand(): string | null {
  const state = useBlackjackStore.getState()
  const dealerId = state.activeDealer.id
  const streak = state.player.currentStreak
  const hands = state.player.handsPlayed
  const outcome = state.outcome

  let newMood: DealerMood = 'neutral'

  // Win streak thresholds
  if (streak >= 7) newMood = 'excited'
  else if (streak >= 3) newMood = 'impressed'
  // Loss detection (streak resets to 0 on loss)
  else if (streak === 0 && (outcome === 'loss' || outcome === 'bust')) {
    // Check if this is a continued losing run by checking hands won ratio
    const recentLossRatio = state.player.handsPlayed > 0
      ? state.player.handsWon / state.player.handsPlayed
      : 0.5
    if (recentLossRatio < 0.35) newMood = 'annoyed'
  }

  // Mood changed -- speak
  let moodLine: string | null = null
  if (newMood !== currentMood) {
    currentMood = newMood
    const lines = MOOD_LINES[dealerId]?.[newMood] || MOOD_LINES.aria[newMood]
    moodLine = lines[Math.floor(Math.random() * lines.length)]
  }

  // Milestone check
  const milestone = MILESTONE_LINES[dealerId]?.[hands]
  if (milestone) {
    // Milestone overrides mood line
    moodLine = milestone
    toastInfo('Milestone', `${hands} hands played!`)
  }

  // Low chips warning
  if (state.player.chips < 200 && state.player.chips > 0) {
    const lowLines = LOW_CHIPS_LINES[dealerId] || LOW_CHIPS_LINES.aria
    moodLine = lowLines[Math.floor(Math.random() * lowLines.length)]
    toastWarning('Low Chips', 'Claim free chips or visit the gem store!')
  }

  return moodLine
}

function getDealerDrawLine(): string {
  const dealerId = useBlackjackStore.getState().activeDealer.id
  const lines = DEALER_DRAW_LINES[dealerId] || DEALER_DRAW_LINES.aria
  return lines[Math.floor(Math.random() * lines.length)]
}

function getDealerBustLine(): string {
  const dealerId = useBlackjackStore.getState().activeDealer.id
  const lines = DEALER_BUST_LINES[dealerId] || DEALER_BUST_LINES.aria
  return lines[Math.floor(Math.random() * lines.length)]
}

// ============================================================
// ACHIEVEMENT ENGINE
// ============================================================

interface AchievementDef {
  id: string
  name: string
  description: string
  icon: string
  reward: number
  check: (player: any, outcome: string | null) => boolean
}

const ACHIEVEMENTS: AchievementDef[] = [
  {
    id: 'first_win',
    name: 'First Blood',
    description: 'Win your first hand',
    icon: '\uD83C\uDFC6',
    reward: 50,
    check: (p, o) => o === 'win' || o === 'blackjack' || o === 'charlie',
  },
  {
    id: 'first_blackjack',
    name: 'Natural 21',
    description: 'Get your first blackjack',
    icon: '\uD83C\uDCCF',
    reward: 200,
    check: (p, o) => o === 'blackjack',
  },
  {
    id: 'hot_streak_5',
    name: 'On Fire',
    description: 'Win 5 hands in a row',
    icon: '\uD83D\uDD25',
    reward: 500,
    check: (p) => p.currentStreak >= 5,
  },
  {
    id: 'hot_streak_10',
    name: 'Unstoppable',
    description: 'Win 10 hands in a row',
    icon: '\u26A1',
    reward: 2000,
    check: (p) => p.currentStreak >= 10,
  },
  {
    id: 'centurion',
    name: 'Centurion',
    description: 'Play 100 hands',
    icon: '\uD83C\uDFDB\uFE0F',
    reward: 1000,
    check: (p) => p.handsPlayed >= 100,
  },
  {
    id: 'big_winner',
    name: 'High Roller',
    description: 'Win 10,000+ chips in one hand',
    icon: '\uD83D\uDCB0',
    reward: 0,
    check: (p) => p.biggestWin >= 10000,
  },
  {
    id: 'gold_rank',
    name: 'Going for Gold',
    description: 'Reach Gold rank',
    icon: '\uD83E\uDD47',
    reward: 2500,
    check: (p) => p.xp >= 5000,
  },
  {
    id: 'diamond_rank',
    name: 'Diamond Club',
    description: 'Reach Diamond rank',
    icon: '\uD83D\uDC8E',
    reward: 10000,
    check: (p) => p.xp >= 40000,
  },
  {
    id: 'lucky_seven',
    name: 'Lucky Seven',
    description: 'Win 7 blackjacks',
    icon: '\uD83C\uDFB0',
    reward: 777,
    check: (p) => p.blackjacks >= 7,
  },
]

export function checkAchievements(): void {
  const state = useBlackjackStore.getState()
  const player = state.player
  const outcome = state.outcome
  const unlocked = new Set(player.unlockedAchievements)
  let chipsBonus = 0
  let newUnlocks: string[] = []

  for (const ach of ACHIEVEMENTS) {
    if (unlocked.has(ach.id)) continue
    if (ach.check(player, outcome)) {
      newUnlocks.push(ach.id)
      chipsBonus += ach.reward

      // Stagger toast notifications
      const delay = newUnlocks.length * 1800
      setTimeout(() => {
        toastAchievement(ach.name, ach.description, ach.reward)
      }, delay)
    }
  }

  if (newUnlocks.length > 0) {
    useBlackjackStore.setState({
      player: {
        ...player,
        chips: player.chips + chipsBonus,
        unlockedAchievements: [...player.unlockedAchievements, ...newUnlocks],
      },
    })
  }

  // XP toast
  if (state.xpEarned > 0) {
    toastXP(state.xpEarned)
  }

  // Rank-up check
  const RANKS: [string, number][] = [
    ['Bronze', 0], ['Silver', 1000], ['Gold', 5000],
    ['Platinum', 15000], ['Diamond', 40000], ['Legend', 100000],
  ]
  const currentXP = player.xp
  const newRank = RANKS.reduce((r, [name, min]) => currentXP >= min ? name : r, 'Bronze')
  if (newRank !== player.rank) {
    toastRankUp(newRank)
    useBlackjackStore.setState({
      player: { ...useBlackjackStore.getState().player, rank: newRank },
    })
  }
}

// ============================================================
// HAND HISTORY
// ============================================================

export interface HandRecord {
  id: number
  outcome: string
  playerValue: number
  dealerValue: number
  chipsDelta: number
  bet: number
  timestamp: number
}

let handHistory: HandRecord[] = []
let historyId = 0

export function recordHand(): void {
  const state = useBlackjackStore.getState()
  if (!state.outcome) return

  const record: HandRecord = {
    id: historyId++,
    outcome: state.outcome,
    playerValue: state.mainHand.value,
    dealerValue: state.dealerHand.value,
    chipsDelta: state.winAmount - state.mainHand.bet,
    bet: state.mainHand.bet,
    timestamp: Date.now(),
  }

  handHistory = [record, ...handHistory].slice(0, 20)
}

export function getHandHistory(): HandRecord[] {
  return handHistory
}

// ============================================================
// RESHUFFLE NOTIFICATION
// ============================================================

export function checkReshuffle(): void {
  const state = useBlackjackStore.getState()
  if (state.shoe.length < 20) {
    toastInfo('Deck Reshuffled', 'The shoe has been reshuffled.')
  }
}

// ============================================================
// MASTER POST-HAND HOOK
// Called after every hand settles. Runs all intelligence systems.
// ============================================================

export function postHandSettle(): string | null {
  // 1. Record hand history
  recordHand()

  // 2. Check achievements
  checkAchievements()

  // 3. Update dealer mood (returns mood line if changed)
  const moodLine = updateMoodAfterHand()

  // 4. Check for reshuffle
  checkReshuffle()

  // 5. Recalculate presence multiplier
  recalculatePresence()

  return moodLine
}

// ============================================================
// PRESENCE MULTIPLIER CALCULATOR
// ============================================================

// Maps item IDs to their presence scores
const OUTFIT_SCORES: Record<string, number> = {
  default_suit: 1.0,
  gold_tux: 1.15,
  diamond_blazer: 1.25,
  neon_suit: 1.20,
  royal_robe: 1.35,
  legendary_drip: 1.50,
}

const AURA_SCORES: Record<string, number> = {
  none: 1.0,
  golden_glow: 1.05,
  hologram_blue: 1.10,
  fire_aura: 1.15,
  legend_aura: 1.25,
}

const RANK_BONUSES: Record<string, number> = {
  Bronze: 0,
  Silver: 0.05,
  Gold: 0.10,
  Platinum: 0.15,
  Diamond: 0.20,
  Legend: 0.30,
}

export function calculatePresence(outfitId: string, auraId: string, rank: string): number {
  const outfitScore = OUTFIT_SCORES[outfitId] || 1.0
  const auraScore = AURA_SCORES[auraId] || 1.0
  const rankBonus = RANK_BONUSES[rank] || 0
  return Math.round((outfitScore * auraScore * (1 + rankBonus)) * 100) / 100
}

export function recalculatePresence(): void {
  const state = useBlackjackStore.getState()
  const player = state.player
  const newPresence = calculatePresence(player.equippedOutfit, player.equippedAura, player.rank)
  if (newPresence !== player.presenceMultiplier) {
    useBlackjackStore.setState({
      player: { ...player, presenceMultiplier: newPresence },
    })
  }
}

// ============================================================
// DEALER NARRATION SYSTEM
// Queues voice lines that play sequentially with timing.
// Makes the dealer call out every phase like a real pit.
// ============================================================

const NARRATION_LINES: Record<string, Record<string, string[]>> = {
  aria: {
    fresh_shoe: ['Fresh shoe. Cards are live.', 'New shoe, fresh chances.'],
    cards_out: ['Cards are out.', 'Here we go.'],
    seat_action: ['Seat {seat}, your action.', 'Seat {seat}, what will it be?'],
    seat_hits: ['Seat {seat} takes a hit.', 'Another card for seat {seat}.'],
    seat_stands: ['Seat {seat} stands.', 'Seat {seat} is firm.'],
    seat_doubles: ['Seat {seat} doubles down. Bold move.', 'Double down at seat {seat}. High roller alert.'],
    seat_busts: ['Seat {seat} busts.', 'Over 21 at seat {seat}.'],
    seat_blackjack: ['Blackjack at seat {seat}. Beautiful.', 'Natural 21 at seat {seat}.'],
    dealer_reveals: ['Dealer reveals.', 'Let me show you what I have.'],
    dealer_hits: ['Dealer must hit.', 'Dealer draws.'],
    dealer_stands: ['Dealer stands at {total}.', 'Dealer has {total}. Standing.'],
    dealer_busts: ['Dealer busts! The table wins.', 'Over 21 for the house.'],
    result_win: ['Seat {seat} wins.', 'Winner at seat {seat}.'],
    result_loss: ['Seat {seat} loses.', 'The house takes seat {seat}.'],
    result_push: ['Seat {seat} pushes.', 'Tie at seat {seat}.'],
    result_bust: ['Seat {seat} busted earlier.', 'Already busted at seat {seat}.'],
  },
  marcus: {
    fresh_shoe: ['New shoe. No mercy.', 'Deck is fresh. Let us see what you got.'],
    cards_out: ['Cards down.', 'Here come the cards.'],
    seat_action: ['Seat {seat}. Your move.', 'Seat {seat}, clock is ticking.'],
    seat_hits: ['Seat {seat} wants another.', 'Hit at seat {seat}.'],
    seat_stands: ['Seat {seat} holds.', 'Standing at seat {seat}. Smart or scared?'],
    seat_doubles: ['Seat {seat} goes all in. Respect.', 'Double down seat {seat}. Big dog energy.'],
    seat_busts: ['Busted at seat {seat}. Tough.', 'Seat {seat} is done. Over 21.'],
    seat_blackjack: ['Blackjack seat {seat}. Even The Shark is impressed.', '21 at seat {seat}. Clean.'],
    dealer_reveals: ['Let me show you.', 'Flipping the hole card.'],
    dealer_hits: ['Dealer hits.', 'Taking another.'],
    dealer_stands: ['Dealer at {total}.', 'Standing on {total}. Let us settle up.'],
    dealer_busts: ['Dealer busts. Your chips.', 'House goes over. Take your money.'],
    result_win: ['Seat {seat} takes it.', 'Win at seat {seat}.'],
    result_loss: ['Seat {seat} loses. The Shark eats.', 'House wins seat {seat}.'],
    result_push: ['Push at seat {seat}.', 'Tied at seat {seat}. Nobody wins.'],
    result_bust: ['Seat {seat} already busted.', 'Seat {seat} went over.'],
  },
  kanisha: {
    fresh_shoe: ['Fresh shoe! Let us GO!', 'New deck, new energy!'],
    cards_out: ['Cards are OUT! Showtime!', 'Here we go y\'all!'],
    seat_action: ['Seat {seat}! Your moment!', 'Seat {seat}, what\'s it gonna be?!'],
    seat_hits: ['Seat {seat} hits! I love the energy!', 'Another card at seat {seat}!'],
    seat_stands: ['Seat {seat} stands strong!', 'Holding at seat {seat}!'],
    seat_doubles: ['DOUBLE DOWN at seat {seat}! OH my!', 'Seat {seat} is going BIG!'],
    seat_busts: ['Ooh seat {seat} busts! It happens!', 'Over at seat {seat}! You\'ll bounce back!'],
    seat_blackjack: ['BLACKJACK seat {seat}! The VIP lounge goes CRAZY!', 'Twenty-one at seat {seat}! LEGENDARY!'],
    dealer_reveals: ['Let me show you what mama got!', 'Revealing!'],
    dealer_hits: ['Dealer has to hit!', 'Taking one more!'],
    dealer_stands: ['Dealer at {total}!', 'Standing on {total}!'],
    dealer_busts: ['DEALER BUSTS! Tonight is YOUR night!', 'The house FALLS! VIP energy!'],
    result_win: ['WINNER at seat {seat}!', 'Seat {seat} TAKES IT!'],
    result_loss: ['Seat {seat} this time. Next hand!', 'House takes seat {seat}. Shake it off!'],
    result_push: ['Push at seat {seat}! Drama!', 'Tied at seat {seat}!'],
    result_bust: ['Seat {seat} busted earlier!', 'Already over at seat {seat}!'],
  },
  bacardi: {
    fresh_shoe: ['Fresh shoe. The ice is ready.', 'New deck. Play or leave.', 'Eight decks. Freshly cut. The frost begins.', 'Shuffled. The ice table resets for no one.'],
    cards_out: ['Cards.', 'Here.', 'Dealt.', 'The frost delivers.', 'Your fate, face up.'],
    seat_action: ['Seat {seat}.', 'Seat {seat}. Decide.', 'Your move, seat {seat}.', 'Seat {seat}. The ice is watching.', 'Seat {seat}. Do not waste my time.'],
    seat_hits: ['Hit at {seat}.', 'Another card. Seat {seat}.', 'Seat {seat} wants more. Brave or foolish.', 'Drawing for {seat}. The ice delivers.'],
    seat_stands: ['Seat {seat} stands.', 'Standing. Seat {seat}.', 'Seat {seat} holds. Smart.', 'Staying put. Seat {seat} knows when to stop.'],
    seat_doubles: ['Double at seat {seat}. Brave.', 'Seat {seat} doubles. Interesting.', 'Seat {seat} doubles down. The ice respects confidence.', 'Double. Seat {seat} has conviction.'],
    seat_busts: ['Bust. Seat {seat}.', 'Over. Seat {seat}.', 'Seat {seat} broke through the ice. Wrong direction.', 'Gone. Seat {seat}. The frost claims another.'],
    seat_blackjack: ['21 at seat {seat}. The Ice acknowledges.', 'Blackjack seat {seat}. Rare praise.', 'Natural 21. Seat {seat}. In all my years, that never gets old.', 'Seat {seat}. Blackjack. The ice bows to no one, but it nods.'],
    dealer_reveals: ['Revealing.', 'The ice shows.', 'Let me show you what the frost was hiding.', 'The hole card. The moment of truth.'],
    dealer_hits: ['Hit.', 'Drawing.', 'The ice takes one more.', 'Another card for the house.'],
    dealer_stands: ['{total}. Standing.', 'Dealer {total}. Done.', '{total}. The ice holds.', 'Standing at {total}. Your move is over.'],
    dealer_busts: ['The ice cracked. Take your chips.', 'Bust. It will not happen twice.', 'Over. The frost broke. Savor it.', 'Dealer busts. The table wins. For now.'],
    result_win: ['Seat {seat} wins.', 'Victory. Seat {seat}.', 'Seat {seat} beat the frost. Respect.', 'The ice concedes seat {seat}. Well played.'],
    result_loss: ['Seat {seat} falls.', 'The ice takes seat {seat}.', 'Seat {seat}. The house wins. As it usually does.', 'Cold. Seat {seat} goes to the frost.'],
    result_push: ['Push. Seat {seat}.', 'Tie. Seat {seat}.', 'Neither wins. The ice and seat {seat} share this one.'],
    result_bust: ['Already over. Seat {seat}.', 'Seat {seat} busted.', 'Seat {seat} was already gone. The ice remembers.'],
  },
}

function pickNarration(category: string, vars: Record<string, string | number> = {}): string {
  const state = useBlackjackStore.getState()
  const dealerId = state.activeDealer.id
  const lines = NARRATION_LINES[dealerId]?.[category] || NARRATION_LINES.aria[category] || ['']
  let line = lines[Math.floor(Math.random() * lines.length)]
  // Replace template vars
  for (const [key, val] of Object.entries(vars)) {
    line = line.replace(`{${key}}`, String(val))
  }
  return line
}

// Queue of lines to speak in sequence
let narrationQueue: string[] = []
let narrationPlaying = false

export function queueNarration(category: string, vars: Record<string, string | number> = {}) {
  const line = pickNarration(category, vars)
  narrationQueue.push(line)
  if (!narrationPlaying) processNarrationQueue()
}

function processNarrationQueue() {
  if (narrationQueue.length === 0) {
    narrationPlaying = false
    return
  }
  narrationPlaying = true
  const line = narrationQueue.shift()!
  useBlackjackStore.getState().setDealerLine(line)

  // Estimate speech duration (~80ms per character, min 1.5s)
  const duration = Math.max(1500, line.length * 80)
  setTimeout(processNarrationQueue, duration)
}

export function clearNarrationQueue() {
  narrationQueue = []
  narrationPlaying = false
}

// Convenience: narrate seat-by-seat results
export function narrateResults() {
  const state = useBlackjackStore.getState()
  for (const r of state.seatResults) {
    const seatNum = r.seatIndex + 1
    if (r.outcome === 'blackjack') queueNarration('seat_blackjack', { seat: seatNum })
    else if (r.outcome === 'win' || r.outcome === 'charlie') queueNarration('result_win', { seat: seatNum })
    else if (r.outcome === 'push') queueNarration('result_push', { seat: seatNum })
    else if (r.outcome === 'bust') queueNarration('result_bust', { seat: seatNum })
    else queueNarration('result_loss', { seat: seatNum })
  }
}
