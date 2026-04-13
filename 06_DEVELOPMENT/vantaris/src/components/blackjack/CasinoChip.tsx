'use client'

import { motion } from 'framer-motion'

/**
 * Premium SVG Casino Chip
 *
 * Proper casino chip with:
 * - Outer ring with edge notches (8 notches, alternating colors)
 * - Inner concentric circles
 * - Metallic sheen gradient
 * - Center denomination text
 * - Shadow + glow on select
 *
 * Based on real casino chip design (Paulson/Chipco style).
 */

interface ChipConfig {
  value: number
  primary: string      // main chip color
  secondary: string    // edge notch / accent color
  text: string         // denomination text color
  ring: string         // inner ring color
}

const CHIP_CONFIGS: ChipConfig[] = [
  { value: 10,   primary: '#c0392b', secondary: '#e74c3c', text: '#fff', ring: '#a93226' },
  { value: 25,   primary: '#1e8449', secondary: '#27ae60', text: '#fff', ring: '#196f3d' },
  { value: 100,  primary: '#1a5276', secondary: '#2980b9', text: '#fff', ring: '#154360' },
  { value: 500,  primary: '#6c3483', secondary: '#8e44ad', text: '#fff', ring: '#5b2c6f' },
  { value: 1000, primary: '#7d6608', secondary: '#c9a84c', text: '#fff', ring: '#6e5c08' },
  { value: 5000, primary: '#111111', secondary: '#444444', text: '#c9a84c', ring: '#1a1a1a' },
]

function ChipSVG({ config, size = 64 }: { config: ChipConfig; size?: number }) {
  const cx = size / 2
  const cy = size / 2
  const outerR = size / 2 - 2
  const innerR = outerR * 0.75
  const coreR = outerR * 0.52
  const spotCount = 6 // edge inlay spots (like real Paulson chips)

  const label = config.value >= 1000 ? `${config.value / 1000}K` : config.value.toString()

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <defs>
        {/* Premium sheen -- top-left highlight simulating overhead light */}
        <radialGradient id={`sheen-${config.value}`} cx="30%" cy="25%" r="70%">
          <stop offset="0%" stopColor="rgba(255,255,255,0.35)" />
          <stop offset="40%" stopColor="rgba(255,255,255,0.08)" />
          <stop offset="100%" stopColor="rgba(0,0,0,0.2)" />
        </radialGradient>
        {/* Clay texture overlay */}
        <radialGradient id={`clay-${config.value}`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="rgba(255,255,255,0.06)" />
          <stop offset="100%" stopColor="rgba(0,0,0,0.08)" />
        </radialGradient>
        {/* Gold emboss for center */}
        <linearGradient id={`emboss-${config.value}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(255,255,255,0.15)" />
          <stop offset="50%" stopColor="rgba(255,255,255,0)" />
          <stop offset="100%" stopColor="rgba(0,0,0,0.12)" />
        </linearGradient>
      </defs>

      {/* Base shadow ring (depth) */}
      <circle cx={cx} cy={cy + 1} r={outerR} fill="rgba(0,0,0,0.3)" />

      {/* Outer rim -- slightly darker than primary */}
      <circle cx={cx} cy={cy} r={outerR} fill={config.ring} />

      {/* Main body */}
      <circle cx={cx} cy={cy} r={outerR - 1.5} fill={config.primary} />

      {/* Edge inlay spots (6 colored spots like real chips) */}
      {Array.from({ length: spotCount }).map((_, i) => {
        const angle = (i * 360) / spotCount - 90
        const rad = (angle * Math.PI) / 180
        const spotR = outerR - 4
        const sx = cx + spotR * Math.cos(rad)
        const sy = cy + spotR * Math.sin(rad)
        return (
          <g key={i}>
            {/* Spot background (white/secondary color inlay) */}
            <circle cx={sx} cy={sy} r={size * 0.06} fill={config.secondary} opacity={0.9} />
            {/* Spot inner dot */}
            <circle cx={sx} cy={sy} r={size * 0.025} fill="#fff" opacity={0.3} />
          </g>
        )
      })}

      {/* Outer ring groove */}
      <circle cx={cx} cy={cy} r={innerR + 2} fill="none" stroke={config.ring} strokeWidth={1.5} opacity={0.5} />

      {/* Inner decorative ring */}
      <circle cx={cx} cy={cy} r={innerR} fill="none" stroke={config.secondary} strokeWidth={1.2} opacity={0.4} />

      {/* Thin gold accent ring */}
      <circle cx={cx} cy={cy} r={innerR - 3} fill="none" stroke="#c9a84c" strokeWidth={0.5} opacity={0.3} />

      {/* Core circle (denomination area) */}
      <circle cx={cx} cy={cy} r={coreR + 2} fill={config.ring} />
      <circle cx={cx} cy={cy} r={coreR} fill={config.primary} />

      {/* Core emboss effect */}
      <circle cx={cx} cy={cy} r={coreR} fill={`url(#emboss-${config.value})`} />

      {/* Core inner accent ring */}
      <circle cx={cx} cy={cy} r={coreR - 1.5} fill="none" stroke={config.secondary} strokeWidth={0.6} opacity={0.4} />

      {/* Clay texture overlay */}
      <circle cx={cx} cy={cy} r={outerR - 1.5} fill={`url(#clay-${config.value})`} />

      {/* Premium sheen (simulates overhead casino light) */}
      <circle cx={cx} cy={cy} r={outerR - 1.5} fill={`url(#sheen-${config.value})`} />

      {/* Denomination text */}
      <text
        x={cx}
        y={cy}
        textAnchor="middle"
        dominantBaseline="central"
        fill={config.text}
        fontSize={config.value >= 1000 ? size * 0.2 : size * 0.26}
        fontWeight="900"
        fontFamily="'Cinzel', serif"
        letterSpacing={config.value >= 1000 ? -0.5 : 0}
      >
        {label}
      </text>

      {/* Small "GC" under denomination */}
      <text
        x={cx}
        y={cy + size * 0.15}
        textAnchor="middle"
        dominantBaseline="central"
        fill={config.text}
        fontSize={size * 0.09}
        fontWeight="600"
        opacity={0.5}
        fontFamily="'Inter', sans-serif"
      >
        GC
      </text>
    </svg>
  )
}

export function CasinoChip({
  value,
  selected,
  onClick,
  size = 64,
}: {
  value: number
  selected: boolean
  onClick: () => void
  size?: number
}) {
  const config = CHIP_CONFIGS.find(c => c.value === value) || CHIP_CONFIGS[0]

  return (
    <motion.button
      onClick={onClick}
      className="relative no-select cursor-pointer"
      style={{
        width: size,
        height: size,
        // Bigger touch target (padding around the chip)
        padding: 4,
        margin: -4,
        filter: selected
          ? `drop-shadow(0 0 14px ${config.secondary}90) drop-shadow(0 0 28px ${config.secondary}40)`
          : `drop-shadow(0 3px 8px rgba(0,0,0,0.7))`,
      }}
      whileHover={{ translateY: -8, scale: 1.12 }}
      whileTap={{ translateY: 0, scale: 0.88 }}
      animate={selected ? { scale: [1, 1.06, 1] } : {}}
      transition={selected ? { duration: 1.5, repeat: Infinity } : { duration: 0.15 }}
    >
      <ChipSVG config={config} size={size} />

      {/* Selection glow ring */}
      {selected && (
        <motion.div
          className="absolute inset-[-4px] rounded-full"
          style={{
            border: `2px solid ${config.secondary}`,
            boxShadow: `0 0 10px ${config.secondary}60`,
          }}
          animate={{ opacity: [0.5, 1, 0.5], scale: [1, 1.02, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
      )}
    </motion.button>
  )
}

export { CHIP_CONFIGS }
