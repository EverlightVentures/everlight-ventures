import { useState } from 'react'
import { chat } from '../lib/api'
import { Send, MessageCircle, Sparkles } from 'lucide-react'

export default function Chat() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hey! I\'m Onyx AI. Ask me anything about your business -- sales, top products, trends, employee hours. Try "How did we do this week?" or "What\'s our best-selling product?"' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  async function sendMessage(e) {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)

    try {
      const res = await chat.send(userMsg)
      setMessages(prev => [...prev, { role: 'assistant', content: res.response }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Sorry, I couldn't process that: ${err.message}` }])
    } finally {
      setLoading(false)
    }
  }

  const suggestions = [
    "How did we do this week?",
    "What's our best-selling product?",
    "Compare cash vs card sales",
    "Any slow-moving inventory?",
  ]

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', height: 'calc(100vh - 48px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <Sparkles size={20} color="#d4a843" />
        <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Ask Onyx</h2>
        <span style={{ fontSize: 12, color: '#555', marginLeft: 'auto' }}>Powered by Claude AI</span>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', marginBottom: 16 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{
            display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            marginBottom: 12,
          }}>
            <div style={{
              maxWidth: '80%', padding: '12px 16px', borderRadius: 12,
              background: msg.role === 'user' ? '#d4a843' : '#1a1a1a',
              color: msg.role === 'user' ? '#0a0a0a' : '#f5f5f5',
              border: msg.role === 'assistant' ? '1px solid #2a2a2a' : 'none',
              fontSize: 14, lineHeight: 1.5, whiteSpace: 'pre-wrap',
            }}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ padding: '12px 16px', background: '#1a1a1a', borderRadius: 12, border: '1px solid #2a2a2a', display: 'inline-block', fontSize: 14, color: '#888' }}>
            Thinking...
          </div>
        )}
      </div>

      {/* Suggestions */}
      {messages.length <= 1 && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
          {suggestions.map(s => (
            <button key={s} onClick={() => { setInput(s); }} style={{
              padding: '8px 14px', background: '#1a1a1a', border: '1px solid #2a2a2a',
              borderRadius: 20, color: '#d4a843', cursor: 'pointer', fontSize: 13,
            }}>{s}</button>
          ))}
        </div>
      )}

      {/* Input */}
      <form onSubmit={sendMessage} style={{ display: 'flex', gap: 8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask about your business..."
          style={{
            flex: 1, padding: '14px 16px', background: '#1a1a1a', border: '1px solid #2a2a2a',
            borderRadius: 10, color: '#f5f5f5', fontSize: 14, outline: 'none',
          }}
        />
        <button type="submit" disabled={loading || !input.trim()} style={{
          padding: '14px 20px', background: '#d4a843', border: 'none', borderRadius: 10,
          cursor: 'pointer', color: '#0a0a0a',
        }}>
          <Send size={18} />
        </button>
      </form>
    </div>
  )
}
