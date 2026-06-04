'use client'

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import dynamic from 'next/dynamic'
import Link from 'next/link'

const MultiplayerTable = dynamic(
  () => import('@/components/blackjack/MultiplayerTable'),
  { ssr: false }
)

/**
 * Multiplayer Blackjack Page
 *
 * URL: /play/blackjack/multi?table=<table_id>
 *
 * Loads the MultiplayerTable component with the table ID from the URL.
 * If no table ID is provided, redirects to the table lobby.
 */

function MultiplayerContent() {
  const searchParams = useSearchParams()
  const tableId = searchParams.get('table')
  const inviteCode = searchParams.get('invite')

  if (!tableId) {
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center gap-4"
        style={{ background: 'var(--vanta-void, #050510)' }}
      >
        <p className="text-sm opacity-60">No table selected.</p>
        <Link href="/tables">
          <button
            className="px-6 py-2 rounded-xl text-xs font-bold tracking-wider"
            style={{
              background: 'linear-gradient(135deg, #c9a84c, #e8c55a)',
              color: '#000',
            }}
          >
            BROWSE TABLES
          </button>
        </Link>
      </div>
    )
  }

  return <MultiplayerTable tableId={tableId} inviteCode={inviteCode || undefined} />
}

export default function MultiplayerPage() {
  return (
    <Suspense
      fallback={
        <div
          className="min-h-screen flex items-center justify-center"
          style={{ background: 'var(--vanta-void, #050510)' }}
        >
          <span className="text-sm animate-pulse" style={{ color: 'var(--gold, #c9a84c)' }}>
            Loading table...
          </span>
        </div>
      }
    >
      <MultiplayerContent />
    </Suspense>
  )
}
