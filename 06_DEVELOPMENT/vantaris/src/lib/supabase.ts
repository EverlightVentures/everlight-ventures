/**
 * Vantaris Supabase Client
 *
 * Connects to the Everlight Supabase project.
 * Handles: auth, player data, game history, leaderboards,
 * edge functions (dealer-speak, checkout, blackjack-api).
 */

import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = 'https://jdqqmsmwmbsnlnstyavl.supabase.co'
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww'

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// ============================================================
// AUTH
// ============================================================

export async function signUp(email: string, password: string, displayName: string) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: { display_name: displayName },
    },
  })
  if (error) throw error
  return data
}

export async function signIn(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) throw error
  return data
}

export async function signInWithGoogle() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: window.location.origin + '/vantaris' },
  })
  if (error) throw error
  return data
}

export async function signOut() {
  const { error } = await supabase.auth.signOut()
  if (error) throw error
}

export async function getSession() {
  const { data: { session } } = await supabase.auth.getSession()
  return session
}

export async function getUser() {
  const { data: { user } } = await supabase.auth.getUser()
  return user
}

// ============================================================
// EDGE FUNCTIONS
// ============================================================

export async function dealerSpeak(text: string, voiceId: string): Promise<Blob | null> {
  try {
    const { data, error } = await supabase.functions.invoke('dealer-speak', {
      body: { text, voice_id: voiceId },
    })
    if (error) throw error
    return data as Blob
  } catch (err) {
    console.warn('[supabase] dealerSpeak failed:', err)
    return null
  }
}

export async function createCheckout(slug: string, profileId: string) {
  const { data, error } = await supabase.functions.invoke('create-checkout', {
    body: {
      slug,
      profile_id: profileId,
      success_url: window.location.origin + '/play/blackjack?checkout=success',
      cancel_url: window.location.origin + '/play/blackjack?checkout=canceled',
      metadata: { slug, product_type: slug.startsWith('gems') ? 'gems' : 'chips' },
    },
  })
  if (error) throw error
  return data
}

export async function verifyCheckout(sessionId: string) {
  const { data, error } = await supabase.functions.invoke('verify-checkout-session', {
    body: { session_id: sessionId },
  })
  if (error) throw error
  return data
}

// ============================================================
// PLAYER DATA
// ============================================================

// Map a real player_accounts row to a back-compat shape so components that
// read profile.gold_coins / profile.id keep working while the source of
// truth is the live player_accounts table.
function withChipAliases(row: any) {
  if (!row) return row
  return {
    ...row,
    id: row.player_id ?? row.id,
    gold_coins: row.chip_balance ?? row.free_chips ?? 0,
    sweeps_coins: row.gem_balance ?? 0,
    rank: row.equipped_title ?? rankFromLevel(row.level ?? 1),
  }
}

function rankFromLevel(level: number): string {
  if (level >= 50) return 'Sovereign'
  if (level >= 30) return 'Ascendant'
  if (level >= 15) return 'Gilded'
  if (level >= 5) return 'Ember'
  return 'Spark'
}

// Translate legacy update keys to real player_accounts columns.
function mapPlayerUpdates(updates: Record<string, any>): Record<string, any> {
  const out: Record<string, any> = { ...updates }
  if ('gold_coins' in out) { out.chip_balance = out.gold_coins; delete out.gold_coins }
  if ('sweeps_coins' in out) { out.gem_balance = out.sweeps_coins; delete out.sweeps_coins }
  if ('rank' in out) delete out.rank
  out.updated_at = new Date().toISOString()
  return out
}

export async function getPlayerProfile(_userId: string) {
  // Players bridge to auth by EMAIL (player_id is the account's own uuid,
  // gen_random_uuid default). The browser can SELECT-own but cannot INSERT
  // player_accounts (RLS = service_role only), so account creation happens
  // server-side; here we just read. Returns null if no account yet.
  const user = await getUser()
  const email = user?.email ?? null
  if (!email) return null
  const { data, error } = await supabase
    .from('player_accounts')
    .select('*')
    .eq('email', email)
    .order('created_at', { ascending: true })
    .limit(1)
    .maybeSingle()
  if (error) {
    console.warn('[supabase] getPlayerProfile failed:', error.message)
    return null
  }
  return data ? withChipAliases(data) : null
}

export async function createPlayerProfile(userId: string) {
  const user = await getUser()
  const displayName = user?.user_metadata?.display_name || 'Player'

  const { data, error } = await supabase
    .from('player_accounts')
    .insert({
      player_id: userId,
      email: user?.email ?? null,
      display_name: displayName,
      chip_balance: 1000,
      free_chips: 0,
      gem_balance: 0,
      level: 1,
      xp: 0,
    })
    .select()
    .single()

  if (error) throw error
  return withChipAliases(data)
}

export async function updatePlayerProfile(playerId: string, updates: Record<string, any>) {
  const { data, error } = await supabase
    .from('player_accounts')
    .update(mapPlayerUpdates(updates))
    .eq('player_id', playerId)
    .select()
    .single()

  if (error) throw error
  return withChipAliases(data)
}

// ============================================================
// GAME HISTORY  (canonical event log = player_events)
// ============================================================

export async function saveGameRound(round: {
  player_id: string
  game: string
  currency: string
  bet_amount: number
  win_amount: number
  net: number
  multiplier: number
  game_data: any
  xp_earned: number
}) {
  const { data, error } = await supabase
    .from('player_events')
    .insert({
      player_id: round.player_id,
      event_type: 'game_round',
      page: `/play/${round.game}`,
      event_data: {
        game: round.game,
        currency: round.currency,
        bet_amount: round.bet_amount,
        win_amount: round.win_amount,
        net: round.net,
        multiplier: round.multiplier,
        xp_earned: round.xp_earned,
        ...round.game_data,
      },
    })
    .select()
    .single()

  if (error) throw error
  return data
}

// Record an arcade high score (dice, mines, plinko, roulette, crash).
export async function submitArcadeScore(game: string, playerName: string, score: number) {
  const { error } = await supabase
    .from('arcade_scores')
    .insert({ game, player_name: playerName, score: Math.floor(score) })
  if (error) console.warn('[supabase] submitArcadeScore failed:', error)
}

export async function getGameHistory(playerId: string, limit: number = 50) {
  const { data, error } = await supabase
    .from('player_events')
    .select('*')
    .eq('player_id', playerId)
    .eq('event_type', 'game_round')
    .order('created_at', { ascending: false })
    .limit(limit)

  if (error) throw error
  return data || []
}

// ============================================================
// LEADERBOARD  (blackjack rollup table + arcade high scores)
// ============================================================

export async function getLeaderboard(game: string = 'blackjack', _period: string = 'all_time') {
  if (game === 'blackjack') {
    const { data, error } = await supabase
      .from('blackjack_leaderboard')
      .select('display_name, total_winnings, hands_played, hands_won, biggest_win, jackpots_won')
      .order('total_winnings', { ascending: false })
      .limit(50)
    if (error) throw error
    return (data || []).map((r, i) => ({
      rank: i + 1,
      display_name: r.display_name,
      score: r.total_winnings,
      hands_played: r.hands_played,
      hands_won: r.hands_won,
      biggest_win: r.biggest_win,
    }))
  }

  const { data, error } = await supabase
    .from('arcade_scores')
    .select('player_name, score')
    .eq('game', game)
    .order('score', { ascending: false })
    .limit(50)
  if (error) throw error
  return (data || []).map((r, i) => ({ rank: i + 1, display_name: r.player_name, score: r.score }))
}

// ============================================================
// REALTIME (for multiplayer table state)
// ============================================================

export function subscribeToTable(tableId: string, callback: (payload: any) => void) {
  return supabase
    .channel(`table:${tableId}`)
    .on('broadcast', { event: 'game_state' }, (payload) => {
      callback(payload)
    })
    .subscribe()
}

export function broadcastToTable(tableId: string, event: string, payload: any) {
  supabase
    .channel(`table:${tableId}`)
    .send({
      type: 'broadcast',
      event,
      payload,
    })
}
