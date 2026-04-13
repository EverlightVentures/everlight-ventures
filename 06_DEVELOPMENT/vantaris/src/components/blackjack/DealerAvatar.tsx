'use client'

import React from 'react'
import { motion } from 'framer-motion'

/**
 * DealerAvatar -- SVG portrait system for 4 dealer personas
 *
 * Each dealer has a unique hand-drawn SVG portrait:
 * - Aria Sinclair: Elegant, gold accents, warm tones
 * - Marcus Vega: Sharp, intense, dark tones
 * - Kanisha Thompson: Vibrant, purple/gold, confident
 * - Bacardi Ice: Cold, cyan/dark, crystalline
 *
 * Includes animated speaking indicator (pulsing green dot).
 */

function AriaSVG() {
  return (
    <svg viewBox="0 0 64 64" className="w-full h-full">
      <defs>
        <radialGradient id="aria-bg" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#2a1a0a" />
          <stop offset="100%" stopColor="#0d0815" />
        </radialGradient>
        <linearGradient id="aria-hair" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1a0d08" />
          <stop offset="100%" stopColor="#0d0604" />
        </linearGradient>
      </defs>
      <circle cx="32" cy="32" r="31" fill="url(#aria-bg)" />
      {/* Hair */}
      <ellipse cx="32" cy="24" rx="18" ry="16" fill="url(#aria-hair)" />
      <ellipse cx="18" cy="32" rx="5" ry="12" fill="#1a0d08" />
      <ellipse cx="46" cy="32" rx="5" ry="12" fill="#1a0d08" />
      {/* Face */}
      <ellipse cx="32" cy="30" rx="13" ry="14" fill="#d4a574" />
      {/* Eyes */}
      <ellipse cx="26" cy="28" rx="2.5" ry="1.8" fill="#fff" />
      <ellipse cx="38" cy="28" rx="2.5" ry="1.8" fill="#fff" />
      <circle cx="26" cy="28" r="1.2" fill="#3d2b1f" />
      <circle cx="38" cy="28" r="1.2" fill="#3d2b1f" />
      {/* Eyebrows */}
      <path d="M23 25 Q26 23 29 25" fill="none" stroke="#3d2b1f" strokeWidth="0.8" />
      <path d="M35 25 Q38 23 41 25" fill="none" stroke="#3d2b1f" strokeWidth="0.8" />
      {/* Nose */}
      <path d="M31 30 Q32 33 33 30" fill="none" stroke="#b8896a" strokeWidth="0.6" />
      {/* Lips */}
      <path d="M27 35 Q32 38 37 35" fill="#c0392b" stroke="none" />
      <path d="M27 35 Q32 33 37 35" fill="#e74c3c" stroke="none" />
      {/* Gold earrings */}
      <circle cx="17" cy="34" r="1.5" fill="#c9a84c" />
      <circle cx="47" cy="34" r="1.5" fill="#c9a84c" />
      {/* Neckline */}
      <path d="M22 42 Q32 48 42 42 L44 52 Q32 56 20 52 Z" fill="#c9a84c" opacity="0.6" />
    </svg>
  )
}

function MarcusSVG() {
  return (
    <svg viewBox="0 0 64 64" className="w-full h-full">
      <defs>
        <radialGradient id="marcus-bg" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#1a0a00" />
          <stop offset="100%" stopColor="#0d0815" />
        </radialGradient>
      </defs>
      <circle cx="32" cy="32" r="31" fill="url(#marcus-bg)" />
      {/* Hair -- short, dark */}
      <ellipse cx="32" cy="22" rx="15" ry="12" fill="#0d0604" />
      {/* Face */}
      <ellipse cx="32" cy="30" rx="13" ry="14" fill="#8d5524" />
      {/* Eyes -- sharp, intense */}
      <ellipse cx="26" cy="28" rx="2.8" ry="1.5" fill="#fff" />
      <ellipse cx="38" cy="28" rx="2.8" ry="1.5" fill="#fff" />
      <circle cx="26.5" cy="28" r="1.3" fill="#1a1a1a" />
      <circle cx="38.5" cy="28" r="1.3" fill="#1a1a1a" />
      {/* Brows -- heavy */}
      <path d="M22 25 L30 24" fill="none" stroke="#1a1a1a" strokeWidth="1.2" />
      <path d="M34 24 L42 25" fill="none" stroke="#1a1a1a" strokeWidth="1.2" />
      {/* Nose */}
      <path d="M30 30 Q32 34 34 30" fill="none" stroke="#7a4a20" strokeWidth="0.8" />
      {/* Goatee */}
      <path d="M28 36 Q32 41 36 36" fill="#1a1a1a" />
      {/* Mouth line */}
      <path d="M28 35 Q32 37 36 35" fill="none" stroke="#5a3010" strokeWidth="0.6" />
      {/* Suit collar */}
      <path d="M20 44 L25 40 L32 44 L39 40 L44 44 L44 52 Q32 56 20 52 Z" fill="#1a1a1a" />
      {/* Tie */}
      <path d="M30 44 L32 52 L34 44 Z" fill="#ff6b35" />
    </svg>
  )
}

function KanishaSVG() {
  return (
    <svg viewBox="0 0 64 64" className="w-full h-full">
      <defs>
        <radialGradient id="kanisha-bg" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#1a0020" />
          <stop offset="100%" stopColor="#0d0815" />
        </radialGradient>
      </defs>
      <circle cx="32" cy="32" r="31" fill="url(#kanisha-bg)" />
      {/* Hair -- voluminous, dark */}
      <ellipse cx="32" cy="22" rx="19" ry="15" fill="#1a0d08" />
      <ellipse cx="16" cy="30" rx="6" ry="14" fill="#1a0d08" />
      <ellipse cx="48" cy="30" rx="6" ry="14" fill="#1a0d08" />
      {/* Face */}
      <ellipse cx="32" cy="30" rx="13" ry="14" fill="#8d5524" />
      {/* Eyes -- warm, expressive */}
      <ellipse cx="26" cy="28" rx="3" ry="2" fill="#fff" />
      <ellipse cx="38" cy="28" rx="3" ry="2" fill="#fff" />
      <circle cx="26" cy="28" r="1.4" fill="#3d1f00" />
      <circle cx="38" cy="28" r="1.4" fill="#3d1f00" />
      {/* Eyelashes */}
      <path d="M23 26.5 Q26 25 29 26.5" fill="none" stroke="#1a1a1a" strokeWidth="0.5" />
      <path d="M35 26.5 Q38 25 41 26.5" fill="none" stroke="#1a1a1a" strokeWidth="0.5" />
      {/* Nose */}
      <path d="M30 30 Q32 34 34 30" fill="none" stroke="#7a4a20" strokeWidth="0.6" />
      {/* Smile -- wide, warm */}
      <path d="M25 34 Q32 39 39 34" fill="#c0392b" />
      <path d="M25 34 Q32 32 39 34" fill="#e74c3c" />
      {/* Gold earring */}
      <circle cx="16" cy="36" r="2" fill="#c9a84c" />
      <circle cx="16" cy="36" r="1" fill="#e8c55a" />
      {/* Purple dress */}
      <path d="M20 42 Q32 48 44 42 L46 52 Q32 58 18 52 Z" fill="#9b59b6" />
      {/* Necklace */}
      <path d="M24 42 Q32 45 40 42" fill="none" stroke="#c9a84c" strokeWidth="0.8" />
      <circle cx="32" cy="44" r="1.5" fill="#c9a84c" />
    </svg>
  )
}

function BacardiSVG() {
  return (
    <svg viewBox="0 0 64 64" className="w-full h-full">
      <defs>
        <radialGradient id="bacardi-bg" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#001520" />
          <stop offset="100%" stopColor="#000a10" />
        </radialGradient>
        <linearGradient id="ice-sheen" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#00bcd4" stopOpacity="0.3" />
          <stop offset="50%" stopColor="#fff" stopOpacity="0.05" />
          <stop offset="100%" stopColor="#00bcd4" stopOpacity="0.3" />
        </linearGradient>
      </defs>
      <circle cx="32" cy="32" r="31" fill="url(#bacardi-bg)" />
      {/* Ice crystal overlay */}
      <circle cx="32" cy="32" r="31" fill="url(#ice-sheen)" />
      {/* Hair -- slicked back, dark */}
      <ellipse cx="32" cy="20" rx="14" ry="10" fill="#0a0a0a" />
      {/* Face -- dark complexion */}
      <ellipse cx="32" cy="30" rx="13" ry="14" fill="#1a1a2e" />
      {/* Eyes -- cyan glow */}
      <ellipse cx="26" cy="28" rx="2.5" ry="1.5" fill="#0a0a0a" />
      <ellipse cx="38" cy="28" rx="2.5" ry="1.5" fill="#0a0a0a" />
      <circle cx="26" cy="28" r="1" fill="#00bcd4" />
      <circle cx="38" cy="28" r="1" fill="#00bcd4" />
      {/* Cyan eye glow */}
      <circle cx="26" cy="28" r="2" fill="#00bcd4" opacity="0.15" />
      <circle cx="38" cy="28" r="2" fill="#00bcd4" opacity="0.15" />
      {/* Brows */}
      <path d="M22 25 L30 24.5" fill="none" stroke="#00bcd4" strokeWidth="0.6" opacity="0.5" />
      <path d="M34 24.5 L42 25" fill="none" stroke="#00bcd4" strokeWidth="0.6" opacity="0.5" />
      {/* Nose */}
      <path d="M31 30 Q32 33 33 30" fill="none" stroke="#111133" strokeWidth="0.6" />
      {/* Mouth -- thin, cold */}
      <path d="M28 35 L36 35" fill="none" stroke="#00bcd4" strokeWidth="0.5" opacity="0.6" />
      {/* Scar (left cheek) */}
      <path d="M20 30 L23 34" fill="none" stroke="#00bcd4" strokeWidth="0.3" opacity="0.4" />
      {/* Dark suit with cyan trim */}
      <path d="M20 44 L25 40 L32 44 L39 40 L44 44 L44 52 Q32 56 20 52 Z" fill="#0a0a15" />
      <path d="M25 40 L32 44 L39 40" fill="none" stroke="#00bcd4" strokeWidth="0.5" opacity="0.4" />
      {/* ICE label */}
      <text x="32" y="53" textAnchor="middle" fill="#00bcd4" fontSize="3.5" fontWeight="900" opacity="0.6" fontFamily="monospace">ICE</text>
    </svg>
  )
}

// ============================================================
// MAIN COMPONENT
// ============================================================

const AVATAR_MAP: Record<string, () => React.ReactElement> = {
  aria: AriaSVG,
  marcus: MarcusSVG,
  kanisha: KanishaSVG,
  bacardi: BacardiSVG,
}

export function DealerAvatar({ dealerId, color, speaking, size = 48 }: {
  dealerId: string
  color: string
  speaking: boolean
  size?: number
}) {
  const AvatarSVG = AVATAR_MAP[dealerId] || AriaSVG

  return (
    <div className="relative" style={{ width: size, height: size }}>
      {/* Glow ring */}
      <div
        className="absolute inset-0 rounded-full"
        style={{
          border: `2px solid ${color}60`,
          boxShadow: `0 0 20px ${color}30, inset 0 0 10px ${color}10`,
        }}
      />

      {/* Avatar */}
      <div className="w-full h-full rounded-full overflow-hidden">
        <AvatarSVG />
      </div>

      {/* Speaking indicator -- pulsing green dot */}
      {speaking && (
        <motion.div
          className="absolute -bottom-0.5 -right-0.5 rounded-full"
          style={{
            width: size * 0.22,
            height: size * 0.22,
            background: '#00e676',
            border: '2px solid #0d0815',
            boxShadow: '0 0 8px #00e67680',
          }}
          animate={{
            scale: [1, 1.3, 1],
            opacity: [1, 0.7, 1],
          }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      )}
    </div>
  )
}
