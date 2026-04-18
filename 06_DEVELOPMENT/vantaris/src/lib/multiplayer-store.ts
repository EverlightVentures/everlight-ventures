/**
 * Vantaris Multiplayer Blackjack -- Client Store
 *
 * Zustand store that:
 * 1. Subscribes to Supabase Realtime channel for a table
 * 2. Dispatches player actions to the blackjack-dealer edge function
 * 3. Updates local state from broadcast events
 * 4. Tracks presence (who's online at the table)
 * 5. Manages turn timer countdown
 *
 * The store NEVER computes game logic -- it's a thin client
 * that renders whatever the server says.
 */

import { create } from 'zustand'
import { supabase } from './supabase'
import type {
  GameTableRow, GameSeatRow, MultiplayerState,
  BroadcastEvent, PlayerPresence, ChatMessage, SeatResult,
  GameAction,
} from './multiplayer-types'
import {
  getPersonaByName, pickLine, dealerAddress, detectGender,
  type BotPersona,
} from './bot-personas'
import type { RealtimeChannel } from '@supabase/supabase-js'

// ============================================================
// STORE INTERFACE
// ============================================================

interface MultiplayerStore extends MultiplayerState {
  // Connection
  connect: (tableId: string) => Promise<void>
  disconnect: () => void

  // Actions (sent to edge function)
  joinSeat: (seatIndex: number) => Promise<void>
  leaveSeat: () => Promise<void>
  placeBet: (amount: number) => Promise<void>
  playerHit: () => Promise<void>
  playerStand: () => Promise<void>
  playerDouble: () => Promise<void>
  playerSplit: () => Promise<void>
  playerSurrender: () => Promise<void>
  playerInsurance: (take: boolean) => Promise<void>

  // Multi-seat betting
  placeBetOnSeat: (seatIndex: number, amount: number) => Promise<void>

  // Invites
  createInvite: (seatIndex: number, friendId?: string) => Promise<{ code: string; invite_url: string } | null>
  joinByInvite: (code: string) => Promise<void>

  // Friends
  getFriends: () => Promise<any[]>
  addFriend: (email: string) => Promise<void>

  // Chat
  sendChat: (text: string) => void
  sendEmoji: (emoji: string, targetSeat?: number) => void

  // Internal
  _channel: RealtimeChannel | null
  _timerInterval: ReturnType<typeof setInterval> | null
  _handleBroadcast: (event: BroadcastEvent) => void
  _sendAction: (action: GameAction) => Promise<any>
  _startTurnTimer: () => void
  _stopTurnTimer: () => void
  _fetchState: () => Promise<void>
}

// ============================================================
// INITIAL STATE
// ============================================================

const INITIAL_STATE: MultiplayerState = {
  connected: false,
  tableId: null,
  channelName: null,
  table: null,
  seats: [],
  mySeatIndex: null,
  mySeatIndices: [],
  myUserId: null,
  turnTimeLeft: 30,
  turnTimerActive: false,
  players: [],
  chatMessages: [],
  isJoining: false,
  error: null,
}

// ============================================================
// EDGE FUNCTION URL
// ============================================================

const DEALER_URL = 'https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-dealer'

// ============================================================
// STORE
// ============================================================

export const useMultiplayerStore = create<MultiplayerStore>((set, get) => ({
  ...INITIAL_STATE,
  _channel: null,
  _timerInterval: null,

  // ========================================================
  // CONNECT to a table
  // ========================================================
  connect: async (tableId: string) => {
    const state = get()
    if (state.connected && state.tableId === tableId) return

    // Disconnect from any existing table
    if (state._channel) {
      state.disconnect()
    }

    // Get current user
    const { data: { user } } = await supabase.auth.getUser()
    const userId = user?.id ?? null

    set({ tableId, myUserId: userId, connected: false, error: null })

    // Fetch initial state
    await get()._fetchState()

    // Subscribe to Realtime channel
    const channelName = `table:${tableId}`
    const channel = supabase
      .channel(channelName)
      .on('broadcast', { event: 'game_state' }, ({ payload }) => {
        get()._handleBroadcast(payload as BroadcastEvent)
      })
      .on('presence', { event: 'sync' }, () => {
        const presenceState = channel.presenceState()
        const players: PlayerPresence[] = []
        for (const key of Object.keys(presenceState)) {
          const entries = presenceState[key] as any[]
          for (const entry of entries) {
            players.push(entry as PlayerPresence)
          }
        }
        set({ players })
      })
      .subscribe(async (status) => {
        if (status === 'SUBSCRIBED') {
          set({ connected: true, channelName })

          // Track presence
          if (userId) {
            const { data: { user: fullUser } } = await supabase.auth.getUser()
            await channel.track({
              user_id: userId,
              display_name: fullUser?.user_metadata?.display_name || fullUser?.user_metadata?.full_name || 'Player',
              avatar_url: fullUser?.user_metadata?.avatar_url || null,
              seat_index: get().mySeatIndex ?? -1,
              chips: 0,
              is_vip: false,
              online_since: new Date().toISOString(),
            })
          }
        }
      })

    set({ _channel: channel })
  },

  // ========================================================
  // DISCONNECT
  // ========================================================
  disconnect: () => {
    const state = get()
    if (state._channel) {
      supabase.removeChannel(state._channel)
    }
    if (state._timerInterval) {
      clearInterval(state._timerInterval)
    }
    set({ ...INITIAL_STATE, _channel: null, _timerInterval: null })
  },

  // ========================================================
  // FETCH STATE (initial load + recovery)
  // ========================================================
  _fetchState: async () => {
    const { tableId, myUserId } = get()
    if (!tableId) return

    try {
      const res = await fetch(DEALER_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'get-state', table_id: tableId }),
      })
      const data = await res.json()

      if (data.success) {
        const mySeats = (data.seats || []).filter((s: GameSeatRow) => s.user_id === myUserId && s.status !== 'empty')
        const mySeatIndices = mySeats.map((s: GameSeatRow) => s.seat_index)
        set({
          table: data.table,
          seats: data.seats || [],
          mySeatIndex: mySeatIndices[0] ?? null,
          mySeatIndices,
        })

        // Start turn timer if it's any of our seats' turn
        if (data.table?.phase === 'player_turn' && mySeatIndices.includes(data.table?.current_seat)) {
          get()._startTurnTimer()
        }
      }
    } catch (err: any) {
      console.error('[multiplayer] Failed to fetch state:', err)
      set({ error: 'Failed to connect to table' })
    }
  },

  // ========================================================
  // HANDLE BROADCAST EVENTS
  // ========================================================
  _handleBroadcast: (event: BroadcastEvent) => {
    const state = get()
    const { myUserId } = state

    // Update table and seats from server
    if (event.table) {
      set({ table: event.table as GameTableRow })
    }
    if (event.seats) {
      const mySeats = (event.seats as GameSeatRow[]).filter((s) => s.user_id === myUserId && s.status !== 'empty')
      const mySeatIndices = mySeats.map((s) => s.seat_index)
      set({
        seats: event.seats as GameSeatRow[],
        mySeatIndex: mySeatIndices[0] ?? state.mySeatIndex,
        mySeatIndices,
      })
    }

    // Handle specific event types
    switch (event.type) {
      case 'turn_started': {
        const isMyTurn = (state.mySeatIndices || []).includes(event.actor_seat ?? -1)
        if (isMyTurn) {
          get()._startTurnTimer()
        } else {
          get()._stopTurnTimer()
        }
        break
      }

      case 'hand_settled': {
        get()._stopTurnTimer()

        // Generate contextual bot chat messages (rate limited)
        const settledSeats = event.seats || state.seats
        const botSeats = settledSeats.filter((s: GameSeatRow) => s.player_id === 'BOT' && !s.user_id && s.outcome)
        const mySettledSeats = settledSeats.filter((s: GameSeatRow) => s.user_id === myUserId && s.outcome)
        const myOutcome = mySettledSeats[0]?.outcome

        let botDelay = 1500 // first bot message after 1.5s
        const newMessages: ChatMessage[] = []

        for (const bot of botSeats) {
          const persona = getPersonaByName(bot.display_name || '')
          if (!persona) continue

          // Pick contextual line
          let line: string | null = null
          const botOutcome = bot.outcome

          if (botOutcome === 'blackjack') {
            line = pickLine(persona.id, persona.onOwnBlackjack, 'onOwnBlackjack')
          } else if (botOutcome === 'win' || botOutcome === 'charlie') {
            line = pickLine(persona.id, persona.onOwnWin, 'onOwnWin')
          } else if (botOutcome === 'bust') {
            line = pickLine(persona.id, persona.onOwnBust, 'onOwnBust')
          } else if (botOutcome === 'loss') {
            line = pickLine(persona.id, persona.onOwnLoss, 'onOwnLoss')
          } else if (botOutcome === 'push') {
            // 50% chance to comment on a push
            if (Math.random() < 0.5) {
              line = pickLine(persona.id, persona.idle, 'idle')
            }
          }

          // React to human player's outcome (30% chance, only if different from own comment)
          if (!line && myOutcome && Math.random() < 0.3) {
            if (myOutcome === 'blackjack') {
              line = pickLine(persona.id, persona.onOtherBlackjack, 'onOtherBlackjack')
            } else if (myOutcome === 'win' || myOutcome === 'charlie') {
              line = pickLine(persona.id, persona.onOtherWin, 'onOtherWin')
            } else if (myOutcome === 'bust') {
              line = pickLine(persona.id, persona.onOtherBust, 'onOtherBust')
            }
          }

          if (line) {
            // Rate limit: 2s between bot messages
            setTimeout(() => {
              const msg: ChatMessage = {
                id: crypto.randomUUID(),
                seat_index: bot.seat_index,
                display_name: bot.display_name || 'Bot',
                text: line!,
                timestamp: Date.now(),
              }
              const current = get()
              set({ chatMessages: [...current.chatMessages.slice(-50), msg] })
            }, botDelay)
            botDelay += 2000 // 2s between each bot message
          }
        }
        break
      }

      case 'table_state': {
        // Full refresh -- check if we should start timer
        if (event.table?.phase === 'player_turn' &&
            event.table?.current_seat === state.mySeatIndex) {
          get()._startTurnTimer()
        }
        break
      }

      case 'chat_message': {
        if (event.message) {
          const msg: ChatMessage = {
            id: crypto.randomUUID(),
            seat_index: event.actor_seat ?? -1,
            display_name: event.seats?.find(
              (s: GameSeatRow) => s.seat_index === event.actor_seat
            )?.display_name || 'Player',
            text: event.message,
            timestamp: Date.now(),
          }
          set({ chatMessages: [...state.chatMessages.slice(-50), msg] })
        }
        break
      }
    }
  },

  // ========================================================
  // SEND ACTION to edge function
  // ========================================================
  _sendAction: async (action: GameAction) => {
    const { tableId } = get()
    if (!tableId) return { error: 'Not connected' }

    try {
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token

      const res = await fetch(DEALER_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(action),
      })

      const data = await res.json()
      if (data.error) {
        set({ error: data.error })
        console.warn('[multiplayer] Action error:', data.error)
      } else {
        set({ error: null })
      }
      return data
    } catch (err: any) {
      console.error('[multiplayer] Action failed:', err)
      set({ error: 'Connection error' })
      return { error: err.message }
    }
  },

  // ========================================================
  // PLAYER ACTIONS
  // ========================================================

  joinSeat: async (seatIndex: number) => {
    set({ isJoining: true })
    const result = await get()._sendAction({
      action: 'join',
      table_id: get().tableId!,
      seat_index: seatIndex,
    })
    if (result?.success) {
      set({ mySeatIndex: seatIndex, isJoining: false })
      // Re-fetch to get updated state
      await get()._fetchState()
    } else {
      set({ isJoining: false })
    }
  },

  leaveSeat: async () => {
    await get()._sendAction({
      action: 'leave',
      table_id: get().tableId!,
    })
    set({ mySeatIndex: null })
    await get()._fetchState()
  },

  placeBet: async (amount: number) => {
    await get()._sendAction({
      action: 'bet',
      table_id: get().tableId!,
      amount,
    })
  },

  playerHit: async () => {
    await get()._sendAction({
      action: 'hit',
      table_id: get().tableId!,
    })
  },

  playerStand: async () => {
    await get()._sendAction({
      action: 'stand',
      table_id: get().tableId!,
    })
  },

  playerDouble: async () => {
    await get()._sendAction({
      action: 'double',
      table_id: get().tableId!,
    })
  },

  playerSplit: async () => {
    await get()._sendAction({
      action: 'split',
      table_id: get().tableId!,
    })
  },

  playerSurrender: async () => {
    await get()._sendAction({
      action: 'surrender',
      table_id: get().tableId!,
    })
  },

  playerInsurance: async (take: boolean) => {
    await get()._sendAction({
      action: 'insurance',
      table_id: get().tableId!,
      take,
    })
  },

  // ========================================================
  // MULTI-SEAT BETTING
  // ========================================================

  placeBetOnSeat: async (seatIndex: number, amount: number) => {
    await get()._sendAction({
      action: 'bet',
      table_id: get().tableId!,
      amount,
      seat_index: seatIndex,
    } as any)
  },

  // ========================================================
  // INVITES
  // ========================================================

  createInvite: async (seatIndex: number, friendId?: string) => {
    const result = await get()._sendAction({
      action: 'create-invite',
      table_id: get().tableId!,
      seat_index: seatIndex,
      friend_id: friendId,
    } as any)
    if (result?.success) {
      return { code: result.code, invite_url: result.invite_url }
    }
    return null
  },

  joinByInvite: async (code: string) => {
    const result = await get()._sendAction({
      action: 'join-by-invite',
      table_id: get().tableId!,
      code,
    } as any)
    if (result?.success) {
      set({ mySeatIndex: result.seat_index })
      await get()._fetchState()
    }
  },

  // ========================================================
  // FRIENDS
  // ========================================================

  getFriends: async () => {
    const result = await get()._sendAction({
      action: 'get-friends',
      table_id: get().tableId!,
    } as any)
    return result?.friends || []
  },

  addFriend: async (email: string) => {
    await get()._sendAction({
      action: 'add-friend',
      table_id: get().tableId!,
      friend_email: email,
    } as any)
  },

  // ========================================================
  // CHAT + EMOJI (via Realtime broadcast)
  // ========================================================

  sendChat: (text: string) => {
    const { _channel, mySeatIndex } = get()
    if (!_channel || mySeatIndex === null) return

    _channel.send({
      type: 'broadcast',
      event: 'game_state',
      payload: {
        type: 'chat_message',
        actor_seat: mySeatIndex,
        message: text,
        table: get().table,
        seats: get().seats,
      },
    })
  },

  sendEmoji: (emoji: string, targetSeat?: number) => {
    const { _channel, mySeatIndex } = get()
    if (!_channel || mySeatIndex === null) return

    _channel.send({
      type: 'broadcast',
      event: 'game_state',
      payload: {
        type: 'emoji_reaction',
        actor_seat: mySeatIndex,
        emoji,
        target_seat: targetSeat,
        table: get().table,
        seats: get().seats,
      },
    })
  },

  // ========================================================
  // TURN TIMER
  // ========================================================

  _startTurnTimer: () => {
    const state = get()
    if (state._timerInterval) clearInterval(state._timerInterval)

    set({ turnTimeLeft: 30, turnTimerActive: true })

    const interval = setInterval(() => {
      const { turnTimeLeft, tableId } = get()
      if (turnTimeLeft <= 1) {
        // Auto-stand when timer expires
        get()._stopTurnTimer()
        get().playerStand()
        return
      }
      set({ turnTimeLeft: turnTimeLeft - 1 })
    }, 1000)

    set({ _timerInterval: interval })
  },

  _stopTurnTimer: () => {
    const { _timerInterval } = get()
    if (_timerInterval) clearInterval(_timerInterval)
    set({ turnTimerActive: false, turnTimeLeft: 30, _timerInterval: null })
  },
}))
