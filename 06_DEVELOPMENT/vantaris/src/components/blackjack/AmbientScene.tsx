'use client'

import { useEffect, useRef } from 'react'

/**
 * Ambient Scene -- Casino Atmosphere
 *
 * Canvas-based replacement for the Three.js 3D scene.
 * Renders: gold dust particles, chandelier glow spots,
 * neon side lights, subtle fog.
 *
 * Performance: ~2% GPU on mobile. No WebGL required.
 * Falls back gracefully on low-end devices.
 */

interface DustParticle {
  x: number
  y: number
  size: number
  speed: number
  opacity: number
  drift: number
}

interface GlowSpot {
  x: number
  y: number
  radius: number
  color: string
  pulse: number
  pulseSpeed: number
}

export function AmbientScene() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let w = 0, h = 0
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = canvas.offsetWidth
      h = canvas.offsetHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.scale(dpr, dpr)
    }
    resize()
    window.addEventListener('resize', resize)

    // Gold dust particles (400 particles)
    const dust: DustParticle[] = Array.from({ length: 200 }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      size: 0.5 + Math.random() * 1.5,
      speed: 0.1 + Math.random() * 0.3,
      opacity: 0.1 + Math.random() * 0.3,
      drift: (Math.random() - 0.5) * 0.3,
    }))

    // Glow spots (chandelier + neon)
    const glows: GlowSpot[] = [
      // Chandelier (top center, warm gold)
      { x: 0.5, y: 0.08, radius: 0.25, color: 'rgba(201,168,76,0.04)', pulse: 0, pulseSpeed: 0.008 },
      // Left neon (blue-violet)
      { x: 0.05, y: 0.5, radius: 0.15, color: 'rgba(68,0,255,0.03)', pulse: 0, pulseSpeed: 0.012 },
      // Right neon (red)
      { x: 0.95, y: 0.5, radius: 0.15, color: 'rgba(255,34,0,0.025)', pulse: 0, pulseSpeed: 0.01 },
      // Back neon (cyan)
      { x: 0.5, y: 0.02, radius: 0.2, color: 'rgba(0,170,255,0.02)', pulse: 0, pulseSpeed: 0.015 },
    ]

    let frame = 0

    function animate() {
      frame++
      ctx.clearRect(0, 0, w, h)

      // Glow spots (radial gradients)
      for (const g of glows) {
        g.pulse += g.pulseSpeed
        const pulseScale = 1 + Math.sin(g.pulse) * 0.15
        const r = g.radius * Math.min(w, h) * pulseScale

        const gradient = ctx.createRadialGradient(
          g.x * w, g.y * h, 0,
          g.x * w, g.y * h, r
        )
        gradient.addColorStop(0, g.color)
        gradient.addColorStop(1, 'transparent')
        ctx.fillStyle = gradient
        ctx.fillRect(0, 0, w, h)
      }

      // Gold dust
      for (const p of dust) {
        p.y -= p.speed
        p.x += p.drift + Math.sin(frame * 0.01 + p.x * 0.01) * 0.2

        // Wrap around
        if (p.y < -5) { p.y = h + 5; p.x = Math.random() * w }
        if (p.x < -5) p.x = w + 5
        if (p.x > w + 5) p.x = -5

        // Twinkle
        const twinkle = 0.5 + Math.sin(frame * 0.05 + p.x) * 0.5

        ctx.globalAlpha = p.opacity * twinkle
        ctx.fillStyle = '#c9a84c'
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fill()
      }

      ctx.globalAlpha = 1
      animRef.current = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      cancelAnimationFrame(animRef.current)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none"
      style={{ width: '100%', height: '100%', opacity: 0.6 }}
    />
  )
}
