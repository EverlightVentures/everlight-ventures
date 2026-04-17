import type { Metadata } from 'next'
import '../styles/design-system.css'
import { SiteNav } from '@/components/layout/SiteNav'
import { SiteFooter } from '@/components/layout/SiteFooter'

export const metadata: Metadata = {
  title: 'Everlight Ventures | Innovation Meets Opportunity',
  description: 'Everlight Ventures -- AI consulting, casino gaming, publishing, SaaS products, and real estate. Built by the Hive Mind.',
  keywords: 'everlight ventures, vantaris casino, alley kingz, onyx pos, hive mind, publishing, wholesale',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&family=Playfair+Display:wght@400;600;700;900&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="noise-overlay">
        <SiteNav />
        {children}
        <SiteFooter />
      </body>
    </html>
  )
}
