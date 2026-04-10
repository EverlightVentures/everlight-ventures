import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, ShoppingCart, Package, Users, BarChart3, MessageCircle, Settings, LogOut } from 'lucide-react'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/pos', icon: ShoppingCart, label: 'Register' },
  { to: '/products', icon: Package, label: 'Products' },
  { to: '/employees', icon: Users, label: 'Team' },
  { to: '/reports', icon: BarChart3, label: 'Reports' },
  { to: '/chat', icon: MessageCircle, label: 'Ask Onyx' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
  const navigate = useNavigate()
  const businessName = localStorage.getItem('onyx_business_name') || 'Onyx POS'

  function logout() {
    localStorage.clear()
    navigate('/login')
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <nav style={{
        width: 240, background: '#1a1a1a', borderRight: '1px solid #2a2a2a',
        display: 'flex', flexDirection: 'column', padding: '20px 0',
      }}>
        <div style={{ padding: '0 20px 20px', borderBottom: '1px solid #2a2a2a' }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: '#d4a843', margin: 0 }}>ONYX</h1>
          <p style={{ fontSize: 12, color: '#888', margin: '4px 0 0' }}>{businessName}</p>
        </div>

        <div style={{ flex: 1, padding: '12px 8px' }}>
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px',
              borderRadius: 8, textDecoration: 'none', fontSize: 14, marginBottom: 2,
              color: isActive ? '#d4a843' : '#aaa',
              background: isActive ? '#2a2a1a' : 'transparent',
            })}>
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </div>

        <button onClick={logout} style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: '10px 20px',
          border: 'none', background: 'none', color: '#666', cursor: 'pointer', fontSize: 14,
        }}>
          <LogOut size={18} /> Logout
        </button>
      </nav>

      {/* Main content */}
      <main style={{ flex: 1, padding: 24, overflowY: 'auto' }}>
        <Outlet />
      </main>
    </div>
  )
}
