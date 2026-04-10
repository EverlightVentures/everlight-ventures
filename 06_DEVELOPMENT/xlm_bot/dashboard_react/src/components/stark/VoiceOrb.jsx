import React, { useState, useEffect, useRef, useCallback } from "react"

/**
 * VoiceOrb -- The visual heart of Stark AI.
 * States: idle | listening | thinking | speaking
 * Uses Web Speech API for STT (free, no API cost).
 */

const STATE_COLORS = {
  idle:      { core: "from-amber-500/60 to-orange-600/40", ring: "border-amber-400/20", glow: "shadow-amber-500/10" },
  listening: { core: "from-blue-400/70 to-cyan-500/50",    ring: "border-blue-400/30",   glow: "shadow-blue-400/20" },
  thinking:  { core: "from-purple-400/60 to-violet-500/50", ring: "border-purple-400/25", glow: "shadow-purple-500/15" },
  speaking:  { core: "from-amber-400/80 to-orange-500/60", ring: "border-amber-300/35",  glow: "shadow-amber-400/25" },
}

const STATE_LABELS = {
  idle: "TAP TO SPEAK",
  listening: "LISTENING...",
  thinking: "PROCESSING...",
  speaking: "LUCREX SPEAKING",
}

export default function VoiceOrb({ onTranscript, state = "idle", audioLevel = 0 }) {
  const [recognition, setRecognition] = useState(null)
  const [supported, setSupported] = useState(true)
  const scale = 1 + audioLevel * 0.15

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) { setSupported(false); return }
    const r = new SR()
    r.continuous = false
    r.interimResults = true
    r.lang = "en-US"
    r.onresult = (e) => {
      const last = e.results[e.results.length - 1]
      if (last.isFinal && onTranscript) {
        onTranscript(last[0].transcript)
      }
    }
    r.onerror = () => {}
    r.onend = () => {}
    setRecognition(r)
  }, [])

  const startListening = useCallback(() => {
    if (!recognition || state === "thinking" || state === "speaking") return
    try { recognition.start() } catch {}
  }, [recognition, state])

  const colors = STATE_COLORS[state] || STATE_COLORS.idle
  const label = STATE_LABELS[state] || "TAP TO SPEAK"

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Orb container */}
      <button
        onClick={startListening}
        disabled={state === "thinking" || state === "speaking" || !supported}
        className="relative group cursor-pointer disabled:cursor-wait focus:outline-none"
      >
        {/* Outer glow */}
        <div className={`absolute inset-[-20px] rounded-full bg-gradient-radial ${colors.glow} blur-[40px] transition-all duration-700 ${
          state === "speaking" ? "opacity-80 scale-110" : state === "listening" ? "opacity-60 scale-105" : "opacity-30"
        }`} style={{ boxShadow: `0 0 80px 20px rgba(245, 158, 11, ${state === "idle" ? 0.05 : 0.15})` }} />

        {/* Ring 3 (outermost) -- slow rotation */}
        <div
          className={`absolute inset-[-12px] rounded-full border ${colors.ring} transition-all duration-500`}
          style={{
            animation: state === "thinking" ? "spin 3s linear infinite" : "pulse 4s ease-in-out infinite",
            transform: `scale(${scale * 1.08})`,
          }}
        />

        {/* Ring 2 -- medium rotation */}
        <div
          className={`absolute inset-[-6px] rounded-full border ${colors.ring} transition-all duration-500`}
          style={{
            animation: state === "thinking" ? "spin 2s linear infinite reverse" : "pulse 3s ease-in-out infinite 0.5s",
            transform: `scale(${scale * 1.04})`,
          }}
        />

        {/* Ring 1 (inner) -- fast */}
        <div
          className={`absolute inset-0 rounded-full border ${colors.ring} transition-all duration-500`}
          style={{
            animation: state === "thinking" ? "spin 1.5s linear infinite" : "pulse 2.5s ease-in-out infinite 1s",
            transform: `scale(${scale})`,
          }}
        />

        {/* Core orb */}
        <div
          className={`relative w-28 h-28 rounded-full bg-gradient-to-br ${colors.core} backdrop-blur-sm transition-all duration-300 flex items-center justify-center shadow-2xl ${colors.glow}`}
          style={{ transform: `scale(${scale})` }}
        >
          {/* Inner icon */}
          {state === "idle" && (
            <svg className="w-8 h-8 text-white/80" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
            </svg>
          )}
          {state === "listening" && (
            <div className="flex items-center gap-1">
              {[0, 1, 2, 3, 4].map(i => (
                <div
                  key={i}
                  className="w-1 bg-white/90 rounded-full"
                  style={{
                    animation: `soundbar 0.8s ease-in-out infinite ${i * 0.1}s`,
                    height: `${12 + Math.random() * 16}px`,
                  }}
                />
              ))}
            </div>
          )}
          {state === "thinking" && (
            <div className="w-6 h-6 border-2 border-white/60 border-t-transparent rounded-full animate-spin" />
          )}
          {state === "speaking" && (
            <div className="flex items-center gap-0.5">
              {[0, 1, 2, 3, 4, 5, 6].map(i => (
                <div
                  key={i}
                  className="w-0.5 bg-white/90 rounded-full"
                  style={{
                    animation: `waveform 1.2s ease-in-out infinite ${i * 0.08}s`,
                    height: `${8 + Math.sin(i * 0.8) * 12}px`,
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Hover ring */}
        <div className="absolute inset-[-2px] rounded-full border border-white/0 group-hover:border-white/10 transition-all duration-300" />
      </button>

      {/* State label */}
      <div className={`text-[10px] tracking-[0.3em] font-medium transition-colors duration-500 ${
        state === "listening" ? "text-blue-400" :
        state === "thinking" ? "text-purple-400" :
        state === "speaking" ? "text-amber-300" :
        "text-gray-500"
      }`}>
        {label}
      </div>

      {!supported && (
        <div className="text-[9px] text-red-400/60">Voice not supported in this browser. Use text input.</div>
      )}

      {/* Inline keyframes */}
      <style>{`
        @keyframes soundbar {
          0%, 100% { height: 8px; }
          50% { height: 24px; }
        }
        @keyframes waveform {
          0%, 100% { transform: scaleY(0.4); }
          50% { transform: scaleY(1.2); }
        }
      `}</style>
    </div>
  )
}
