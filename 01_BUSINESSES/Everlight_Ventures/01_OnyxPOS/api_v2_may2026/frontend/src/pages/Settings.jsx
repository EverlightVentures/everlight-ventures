import { useState } from 'react'
import { billing } from '../lib/api'

export default function Settings() {
  const [loading, setLoading] = useState(false)
  const businessName = localStorage.getItem('onyx_business_name') || 'Your Business'

  async function handleUpgrade() {
    setLoading(true)
    try {
      const res = await billing.createCheckout()
      window.location.href = res.checkout_url
    } catch (err) {
      alert(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 600 }}>
      <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 24 }}>Settings</h2>

      <div style={{ background: '#1a1a1a', borderRadius: 12, padding: 24, border: '1px solid #2a2a2a', marginBottom: 20 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: '#d4a843', marginBottom: 12 }}>Business</h3>
        <p style={{ fontSize: 14, color: '#888' }}>Business Name: <span style={{ color: '#f5f5f5' }}>{businessName}</span></p>
      </div>

      <div style={{ background: '#1a1a1a', borderRadius: 12, padding: 24, border: '1px solid #2a2a2a' }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: '#d4a843', marginBottom: 12 }}>Subscription</h3>
        <p style={{ fontSize: 14, color: '#888', marginBottom: 16 }}>
          Current plan: <span style={{ color: '#22c55e' }}>Free Trial</span> (60 days)
        </p>
        <p style={{ fontSize: 13, color: '#555', marginBottom: 16 }}>
          After trial: $49/mo for unlimited sales, employees, and AI insights.
        </p>
        <button onClick={handleUpgrade} disabled={loading} style={{
          padding: '12px 24px', background: '#d4a843', color: '#0a0a0a',
          border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer',
        }}>
          {loading ? 'Loading...' : 'Upgrade to Starter ($49/mo)'}
        </button>
      </div>
    </div>
  )
}
