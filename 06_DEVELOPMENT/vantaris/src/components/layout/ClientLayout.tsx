'use client'

import { useState, useCallback } from 'react'
import { AnimatePresence } from 'framer-motion'
import { SiteNav } from './SiteNav'
import { SiteFooter } from './SiteFooter'
import { PageTransition } from './PageTransition'
import { CustomCursor } from '../shared/CustomCursor'
import { IntroLoader } from '../shared/IntroLoader'
import { AuthProvider } from '../shared/AuthProvider'

export function ClientLayout({ children }: { children: React.ReactNode }) {
  const [loaded, setLoaded] = useState(false)
  const onComplete = useCallback(() => setLoaded(true), [])

  return (
    <AuthProvider>
      {!loaded && <IntroLoader onComplete={onComplete} />}
      <CustomCursor />
      <SiteNav />
      <AnimatePresence mode="wait">
        <PageTransition>{children}</PageTransition>
      </AnimatePresence>
      <SiteFooter />
    </AuthProvider>
  )
}
