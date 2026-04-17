'use client'

import { useEffect, useRef, useState } from 'react'

/**
 * Subtle casino ambiance using Web Audio API.
 * Generates a warm, low-frequency noise pad with gentle modulation.
 * Plays only after user interaction (browser autoplay policy).
 */
export function CasinoAmbience() {
  const ctxRef = useRef<AudioContext | null>(null)
  const [playing, setPlaying] = useState(false)
  const [muted, setMuted] = useState(false)
  const gainRef = useRef<GainNode | null>(null)

  function startAmbience() {
    if (ctxRef.current) return

    const ctx = new AudioContext()
    ctxRef.current = ctx
    const gain = ctx.createGain()
    gain.gain.value = 0.06
    gainRef.current = gain
    gain.connect(ctx.destination)

    // Warm noise pad
    const bufferSize = ctx.sampleRate * 4
    const buffer = ctx.createBuffer(2, bufferSize, ctx.sampleRate)
    for (let ch = 0; ch < 2; ch++) {
      const data = buffer.getChannelData(ch)
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * 0.3
      }
    }
    const noise = ctx.createBufferSource()
    noise.buffer = buffer
    noise.loop = true

    // Low-pass filter for warmth
    const lp = ctx.createBiquadFilter()
    lp.type = 'lowpass'
    lp.frequency.value = 200
    lp.Q.value = 0.5

    // Subtle LFO on filter frequency
    const lfo = ctx.createOscillator()
    const lfoGain = ctx.createGain()
    lfo.frequency.value = 0.08
    lfoGain.gain.value = 80
    lfo.connect(lfoGain)
    lfoGain.connect(lp.frequency)
    lfo.start()

    // Gentle chime oscillator (casino bell vibe)
    const chime = ctx.createOscillator()
    const chimeGain = ctx.createGain()
    chime.type = 'sine'
    chime.frequency.value = 1200
    chimeGain.gain.value = 0
    chime.connect(chimeGain)
    chimeGain.connect(gain)
    chime.start()

    // Random chime triggers
    function triggerChime() {
      const now = ctx.currentTime
      chimeGain.gain.setValueAtTime(0, now)
      chimeGain.gain.linearRampToValueAtTime(0.008, now + 0.02)
      chimeGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.8)
      chime.frequency.setValueAtTime(800 + Math.random() * 1200, now)
      setTimeout(triggerChime, 3000 + Math.random() * 8000)
    }
    setTimeout(triggerChime, 2000)

    noise.connect(lp)
    lp.connect(gain)
    noise.start()

    setPlaying(true)
  }

  function toggleMute() {
    if (!gainRef.current) return
    if (muted) {
      gainRef.current.gain.linearRampToValueAtTime(0.06, (ctxRef.current?.currentTime || 0) + 0.3)
    } else {
      gainRef.current.gain.linearRampToValueAtTime(0, (ctxRef.current?.currentTime || 0) + 0.3)
    }
    setMuted(!muted)
  }

  useEffect(() => {
    return () => {
      ctxRef.current?.close()
    }
  }, [])

  if (!playing) {
    return (
      <button onClick={startAmbience} className="fixed bottom-14 right-4 z-20 px-3 py-1.5 rounded-lg text-[10px] font-medium tracking-wider transition-opacity hover:opacity-100 opacity-60"
        style={{ background: 'rgba(201,168,76,0.1)', border: '1px solid rgba(201,168,76,0.2)', color: '#c9a84c' }}>
        {'\u266B'} AMBIENCE
      </button>
    )
  }

  return (
    <button onClick={toggleMute} className="fixed bottom-14 right-4 z-20 px-3 py-1.5 rounded-lg text-[10px] font-medium tracking-wider"
      style={{ background: muted ? 'rgba(255,255,255,0.05)' : 'rgba(201,168,76,0.1)', border: `1px solid ${muted ? 'rgba(255,255,255,0.1)' : 'rgba(201,168,76,0.2)'}`, color: muted ? 'var(--text-tertiary)' : '#c9a84c' }}>
      {muted ? '\u266B MUTED' : '\u266B LIVE'}
    </button>
  )
}
