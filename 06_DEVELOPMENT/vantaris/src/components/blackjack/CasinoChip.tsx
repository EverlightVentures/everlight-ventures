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
  const innerR = outerR * 0.72
  const coreR = outerR * 0.55
  const notchCount = 8
  const notchW = 4
  const notchH = outerR * 0.22

  const label = config.value >= 1000 ? `${config.value / 1000}K` : config.value.toString()

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <defs>
        {/* Metallic sheen gradient */}
        <radialGradient id={`sheen-${config.value}`} cx="35%" cy="35%" r="65%">
          <stop offset="0%" stopColor="rgba(255,255,255,0.25)" />
          <stop offset="50%" stopColor="rgba(255,255,255,0.05)" />
          <stop offset="100%" stopColor="rgba(0,0,0,0.15)" />
        </radialGradient>
        {/* Edge shadow */}
        <filter id={`shadow-${config.value}`}>
          <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.5" />
        </filter>
      </defs>

      {/* Outer circle -- main color */}
      <circle cx={cx} cy={cy} r={outerR} fill={config.primary} />

      {/* Edge notches (8, evenly spaced) */}
      {Array.from({ length: notchCount }).map((_, i) => {
        const angle = (i * 360) / notchCount - 90
        const rad = (angle * Math.PI) / 180
        const nx = cx + (outerR - notchH / 2) * Math.cos(rad)
        const ny = cy + (outerR - notchH / 2) * Math.sin(rad)
        return (
          <rect
            key={i}
            x={nx - notchW / 2}
            y={ny - notchH / 2}
            width={notchW}
            height={notchH}
            rx={1.5}
            fill={config.secondary}
            transform={`rotate(${angle + 90}, ${nx}, ${ny})`}
          />
        )
      })}

      {/* Middle ring */}
      <circle cx={cx} cy={cy} r={innerR} fill="none" stroke={config.ring} strokeWidth={2} opacity={0.6} />

      {/* Inner dashed ring */}
      <circle
        cx={cx} cy={cy} r={innerR - 4}
        fill="none" stroke={config.secondary} strokeWidth={1}
        strokeDasharray="3 3" opacity={0.4}
      />

      {/* Core circle */}
      <circle cx={cx} cy={cy} r={coreR} fill={config.primary} />
      <circle cx={cx} cy={cy} r={coreR - 2} fill="none" stroke={config.secondary} strokeWidth={0.8} opacity={0.5} />

      {/* Metallic sheen overlay */}
      <circle cx={cx} cy={cy} r={outerR} fill={`url(#sheen-${config.value})`} />

      {/* Denomination text */}
      <text
        x={cx}
        y={cy + 1}
        textAnchor="middle"
        dominantBaseline="central"
        fill={config.text}
        fontSize={config.value >= 1000 ? size * 0.22 : size * 0.28}
        fontWeight="800"
        fontFamily="'Cinzel', serif"
        style={{ textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}
      >
        {label}
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
        filter: selected
          ? `drop-shadow(0 0 12px ${config.secondary}80) drop-shadow(0 0 24px ${config.secondary}30)`
          : `drop-shadow(0 2px 6px rgba(0,0,0,0.6))`,
      }}
      whileHover={{ translateY: -6, scale: 1.1 }}
      whileTap={{ translateY: 0, scale: 0.92 }}
      animate={selected ? { scale: [1, 1.05, 1] } : {}}
      transition={selected ? { duration: 1.5, repeat: Infinity } : { duration: 0.15 }}
    >
      <ChipSVG config={config} size={size} />

      {/* Selection ring */}
      {selected && (
        <motion.div
          className="absolute inset-[-3px] rounded-full"
          style={{ border: '2px solid #fff', opacity: 0.6 }}
          animate={{ opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
      )}
    </motion.button>
  )
}

export { CHIP_CONFIGS }
