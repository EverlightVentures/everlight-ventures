'use client'

import { useEffect, useRef } from 'react'

/**
 * Win Particle Canvas
 *
 * Overlays the game area. Fires gold particles on blackjack,
 * green on regular win. 120 particles with gravity + fade.
 *
 * From the original Three.js build, translated to pure canvas.
 */

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  life: number
  decay: number
  size: number
  color: string
}

const GOLD_COLORS = ['#c9a84c', '#f0d080', '#fff', '#ffe066', '#e8c55a']
const GREEN_COLORS = ['#27ae60', '#2ecc71', '#a8ffb0', '#fff', '#00e676']
const LOSS_COLORS = ['#ff2d55', '#ff6b6b', '#cc2244']

export function WinParticles({
  trigger,
  type,
}: {
  trigger: number // increment to fire
  type: 'blackjack' | 'win' | 'loss' | null
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const particlesRef = useRef<Particle[]>([])
  const animFrameRef = useRef<number>(0)

  useEffect(() => {
    if (!type || trigger === 0) return

    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = canvas.offsetWidth * dpr
    canvas.height = canvas.offsetHeight * dpr
    ctx.scale(dpr, dpr)

    const w = canvas.offsetWidth
    const h = canvas.offsetHeight
    const cx = w / 2
    const cy = h / 2

    const colors = type === 'blackjack' ? GOLD_COLORS : type === 'win' ? GREEN_COLORS : LOSS_COLORS
    const count = type === 'blackjack' ? 150 : type === 'win' ? 80 : 40

    // Spawn particles from center
    const particles: Particle[] = []
    for (let i = 0; i < count; i++) {
      const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.5
      const speed = 3 + Math.random() * 8
      particles.push({
        x: cx + (Math.random() - 0.5) * 40,
        y: cy + (Math.random() - 0.5) * 40,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 3,
        life: 1.0,
        decay: 0.008 + Math.random() * 0.012,
        size: 2 + Math.random() * 4,
        color: colors[Math.floor(Math.random() * colors.length)],
      })
    }
    particlesRef.current = particles

    function animate() {
      if (!ctx || !canvas) return
      const w2 = canvas.offsetWidth
      const h2 = canvas.offsetHeight

      ctx.clearRect(0, 0, w2, h2)

      let alive = false
      for (const p of particlesRef.current) {
        if (p.life <= 0) continue
        alive = true

        p.x += p.vx
        p.y += p.vy
        p.vy += 0.15 // gravity
        p.life -= p.decay

        ctx.globalAlpha = Math.max(0, p.life)
        ctx.fillStyle = p.color
        ctx.beginPath()
        ctx.arc(p.x, p.y, Math.max(0.1, p.size * p.life), 0, Math.PI * 2)
        ctx.fill()
      }

      ctx.globalAlpha = 1

      if (alive) {
        animFrameRef.current = requestAnimationFrame(animate)
      }
    }

    animate()

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
    }
  }, [trigger, type])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none z-40"
      style={{ width: '100%', height: '100%' }}
    />
  )
}
