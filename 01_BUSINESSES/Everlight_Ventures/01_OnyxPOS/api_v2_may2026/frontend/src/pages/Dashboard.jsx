import { useState, useEffect } from 'react'
import { reports, sales } from '../lib/api'
import { DollarSign, ShoppingCart, TrendingUp, CreditCard } from 'lucide-react'

function StatCard({ icon: Icon, label, value, color = '#d4a843' }) {
  return (
    <div style={{ background: '#1a1a1a', borderRadius: 12, padding: 20, border: '1px solid #2a2a2a' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        <Icon size={18} color={color} />
        <span style={{ fontSize: 13, color: '#888' }}>{label}</span>
      </div>
      <p style={{ fontSize: 28, fontWeight: 700, margin: 0, color }}>{value}</p>
    </div>
  )
}

export default function Dashboard() {
  const [daily, setDaily] = useState(null)
  const [topProducts, setTopProducts] = useState([])
  const [recentSales, setRecentSales] = useState([])

  useEffect(() => {
    reports.daily().then(setDaily).catch(console.error)
    reports.topProducts(30).then(setTopProducts).catch(console.error)
    sales.list(7).then(setRecentSales).catch(console.error)
  }, [])

  const biz = localStorage.getItem('onyx_business_name') || 'Your Business'

  return (
    <div>
      <h2 style={{ fontSize: 24, fontWeight: 600, marginBottom: 24 }}>
        {biz} <span style={{ color: '#555', fontWeight: 400, fontSize: 14 }}>Today</span>
      </h2>

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
        <StatCard icon={DollarSign} label="Revenue" value={daily ? `$${daily.total_revenue.toFixed(2)}` : '...'} />
        <StatCard icon={ShoppingCart} label="Transactions" value={daily?.total_transactions ?? '...'} color="#22c55e" />
        <StatCard icon={TrendingUp} label="Cash Sales" value={daily ? `$${daily.cash_sales.toFixed(2)}` : '...'} color="#3b82f6" />
        <StatCard icon={CreditCard} label="Card Sales" value={daily ? `$${daily.card_sales.toFixed(2)}` : '...'} color="#a855f7" />
      </div>

      {/* Two columns: Top Products + Recent Sales */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Top Products */}
        <div style={{ background: '#1a1a1a', borderRadius: 12, padding: 20, border: '1px solid #2a2a2a' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: '#d4a843' }}>Top Products (30d)</h3>
          {topProducts.length === 0 ? (
            <p style={{ color: '#555', fontSize: 14 }}>No sales data yet. Ring up your first sale!</p>
          ) : (
            topProducts.slice(0, 8).map((p, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #2a2a2a' }}>
                <span style={{ fontSize: 14 }}>{p.product}</span>
                <span style={{ fontSize: 14, color: '#22c55e' }}>${p.revenue.toFixed(2)} ({p.quantity} sold)</span>
              </div>
            ))
          )}
        </div>

        {/* Recent Sales */}
        <div style={{ background: '#1a1a1a', borderRadius: 12, padding: 20, border: '1px solid #2a2a2a' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: '#d4a843' }}>Recent Sales</h3>
          {recentSales.length === 0 ? (
            <p style={{ color: '#555', fontSize: 14 }}>No recent sales. Hit the Register tab to start!</p>
          ) : (
            recentSales.slice(0, 8).map((s, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #2a2a2a' }}>
                <span style={{ fontSize: 14 }}>
                  {s.onyx_employees?.full_name || 'Staff'} &middot; {s.payment_method}
                </span>
                <span style={{ fontSize: 14, fontWeight: 600, color: '#22c55e' }}>${s.total.toFixed(2)}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
