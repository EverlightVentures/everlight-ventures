import React, { useState, useRef, useEffect } from "react"

/**
 * CommandTerminal -- Chat interface for Stark AI.
 * Shows message history with agent attribution and typewriter effect.
 */

function TypewriterText({ text, speed = 12, onDone }) {
  const [displayed, setDisplayed] = useState("")
  const idx = useRef(0)

  useEffect(() => {
    idx.current = 0
    setDisplayed("")
    const timer = setInterval(() => {
      idx.current++
      if (idx.current >= text.length) {
        setDisplayed(text)
        clearInterval(timer)
        onDone && onDone()
      } else {
        setDisplayed(text.slice(0, idx.current))
      }
    }, speed)
    return () => clearInterval(timer)
  }, [text])

  return <span>{displayed}<span className="animate-pulse text-amber-400">|</span></span>
}

const AGENT_COLORS = {
  "Lucrex":        "text-amber-400",
  "Marcus Cole":   "text-amber-300",
  "Rex Thornton":  "text-green-400",
  "Rex Blackwell": "text-orange-400",
  "Piper Reeves":  "text-pink-400",
  "Penny Vance":   "text-emerald-400",
  "Filter Banks":  "text-cyan-400",
  "Harrison Knox": "text-yellow-400",
  "Forge Steele":  "text-lime-400",
  "Cipher Wolfe":  "text-purple-400",
  "Major Dex":     "text-blue-400",
}

export default function CommandTerminal({ messages, onSend, isProcessing }) {
  const [input, setInput] = useState("")
  const scrollRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || isProcessing) return
    onSend(input.trim())
    setInput("")
  }

  return (
    <div className="flex flex-col h-full bg-[#08080d]/80 rounded-xl border border-white/[0.04] backdrop-blur-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.04]">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <span className="text-[10px] tracking-[0.2em] text-gray-400 font-medium">STARK TERMINAL</span>
        </div>
        <span className="text-[9px] text-gray-600 font-mono">{messages.length} commands</span>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3 scrollbar-thin">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <div className="text-gray-600 text-sm mb-2">No commands yet.</div>
            <div className="text-gray-700 text-xs">Type a command or tap the voice orb to begin.</div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`${msg.role === "user" ? "ml-8" : "mr-4"}`}>
            {msg.role === "user" ? (
              <div className="flex items-start gap-2 justify-end">
                <div className="bg-white/[0.04] border border-white/[0.06] rounded-lg px-3 py-2 max-w-[85%]">
                  <div className="text-[11px] text-gray-300">{msg.text}</div>
                </div>
                <div className="w-6 h-6 rounded-md bg-white/[0.06] flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-[9px] text-gray-500">YOU</span>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-2">
                <div className="w-6 h-6 rounded-md bg-gradient-to-br from-amber-500/20 to-orange-600/10 border border-amber-400/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-[9px] font-bold text-amber-400">L</span>
                </div>
                <div className="flex-1 min-w-0">
                  {/* Agent attribution */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] font-semibold ${AGENT_COLORS[msg.agent] || "text-amber-400"}`}>
                      {msg.agent || "Lucrex"}
                    </span>
                    {msg.category && (
                      <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-white/[0.04] text-gray-500 border border-white/[0.04]">
                        {msg.category}
                      </span>
                    )}
                    {msg.latency_ms && (
                      <span className="text-[8px] text-gray-600 font-mono">{msg.latency_ms}ms</span>
                    )}
                  </div>
                  {/* Response text */}
                  <div className="bg-gradient-to-br from-white/[0.02] to-transparent border border-white/[0.04] rounded-lg px-3 py-2">
                    <div className="text-[11px] text-gray-200 leading-relaxed whitespace-pre-wrap">
                      {i === messages.length - 1 && msg.role === "assistant" && !msg.typed ? (
                        <TypewriterText text={msg.text} onDone={() => msg.typed = true} />
                      ) : (
                        msg.text
                      )}
                    </div>
                  </div>
                  {/* Agents used */}
                  {msg.agents_used && msg.agents_used.length > 1 && (
                    <div className="flex items-center gap-1 mt-1.5 flex-wrap">
                      <span className="text-[8px] text-gray-600">Agents:</span>
                      {msg.agents_used.map((a, j) => (
                        <span key={j} className={`text-[8px] ${AGENT_COLORS[a] || "text-gray-500"}`}>{a}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Thinking indicator */}
        {isProcessing && (
          <div className="flex items-start gap-2">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-purple-500/20 to-violet-600/10 border border-purple-400/10 flex items-center justify-center flex-shrink-0">
              <span className="text-[9px] font-bold text-purple-400">L</span>
            </div>
            <div className="bg-white/[0.02] border border-white/[0.04] rounded-lg px-3 py-2">
              <div className="flex items-center gap-1.5">
                <div className="flex gap-0.5">
                  {[0, 1, 2].map(i => (
                    <div key={i} className="w-1.5 h-1.5 rounded-full bg-purple-400/60 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                </div>
                <span className="text-[10px] text-purple-400/60">Hive dispatching...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="px-3 py-2.5 border-t border-white/[0.04]">
        <div className="flex items-center gap-2 bg-white/[0.03] rounded-lg border border-white/[0.06] px-3 py-1.5 focus-within:border-amber-400/20 transition-colors">
          <span className="text-amber-400/60 text-sm font-mono">&gt;</span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Command the Hive..."
            disabled={isProcessing}
            className="flex-1 bg-transparent text-[12px] text-gray-200 placeholder:text-gray-600 outline-none disabled:opacity-40"
            autoFocus
          />
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className="text-[10px] text-amber-400/60 hover:text-amber-400 disabled:opacity-20 transition-colors px-1"
          >
            SEND
          </button>
        </div>
      </form>
    </div>
  )
}
