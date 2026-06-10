// Supabase Edge Function: game-event
// ---------------------------------------------------------------------------
// Server-side writer for game persistence + analytics. The browser is RLS-
// blocked from writing the game tables, so all writes funnel through here with
// the service_role key.
//
// IMPORT-FREE BY DESIGN: uses built-in Deno.serve + fetch against the Supabase
// REST/Auth API instead of the supabase-js client, so raw-source deploys (via
// the Management API, no CLI bundler) boot cleanly with zero remote imports.
//
// Accepts (POST JSON):
//   { type: "game_round", game, bet, win, net, multiplier, gameData,
//     playerId?, displayName?, newBalance? }
//   { type: "track", event_name, props?, page?, playerId? }
// The caller's auth JWT (Authorization: Bearer ...) identifies the player by
// email so chip-balance updates land on the right account.
// ---------------------------------------------------------------------------

const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

const cors: Record<string, string> = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, content-type, apikey',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
}
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { ...cors, 'Content-Type': 'application/json' } })

const sk = { apikey: SERVICE_KEY, Authorization: `Bearer ${SERVICE_KEY}`, 'Content-Type': 'application/json' }

async function insertRow(table: string, row: unknown) {
  await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: 'POST', headers: { ...sk, Prefer: 'return=minimal' }, body: JSON.stringify(row),
  })
}
async function updateBalanceByEmail(email: string, chip_balance: number) {
  await fetch(`${SUPABASE_URL}/rest/v1/player_accounts?email=eq.${encodeURIComponent(email)}`, {
    method: 'PATCH', headers: { ...sk, Prefer: 'return=minimal' }, body: JSON.stringify({ chip_balance }),
  })
}
async function emailFromJwt(jwt: string): Promise<string | null> {
  if (!jwt) return null
  try {
    const r = await fetch(`${SUPABASE_URL}/auth/v1/user`, { headers: { apikey: SERVICE_KEY, Authorization: `Bearer ${jwt}` } })
    if (!r.ok) return null
    const u = await r.json()
    return u?.email ?? null
  } catch { return null }
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors })
  if (req.method !== 'POST') return json({ ok: false, error: 'POST only' }, 405)

  let body: Record<string, any>
  try { body = await req.json() } catch { return json({ ok: false, error: 'bad json' }, 400) }

  const jwt = (req.headers.get('Authorization') || '').replace(/^Bearer\s+/i, '')
  const email = await emailFromJwt(jwt)
  const safe = async (label: string, fn: () => Promise<unknown>) => {
    try { await fn() } catch (e) { console.warn(`[game-event] ${label} failed:`, String(e)) }
  }

  if (body.type === 'game_round') {
    const { game, bet = 0, win = 0, net = win - bet, multiplier = 0, gameData = {}, playerId = null, displayName, newBalance } = body
    await safe('event', () => insertRow('player_events', {
      player_id: playerId, event_type: 'game_round', page: `/play/${game}`,
      event_data: { game, bet, win, net, multiplier, ...gameData },
    }))
    if (win - bet > 0 && displayName) {
      await safe('score', () => insertRow('arcade_scores', { game, player_name: displayName, score: Math.floor(win - bet) }))
    }
    if (email && typeof newBalance === 'number') {
      await safe('balance', () => updateBalanceByEmail(email, Math.max(0, Math.floor(newBalance))))
    }
    return json({ ok: true })
  }

  if (body.type === 'track') {
    await safe('track', () => insertRow('player_events', {
      player_id: body.playerId ?? null,
      event_type: String(body.event_name || 'event').slice(0, 60),
      page: body.page ?? null,
      event_data: body.props ?? {},
    }))
    return json({ ok: true })
  }

  return json({ ok: false, error: 'unknown type' }, 400)
})
