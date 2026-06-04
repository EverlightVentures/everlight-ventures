'use client'

import { useState } from 'react'
import { CasinoLoader } from '@/components/shared/CasinoLoader'

/**
 * Game-entry layout: the "walking into Vantaris" animation plays ONCE when you
 * SELECT A GAME (enter any /play/* route from the lobby), not when you open the
 * casino tab. The layout mounts on entry to the game section and the loader
 * dismisses itself, revealing the game behind it -- like walking through the doors.
 */
export default function PlayLayout({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false)
  return (
    <>
      {!ready && <CasinoLoader onComplete={() => setReady(true)} />}
      {children}
    </>
  )
}
