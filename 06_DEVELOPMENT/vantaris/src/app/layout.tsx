import type { Metadata } from 'next'
import '../styles/design-system.css'

export const metadata: Metadata = {
  title: 'Vantaris | The Darkest Star Burns Brightest',
  description: 'Provably fair online casino. Crypto + Sweepstakes. 6 games. AI dealers. You didn\'t find Vantaris. Vantaris found you.',
  keywords: 'casino, crypto casino, sweepstakes, provably fair, blackjack, crash, roulette, dice, plinko, mines',
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
        {children}
      </body>
    </html>
  )
}
