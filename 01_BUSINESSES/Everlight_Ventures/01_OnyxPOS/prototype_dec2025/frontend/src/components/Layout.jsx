import { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  ShoppingCart,
  Package,
  BarChart3,
  Settings,
  CreditCard,
  LogOut,
  Menu,
  X,
  Zap,
  DollarSign,
  Clock,
  Users,
  Calendar,
  Wallet,
  Palmtree,
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { motion, AnimatePresence } from 'framer-motion'

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isDesktop, setIsDesktop] = useState(false)

  // Track viewport to drive auto-hide behavior.
  useEffect(() => {
    const handleResize = () => {
      setIsDesktop(window.innerWidth >= 1024)
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])
  useEffect(() => {
    if (!isDesktop) {
      setSidebarOpen(false)
    }
  }, [isDesktop])
  const location = useLocation()
  const navigate = useNavigate()
  const { user, tenant, logout } = useAuthStore()

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Sales', href: '/sales', icon: ShoppingCart },
    { name: 'Inventory', href: '/inventory', icon: Package },
    { name: 'Time Clock', href: '/timeclock', icon: Clock },
    { name: 'Employees', href: '/employees', icon: Users },
    { name: 'Schedule', href: '/schedule', icon: Calendar },
    { name: 'Time Off', href: '/timeoff', icon: Palmtree },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { name: 'Settings', href: '/settings', icon: Settings },
  ]

  // Add payroll, billing and platform revenue for owners/managers
  if (user?.role === 'owner' || user?.role === 'manager') {
    navigation.splice(6, 0, { name: 'Payroll', href: '/payroll', icon: Wallet })
  }

  if (user?.role === 'owner') {
    navigation.push({ name: 'Billing', href: '/billing', icon: CreditCard })
    navigation.push({ name: '💰 Your Profit', href: '/platform-revenue', icon: DollarSign })
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-dark-950 flex">
      {/* Desktop hover trigger to reveal sidebar */}
      {isDesktop && !sidebarOpen && (
        <div
          onMouseEnter={() => setSidebarOpen(true)}
          className="fixed left-0 top-0 h-full w-3 z-40"
        />
      )}
      {/* Overlay for mobile */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSidebarOpen(false)}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30"
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.aside
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ type: 'spring', damping: 20 }}
            onMouseLeave={() => {
              if (isDesktop) {
                setSidebarOpen(false)
              }
            }}
            className="w-[280px] bg-dark-900 border-r border-dark-700 flex flex-col fixed h-full z-40"
          >
            {/* Logo */}
            <div className="p-6 border-b border-dark-700">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-neon-blue to-neon-purple rounded-lg flex items-center justify-center">
                  <Zap className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gradient from-neon-blue to-neon-purple">
                    OnyxPOS
                  </h1>
                  <p className="text-xs text-gray-500">{tenant?.business_name}</p>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-4 space-y-1">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href
                const Icon = item.icon

                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`
                      flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200
                      ${isActive
                        ? 'bg-neon-blue text-white shadow-lg shadow-neon-blue/50'
                        : 'text-gray-400 hover:bg-dark-800 hover:text-gray-200'
                      }
                    `}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{item.name}</span>
                  </Link>
                )
              })}
            </nav>

            {/* User info */}
            <div className="p-4 border-t border-dark-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-neon-purple to-neon-pink rounded-full flex items-center justify-center">
                    <span className="text-sm font-bold text-white">
                      {user?.first_name?.[0]}{user?.last_name?.[0]}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-200">{user?.full_name}</p>
                    <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
                  </div>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 text-gray-400 hover:text-gray-200 hover:bg-dark-800 rounded-lg transition-colors"
                  title="Logout"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main content */}
      <div className="flex-1 flex flex-col transition-all duration-300">
        {/* Top bar */}
        <header className="h-16 bg-dark-900 border-b border-dark-700 flex items-center justify-between px-6">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 text-gray-400 hover:text-gray-200 hover:bg-dark-800 rounded-lg transition-colors"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          <div className="flex items-center space-x-4">
            {/* Trial banner for trial users */}
            {tenant?.subscription_status === 'trial' && (
              <div className="flex items-center space-x-2 px-4 py-2 bg-neon-amber/10 border border-neon-amber/30 rounded-lg">
                <Zap className="w-4 h-4 text-neon-amber" />
                <span className="text-sm text-neon-amber font-medium">
                  {tenant?.trial_days_remaining} days left in trial
                </span>
              </div>
            )}

            {/* User info & logout */}
            <div className="flex items-center space-x-3">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium text-gray-200">{user?.first_name} {user?.last_name}</p>
                <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center space-x-2 px-4 py-2 bg-dark-800 hover:bg-dark-700 text-gray-300 hover:text-white rounded-lg transition-colors border border-dark-600"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  )
}
