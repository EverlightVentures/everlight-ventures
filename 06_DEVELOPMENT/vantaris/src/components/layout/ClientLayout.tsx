'use client'

import { AnimatePresence } from 'framer-motion'
import { SiteNav } from './SiteNav'
import { SiteFooter } from './SiteFooter'
import { PageTransition } from './PageTransition'
import { CustomCursor } from '../shared/CustomCursor'
import { AuthProvider } from '../shared/AuthProvider'

export function ClientLayout({ children }: { children: React.ReactNode }) {
  // Site no longer shows a global intro loader on open. The "walking into
  // Vantaris" animation now plays only on game-select (src/app/play/layout.tsx).
  return (
    <AuthProvider>
      <CustomCursor />
      <SiteNav />
      <AnimatePresence mode="wait">
        <PageTransition>{children}</PageTransition>
      </AnimatePresence>
      <SiteFooter />
    </AuthProvider>
  )
}
