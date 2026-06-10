import { useState, useEffect } from 'react'
import { products as api, categories as catApi } from '../lib/api'
import { Plus, Package } from 'lucide-react'

export default function Products() {
  const [products, setProducts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', unit_price: '', sku: '', stock_quantity: '', description: '' })

  useEffect(() => { api.list().then(setProducts).catch(console.error) }, [])

  async function addProduct(e) {
    e.preventDefault()
    await api.create({ ...form, unit_price: parseFloat(form.unit_price), stock_quantity: form.stock_quantity ? parseInt(form.stock_quantity) : null })
    setForm({ name: '', unit_price: '', sku: '', stock_quantity: '', description: '' })
    setShowForm(false)
    api.list().then(setProducts)
  }

  const inputStyle = { width: '100%', padding: '10px 12px', background: '#0a0a0a', border: '1px solid #2a2a2a', borderRadius: 6, color: '#f5f5f5', fontSize: 14, boxSizing: 'border-box' }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Products</h2>
        <button onClick={() => setShowForm(!showForm)} style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '10px 16px', background: '#d4a843',
          color: '#0a0a0a', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer',
        }}><Plus size={16} /> Add Product</button>
      </div>

      {showForm && (
        <form onSubmit={addProduct} style={{ background: '#1a1a1a', padding: 20, borderRadius: 12, marginBottom: 20, border: '1px solid #2a2a2a' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <input placeholder="Product name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} style={inputStyle} required />
            <input placeholder="Price" type="number" step="0.01" value={form.unit_price} onChange={e => setForm({ ...form, unit_price: e.target.value })} style={inputStyle} required />
            <input placeholder="SKU (optional)" value={form.sku} onChange={e => setForm({ ...form, sku: e.target.value })} style={inputStyle} />
            <input placeholder="Stock quantity" type="number" value={form.stock_quantity} onChange={e => setForm({ ...form, stock_quantity: e.target.value })} style={inputStyle} />
          </div>
          <button type="submit" style={{ marginTop: 12, padding: '10px 24px', background: '#22c55e', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer' }}>Save Product</button>
        </form>
      )}

      <div style={{ background: '#1a1a1a', borderRadius: 12, border: '1px solid #2a2a2a', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #2a2a2a' }}>
              {['Product', 'Price', 'SKU', 'Stock', 'Status'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '12px 16px', fontSize: 12, color: '#888', fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {products.map(p => (
              <tr key={p.id} style={{ borderBottom: '1px solid #1f1f1f' }}>
                <td style={{ padding: '12px 16px', fontSize: 14 }}>{p.name}</td>
                <td style={{ padding: '12px 16px', fontSize: 14, color: '#d4a843' }}>${p.unit_price.toFixed(2)}</td>
                <td style={{ padding: '12px 16px', fontSize: 14, color: '#888' }}>{p.sku || '-'}</td>
                <td style={{ padding: '12px 16px', fontSize: 14, color: p.stock_quantity != null && p.stock_quantity <= p.reorder_point ? '#ef4444' : '#888' }}>
                  {p.stock_quantity ?? '-'}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ fontSize: 12, padding: '3px 8px', borderRadius: 4, background: p.is_active ? '#1a2e1a' : '#2e1a1a', color: p.is_active ? '#22c55e' : '#ef4444' }}>
                    {p.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {products.length === 0 && (
          <div style={{ padding: 40, textAlign: 'center', color: '#555' }}>
            <Package size={32} style={{ margin: '0 auto 12px', display: 'block' }} />
            No products yet. Add your first product above.
          </div>
        )}
      </div>
    </div>
  )
}
