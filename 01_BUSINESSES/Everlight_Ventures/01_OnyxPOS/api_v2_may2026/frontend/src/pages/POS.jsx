import { useState, useEffect } from 'react'
import { products as productsApi, sales as salesApi } from '../lib/api'
import { Plus, Minus, Trash2, ShoppingCart } from 'lucide-react'

export default function POS() {
  const [products, setProducts] = useState([])
  const [cart, setCart] = useState([])
  const [search, setSearch] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('cash')
  const [amountReceived, setAmountReceived] = useState('')
  const [receipt, setReceipt] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    productsApi.list().then(setProducts).catch(console.error)
  }, [])

  const filteredProducts = products.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase())
  )

  function addToCart(product) {
    const existing = cart.find(c => c.product_id === product.id)
    if (existing) {
      setCart(cart.map(c => c.product_id === product.id ? { ...c, quantity: c.quantity + 1 } : c))
    } else {
      setCart([...cart, {
        product_id: product.id,
        product_name: product.name,
        category_name: product.onyx_categories?.name || '',
        unit_price: product.unit_price,
        quantity: 1,
      }])
    }
  }

  function updateQty(productId, delta) {
    setCart(cart.map(c => {
      if (c.product_id === productId) {
        const newQty = c.quantity + delta
        return newQty > 0 ? { ...c, quantity: newQty } : c
      }
      return c
    }).filter(c => c.quantity > 0))
  }

  function removeFromCart(productId) {
    setCart(cart.filter(c => c.product_id !== productId))
  }

  const subtotal = cart.reduce((sum, c) => sum + c.unit_price * c.quantity, 0)
  const taxRate = 0.0825
  const tax = subtotal * taxRate
  const total = subtotal + tax
  const changeDue = paymentMethod === 'cash' && amountReceived ? parseFloat(amountReceived) - total : 0

  async function completeSale() {
    if (cart.length === 0) return
    setLoading(true)
    try {
      const employeeId = localStorage.getItem('onyx_employee_id') || null
      const result = await salesApi.create({
        employee_id: employeeId,
        items: cart,
        payment_method: paymentMethod,
        amount_received: paymentMethod === 'cash' ? parseFloat(amountReceived || 0) : null,
      })
      setReceipt(result)
      setCart([])
      setAmountReceived('')
    } catch (err) {
      alert(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (receipt) {
    return (
      <div style={{ maxWidth: 400, margin: '40px auto', textAlign: 'center' }}>
        <div style={{ background: '#1a1a1a', borderRadius: 12, padding: 32, border: '1px solid #2a2a2a' }}>
          <h2 style={{ color: '#22c55e', fontSize: 24, marginBottom: 16 }}>Sale Complete</h2>
          <p style={{ fontSize: 36, fontWeight: 700, color: '#d4a843' }}>${receipt.total.toFixed(2)}</p>
          {receipt.change_due > 0 && (
            <p style={{ fontSize: 18, color: '#22c55e', marginTop: 8 }}>Change: ${receipt.change_due.toFixed(2)}</p>
          )}
          <p style={{ color: '#555', fontSize: 13, marginTop: 16 }}>{receipt.items} items</p>
          <button onClick={() => setReceipt(null)} style={{
            marginTop: 24, padding: '12px 32px', background: '#d4a843', color: '#0a0a0a',
            border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer', fontSize: 15,
          }}>
            New Sale
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 24, height: 'calc(100vh - 48px)' }}>
      {/* Product Grid */}
      <div>
        <input
          placeholder="Search products..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            width: '100%', padding: '12px 16px', background: '#1a1a1a', border: '1px solid #2a2a2a',
            borderRadius: 8, color: '#f5f5f5', fontSize: 14, marginBottom: 16, boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, overflowY: 'auto', maxHeight: 'calc(100vh - 140px)' }}>
          {filteredProducts.map(p => (
            <button key={p.id} onClick={() => addToCart(p)} style={{
              background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: 10, padding: 16,
              cursor: 'pointer', textAlign: 'left', color: '#f5f5f5',
            }}>
              <p style={{ fontSize: 14, fontWeight: 500, margin: '0 0 4px' }}>{p.name}</p>
              <p style={{ fontSize: 18, fontWeight: 700, color: '#d4a843', margin: 0 }}>${p.unit_price.toFixed(2)}</p>
              {p.stock_quantity != null && (
                <p style={{ fontSize: 11, color: p.stock_quantity <= p.reorder_point ? '#ef4444' : '#555', margin: '4px 0 0' }}>
                  {p.stock_quantity} in stock
                </p>
              )}
            </button>
          ))}
          {filteredProducts.length === 0 && (
            <p style={{ color: '#555', gridColumn: '1/-1', textAlign: 'center', padding: 40 }}>
              {products.length === 0 ? 'Add products in the Products tab first' : 'No products match your search'}
            </p>
          )}
        </div>
      </div>

      {/* Cart */}
      <div style={{ background: '#1a1a1a', borderRadius: 12, padding: 20, border: '1px solid #2a2a2a', display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <ShoppingCart size={18} color="#d4a843" /> Cart ({cart.length})
        </h3>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {cart.map(item => (
            <div key={item.product_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid #2a2a2a' }}>
              <div>
                <p style={{ fontSize: 14, margin: 0 }}>{item.product_name}</p>
                <p style={{ fontSize: 12, color: '#888', margin: '2px 0 0' }}>${item.unit_price.toFixed(2)} each</p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <button onClick={() => updateQty(item.product_id, -1)} style={{ background: '#2a2a2a', border: 'none', borderRadius: 4, padding: 4, cursor: 'pointer', color: '#f5f5f5' }}>
                  <Minus size={14} />
                </button>
                <span style={{ fontSize: 14, minWidth: 20, textAlign: 'center' }}>{item.quantity}</span>
                <button onClick={() => updateQty(item.product_id, 1)} style={{ background: '#2a2a2a', border: 'none', borderRadius: 4, padding: 4, cursor: 'pointer', color: '#f5f5f5' }}>
                  <Plus size={14} />
                </button>
                <button onClick={() => removeFromCart(item.product_id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', padding: 4 }}>
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Totals */}
        <div style={{ borderTop: '1px solid #2a2a2a', paddingTop: 16, marginTop: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ color: '#888', fontSize: 14 }}>Subtotal</span>
            <span style={{ fontSize: 14 }}>${subtotal.toFixed(2)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ color: '#888', fontSize: 14 }}>Tax (8.25%)</span>
            <span style={{ fontSize: 14 }}>${tax.toFixed(2)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <span style={{ fontWeight: 700, fontSize: 18 }}>Total</span>
            <span style={{ fontWeight: 700, fontSize: 18, color: '#d4a843' }}>${total.toFixed(2)}</span>
          </div>

          {/* Payment Method */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            {['cash', 'card'].map(m => (
              <button key={m} onClick={() => setPaymentMethod(m)} style={{
                flex: 1, padding: '10px', border: `1px solid ${paymentMethod === m ? '#d4a843' : '#2a2a2a'}`,
                background: paymentMethod === m ? '#2a2a1a' : '#0a0a0a', borderRadius: 8,
                color: paymentMethod === m ? '#d4a843' : '#888', cursor: 'pointer', fontWeight: 500, textTransform: 'capitalize',
              }}>{m}</button>
            ))}
          </div>

          {paymentMethod === 'cash' && (
            <div style={{ marginBottom: 12 }}>
              <input type="number" placeholder="Amount received" value={amountReceived}
                onChange={e => setAmountReceived(e.target.value)}
                style={{ width: '100%', padding: '10px', background: '#0a0a0a', border: '1px solid #2a2a2a', borderRadius: 8, color: '#f5f5f5', fontSize: 14, boxSizing: 'border-box' }}
              />
              {changeDue > 0 && <p style={{ color: '#22c55e', fontSize: 14, margin: '8px 0 0' }}>Change: ${changeDue.toFixed(2)}</p>}
            </div>
          )}

          <button onClick={completeSale} disabled={loading || cart.length === 0} style={{
            width: '100%', padding: '14px', background: cart.length > 0 ? '#22c55e' : '#2a2a2a',
            color: '#fff', border: 'none', borderRadius: 8, fontWeight: 700, fontSize: 16,
            cursor: cart.length > 0 ? 'pointer' : 'not-allowed',
          }}>
            {loading ? 'Processing...' : `Complete Sale - $${total.toFixed(2)}`}
          </button>
        </div>
      </div>
    </div>
  )
}
