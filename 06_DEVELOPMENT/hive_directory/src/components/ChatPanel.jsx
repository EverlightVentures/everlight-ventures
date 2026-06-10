import React, { useEffect, useRef, useState } from 'react'

const API_BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '') + '/api'

export default function ChatPanel({ employee }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [attachedFile, setAttachedFile] = useState(null)
  const [listening, setListening] = useState(false)
  const [speakingIdx, setSpeakingIdx] = useState(null)
  const endRef = useRef(null)
  const recognitionRef = useRef(null)
  const audioRef = useRef(null)

  const slug = employee?.slug
  const name = employee?.name || employee?.identity?.full_name || slug
  const nickname = employee?.identity?.nickname || ''
  const displayName = nickname ? `${name} ("${nickname}")` : name
  const catchphrase = (employee?.memory?.catchphrase || '').trim().replace(/^"|"$/g, '')
  const isOrchestrator = [
    'marcus-cole', 'major-dex', 'franklin-steele', 'dominic-reyes',
    'bernard-calloway', 'atlas-vega',
  ].includes(slug)

  useEffect(() => {
    setInput('')
    setError(null)
    setAttachedFile(null)
    // Load persisted history when the employee switches
    ;(async () => {
      try {
        const r = await fetch(API_BASE + '/team/' + encodeURIComponent(slug) + '/history')
        if (r.ok) {
          const j = await r.json()
          const loaded = (j.messages || []).map((m) => ({
            role: m.role,
            content: m.content,
            consulted: m.meta?.consulted,
            source: m.meta?.source,
          }))
          setMessages(loaded)
        } else {
          setMessages([])
        }
      } catch {
        setMessages([])
      }
    })()
  }, [slug])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, busy])

  async function send() {
    const text = input.trim()
    if ((!text && !attachedFile) || busy) return
    setBusy(true)
    setError(null)

    let fileContext = ''
    if (attachedFile) {
      try {
        fileContext = await attachedFile.text()
      } catch (e) {
        fileContext = `(binary file ${attachedFile.name} -- ${attachedFile.size} bytes; cannot read as text)`
      }
    }

    const userTurn = attachedFile
      ? { role: 'user', content: text + (text ? '\n\n' : '') + `[attached: ${attachedFile.name}]` }
      : { role: 'user', content: text }

    const historyForSend = [...messages.filter((m) => !m.error), userTurn].map((m) => ({
      role: m.role === 'assistant' ? 'assistant' : 'user',
      content: m.content,
    }))

    setMessages((m) => [...m, userTurn])
    setInput('')
    setAttachedFile(null)

    try {
      const r = await fetch(API_BASE + '/team/' + encodeURIComponent(slug) + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: historyForSend,
          file_context: fileContext,
        }),
      })
      const j = await r.json()
      if (!j.ok) {
        setError(j.error || j.errors?.gemini || 'chat failed')
        setMessages((m) => [
          ...m,
          { role: 'assistant', content: j.reply || '(offline)', error: true },
        ])
      } else {
        setMessages((m) => [
          ...m,
          {
            role: 'assistant',
            content: j.reply || '',
            consulted: j.consulted || [],
            source: j.source,
          },
        ])
      }
    } catch (e) {
      setError(String(e))
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: '(connection error: ' + String(e) + ')', error: true },
      ])
    } finally {
      setBusy(false)
    }
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  async function clearChat() {
    setMessages([])
    try {
      await fetch(API_BASE + '/team/' + encodeURIComponent(slug) + '/history', {
        method: 'DELETE',
      })
    } catch {}
  }

  function onFile(e) {
    const f = e.target.files?.[0]
    if (f) setAttachedFile(f)
    e.target.value = ''
  }

  function toggleMic() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) {
      setError('Mic not supported in this browser (try Chrome).')
      return
    }
    if (listening) {
      recognitionRef.current?.stop()
      setListening(false)
      return
    }
    const rec = new SR()
    rec.lang = 'en-US'
    rec.continuous = false
    rec.interimResults = true
    rec.onresult = (ev) => {
      const transcript = Array.from(ev.results)
        .map((r) => r[0].transcript)
        .join(' ')
      setInput(transcript)
    }
    rec.onerror = (ev) => {
      setError('Mic error: ' + ev.error)
      setListening(false)
    }
    rec.onend = () => setListening(false)
    recognitionRef.current = rec
    rec.start()
    setListening(true)
  }

  async function speak(idx, text) {
    if (speakingIdx === idx) {
      audioRef.current?.pause()
      setSpeakingIdx(null)
      return
    }
    try {
      const r = await fetch(API_BASE + '/team/' + encodeURIComponent(slug) + '/voice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      if (!r.ok) {
        const det = await r.text()
        setError('Voice failed: ' + det.slice(0, 200))
        return
      }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      if (!audioRef.current) audioRef.current = new Audio()
      audioRef.current.src = url
      audioRef.current.onended = () => setSpeakingIdx(null)
      audioRef.current.play()
      setSpeakingIdx(idx)
    } catch (e) {
      setError('Voice error: ' + String(e))
      setSpeakingIdx(null)
    }
  }

  const promptSuggestions = isOrchestrator
    ? [
        "What is happening in the pipeline right now?",
        "How many deals are we close to closing this week?",
        "Who needs my attention today?",
        "Get me a 60-second status across all departments.",
      ]
    : [
        "What are you working on right now?",
        "Give me 3 things you can do for me this week.",
        "Who should I talk to about...",
        "Draft me something in your voice.",
      ]

  return (
    <div className="card p-5 flex flex-col">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-amber-400 flex items-center gap-2">
            <span>Direct line to {displayName}</span>
            {isOrchestrator && (
              <span className="px-2 py-0.5 rounded-full bg-amber-400/15 text-amber-400 text-[9px] font-bold tracking-wider border border-amber-400/25">
                ORCHESTRATOR
              </span>
            )}
          </div>
          {catchphrase && (
            <div className="text-xs text-gray-500 mt-1 italic">"{catchphrase}"</div>
          )}
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="text-[11px] text-gray-500 hover:text-amber-400 transition"
          >
            clear chat
          </button>
        )}
      </div>

      <div
        className="flex-1 overflow-y-auto space-y-3 mb-3 pr-1"
        style={{ maxHeight: '480px', minHeight: '220px' }}
      >
        {messages.length === 0 && (
          <div className="text-sm text-gray-500 space-y-3">
            <div>
              Talk to {name}.{' '}
              {isOrchestrator
                ? 'They lead a team -- ask big questions and they consult colleagues in real time.'
                : 'They know their team and will hand off when you ask about something outside their lane.'}
            </div>
            <div className="flex flex-wrap gap-2">
              {promptSuggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => setInput(s)}
                  className="text-[11px] px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-amber-400/10 text-gray-400 hover:text-amber-400 transition border border-white/5 hover:border-amber-400/30"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={'flex ' + (m.role === 'user' ? 'justify-end' : 'justify-start')}>
            <div
              className={
                'max-w-[88%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ' +
                (m.role === 'user'
                  ? 'bg-amber-400/10 text-amber-100 border border-amber-400/20'
                  : m.error
                  ? 'bg-red-400/10 text-red-300 border border-red-400/20'
                  : 'bg-white/5 text-gray-200 border border-white/10')
              }
            >
              {m.consulted && m.consulted.length > 0 && (
                <div className="mb-2 text-[10px] uppercase tracking-wider text-amber-400/80 flex items-center gap-1.5 flex-wrap">
                  <span>consulted:</span>
                  {m.consulted.map((s) => (
                    <span
                      key={s}
                      className="px-1.5 py-0.5 rounded bg-amber-400/10 text-amber-400/90 border border-amber-400/20"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}
              <div>{m.content}</div>
              {m.role === 'assistant' && !m.error && m.content && (
                <div className="mt-2 flex items-center gap-3">
                  <button
                    onClick={() => speak(i, m.content)}
                    className="text-[10px] uppercase tracking-wider text-gray-500 hover:text-amber-400 transition"
                    title="Speak aloud"
                  >
                    {speakingIdx === i ? 'stop' : 'speak'}
                  </button>
                  {m.source && (
                    <span className="text-[10px] text-gray-600">via {m.source}</span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {busy && (
          <div className="flex justify-start">
            <div className="rounded-2xl px-4 py-2.5 text-sm bg-white/5 text-gray-500 border border-white/10">
              <span className="inline-block animate-pulse">
                {isOrchestrator
                  ? `${name} is consulting the team...`
                  : `${name} is typing...`}
              </span>
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {attachedFile && (
        <div className="mb-2 flex items-center gap-2 text-xs">
          <span className="px-2 py-1 rounded bg-amber-400/10 text-amber-400 border border-amber-400/20">
            attached: {attachedFile.name} ({Math.round(attachedFile.size / 1024)} KB)
          </span>
          <button
            onClick={() => setAttachedFile(null)}
            className="text-gray-500 hover:text-red-400 transition"
          >
            remove
          </button>
        </div>
      )}

      <div className="flex gap-2 items-end">
        <label
          className="cursor-pointer px-3 py-2 rounded-xl bg-white/5 hover:bg-amber-400/10 border border-white/10 hover:border-amber-400/30 text-gray-400 hover:text-amber-400 text-sm transition"
          title="Attach file"
        >
          +
          <input type="file" onChange={onFile} className="hidden" />
        </label>

        <button
          onClick={toggleMic}
          className={
            'px-3 py-2 rounded-xl border text-sm transition ' +
            (listening
              ? 'bg-red-400/20 text-red-400 border-red-400/30 animate-pulse'
              : 'bg-white/5 hover:bg-amber-400/10 border-white/10 hover:border-amber-400/30 text-gray-400 hover:text-amber-400')
          }
          title="Talk to mic"
        >
          {listening ? 'listening...' : 'mic'}
        </button>

        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder={`Message ${name}... (Enter to send, Shift+Enter for newline)`}
          rows={2}
          disabled={busy}
          className="flex-1 bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-amber-400/40 resize-none"
        />

        <button
          onClick={send}
          disabled={busy || (!input.trim() && !attachedFile)}
          className="px-5 py-2 rounded-xl bg-amber-400/20 hover:bg-amber-400/30 text-amber-400 disabled:opacity-30 disabled:cursor-not-allowed border border-amber-400/30 text-sm font-semibold transition"
        >
          {busy ? '...' : 'Send'}
        </button>
      </div>

      {error && (
        <div className="mt-2 text-[11px] text-red-400">error: {error}</div>
      )}
    </div>
  )
}
