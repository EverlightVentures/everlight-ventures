import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { auth } from '../lib/api'

export default function Register() {
  const [form, setForm] = useState({ email: '', password: '', business_name: '', full_name: '', phone: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  function update(field) {
    return e => setForm({ ...form, [field]: e.target.value })
  }

  async function handleSignup(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await auth.signup(form)
      const data = await auth.login(form.email, form.password)
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
      <div style={{ width: 440, padding: 40 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1 style={{ fontSize: 36, fontWeight: 700, color: '#d4a843', margin: 0 }}>ONYX</h1>
          <p style={{ color: '#666', margin: '8px 0 0', fontSize: 14 }}>Start your 60-day free trial</p>
        </div>

        <form onSubmit={handleSignup}>
          {error && <p style={{ color: '#ef4444', fontSize: 13, marginBottom: 12 }}>{error}</p>}

          <div style={{ marginBottom: 12 }}>
            <input placeholder="Business Name" value={form.business_name} onChange={update('business_name')} style={inputStyle} required />
          </div>
          <div style={{ marginBottom: 12 }}>
            <input placeholder="Your Full Name" value={form.full_name} onChange={update('full_name')} style={inputStyle} required />
          </div>
          <div style={{ marginBottom: 12 }}>
            <input type="email" placeholder="Email" value={form.email} onChange={update('email')} style={inputStyle} required />
          </div>
          <div style={{ marginBottom: 12 }}>
            <input type="tel" placeholder="Phone (optional)" value={form.phone} onChange={update('phone')} style={inputStyle} />
          </div>
          <div style={{ marginBottom: 24 }}>
            <input type="password" placeholder="Password" value={form.password} onChange={update('password')} style={inputStyle} required minLength={8} />
          </div>

          <button type="submit" disabled={loading} style={{
            width: '100%', padding: '12px', background: '#d4a843', color: '#0a0a0a',
            border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 15, cursor: 'pointer',
            opacity: loading ? 0.6 : 1,
          }}>
            {loading ? 'Creating account...' : 'Start Free Trial'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: 16, fontSize: 12, color: '#555' }}>
          60 days free. No credit card required. $49/mo after trial.
        </p>
        <p style={{ textAlign: 'center', marginTop: 8, fontSize: 13, color: '#666' }}>
          Already have an account? <Link to="/login" style={{ color: '#d4a843', textDecoration: 'none' }}>Sign in</Link>
        </p>
      </div>
    </div>
  )
}
