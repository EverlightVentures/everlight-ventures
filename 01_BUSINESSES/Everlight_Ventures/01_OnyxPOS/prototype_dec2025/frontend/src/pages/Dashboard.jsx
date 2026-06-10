import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../utils/api'
import toast from 'react-hot-toast'
import {
  DollarSign,
  ShoppingCart,
  Package,
  TrendingUp,
  AlertCircle,
  ArrowRight,
  Sparkles,
} from 'lucide-react'
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { motion } from 'framer-motion'
import { format } from 'date-fns'

const COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#10b981', '#f59e0b']

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [salesTrend, setSalesTrend] = useState([])
  const [topSelling, setTopSelling] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      const [metricsRes, trendRes, topSellingRes] = await Promise.all([
        api.get('/analytics/dashboard'),
        api.get('/analytics/sales-trend?days=7'),
        api.get('/analytics/top-selling?limit=5&days=30'),
      ])

      setMetrics(metricsRes.data)
      setSalesTrend(trendRes.data.trend)
      setTopSelling(topSellingRes.data.top_selling)
    } catch (error) {
      toast.error('Failed to load dashboard data')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="animate-pulse">
            <div className="h-8 bg-dark-700 rounded w-48 mb-2"></div>
            <div className="h-4 bg-dark-700 rounded w-64"></div>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 bg-dark-700 rounded-lg"></div>
                <div className="w-5 h-5 bg-dark-700 rounded"></div>
              </div>
              <div className="h-4 bg-dark-700 rounded w-24 mb-2"></div>
              <div className="h-8 bg-dark-700 rounded w-32 mb-2"></div>
              <div className="h-3 bg-dark-700 rounded w-20"></div>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card animate-pulse">
            <div className="h-6 bg-dark-700 rounded w-40 mb-6"></div>
            <div className="h-64 bg-dark-700 rounded"></div>
          </div>
          <div className="card animate-pulse">
            <div className="h-6 bg-dark-700 rounded w-40 mb-6"></div>
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-dark-700 rounded-lg"></div>
                  <div className="flex-1">
                    <div className="h-4 bg-dark-700 rounded w-32 mb-2"></div>
                    <div className="h-3 bg-dark-700 rounded w-20"></div>
                  </div>
                  <div className="h-4 bg-dark-700 rounded w-16"></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  const stats = [
    {
      name: "Today's Revenue",
      value: `$${metrics?.today?.revenue?.toFixed(2) || '0.00'}`,
      change: '+12.5%',
      icon: DollarSign,
      color: 'from-neon-green to-neon-cyan',
      gradient: 'neon-green',
    },
    {
      name: 'Transactions',
      value: metrics?.today?.transaction_count || 0,
      change: '+8.2%',
      icon: ShoppingCart,
      color: 'from-neon-blue to-neon-purple',
      gradient: 'neon-blue',
    },
    {
      name: 'Low Stock Items',
      value: metrics?.inventory?.low_stock_count || 0,
      change: metrics?.inventory?.low_stock_count > 0 ? 'Needs attention' : 'All good',
      icon: AlertCircle,
      color: 'from-neon-amber to-neon-pink',
      gradient: 'neon-amber',
    },
    {
      name: 'Inventory Value',
      value: `$${(metrics?.inventory?.total_value || 0).toLocaleString()}`,
      change: '+5.1%',
      icon: Package,
      color: 'from-neon-purple to-neon-pink',
      gradient: 'neon-purple',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Dashboard</h1>
          <p className="text-gray-400">Welcome back! Here's what's happening today.</p>
        </div>
        <Link to="/sales" className="btn-primary flex items-center space-x-2">
          <ShoppingCart className="w-5 h-5" />
          <span>New Sale</span>
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ y: -5, transition: { duration: 0.2 } }}
            className="stat-card group relative overflow-hidden"
            style={{
              '--gradient-from': `var(--${stat.gradient})`,
              '--gradient-to': `var(--${stat.gradient})`,
            }}
          >
            {/* Animated background gradient */}
            <motion.div
              className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300"
              style={{
                background: `linear-gradient(135deg, var(--${stat.gradient}) 0%, transparent 100%)`,
              }}
            />

            <div className="flex items-start justify-between mb-4 relative z-10">
              <motion.div
                whileHover={{ rotate: 360, scale: 1.1 }}
                transition={{ duration: 0.6 }}
                className={`w-12 h-12 bg-gradient-to-br ${stat.color} rounded-lg flex items-center justify-center shadow-lg`}
              >
                <stat.icon className="w-6 h-6 text-white" />
              </motion.div>
              <motion.div
                animate={{
                  rotate: [0, 10, -10, 0],
                  scale: [1, 1.1, 1],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  repeatDelay: 3,
                }}
              >
                <Sparkles className="w-5 h-5 text-gray-600 group-hover:text-neon-blue transition-colors" />
              </motion.div>
            </div>
            <div className="relative z-10">
              <p className="text-gray-400 text-sm font-medium mb-1">{stat.name}</p>
              <motion.p
                initial={{ scale: 1 }}
                animate={{ scale: 1 }}
                whileHover={{ scale: 1.05 }}
                className="text-3xl font-bold text-white mb-2"
              >
                {stat.value}
              </motion.p>
              <div className="flex items-center space-x-2">
                <motion.div
                  animate={{ y: [0, -3, 0] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                >
                  <TrendingUp className="w-4 h-4 text-neon-green" />
                </motion.div>
                <span className="text-sm text-neon-green font-medium">{stat.change}</span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sales Trend */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-white">Sales Trend (7 Days)</h2>
            <Link to="/analytics" className="text-neon-blue hover:text-neon-cyan transition-colors text-sm font-medium flex items-center space-x-1">
              <span>View details</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={salesTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d2d2d" />
                <XAxis
                  dataKey="date"
                  stroke="#737373"
                  tickFormatter={(date) => format(new Date(date), 'MMM dd')}
                />
                <YAxis stroke="#737373" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1a1a1a',
                    border: '1px solid #2d2d2d',
                    borderRadius: '8px',
                  }}
                  labelStyle={{ color: '#fff' }}
                />
                <Line
                  type="monotone"
                  dataKey="revenue"
                  stroke="#3b82f6"
                  strokeWidth={3}
                  dot={{ fill: '#3b82f6', r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Top Selling Products */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-white">Top Selling (30 Days)</h2>
            <Link to="/analytics" className="text-neon-blue hover:text-neon-cyan transition-colors text-sm font-medium flex items-center space-x-1">
              <span>View all</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="space-y-4">
            {topSelling.map((item, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center bg-gradient-to-br ${
                    index === 0 ? 'from-neon-blue to-neon-purple' :
                    index === 1 ? 'from-neon-purple to-neon-pink' :
                    'from-neon-green to-neon-cyan'
                  }`}>
                    <span className="text-white font-bold">{index + 1}</span>
                  </div>
                  <div>
                    <p className="text-white font-medium">{item.item_name}</p>
                    <p className="text-gray-400 text-sm">{item.quantity_sold} sold</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-white font-bold">${item.revenue.toFixed(2)}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="card"
      >
        <h2 className="text-xl font-bold text-white mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link to="/sales" className="p-4 bg-dark-800 hover:bg-dark-700 rounded-lg border border-dark-600 hover:border-neon-blue transition-all group">
            <ShoppingCart className="w-8 h-8 text-neon-blue mb-2 group-hover:scale-110 transition-transform" />
            <p className="text-white font-medium">New Sale</p>
            <p className="text-gray-400 text-sm">Process a transaction</p>
          </Link>
          <Link to="/inventory" className="p-4 bg-dark-800 hover:bg-dark-700 rounded-lg border border-dark-600 hover:border-neon-purple transition-all group">
            <Package className="w-8 h-8 text-neon-purple mb-2 group-hover:scale-110 transition-transform" />
            <p className="text-white font-medium">Add Product</p>
            <p className="text-gray-400 text-sm">Manage inventory</p>
          </Link>
          <Link to="/analytics" className="p-4 bg-dark-800 hover:bg-dark-700 rounded-lg border border-dark-600 hover:border-neon-green transition-all group">
            <TrendingUp className="w-8 h-8 text-neon-green mb-2 group-hover:scale-110 transition-transform" />
            <p className="text-white font-medium">View Reports</p>
            <p className="text-gray-400 text-sm">Analyze performance</p>
          </Link>
        </div>
      </motion.div>
    </div>
  )
}
