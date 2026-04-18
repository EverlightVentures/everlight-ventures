'use client'

import { useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { useBlackjackStore } from '@/lib/blackjack-store'

// VIP accounts -- auto-credited on sign-in
const VIP_EMAILS = [
  '1m.rich.gee@gmail.com',   // Founder/CEO
  'tapizme@gmail.com',        // VIP guest
]

const VIP_CREDIT = 100000 // 100K chips on first VIP sign-in

function handleVipSetup(email: string, name: string, avatarUrl?: string) {
  localStorage.setItem('vantaris_player_name', name)
  localStorage.setItem('vantaris_welcomed', 'true')
  if (avatarUrl) localStorage.setItem('vantaris_avatar_url', avatarUrl)

  if (VIP_EMAILS.includes(email)) {
    localStorage.setItem('vantaris_vip', 'true')

    // One-time VIP chip credit
    const creditKey = `vantaris_vip_credited_${email}`
    if (!localStorage.getItem(creditKey)) {
      const state = useBlackjackStore.getState()
      useBlackjackStore.setState({
        player: {
          ...state.player,
          chips: state.player.chips + VIP_CREDIT,
          sweepsCoins: state.player.sweepsCoins + 50,
          gems: state.player.gems + 500,
        },
      })
      localStorage.setItem(creditKey, 'true')
    }
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        const name = session.user.user_metadata?.display_name || session.user.user_metadata?.full_name || session.user.email?.split('@')[0] || 'Player'
        const avatar = session.user.user_metadata?.avatar_url || session.user.user_metadata?.picture || ''
        handleVipSetup(session.user.email || '', name, avatar)
      }
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session?.user) {
        const name = session.user.user_metadata?.display_name || session.user.user_metadata?.full_name || session.user.email?.split('@')[0] || 'Player'
        const avatar = session.user.user_metadata?.avatar_url || session.user.user_metadata?.picture || ''
        handleVipSetup(session.user.email || '', name, avatar)
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
