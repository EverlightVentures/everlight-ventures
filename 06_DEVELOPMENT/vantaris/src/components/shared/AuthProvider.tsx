'use client'

import { useEffect } from 'react'
import { supabase } from '@/lib/supabase'

/**
 * Listens for Supabase auth state changes (OAuth redirects, session refresh).
 * Mounted in the root layout so it catches the OAuth callback on any page.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // This triggers Supabase to check the URL hash for OAuth tokens
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        const name = session.user.user_metadata?.display_name || session.user.user_metadata?.full_name || session.user.email?.split('@')[0] || 'Player'
        localStorage.setItem('vantaris_player_name', name)
        localStorage.setItem('vantaris_welcomed', 'true')
        if (session.user.email === '1m.rich.gee@gmail.com') {
          localStorage.setItem('vantaris_vip', 'true')
        }
      }
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session?.user) {
        const name = session.user.user_metadata?.display_name || session.user.user_metadata?.full_name || session.user.email?.split('@')[0] || 'Player'
        localStorage.setItem('vantaris_player_name', name)
        localStorage.setItem('vantaris_welcomed', 'true')
        if (session.user.email === '1m.rich.gee@gmail.com') {
          localStorage.setItem('vantaris_vip', 'true')
        }
      }
      if (event === 'SIGNED_OUT') {
        localStorage.removeItem('vantaris_player_name')
        localStorage.removeItem('vantaris_vip')
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  return <>{children}</>
}
