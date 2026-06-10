import { useState, useEffect } from 'react'
import { employees as api } from '../lib/api'
import { Plus, Users } from 'lucide-react'

export default function Employees() {
  const [emps, setEmps] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ full_name: '', role: 'employee', pin: '', phone: '', email: '', hourly_rate: '' })

  useEffect(() => { api.list().then(setEmps).catch(console.error) }, [])

  async function addEmployee(e) {
    e.preventDefault()
    const data = { ...form }
    if (data.hourly_rate) data.hourly_rate = parseFloat(data.hourly_rate)
    else delete data.hourly_rate
    if (!data.pin) delete data.pin
    await api.create(data)
    setForm({ full_name: '', role: 'employee', pin: '', phone: '', email: '', hourly_rate: '' })
    setShowForm(false)
    api.list().then(setEmps)
  }

  const inputStyle = { width: '100%', padding: '10px 12px', background: '#0a0a0a', border: '1px solid #2a2a2a', borderRadius: 6, color: '#f5f5f5', fontSize: 14, boxSizing: 'border-box' }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Team</h2>
        <button onClick={() => setShowForm(!showForm)} style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '10px 16px', background: '#d4a843',
          color: '#0a0a0a', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer',
        }}><Plus size={16} /> Add Employee</button>
      </div>

      {showForm && (
        <form onSubmit={addEmployee} style={{ background: '#1a1a1a', padding: 20, borderRadius: 12, marginBottom: 20, border: '1px solid #2a2a2a' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <input placeholder="Full name" value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} style={inputStyle} required />
            <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} style={inputStyle}>
              <option value="employee">Employee</option>
              <option value="manager">Manager</option>
              <option value="owner">Owner</option>
            </select>
            <input placeholder="PIN (for register login)" value={form.pin} onChange={e => setForm({ ...form, pin: e.target.value })} style={inputStyle} maxLength={6} />
            <input placeholder="Hourly rate" type="number" step="0.01" value={form.hourly_rate} onChange={e => setForm({ ...form, hourly_rate: e.target.value })} style={inputStyle} />
            <input placeholder="Phone" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} style={inputStyle} />
            <input placeholder="Email" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} style={inputStyle} />
          </div>
          <button type="submit" style={{ marginTop: 12, padding: '10px 24px', background: '#22c55e', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer' }}>Save Employee</button>
        </form>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {emps.map(emp => (
          <div key={emp.id} style={{ background: '#1a1a1a', borderRadius: 12, padding: 20, border: '1px solid #2a2a2a' }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 4px' }}>{emp.full_name}</h3>
            <p style={{ fontSize: 12, color: '#d4a843', margin: '0 0 12px', textTransform: 'capitalize' }}>{emp.role}</p>
            {emp.phone && <p style={{ fontSize: 13, color: '#888', margin: '4px 0' }}>{emp.phone}</p>}
            {emp.email && <p style={{ fontSize: 13, color: '#888', margin: '4px 0' }}>{emp.email}</p>}
            {emp.hourly_rate && <p style={{ fontSize: 13, color: '#22c55e', margin: '4px 0' }}>${emp.hourly_rate}/hr</p>}
          </div>
        ))}
      </div>
      {emps.length === 0 && (
        <div style={{ padding: 60, textAlign: 'center', color: '#555' }}>
          <Users size={32} style={{ margin: '0 auto 12px', display: 'block' }} />
          No employees yet. You were added as owner on signup.
        </div>
      )}
    </div>
  )
}
