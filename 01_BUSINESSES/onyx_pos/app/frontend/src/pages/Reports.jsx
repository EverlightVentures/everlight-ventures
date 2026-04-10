import { useState, useEffect } from 'react'
import { reports } from '../lib/api'

export default function Reports() {
  const [daily, setDaily] = useState(null)
  const [topProducts, setTopProducts] = useState([])
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])

  useEffect(() => {
    reports.daily(selectedDate).then(setDaily).catch(console.error)
    reports.topProducts(30).then(setTopProducts).catch(console.error)
  }, [selectedDate])

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Reports</h2>
        <input type="date" value={selectedDate} onChange={e => setSelectedDate(e.target.value)}
          style={{ padding: '8px 12px', background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: 6, color: '#f5f5f5', fontSize: 14 }} />
      </div>

      {daily && (
        <div style={{ background: '#1a1a1a', borderRadius: 12, padding: 24, border: '1px solid #2a2a2a', marginBottom: 24 }}>
          <h3 style={{ color: '#d4a843', fontSize: 16, marginBottom: 16 }}>Daily Summary - {daily.date}</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
            <div><p style={{ color: '#888', fontSize: 13, margin: 0 }}>Revenue</p><p style={{ fontSize: 24, fontWeight: 700, color: '#22c55e', margin: '4px 0 0' }}>${daily.total_revenue.toFixed(2)}</p></div>
            <div><p style={{ color: '#888', fontSize: 13, margin: 0 }}>Transactions</p><p style={{ fontSize: 24, fontWeight: 700, margin: '4px 0 0' }}>{daily.total_transactions}</p></div>
            <div><p style={{ color: '#888', fontSize: 13, margin: 0 }}>Tax Collected</p><p style={{ fontSize: 24, fontWeight: 700, color: '#a855f7', margin: '4px 0 0' }}>${daily.total_tax.toFixed(2)}</p></div>
            <div><p style={{ color: '#888', fontSize: 13, margin: 0 }}>Cash</p><p style={{ fontSize: 18, fontWeight: 600, margin: '4px 0 0' }}>${daily.cash_sales.toFixed(2)}</p></div>
            <div><p style={{ color: '#888', fontSize: 13, margin: 0 }}>Card</p><p style={{ fontSize: 18, fontWeight: 600, margin: '4px 0 0' }}>${daily.card_sales.toFixed(2)}</p></div>
          </div>
        </div>
      )}

      <div style={{ background: '#1a1a1a', borderRadius: 12, padding: 24, border: '1px solid #2a2a2a' }}>
        <h3 style={{ color: '#d4a843', fontSize: 16, marginBottom: 16 }}>Top Products (30 days)</h3>
        {topProducts.map((p, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid #2a2a2a' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 12, color: '#555', width: 20 }}>#{i + 1}</span>
              <span style={{ fontSize: 14 }}>{p.product}</span>
            </div>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: '#22c55e' }}>${p.revenue.toFixed(2)}</span>
              <span style={{ fontSize: 12, color: '#888', marginLeft: 8 }}>{p.quantity} sold</span>
            </div>
          </div>
        ))}
        {topProducts.length === 0 && <p style={{ color: '#555', fontSize: 14 }}>No sales data yet.</p>}
      </div>
    </div>
  )
}
