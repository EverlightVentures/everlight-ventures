import React, { useState, useRef, useEffect } from "react"

function CopyBtn({ text }) {
  const [ok, setOk] = useState(false)
  return (
    <button onClick={() => { navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 1500) }}
      className="text-[8px] px-1 py-0.5 rounded bg-white/5 text-gray-600 hover:text-amber-400 transition-all">
      {ok ? "Copied" : "Copy"}
    </button>
  )
}

export default function TradingChat() {
  const [open, setOpen] = useState(false)
  const [pin, setPin] = useState("")
  const [unlocked, setUnlocked] = useState(false)
  const [pinError, setPinError] = useState(false)
  const [messages, setMessages] = useState([
    { role: "ai", text: "I'm Lucrex. Ask me anything about your trade, change strategy, or adjust the bot. I have full context of your live position and bot state." }
  ])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState("review")
  const bottomRef = useRef(null)
  const correctPin = "080085"

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages, open])

  // Auto-verify when 6 digits entered
  useEffect(() => {
    if (pin.length === 6) {
      if (pin === correctPin) {
        setPinError(false)
        setTimeout(() => setUnlocked(true), 400)
      } else {
        setPinError(true)
        setTimeout(() => { setPin(""); setPinError(false) }, 800)
      }
    }
  }, [pin])

  const send = async () => {
    if (!input.trim() || loading) return
    const userText = input
    setMessages(p => [...p, { role: "user", text: userText }])
    setInput("")
    setLoading(true)
    try {
      const res = await fetch("/api/claude/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText, mode, pin: correctPin }),
      })
      const data = await res.json()
      setMessages(p => [...p, { role: "ai", text: data.answer || "No response.", mode: data.mode }])
    } catch (e) {
      setMessages(p => [...p, { role: "ai", text: "Connection error: " + e.message }])
    }
    setLoading(false)
  }

  // Closed state - golden crown bubble
  if (!open) {
    return (
      <button onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 w-14 h-14 rounded-full overflow-hidden shadow-2xl shadow-amber-500/30 hover:scale-110 transition-transform z-50 breathing"
        style={{boxShadow: "0 0 20px rgba(255,165,0,0.2), 0 0 40px rgba(255,165,0,0.1)"}}>
        <img src="/lucrex_icon.png" alt="Lucrex" className="w-full h-full object-cover" />
      </button>
    )
  }

  // PIN pad lock screen
  if (!unlocked) {
    return (
      <div className="fixed bottom-5 right-5 w-[320px] bg-[#0a0a0f] border border-white/[0.08] rounded-2xl shadow-2xl shadow-black/50 overflow-hidden z-50 page-enter"
        style={{boxShadow: "0 0 30px rgba(0,0,0,0.5), 0 0 60px rgba(255,165,0,0.05)"}}>
        {/* Close button */}
        <button onClick={() => { setOpen(false); setPin(""); setPinError(false) }}
          className="absolute top-3 right-3 text-gray-600 hover:text-white z-10 text-sm">x</button>

        <div className="flex flex-col items-center py-8 px-6">
          {/* Crown logo with glow */}
          <div className="w-20 h-20 rounded-2xl overflow-hidden shadow-2xl mb-5 relative"
            style={{boxShadow: "0 0 30px rgba(255,165,0,0.3), 0 0 60px rgba(255,165,0,0.1)"}}>
            <img src="/lucrex_icon.png" alt="Lucrex" className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent" />
          </div>

          <div className="text-[10px] tracking-[0.3em] text-amber-400/60 uppercase mb-1">Lucrex</div>
          <div className="text-[9px] text-gray-600 mb-5">Enter PIN to unlock</div>

          {/* PIN dots */}
          <div className="flex gap-3 mb-6">
            {[0,1,2,3,4,5].map(i => (
              <div key={i} className={`w-3 h-3 rounded-full transition-all duration-200 ${
                pinError ? "bg-red-500 border-red-500 shadow-red-500/50" :
                i < pin.length ? "bg-amber-400 border-amber-400 shadow-lg shadow-amber-400/50 scale-110" :
                "border-2 border-gray-700"
              }`} style={i < pin.length && !pinError ? {boxShadow: "0 0 8px rgba(255,165,0,0.5)"} : {}} />
            ))}
          </div>

          {/* Number pad */}
          <div className="grid grid-cols-3 gap-2.5">
            {[1,2,3,4,5,6,7,8,9,"",0,"clr"].map((d, i) => {
              if (d === "") return <div key={i} />
              if (d === "clr") return (
                <button key={i} onClick={() => setPin("")}
                  className="w-16 h-12 rounded-xl bg-white/[0.03] border border-red-500/20 text-[10px] font-medium text-red-400/70 hover:bg-red-500/10 active:scale-95 transition-all">
                  CLR
                </button>
              )
              return (
                <button key={i} onClick={() => pin.length < 6 && setPin(p => p + d)}
                  className="w-16 h-12 rounded-xl bg-white/[0.03] border border-white/[0.06] text-lg font-light text-gray-300 hover:bg-amber-400/10 hover:border-amber-400/20 hover:text-amber-400 active:scale-95 active:bg-amber-400/20 transition-all"
                  style={{fontFamily: "Inter, -apple-system, sans-serif"}}>
                  {d}
                </button>
              )
            })}
          </div>

          {pinError && <div className="text-[9px] text-red-400 mt-3 animate-pulse">Incorrect PIN</div>}
        </div>
      </div>
    )
  }

  // Chat interface (unlocked)
  return (
    <div className="fixed bottom-5 right-5 w-[380px] h-[520px] bg-[#0d0d14] border border-white/[0.08] rounded-2xl shadow-2xl shadow-black/50 flex flex-col overflow-hidden z-50 page-enter">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06] bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg overflow-hidden shadow-lg shadow-amber-500/20">
            <img src="/lucrex_icon.png" alt="L" className="w-full h-full object-cover" />
          </div>
          <div>
            <div className="text-xs font-bold">Lucrex Trading Advisor</div>
            <div className="text-[9px] text-gray-500">Live bot context | Claude Max</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setMode(m => m === "review" ? "execute" : "review")}
            className={`text-[9px] px-2 py-1 rounded-full font-medium transition-all ${
              mode === "execute" ? "bg-red-400/10 text-red-400 border border-red-400/20" : "bg-blue-400/10 text-blue-400 border border-blue-400/20"
            }`}>{mode === "execute" ? "EXECUTE" : "REVIEW"}</button>
          <button onClick={() => { setOpen(false); setUnlocked(false); setPin("") }}
            className="text-gray-500 hover:text-white transition-colors text-lg leading-none">x</button>
        </div>
      </div>

      {mode === "execute" && (
        <div className="px-3 py-1.5 bg-red-400/[0.05] border-b border-red-400/10 text-[9px] text-red-400/80 text-center">
          EXECUTE MODE -- Bot config changes will be applied live
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
            <div className={`w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-bold flex-shrink-0 overflow-hidden ${
              msg.role === "user" ? "bg-blue-500/20 text-blue-400" : ""
            }`}>
              {msg.role === "user" ? "U" : <img src="/lucrex_icon.png" alt="L" className="w-full h-full object-cover" />}
            </div>
            <div className={`max-w-[85%] ${msg.role === "user" ? "text-right" : ""}`}>
              <div className={`rounded-xl px-3 py-2 text-[12px] leading-relaxed ${
                msg.role === "user" ? "bg-blue-500/10 text-gray-200" : "bg-white/[0.04] text-gray-300"
              }`}>{msg.text}</div>
              <div className="flex items-center gap-1.5 mt-0.5 px-1">
                {msg.role === "ai" && <CopyBtn text={msg.text} />}
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-2">
            <div className="w-6 h-6 rounded-lg overflow-hidden"><img src="/lucrex_icon.png" alt="L" className="w-full h-full object-cover" /></div>
            <div className="bg-white/[0.04] rounded-xl px-3 py-2 flex gap-1">
              <span className="w-1.5 h-1.5 bg-amber-400/50 rounded-full animate-bounce" />
              <span className="w-1.5 h-1.5 bg-amber-400/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-1.5 h-1.5 bg-amber-400/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-3 py-2.5 border-t border-white/[0.06]">
        <div className="flex gap-2">
          <input value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && send()}
            placeholder="Ask about your trade..."
            className="flex-1 bg-white/[0.04] border border-white/[0.06] rounded-lg px-3 py-2 text-xs text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-amber-400/30 transition-all" />
          <button onClick={send} disabled={loading || !input.trim()}
            className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-orange-600 flex items-center justify-center text-black disabled:opacity-30 transition-all hover:shadow-lg hover:shadow-amber-500/20">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 19V5m0 0l-7 7m7-7l7 7" />
            </svg>
          </button>
        </div>
        <div className="text-[8px] text-gray-600 mt-1 px-1">
          {mode === "review" ? "Read-only -- ask questions, get analysis" : "Execute -- can change config, restart bot"}
        </div>
      </div>
    </div>
  )
}
