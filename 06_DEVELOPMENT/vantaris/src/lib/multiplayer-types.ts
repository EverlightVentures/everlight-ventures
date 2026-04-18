/**
 * Vantaris Multiplayer Blackjack -- Shared Types
 *
 * Used by both the client (useMultiplayerStore) and
 * referenced in the edge function contract.
 */

import type { Card, Outcome, GamePhase } from './blackjack-engine'

// ============================================================
// DATABASE ROW TYPES (match Supabase schema)
// ============================================================

export interface GameTableRow {
  id: string
  name: string
  variant: 'classic' | 'lightning' | 'speed' | 'switch' | 'highroller'
  min_bet: number
  max_bet: number
  max_seats: number
  status: 'waiting' | 'active' | 'settling'
  phase: 'betting' | 'dealing' | 'player_turn' | 'dealer_turn' | 'settled'
  current_seat: number
  dealer_hand: Card[]
  dealer_total: number
  round_number: number
  deck_count: number
  blackjack_pays: '3:2' | '6:5'
  dealer_hits_soft17: boolean
  double_after_split: boolean
  surrender_allowed: boolean
  six_card_charlie: boolean
  side_bets_enabled: boolean
  felt_color: string
  dealer_name: string
  dealer_avatar: string
  created_at: string
  updated_at: string
}

export type SeatStatus = 'empty' | 'waiting' | 'betting' | 'acting' | 'standing' | 'busted' | 'blackjack' | 'settled'

export interface GameSeatRow {
  id: string
  table_id: string
  seat_index: number
  user_id: string | null
  player_id: string | null
  display_name: string | null
  avatar_url: string | null
  is_vip: boolean
  chips: number
  bet: number
  side_bets: Record<string, { active: boolean; bet: number; payout: number }>
  cards: Card[]
  split_cards: Card[] | null
  hand_total: number
  split_total: number | null
  is_split: boolean
  doubled: boolean
  insured: boolean
  insurance_bet: number
  status: SeatStatus
  outcome: Outcome | null
  payout: number
  turn_started_at: string | null
  afk_count: number
  joined_at: string
}

// ============================================================
// ACTIONS (sent from client to edge function)
// ============================================================

export type GameAction =
  | { action: 'join'; table_id: string; seat_index: number }
  | { action: 'leave'; table_id: string }
  | { action: 'bet'; table_id: string; amount: number; side_bets?: Record<string, number> }
  | { action: 'deal'; table_id: string }
  | { action: 'hit'; table_id: string }
  | { action: 'stand'; table_id: string }
  | { action: 'double'; table_id: string }
  | { action: 'split'; table_id: string }
  | { action: 'insurance'; table_id: string; take: boolean }
  | { action: 'surrender'; table_id: string }

// ============================================================
// BROADCAST EVENTS (sent from edge function to all clients)
// ============================================================

export type BroadcastEventType =
  | 'table_state'        // full state refresh
  | 'player_joined'      // someone sat down
  | 'player_left'        // someone left
  | 'bets_placed'        // betting round update
  | 'cards_dealt'        // initial deal
  | 'player_action'      // hit/stand/double/split result
  | 'dealer_turn'        // dealer draws + final hand
  | 'hand_settled'       // results + payouts
  | 'turn_started'       // new player's turn (with timer)
  | 'chat_message'       // table chat
  | 'emoji_reaction'     // emoji sent to another player

export interface BroadcastEvent {
  type: BroadcastEventType
  table: GameTableRow
  seats: GameSeatRow[]
  // Optional extra data depending on event type
  actor_seat?: number           // who triggered this
  dealer_cards?: Card[]         // revealed dealer cards
  results?: SeatResult[]        // settlement results
  message?: string              // chat message
  emoji?: string                // emoji reaction
  target_seat?: number          // who the emoji is aimed at
}

export interface SeatResult {
  seat_index: number
  outcome: Outcome
  payout: number
  cards: Card[]
  hand_total: number
}

// ============================================================
// PRESENCE (tracked per player in Realtime channel)
// ============================================================

export interface PlayerPresence {
  user_id: string
  display_name: string
  avatar_url: string | null
  seat_index: number
  chips: number
  is_vip: boolean
  online_since: string
}

// ============================================================
// CLIENT STATE (used by useMultiplayerStore)
// ============================================================

export interface MultiplayerState {
  // Connection
  connected: boolean
  tableId: string | null
  channelName: string | null

  // Table state (from server)
  table: GameTableRow | null
  seats: GameSeatRow[]

  // Local player
  mySeatIndex: number | null        // primary seat
  mySeatIndices: number[]           // all seats this player occupies
  myUserId: string | null

  // Turn timer
  turnTimeLeft: number       // seconds remaining
  turnTimerActive: boolean

  // Presence
  players: PlayerPresence[]

  // Chat
  chatMessages: ChatMessage[]

  // UI
  isJoining: boolean
  error: string | null
}

export interface ChatMessage {
  id: string
  seat_index: number
  display_name: string
  text: string
  timestamp: number
}

// ============================================================
// EDGE FUNCTION RESPONSE
// ============================================================

export interface DealerResponse {
  success: boolean
  error?: string
  table?: GameTableRow
  seats?: GameSeatRow[]
  results?: SeatResult[]
  broadcast?: BroadcastEvent
}
