import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { auth } from '../lib/api'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleLogin(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await auth.login(email, password)
      localStorage.setItem('onyx_token', data.access_token)
      localStorage.setItem('onyx_tenant_id', data.tenant_id)
      localStorage.setItem('onyx_business_name', data.business_name)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    width: '100%', padding: '12px 16px', background: '#1a1a1a', border: '1px solid #2a2a2a',
    borderRadius: 8, color: '#f5f5f5', fontSize: 14, outline: 'none', boxSizing: 'border-box',
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0a0a0a' }}>
      <div style={{ width: 400, padding: 40 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1 style={{ fontSize: 36, fontWeight: 700, color: '#d4a843', margin: 0 }}>ONYX</h1>
          <p style={{ color: '#666', margin: '8px 0 0', fontSize: 14 }}>Point of Sale</p>
        </div>

        <form onSubmit={handleLogin}>
          {error && <p style={{ color: '#ef4444', fontSize: 13, marginBottom: 12 }}>{error}</p>}

          <div style={{ marginBottom: 16 }}>
            <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)}
              style={inputStyle} required />
          </div>
          <div style={{ marginBottom: 24 }}>
            <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)}
              style={inputStyle} required />
          </div>

          <button type="submit" disabled={loading} style={{
            width: '100%', padding: '12px', background: '#d4a843', color: '#0a0a0a',
            border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 15, cursor: 'pointer',
            opacity: loading ? 0.6 : 1,
          }}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: 20, fontSize: 13, color: '#666' }}>
          No account? <Link to="/register" style={{ color: '#d4a843', textDecoration: 'none' }}>Start free trial</Link>
        </p>
      </div>
    </div>
  )
}
