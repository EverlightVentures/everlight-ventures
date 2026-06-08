'use client'

import { useRef, useEffect } from 'react'
import { useBlackjackStore } from '@/lib/blackjack-store'
import { DealerAvatar } from './DealerAvatar'

/**
 * DealerStage -- the seated dealer, bigger than the old icon, that DEALS IN SYNC
 * with the game. The dealer's live-action video (bcardd_live / aria_live) plays
 * its dealing motion on EACH card dealt (initial deal, hit, double, split, and
 * the dealer's own draws), then pauses on a frame (idle) when no one is acting.
 *
 * The sync signal is the total card count in the store (dealerHand + every seat's
 * hand + split hands). When it rises, a card was just dealt -> play the motion;
 * after ~1.8s with no new card, pause. Settle / new round resets to idle. No
 * random loop -- the dealing is coordinated to real game actions.
 *
 * Dealers without a video clip (marcus/kanisha) fall back to the SVG avatar.
 */

const DEALER_VIDEOS: Record<string, string> = {
  // official_bdl.mp4 = the new official B-CARDD dealer footage (replaces bcardd_live).
  bcardd: '/dealers/official_bdl.mp4',
  aria: '/dealers/aria_live.mp4',
}
const DEAL_MOTION_MS = 1800

export function DealerStage({ size = 72 }: { size?: number }) {
  const activeDealer = useBlackjackStore((s) => s.activeDealer)
  const dealerHand = useBlackjackStore((s) => s.dealerHand)
  const seats = useBlackjackStore((s) => s.seats)
  const phase = useBlackjackStore((s) => s.phase)

  // Rises whenever a card is physically dealt anywhere on the table.
  const totalCards =
    (dealerHand?.cards?.length || 0) +
    seats.reduce((n, s) => n + (s.hand?.cards?.length || 0) + (s.splitHand?.cards?.length || 0), 0)

  const vid = useRef<HTMLVideoElement>(null)
  const prev = useRef(totalCards)
  const idle = useRef<ReturnType<typeof setTimeout> | null>(null)

  const src = activeDealer ? DEALER_VIDEOS[activeDealer.id] : undefined

  // Deal on each new card; idle (pause) a beat after the last one.
  useEffect(() => {
    const v = vid.current
    if (v && totalCards > prev.current) {
      try { v.currentTime = 0; v.play() } catch {}
      if (idle.current) clearTimeout(idle.current)
      idle.current = setTimeout(() => { try { v.pause() } catch {} }, DEAL_MOTION_MS)
    }
    prev.current = totalCards
    return () => { if (idle.current) clearTimeout(idle.current) }
  }, [totalCards])

  // New round / settled -> reset to a calm idle frame.
  useEffect(() => {
    const v = vid.current
    if (v && (phase === 'betting' || phase === 'settled')) {
      try { v.pause(); v.currentTime = 0 } catch {}
    }
  }, [phase])

  if (!activeDealer) return null
  const ring = activeDealer.color || '#c9a84c'

  if (!src) {
    // No live clip for this dealer -- keep the SVG avatar.
    return <DealerAvatar dealerId={activeDealer.id} color={ring} speaking={false} size={size} />
  }

  return (
    <div
      className="relative rounded-full overflow-hidden flex-shrink-0"
      style={{
        width: size, height: size,
        border: `2px solid ${ring}66`,
        boxShadow: `0 6px 18px rgba(0,0,0,.55), 0 0 20px ${ring}40, inset 0 0 12px ${ring}22`,
      }}
    >
      <video
        ref={vid}
        src={src}
        muted
        playsInline
        preload="auto"
        className="w-full h-full object-cover"
        style={{ transform: 'scale(1.18)' }}
      />
      {/* soft bottom shade so a name overlay (if added) stays legible */}
      <div className="absolute inset-x-0 bottom-0 h-1/3 pointer-events-none"
        style={{ background: 'linear-gradient(180deg, transparent, rgba(0,0,0,.45))' }} />
    </div>
  )
}
