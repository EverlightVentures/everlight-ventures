/**
 * Vantaris / Everlight First-Party Analytics
 *
 * SSR-safe, never-throws client analytics. Mirrors a Google-Analytics-style
 * event model into our own Supabase tables so we own every data point the site
 * generates (free-first law, no paid vendor).
 *
 * CONTRACT: this file is one of three artifacts that share a single contract
 * (the migration + the event taxonomy are the other two). The object inserted
 * into analytics_events has EXACTLY these keys, matching the migration columns:
 *   { event_name, user_id, anon_id, session_id, page, referrer, props, created_at }
 *
 * Canonical event names (snake_case, STABLE -- never renamed; new behavior =
 * new event): page_view, session_start, click, scroll_depth, search,
 * outbound_click, sign_up, login, lead_captured, checkout_started,
 * checkout_completed, game_started, game_round, game_cashout, high_score_set,
 * level_up, wholesale_lead_created, wholesale_status_changed.
 *
 * Surface:
 *   track(eventName, props?)                 -> queue a custom event
 *   trackPageView(path, title?)              -> queue a page_view event
 *   trackPageViewRow(path, title?, durMs?)   -> write the narrow page_views row
 *   ensureSession(acq?)                      -> upsert the sessions row once
 *   submitHighScore(args)                    -> write a high_scores row
 *   identify(userId)                         -> stamp the known auth user
 *   getAnonId() / getSessionId()             -> stable ids
 *
 * PRIVACY: never put raw PII (email, phone, full name, card, gov id, raw IP,
 * free-text message bodies) into props. Reference by user_id / lead_id instead.
 * sanitizeProps() strips known-PII keys defensively before every insert.
 *
 * Hard rules:
 *   - Wrapped in try/catch everywhere. A broken analytics call MUST NOT break UI.
 *   - No-op on the server (typeof window === 'undefined').
 *   - Fire-and-forget batched flush. Never blocks render or user input.
 */

import { supabase } from './supabase'

// ============================================================
// CONSTANTS
// ============================================================

const ANON_KEY = 'ev_anon_id'
const SESSION_ID_KEY = 'ev_session_id'
const SESSION_TS_KEY = 'ev_session_last'
const SESSION_SENT_KEY = 'ev_session_sent'
const USER_KEY = 'ev_user_id'

const SESSION_IDLE_MS = 30 * 60 * 1000 // 30-minute idle window
const FLUSH_INTERVAL_MS = 4000         // background flush cadence
const MAX_BATCH = 25                   // rows per insert
const MAX_QUEUE = 500                  // hard cap so a dead network cannot grow memory forever

// Keys we refuse to write into props (defense-in-depth against PII leakage).
const PII_DENY_KEYS = new Set([
  'email', 'phone', 'name', 'first_name', 'last_name', 'full_name',
  'password', 'token', 'jwt', 'api_key', 'card', 'card_number', 'pan', 'cvv',
  'cvc', 'ssn', 'dob', 'address', 'street', 'zip', 'zip_code', 'ip',
  'message', 'message_body', 'owner_name',
])

// ============================================================
// TYPES
// ============================================================

export interface AnalyticsEventRow {
  event_name: string
  user_id: string | null
  anon_id: string
  session_id: string
  page: string | null
  referrer: string | null
  props: Record<string, unknown>
  created_at: string // client ISO timestamp (server also defaults its own)
}

export interface Acquisition {
  utm_source?: string
  utm_medium?: string
  utm_campaign?: string
  utm_term?: string
  utm_content?: string
}

// ============================================================
// ENVIRONMENT GUARD
// ============================================================

const isBrowser = (): boolean => typeof window !== 'undefined'

// ============================================================
// ID HELPERS
// ============================================================

function uuid(): string {
  try {
    if (isBrowser() && window.crypto && 'randomUUID' in window.crypto) {
      return window.crypto.randomUUID()
    }
  } catch {
    /* fall through */
  }
  // Fallback for older runtimes
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

function safeGet(key: string): string | null {
  try {
    if (!isBrowser()) return null
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function safeSet(key: string, value: string): void {
  try {
    if (!isBrowser()) return
    window.localStorage.setItem(key, value)
  } catch {
    /* private mode / quota / SSR: ignore */
  }
}

export function getAnonId(): string {
  try {
    if (!isBrowser()) return 'ssr'
    let id = safeGet(ANON_KEY)
    if (!id) {
      id = uuid()
      safeSet(ANON_KEY, id)
    }
    return id
  } catch {
    return 'ssr'
  }
}

export function getSessionId(): string {
  try {
    if (!isBrowser()) return 'ssr'
    const now = Date.now()
    const lastRaw = safeGet(SESSION_TS_KEY)
    const last = lastRaw ? parseInt(lastRaw, 10) : 0
    let id = safeGet(SESSION_ID_KEY)

    // New session if none exists or the idle window expired.
    if (!id || !last || now - last > SESSION_IDLE_MS) {
      id = uuid()
      safeSet(SESSION_ID_KEY, id)
      // A brand-new session id means we must (re)write the sessions row.
      try { window.localStorage.removeItem(SESSION_SENT_KEY) } catch { /* no-op */ }
    }
    // Roll the idle clock forward on every touch.
    safeSet(SESSION_TS_KEY, String(now))
    return id
  } catch {
    return 'ssr'
  }
}

export function identify(userId: string | null): void {
  try {
    if (!isBrowser()) return
    if (userId) {
      safeSet(USER_KEY, userId)
    } else {
      window.localStorage.removeItem(USER_KEY)
    }
  } catch {
    /* no-op */
  }
}

function currentUserId(): string | null {
  return safeGet(USER_KEY)
}

// ============================================================
// PROP SANITIZER (deny-by-known-PII, defense in depth)
// ============================================================

function sanitizeProps(props: Record<string, unknown>): Record<string, unknown> {
  try {
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(props || {})) {
      if (PII_DENY_KEYS.has(k.toLowerCase())) continue
      // Drop obvious raw email/phone values even under an allowed key name.
      if (typeof v === 'string') {
        if (/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) continue
        if (/\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b/.test(v)) continue
      }
      out[k] = v
    }
    return out
  } catch {
    return {}
  }
}

// ============================================================
// QUEUE + FLUSH (fire-and-forget batching)
// ============================================================

let queue: AnalyticsEventRow[] = []
let timer: ReturnType<typeof setInterval> | null = null
let flushing = false

function ensureTimer(): void {
  try {
    if (!isBrowser() || timer) return
    timer = setInterval(() => {
      void flush()
    }, FLUSH_INTERVAL_MS)

    // Best-effort flush when the tab is backgrounded or closed.
    window.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') void flush()
    })
    window.addEventListener('pagehide', () => {
      void flush()
    })
  } catch {
    /* no-op */
  }
}

async function flush(): Promise<void> {
  try {
    if (!isBrowser() || flushing || queue.length === 0) return
    flushing = true

    const batch = queue.slice(0, MAX_BATCH)
    const { error } = await supabase.from('analytics_events').insert(batch)

    if (error) {
      // Keep the batch; it will be retried next tick. Do not throw.
      flushing = false
      return
    }

    // Drop the rows we successfully sent.
    queue = queue.slice(batch.length)
    flushing = false

    // Drain quickly if a backlog built up.
    if (queue.length > 0) void flush()
  } catch {
    flushing = false
  }
}

function enqueue(eventName: string, page: string | null, props: Record<string, unknown>): void {
  try {
    if (!isBrowser()) return

    const evt: AnalyticsEventRow = {
      event_name: String(eventName).slice(0, 40),
      user_id: currentUserId(),
      anon_id: getAnonId(),
      session_id: getSessionId(),
      page: page ?? (isBrowser() ? window.location.pathname : null),
      referrer: isBrowser() ? document.referrer || null : null,
      props: sanitizeProps(props || {}),
      created_at: new Date().toISOString(),
    }

    queue.push(evt)
    if (queue.length > MAX_QUEUE) queue = queue.slice(-MAX_QUEUE)

    ensureTimer()
  } catch {
    /* never throw from analytics */
  }
}

// ============================================================
// PUBLIC API
// ============================================================

export function track(eventName: string, props: Record<string, unknown> = {}): void {
  enqueue(eventName, null, props)
}

export function trackPageView(path: string, title?: string): void {
  enqueue('page_view', path, {
    page_path: path,
    page_title: title ?? (isBrowser() ? document.title : null),
  })
}

/**
 * Write the narrow page_views row (mirrors GA "Pages and screens"). Call this
 * in addition to trackPageView when you want time-on-page / query-string in the
 * cheap denormalized table that feeds site_traffic_daily.
 */
export function trackPageViewRow(path: string, title?: string, durationMs?: number): void {
  try {
    if (!isBrowser()) return
    const row = {
      session_id: getSessionId(),
      anon_id: getAnonId(),
      user_id: currentUserId(),
      page: path,
      page_title: title ?? document.title ?? null,
      referrer: document.referrer || null,
      query_string: window.location.search ? window.location.search.slice(1) : null,
      duration_ms: typeof durationMs === 'number' ? Math.max(0, Math.floor(durationMs)) : null,
      created_at: new Date().toISOString(),
    }
    void supabase.from('page_views').insert(row)
  } catch {
    /* never throw */
  }
}

/**
 * Upsert the sessions row once per session id. Fires session_start the first
 * time a session is seen. Safe to call on every mount -- guarded by a sent flag.
 */
export function ensureSession(acq: Acquisition = {}): void {
  try {
    if (!isBrowser()) return
    const sessionId = getSessionId()
    const alreadySent = safeGet(SESSION_SENT_KEY)
    if (alreadySent === sessionId) return

    const params = new URLSearchParams(window.location.search)
    const utm: Acquisition = {
      utm_source: acq.utm_source ?? params.get('utm_source') ?? undefined,
      utm_medium: acq.utm_medium ?? params.get('utm_medium') ?? undefined,
      utm_campaign: acq.utm_campaign ?? params.get('utm_campaign') ?? undefined,
      utm_term: acq.utm_term ?? params.get('utm_term') ?? undefined,
      utm_content: acq.utm_content ?? params.get('utm_content') ?? undefined,
    }

    const ua = navigator.userAgent || ''
    const deviceType = /Mobi|Android|iPhone/i.test(ua)
      ? 'mobile'
      : /iPad|Tablet/i.test(ua)
        ? 'tablet'
        : 'desktop'

    const row = {
      session_id: sessionId,
      anon_id: getAnonId(),
      user_id: currentUserId(),
      landing_page: window.location.pathname,
      referrer: document.referrer || null,
      utm_source: utm.utm_source ?? null,
      utm_medium: utm.utm_medium ?? null,
      utm_campaign: utm.utm_campaign ?? null,
      utm_term: utm.utm_term ?? null,
      utm_content: utm.utm_content ?? null,
      device_type: deviceType,
      os: null,
      browser: null,
      screen_w: window.screen?.width ?? null,
      screen_h: window.screen?.height ?? null,
      language: navigator.language || null,
    }

    void supabase.from('sessions').upsert(row, { onConflict: 'session_id' })
    safeSet(SESSION_SENT_KEY, sessionId)

    // The first event of a new session is session_start (taxonomy).
    track('session_start', {
      session_id: sessionId,
      is_first_session: !safeGet(ANON_KEY) ? true : undefined,
      landing_path: window.location.pathname,
      ...utm,
    })
  } catch {
    /* never throw */
  }
}

/**
 * Record a high score. Call alongside a high_score_set event when a personal or
 * global best is beaten. score is numeric (holds multipliers + integer scores).
 */
export function submitHighScore(args: {
  game: string
  score: number
  metric?: string // max_win | max_multiplier | win_streak | net_session | tiles | points
  period?: string // daily | weekly | monthly | all_time
  playerId?: string | null
  displayName?: string | null
  props?: Record<string, unknown>
}): void {
  try {
    if (!isBrowser()) return
    const row = {
      game: args.game,
      player_id: args.playerId ?? null,
      user_id: currentUserId(),
      display_name: args.displayName ?? null,
      score: args.score,
      metric: args.metric ?? 'score',
      period: args.period ?? 'all_time',
      props: sanitizeProps(args.props ?? {}),
      created_at: new Date().toISOString(),
    }
    void supabase.from('high_scores').insert(row)
    // Mirror as an analytics event for funnel/cohort joins.
    track('high_score_set', {
      game: args.game,
      score: args.score,
      score_type: args.metric ?? 'score',
      scope: 'personal',
      period: args.period ?? 'all_time',
    })
  } catch {
    /* never throw */
  }
}

// Default export for ergonomic imports.
const analytics = {
  track,
  trackPageView,
  trackPageViewRow,
  ensureSession,
  submitHighScore,
  identify,
  getAnonId,
  getSessionId,
}
export default analytics
