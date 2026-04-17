'use client'

export function SectionDivider({ color = '#D4AF37' }: { color?: string }) {
  return (
    <div className="max-w-xs mx-auto h-px" style={{ background: `linear-gradient(90deg, transparent, ${color}30, transparent)` }} />
  )
}
