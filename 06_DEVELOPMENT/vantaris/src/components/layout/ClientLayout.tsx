'use client'

import { AnimatePresence } from 'framer-motion'
import { SiteNav } from './SiteNav'
import { SiteFooter } from './SiteFooter'
import { PageTransition } from './PageTransition'

export function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SiteNav />
      <AnimatePresence mode="wait">
        <PageTransition>{children}</PageTransition>
      </AnimatePresence>
      <SiteFooter />
    </>
  )
}
