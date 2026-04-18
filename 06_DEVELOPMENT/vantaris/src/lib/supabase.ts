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

export async function createCheckout(packageId: string, profileId: string) {
  const { data, error } = await supabase.functions.invoke('create-checkout', {
    body: {
      package_id: packageId,
      profile_id: profileId,
      success_url: window.location.origin + '/play/blackjack?checkout=success',
      cancel_url: window.location.origin + '/play/blackjack?checkout=canceled',
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

export async function getPlayerProfile(userId: string) {
  const { data, error } = await supabase
    .from('casino_players')
    .select('*')
    .eq('user_id', userId)
    .single()

  if (error && error.code === 'PGRST116') {
    // Profile doesn't exist, create one
    return createPlayerProfile(userId)
  }
  if (error) throw error
  return data
}

export async function createPlayerProfile(userId: string) {
  const user = await getUser()
  const displayName = user?.user_metadata?.display_name || 'Player'

  const { data, error } = await supabase
    .from('casino_players')
    .insert({
      user_id: userId,
      display_name: displayName,
      gold_coins: 1000,
      sweeps_coins: 0,
      xp: 0,
      rank: 'Ember',
    })
    .select()
    .single()

  if (error) throw error
  return data
}

export async function updatePlayerProfile(playerId: string, updates: Record<string, any>) {
  const { data, error } = await supabase
    .from('casino_players')
    .update(updates)
    .eq('id', playerId)
    .select()
    .single()

  if (error) throw error
  return data
}

// ============================================================
// GAME HISTORY
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
    .from('casino_game_rounds')
    .insert(round)
    .select()
    .single()

  if (error) throw error
  return data
}

export async function getGameHistory(playerId: string, limit: number = 50) {
  const { data, error } = await supabase
    .from('casino_game_rounds')
    .select('*')
    .eq('player_id', playerId)
    .order('played_at', { ascending: false })
    .limit(limit)

  if (error) throw error
  return data || []
}

// ============================================================
// LEADERBOARD
// ============================================================

export async function getLeaderboard(game: string = 'blackjack', period: string = 'weekly') {
  const since = period === 'daily'
    ? new Date(Date.now() - 86400000).toISOString()
    : period === 'weekly'
      ? new Date(Date.now() - 604800000).toISOString()
      : new Date(Date.now() - 31536000000).toISOString()

  const { data, error } = await supabase
    .from('casino_game_rounds')
    .select('player_id, casino_players(display_name, rank)')
    .eq('game', game)
    .gte('played_at', since)

  if (error) throw error
  return data || []
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
