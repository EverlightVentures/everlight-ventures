import { useState, useEffect } from 'react'
import { DollarSign, TrendingUp, Users, CreditCard, Building2, ArrowUpRight } from 'lucide-react'
import { motion } from 'framer-motion'
import api from '../utils/api'
import toast from 'react-hot-toast'

export default function PlatformRevenue() {
  const [revenue, setRevenue] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedPeriod, setSelectedPeriod] = useState(30)

  useEffect(() => {
    loadRevenue()
  }, [selectedPeriod])

  const loadRevenue = async () => {
    try {
      setLoading(true)
      const response = await api.get(`/connect/platform-revenue?days=${selectedPeriod}`)
      setRevenue(response.data)
    } catch (error) {
      toast.error('Failed to load revenue data')
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
            <div className="h-8 bg-dark-700 rounded w-64 mb-2"></div>
            <div className="h-4 bg-dark-700 rounded w-96"></div>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-32 bg-dark-700 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  const stats = [
    {
      name: 'Platform Fees Collected',
      value: `$${revenue?.platform_fees_collected?.toLocaleString() || '0.00'}`,
      change: `Last ${selectedPeriod} days`,
      icon: DollarSign,
      gradient: 'from-neon-green to-neon-cyan',
    },
    {
      name: 'Subscription Revenue',
      value: `$${revenue?.monthly_subscription_revenue?.toLocaleString() || '0'}/mo`,
      change: 'Monthly recurring',
      icon: CreditCard,
      gradient: 'from-neon-blue to-neon-purple',
    },
    {
      name: 'Total Revenue',
      value: `$${revenue?.total_monthly_revenue?.toLocaleString() || '0'}`,
      change: 'Fees + Subscriptions',
      icon: TrendingUp,
      gradient: 'from-neon-purple to-neon-pink',
    },
    {
      name: 'Active Tenants',
      value: revenue?.tenant_count || 0,
      change: `${revenue?.total_transactions || 0} transactions`,
      icon: Users,
      gradient: 'from-neon-amber to-neon-pink',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">💰 Platform Revenue</h1>
          <p className="text-gray-400">Your earnings from OnyxPOS platform fees and subscriptions</p>
        </div>

        {/* Period Selector */}
        <div className="flex items-center space-x-2 bg-dark-800 rounded-lg p-1">
          {[7, 30, 90, 365].map((days) => (
            <button
              key={days}
              onClick={() => setSelectedPeriod(days)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                selectedPeriod === days
                  ? 'bg-neon-blue text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {days === 365 ? '1Y' : `${days}D`}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ y: -5 }}
            className="stat-card group relative overflow-hidden"
          >
            <div className="flex items-start justify-between mb-4">
              <div className={`w-12 h-12 bg-gradient-to-br ${stat.gradient} rounded-lg flex items-center justify-center shadow-lg`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
            </div>
            <div>
              <p className="text-gray-400 text-sm font-medium mb-1">{stat.name}</p>
              <p className="text-3xl font-bold text-white mb-2">{stat.value}</p>
              <p className="text-sm text-gray-500">{stat.change}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Annual Projections */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="card bg-gradient-to-br from-neon-purple/10 to-transparent border-neon-purple/30"
      >
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-white mb-1">📈 Annual Projections</h2>
            <p className="text-gray-400 text-sm">Based on current performance</p>
          </div>
          <div className="w-12 h-12 bg-gradient-to-br from-neon-purple to-neon-pink rounded-lg flex items-center justify-center">
            <ArrowUpRight className="w-6 h-6 text-white" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-dark-900/50 rounded-lg p-4">
            <p className="text-gray-400 text-sm mb-1">Annual Transaction Fees</p>
            <p className="text-2xl font-bold text-white mb-1">
              ${revenue?.projections?.annual_transaction_fees?.toLocaleString() || '0'}
            </p>
            <p className="text-xs text-neon-green">From payment processing</p>
          </div>
          <div className="bg-dark-900/50 rounded-lg p-4">
            <p className="text-gray-400 text-sm mb-1">Annual Subscriptions</p>
            <p className="text-2xl font-bold text-white mb-1">
              ${revenue?.projections?.annual_subscription_revenue?.toLocaleString() || '0'}
            </p>
            <p className="text-xs text-neon-blue">Monthly recurring × 12</p>
          </div>
          <div className="bg-dark-900/50 rounded-lg p-4 border-2 border-neon-green/30">
            <p className="text-gray-400 text-sm mb-1">Total Annual Revenue</p>
            <p className="text-2xl font-bold text-neon-green mb-1">
              ${revenue?.projections?.total_annual_revenue?.toLocaleString() || '0'}
            </p>
            <p className="text-xs text-gray-400">Your yearly profit</p>
          </div>
        </div>
      </motion.div>

      {/* Tenant Breakdown */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="card"
      >
        <h2 className="text-xl font-bold text-white mb-4">Tenant Performance</h2>

        {revenue?.tenants && revenue.tenants.length > 0 ? (
          <div className="space-y-3">
            {revenue.tenants.map((tenant, index) => (
              <div
                key={index}
                className="bg-dark-800 border border-dark-600 rounded-lg p-4 hover:border-dark-500 transition-colors"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-neon-blue to-neon-purple rounded-lg flex items-center justify-center">
                      <Building2 className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <p className="text-white font-semibold">{tenant.business_name}</p>
                      <p className="text-gray-400 text-sm capitalize">{tenant.plan_tier} Plan</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-neon-green font-bold text-lg">
                      ${tenant.platform_fees.toFixed(2)}
                    </p>
                    <p className="text-gray-400 text-xs">{tenant.fee_percent}% fee</p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t border-dark-600">
                  <div>
                    <p className="text-gray-500 text-xs">Transactions</p>
                    <p className="text-white font-medium">{tenant.transaction_count}</p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-xs">Total Sales</p>
                    <p className="text-white font-medium">${tenant.total_sales.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-xs">Your Profit</p>
                    <p className="text-neon-green font-medium">${tenant.platform_fees.toFixed(2)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <Users className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No tenants with transactions yet</p>
            <p className="text-gray-500 text-sm mt-1">Revenue data will appear once tenants start processing payments</p>
          </div>
        )}
      </motion.div>

      {/* Growth Tips */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="card bg-gradient-to-br from-neon-blue/10 to-transparent border-neon-blue/30"
      >
        <h2 className="text-xl font-bold text-white mb-4">💡 Growth Opportunities</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 bg-neon-green/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
              <TrendingUp className="w-4 h-4 text-neon-green" />
            </div>
            <div>
              <h3 className="text-white font-semibold mb-1">Increase Transaction Volume</h3>
              <p className="text-gray-400 text-sm">
                Help existing tenants grow their sales through marketing tools and features
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 bg-neon-blue/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
              <Users className="w-4 h-4 text-neon-blue" />
            </div>
            <div>
              <h3 className="text-white font-semibold mb-1">Acquire More Tenants</h3>
              <p className="text-gray-400 text-sm">
                Each new business = ${((29 + 79 + 199) / 3).toFixed(0)}/mo subscription + transaction fees
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 bg-neon-purple/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
              <ArrowUpRight className="w-4 h-4 text-neon-purple" />
            </div>
            <div>
              <h3 className="text-white font-semibold mb-1">Upsell to Higher Plans</h3>
              <p className="text-gray-400 text-sm">
                Encourage upgrades with premium features and lower transaction fees
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 bg-neon-amber/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
              <DollarSign className="w-4 h-4 text-neon-amber" />
            </div>
            <div>
              <h3 className="text-white font-semibold mb-1">Add Premium Features</h3>
              <p className="text-gray-400 text-sm">
                Charge extra for advanced analytics, multi-location, or API access
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
