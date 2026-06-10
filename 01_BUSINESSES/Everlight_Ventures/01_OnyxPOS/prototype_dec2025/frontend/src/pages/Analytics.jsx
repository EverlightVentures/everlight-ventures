import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  ShoppingCart,
  Package,
  AlertTriangle,
  BarChart3,
  Calendar
} from 'lucide-react'
import api from '../utils/api'
import toast from 'react-hot-toast'

export default function Analytics() {
  const [loading, setLoading] = useState(true)
  const [dashboard, setDashboard] = useState(null)
  const [salesTrend, setSalesTrend] = useState([])
  const [topSelling, setTopSelling] = useState([])
  const [trendDays, setTrendDays] = useState(30)

  useEffect(() => {
    fetchAnalytics()
  }, [trendDays])

  const fetchAnalytics = async () => {
    try {
      setLoading(true)
      const [dashboardRes, trendRes, topSellingRes] = await Promise.all([
        api.get('/analytics/dashboard'),
        api.get(`/analytics/sales-trend?days=${trendDays}`),
        api.get(`/analytics/top-selling?days=${trendDays}&limit=10`)
      ])

      setDashboard(dashboardRes.data)
      setSalesTrend(trendRes.data.trend)
      setTopSelling(topSellingRes.data.top_selling)
    } catch (error) {
      toast.error('Failed to load analytics')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Analytics</h1>
          <p className="text-gray-400">Loading your business insights...</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-24 bg-dark-700 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  const metrics = [
    {
      label: "Today's Revenue",
      value: `$${dashboard?.today?.revenue?.toFixed(2) || '0.00'}`,
      change: '+12.5%',
      icon: DollarSign,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10'
    },
    {
      label: "Today's Transactions",
      value: dashboard?.today?.transaction_count || 0,
      change: '+8.2%',
      icon: ShoppingCart,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10'
    },
    {
      label: 'MTD Revenue',
      value: `$${dashboard?.month_to_date?.revenue?.toFixed(2) || '0.00'}`,
      change: '+18.7%',
      icon: TrendingUp,
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10'
    },
    {
      label: 'Low Stock Items',
      value: dashboard?.inventory?.low_stock_count || 0,
      change: dashboard?.inventory?.low_stock_count > 0 ? 'Needs attention' : 'All good',
      icon: AlertTriangle,
      color: dashboard?.inventory?.low_stock_count > 0 ? 'text-amber-500' : 'text-green-500',
      bgColor: dashboard?.inventory?.low_stock_count > 0 ? 'bg-amber-500/10' : 'bg-green-500/10'
    }
  ]

  // Calculate max revenue for chart scaling
  const maxRevenue = Math.max(...salesTrend.map(d => d.revenue), 1)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Analytics</h1>
          <p className="text-gray-400">Real-time business insights and trends</p>
        </div>
        <button
          onClick={fetchAnalytics}
          className="btn-secondary flex items-center space-x-2"
        >
          <BarChart3 className="w-4 h-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((metric, index) => (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="card group hover:border-dark-500 transition-all duration-300"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-sm text-gray-400 mb-2">{metric.label}</p>
                <p className="text-2xl font-bold text-white mb-1">{metric.value}</p>
                <p className={`text-sm ${metric.color}`}>{metric.change}</p>
              </div>
              <div className={`p-3 rounded-lg ${metric.bgColor} group-hover:scale-110 transition-transform`}>
                <metric.icon className={`w-6 h-6 ${metric.color}`} />
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Sales Trend Chart */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="card"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white flex items-center">
            <TrendingUp className="w-5 h-5 mr-2 text-blue-500" />
            Sales Trend
          </h2>
          <div className="flex space-x-2">
            {[7, 30, 90].map((days) => (
              <button
                key={days}
                onClick={() => setTrendDays(days)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  trendDays === days
                    ? 'bg-blue-500 text-white'
                    : 'bg-dark-700 text-gray-400 hover:bg-dark-600'
                }`}
              >
                {days}d
              </button>
            ))}
          </div>
        </div>

        {salesTrend.length === 0 ? (
          <div className="text-center py-12">
            <Calendar className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No sales data for this period</p>
            <p className="text-gray-500 text-sm mt-2">Make some sales to see trends</p>
          </div>
        ) : (
          <div className="space-y-3">
            {salesTrend.map((day, index) => {
              const barWidth = maxRevenue > 0 ? (day.revenue / maxRevenue) * 100 : 0
              return (
                <div key={index} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">
                      {new Date(day.date).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric'
                      })}
                    </span>
                    <div className="flex items-center space-x-4">
                      <span className="text-gray-500">{day.transaction_count} sales</span>
                      <span className="text-white font-medium">${day.revenue.toFixed(2)}</span>
                    </div>
                  </div>
                  <div className="bg-dark-700 rounded-full h-2 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${barWidth}%` }}
                      transition={{ delay: index * 0.02, duration: 0.5 }}
                      className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                    />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </motion.div>

      {/* Top Selling Items */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="card"
      >
        <h2 className="text-xl font-bold text-white mb-6 flex items-center">
          <Package className="w-5 h-5 mr-2 text-green-500" />
          Top Selling Items (Last {trendDays} Days)
        </h2>

        {topSelling.length === 0 ? (
          <div className="text-center py-12">
            <Package className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No sales data available</p>
            <p className="text-gray-500 text-sm mt-2">Start making sales to see top products</p>
          </div>
        ) : (
          <div className="space-y-3">
            {topSelling.map((item, index) => {
              const maxQuantity = Math.max(...topSelling.map(i => i.quantity_sold), 1)
              const barWidth = (item.quantity_sold / maxQuantity) * 100

              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-dark-700/50 rounded-lg p-4 hover:bg-dark-700 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-3">
                      <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 text-white text-sm font-bold">
                        {index + 1}
                      </div>
                      <div>
                        <p className="text-white font-medium">{item.item_name}</p>
                        <p className="text-sm text-gray-400">
                          {item.quantity_sold} units sold
                        </p>
                      </div>
                    </div>
                    <p className="text-green-500 font-medium">
                      ${item.revenue.toFixed(2)}
                    </p>
                  </div>
                  <div className="bg-dark-600 rounded-full h-2 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${barWidth}%` }}
                      transition={{ delay: index * 0.05, duration: 0.5 }}
                      className="h-full bg-gradient-to-r from-green-500 to-emerald-500 rounded-full"
                    />
                  </div>
                </motion.div>
              )
            })}
          </div>
        )}
      </motion.div>

      {/* Inventory Summary */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="grid grid-cols-1 md:grid-cols-2 gap-6"
      >
        <div className="card">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center">
            <Package className="w-5 h-5 mr-2 text-blue-500" />
            Inventory Value
          </h2>
          <p className="text-3xl font-bold text-white">
            ${dashboard?.inventory?.total_value?.toFixed(2) || '0.00'}
          </p>
          <p className="text-sm text-gray-400 mt-2">Total value of all inventory</p>
        </div>

        <div className="card">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center">
            <AlertTriangle className="w-5 h-5 mr-2 text-amber-500" />
            Stock Alerts
          </h2>
          <p className="text-3xl font-bold text-white">
            {dashboard?.inventory?.low_stock_count || 0}
          </p>
          <p className="text-sm text-gray-400 mt-2">
            {dashboard?.inventory?.low_stock_count > 0
              ? 'Items below reorder point'
              : 'All items adequately stocked'}
          </p>
        </div>
      </motion.div>
    </div>
  )
}
