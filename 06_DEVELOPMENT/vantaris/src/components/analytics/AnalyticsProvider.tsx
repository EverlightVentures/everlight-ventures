'use client'

/**
 * AnalyticsProvider
 *
 * Auto-fires a page_view (event + page_views row) on every App Router
 * navigation, ensures the sessions row exists once per session, and keeps
 * identify() synced with the Supabase auth user so every queued event carries
 * the right user_id. Renders nothing. Mount once, high in the tree (inside
 * ClientLayout, just under AuthProvider).
 *
 * Contract: uses the same canonical event names + property keys as
 * src/lib/analytics.ts and the migration (page_view, session_start, etc.).
 */

import { useEffect, useRef, Suspense } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import {
  trackPageView,
  trackPageViewRow,
  ensureSession,
  identify,
} from '@/lib/analytics'

function PageViewTracker() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const enterMsRef = useRef<number>(Date.now())
  const lastPathRef = useRef<string | null>(null)

  useEffect(() => {
    if (!pathname) return

    // Time-on-page for the PREVIOUS route (sent when we navigate away).
    const now = Date.now()
    if (lastPathRef.current && lastPathRef.current !== pathname) {
      const durationMs = now - enterMsRef.current
      trackPageViewRow(lastPathRef.current, undefined, durationMs)
    }

    const qs = searchParams?.toString()
    const fullPath = qs ? `${pathname}?${qs}` : pathname

    // Make sure the session row exists before the first event of the session.
    ensureSession()
    trackPageView(fullPath)

    lastPathRef.current = pathname
    enterMsRef.current = now
  }, [pathname, searchParams])

  // Flush the final page_views row (with duration) on unload.
  useEffect(() => {
    const handler = () => {
      if (lastPathRef.current) {
        trackPageViewRow(lastPathRef.current, undefined, Date.now() - enterMsRef.current)
      }
    }
    window.addEventListener('pagehide', handler)
    return () => window.removeEventListener('pagehide', handler)
  }, [])

  return null
}

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  // Keep the known user id stamped onto every queued event.
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      identify(session?.user?.id ?? null)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session?.user) {
        identify(session.user.id)
      }
      if (event === 'SIGNED_OUT') {
        identify(null)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  return (
    <>
      {/* useSearchParams requires a Suspense boundary in App Router. */}
      <Suspense fallback={null}>
        <PageViewTracker />
      </Suspense>
      {children}
    </>
  )
}
