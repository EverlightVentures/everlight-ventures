/**
 * Django Sync Layer
 *
 * Bridges the Vantaris client-side game with the existing
 * Everlight Django backend on Oracle. When deployed to
 * everlightventures.io, this module handles:
 *
 * 1. AUTH -- login/register/guest via Django sessions
 * 2. PROFILE -- load/save player stats, chips, achievements
 * 3. GAME SYNC -- POST hand results to Django after each settle
 * 4. LEADERBOARD -- GET real rankings from Django
 * 5. SHOP -- POST purchases to Django
 *
 * In local dev mode (localhost), this is a no-op -- everything
 * stays in localStorage via Zustand persist. On production
 * (everlightventures.io), it syncs to Django.
 *
 * The Django API endpoints (from the Everlight game):
 * - POST /blackjack/api/deal/
 * - POST /blackjack/api/action/
 * - GET  /blackjack/api/profile/
 * - GET  /blackjack/api/leaderboard/
 * - POST /blackjack/api/avatar/
 * - POST /blackjack/api/purchase/
 * - POST /blackjack/api/ad-reward/
 * - POST /blackjack/api/checkout/gems/
 */

// Detect if we're on the real domain vs localhost
const IS_PRODUCTION = typeof window !== 'undefined' &&
  window.location.hostname.includes('everlightventures')

// Django API base URL (Oracle E5 server)
const DJANGO_BASE = IS_PRODUCTION
  ? '' // same-origin on production
  : 'https://everlightventures.io' // cross-origin in dev (won't work, that's fine)

// CSRF token from Django cookie
function getCSRFToken(): string {
  if (typeof document === 'undefined') return ''
  const match = document.cookie.match(/csrftoken=([^;]+)/)
  return match ? match[1] : ''
}

// Shared fetch wrapper with Django auth headers
async function djangoFetch(path: string, options: RequestInit = {}): Promise<Response | null> {
  if (!IS_PRODUCTION) return null // no-op in dev

  try {
    return await fetch(`${DJANGO_BASE}${path}`, {
      ...options,
      credentials: 'include', // send session cookies
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
        ...(options.headers || {}),
      },
    })
  } catch (err) {
    console.warn('[django-sync] Request failed:', path, err)
    return null
  }
}

// ============================================================
// AUTH
// ============================================================

export async function djangoLogin(username: string, password: string): Promise<boolean> {
  const res = await djangoFetch('/blackjack/api/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  return res?.ok || false
}

export async function djangoRegister(username: string, email: string, password: string): Promise<boolean> {
  const res = await djangoFetch('/blackjack/api/register/', {
    method: 'POST',
    body: JSON.stringify({ username, email, password }),
  })
  return res?.ok || false
}

export async function djangoGuestLogin(): Promise<boolean> {
  const res = await djangoFetch('/blackjack/api/guest/', { method: 'POST' })
  return res?.ok || false
}

// ============================================================
// PROFILE SYNC
// ============================================================

export interface DjangoProfile {
  chips: number
  gems: number
  sweeps_coins: number
  xp: number
  rank: string
  hands_played: number
  hands_won: number
  blackjacks: number
  best_streak: number
  biggest_win: number
  win_rate: number
  presence_multiplier: number
  achievements: string[]
  owned_items: string[]
  avatar: Record<string, string>
}

export async function loadProfile(): Promise<DjangoProfile | null> {
  const res = await djangoFetch('/blackjack/api/profile/')
  if (!res?.ok) return null
  return res.json()
}

export async function saveAvatar(avatar: Record<string, string>): Promise<boolean> {
  const res = await djangoFetch('/blackjack/api/avatar/', {
    method: 'POST',
    body: JSON.stringify(avatar),
  })
  return res?.ok || false
}

// ============================================================
// GAME SYNC (post results after each hand)
// ============================================================

export async function syncHandResult(data: {
  outcome: string
  player_total: number
  dealer_total: number
  bet: number
  payout: number
  side_bets: Record<string, number>
}): Promise<void> {
  await djangoFetch('/blackjack/api/sync-hand/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ============================================================
// LEADERBOARD
// ============================================================

export async function loadLeaderboard(): Promise<any[] | null> {
  const res = await djangoFetch('/blackjack/api/leaderboard/')
  if (!res?.ok) return null
  return res.json()
}

// ============================================================
// SHOP
// ============================================================

export async function purchaseItem(itemId: string, currency: 'chips' | 'gems'): Promise<boolean> {
  const res = await djangoFetch('/blackjack/api/purchase/', {
    method: 'POST',
    body: JSON.stringify({ item_id: itemId, currency }),
  })
  return res?.ok || false
}

export async function claimAdReward(): Promise<{ success: boolean; chips_added: number }> {
  const res = await djangoFetch('/blackjack/api/ad-reward/', { method: 'POST' })
  if (!res?.ok) return { success: false, chips_added: 0 }
  return res.json()
}

// ============================================================
// MIGRATION HELPER
// Called on first load on production to sync localStorage
// state UP to Django (one-time migration for existing players)
// ============================================================

export async function migrateLocalToServer(): Promise<void> {
  if (!IS_PRODUCTION) return

  const migrated = localStorage.getItem('vantaris_migrated')
  if (migrated) return

  // Try to load server profile first
  const serverProfile = await loadProfile()
  if (serverProfile && serverProfile.hands_played > 0) {
    // Server has data -- server wins, don't overwrite
    localStorage.setItem('vantaris_migrated', 'true')
    return
  }

  // Server is empty but local has data -- push local up
  const localData = localStorage.getItem('vantaris-player')
  if (localData) {
    try {
      const parsed = JSON.parse(localData)
      if (parsed.state?.player) {
        await djangoFetch('/blackjack/api/migrate/', {
          method: 'POST',
          body: JSON.stringify(parsed.state.player),
        })
      }
    } catch (err) {
      console.warn('[django-sync] Migration failed:', err)
    }
  }

  localStorage.setItem('vantaris_migrated', 'true')
}

// ============================================================
// AUTO-INIT (call on page mount)
// ============================================================

export function initDjangoSync(): void {
  if (!IS_PRODUCTION) {
    console.log('[django-sync] Dev mode -- syncing disabled, using localStorage')
    return
  }
  console.log('[django-sync] Production mode -- syncing to Django backend')
  migrateLocalToServer()
}

export { IS_PRODUCTION }
