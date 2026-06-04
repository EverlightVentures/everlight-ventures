'use client'

import type { CSSProperties } from 'react'

/**
 * Premium betting chip -- CSS glow chip (per the chip-restyle brief).
 * VISUAL ONLY. Props, onClick, and size are unchanged, so all bet logic,
 * selection, and drag handling in BettingLayout keep working untouched.
 * The style lives in design-system.css (.chip / .face / denominations /
 * chipBeat). Everything scales off the single --cs (chip diameter) var.
 */

const DENOM: Record<number, { cls: string; label: string }> = {
  10: { cls: 'c10', label: '10' },
  25: { cls: 'c25', label: '25' },
  100: { cls: 'c100', label: '100' },
  500: { cls: 'c500', label: '500' },
  1000: { cls: 'c1k', label: '1K' },
  5000: { cls: 'c5k', label: '5K' },
}

// Kept for back-compat (denomination -> accent). Nothing external imports this
// today, but exporting it avoids breaking any future reference.
export const CHIP_CONFIGS = [
  { value: 10, primary: '#cf4747' },
  { value: 25, primary: '#33a972' },
  { value: 100, primary: '#4185db' },
  { value: 500, primary: '#a274d8' },
  { value: 1000, primary: '#d4ab52' },
  { value: 5000, primary: '#1a1a1a' },
]

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
  const d = DENOM[value] || { cls: 'c100', label: String(value) }
  return (
    <button
      type="button"
      onClick={onClick}
      data-val={value}
      aria-label={`${d.label} GC chip`}
      className={`chip ${d.cls}${selected ? ' sel' : ''} no-select`}
      style={{ '--cs': `${size}px` } as CSSProperties}
    >
      <div className="face">
        <div className="v">{d.label}</div>
        <div className="u">GC</div>
      </div>
    </button>
  )
}
