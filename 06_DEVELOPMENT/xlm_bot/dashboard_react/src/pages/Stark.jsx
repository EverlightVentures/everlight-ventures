import React, { useState, useEffect, useCallback, useRef } from "react"
import VoiceOrb from "../components/stark/VoiceOrb"
import CommandTerminal from "../components/stark/CommandTerminal"
import AgentFeed from "../components/stark/AgentFeed"
import AuthGate from "../components/stark/AuthGate"

/**
 * Stark AI -- Voice-First Command Center
 * The Tony Stark experience for Everlight Ventures.
 * Supabase auth + ElevenLabs voice + Hive Mind dispatch.
 */

const STARK_API = window.location.hostname === "localhost"
  ? "http://localhost:8511"
  : ""

export default function Stark() {
  // Auth state
  const [auth, setAuth] = useState(null)       // { token, user }
  const [showAuth, setShowAuth] = useState(false)
  const [isGuest, setIsGuest] = useState(false)

  // Chat state
  const [messages, setMessages] = useState([])
  const [orbState, setOrbState] = useState("idle")
  const [activeAgents, setActiveAgents] = useState([])
  const [recentActivity, setRecentActivity] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const audioRef = useRef(null)

  // Check for saved auth on mount
  useEffect(() => {
    const token = localStorage.getItem("stark_token")
    const userStr = localStorage.getItem("stark_user")
    if (token && userStr) {
      try {
        setAuth({ token, user: JSON.parse(userStr) })
      } catch {
        localStorage.removeItem("stark_token")
        localStorage.removeItem("stark_user")
      }
    } else {
      setShowAuth(true)
    }
  }, [])

  // Create session on auth
  useEffect(() => {
    if (!auth) return
    fetch(`${STARK_API}/api/stark/session`, {
      method: "POST",
      headers: { Authorization: `Bearer ${auth.token}` },
    })
      .then(r => r.json())
      .then(d => { if (d.ok) setSessionId(d.session_id) })
      .catch(() => {})
  }, [auth])

  // Welcome message
  useEffect(() => {
    const name = auth?.user?.display_name || (isGuest ? "Guest" : "")
    if (name && messages.length === 0) {
      setMessages([{
        role: "assistant",
        text: isGuest
          ? "Lucrex here. You're in guest mode -- limited commands available. Sign up to unlock the full Hive Mind: trading, dispatch, voice control, 63 agents at your command."
          : `${name}. Lucrex online. The Hive is active -- 63 agents standing by across 4 squads. Voice or text, your call.`,
        agent: "Lucrex",
        category: "system",
        agents_used: ["Marcus Cole"],
      }])
      setActiveAgents(["Marcus Cole"])
      setTimeout(() => setActiveAgents([]), 3000)
    }
  }, [auth, isGuest])

  const sendCommand = useCallback(async (text) => {
    // Add user message
    setMessages(prev => [...prev, { role: "user", text }])
    setOrbState("thinking")

    try {
      const endpoint = auth && !isGuest ? "/api/stark/command" : "/api/stark/demo"
      const headers = { "Content-Type": "application/json" }
      if (auth && !isGuest) {
        headers["Authorization"] = `Bearer ${auth.token}`
      }

      const resp = await fetch(`${STARK_API}${endpoint}`, {
        method: "POST",
        headers,
        body: JSON.stringify({ text, voice: true, session_id: sessionId }),
      })
      const data = await resp.json()

      // Light up agents
      const agents = data.agents_used || []
      setActiveAgents(agents)
      setTimeout(() => setActiveAgents([]), 5000)

      // Add activity log entry
      const now = new Date()
      const timeStr = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "America/Los_Angeles" })
      agents.forEach(a => {
        setRecentActivity(prev => [...prev.slice(-20), { time: timeStr, agent: a, action: `Handled: ${text.slice(0, 40)}` }])
      })

      // Add response
      setMessages(prev => [...prev, {
        role: "assistant",
        text: data.text || "No response.",
        agent: data.agent || "Lucrex",
        category: data.category,
        agents_used: data.agents_used,
        latency_ms: data.latency_ms,
        audio_url: data.audio_url,
      }])

      // Play TTS audio if available
      if (data.audio_url && auth && !isGuest) {
        setOrbState("speaking")
        const audioUrl = `${STARK_API}${data.audio_url}`
        if (audioRef.current) {
          audioRef.current.src = audioUrl
          audioRef.current.play().catch(() => {})
          audioRef.current.onended = () => setOrbState("idle")
        } else {
          setTimeout(() => setOrbState("idle"), 2000)
        }
      } else {
        setOrbState("idle")
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: "assistant",
        text: "Connection to Stark AI backend failed. Ensure the service is running on port 8511.",
        agent: "System",
        category: "error",
      }])
      setOrbState("idle")
    }
  }, [auth, isGuest, sessionId])

  const handleVoiceTranscript = useCallback((transcript) => {
    if (transcript.trim()) sendCommand(transcript)
  }, [sendCommand])

  const handleAuth = (data) => {
    setAuth(data)
    setShowAuth(false)
    setIsGuest(false)
  }

  const handleSkip = () => {
    setShowAuth(false)
    setIsGuest(true)
  }

  const handleLogout = () => {
    localStorage.removeItem("stark_token")
    localStorage.removeItem("stark_user")
    localStorage.removeItem("stark_refresh")
    setAuth(null)
    setIsGuest(false)
    setMessages([])
    setShowAuth(true)
  }

  // Auth gate
  if (showAuth) {
    return <AuthGate onAuth={handleAuth} onSkip={handleSkip} />
  }

  const tier = auth?.user?.tier || (isGuest ? "public" : "client")
  const displayName = auth?.user?.display_name || "Guest"

  return (
    <div className="h-full flex flex-col bg-[#0a0a0f] overflow-hidden">
      {/* Hidden audio element for TTS playback */}
      <audio ref={audioRef} className="hidden" />

      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-white/[0.04]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 via-orange-500 to-red-600 flex items-center justify-center text-xs font-black text-black shadow-lg shadow-amber-500/20">
            S
          </div>
          <div>
            <div className="text-sm font-bold tracking-[0.15em] bg-gradient-to-r from-amber-300 to-orange-400 bg-clip-text text-transparent">
              STARK AI
            </div>
            <div className="text-[8px] tracking-[0.1em] text-gray-600">VOICE COMMAND CENTER</div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Tier badge */}
          <div className={`px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wider border ${
            tier === "god" ? "bg-amber-400/10 text-amber-400 border-amber-400/20" :
            tier === "client" ? "bg-blue-400/10 text-blue-400 border-blue-400/20" :
            "bg-gray-400/10 text-gray-500 border-gray-400/10"
          }`}>
            {tier.toUpperCase()}
          </div>

          {/* User info */}
          <div className="text-right">
            <div className="text-[10px] text-gray-400">{displayName}</div>
            <div className="text-[8px] text-gray-600">{auth?.user?.email || "guest"}</div>
          </div>

          {/* Logout */}
          {auth && !isGuest && (
            <button onClick={handleLogout} className="text-[9px] text-gray-600 hover:text-red-400 transition-colors">
              LOGOUT
            </button>
          )}
          {isGuest && (
            <button onClick={() => setShowAuth(true)} className="text-[9px] text-amber-400/60 hover:text-amber-400 transition-colors">
              SIGN IN
            </button>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Voice + Terminal */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Voice orb section */}
          <div className="flex-shrink-0 flex items-center justify-center py-8 relative">
            {/* Background glow */}
            <div className="absolute w-[300px] h-[200px] bg-gradient-radial from-amber-500/[0.04] to-transparent blur-[60px] pointer-events-none" />
            <VoiceOrb
              onTranscript={handleVoiceTranscript}
              state={orbState}
              audioLevel={orbState === "speaking" ? 0.6 : orbState === "listening" ? 0.3 : 0}
            />
          </div>

          {/* Command terminal */}
          <div className="flex-1 px-4 pb-4 min-h-0">
            <CommandTerminal
              messages={messages}
              onSend={sendCommand}
              isProcessing={orbState === "thinking"}
            />
          </div>
        </div>

        {/* Right: Agent feed */}
        <div className="w-64 flex-shrink-0 border-l border-white/[0.04] p-3">
          <AgentFeed activeAgents={activeAgents} recentActivity={recentActivity} />
        </div>
      </div>

      {/* Footer status bar */}
      <div className="flex items-center justify-between px-6 py-1.5 border-t border-white/[0.04] bg-[#08080d]/50">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <span className="text-[8px] text-gray-600 font-mono">ORACLE E5 ONLINE</span>
          </div>
          <span className="text-[8px] text-gray-700">|</span>
          <span className="text-[8px] text-gray-600 font-mono">63 AGENTS ACTIVE</span>
          <span className="text-[8px] text-gray-700">|</span>
          <span className="text-[8px] text-gray-600 font-mono">ELEVENLABS TTS</span>
        </div>
        <div className="text-[8px] text-gray-700 font-mono">
          EVERLIGHT VENTURES &copy; 2026
        </div>
      </div>
    </div>
  )
}
