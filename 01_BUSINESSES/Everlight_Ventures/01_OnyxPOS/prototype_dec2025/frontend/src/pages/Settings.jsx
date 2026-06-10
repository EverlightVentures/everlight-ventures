import { useState, useEffect } from 'react'
import { Settings as SettingsIcon, CreditCard, DollarSign, CheckCircle, AlertCircle, ExternalLink } from 'lucide-react'
import { motion } from 'framer-motion'
import api from '../utils/api'
import toast from 'react-hot-toast'

export default function Settings() {
  const [stripeStatus, setStripeStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [connecting, setConnecting] = useState(false)

  useEffect(() => {
    loadStripeStatus()
  }, [])

  const loadStripeStatus = async () => {
    try {
      const response = await api.get('/connect/connect-status')
      setStripeStatus(response.data)
    } catch (error) {
      console.error('Failed to load Stripe status:', error)
    } finally {
      setLoading(false)
    }
  }

  const connectStripe = async () => {
    try {
      setConnecting(true)
      const response = await api.post('/connect/connect-account')

      // Redirect to Stripe OAuth
      if (response.data.onboarding_url) {
        window.location.href = response.data.onboarding_url
      } else {
        toast.success('Stripe account already connected!')
        loadStripeStatus()
      }
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to connect Stripe')
    } finally {
      setConnecting(false)
    }
  }

  const openStripeDashboard = async () => {
    try {
      const response = await api.get('/connect/dashboard-link')
      window.open(response.data.url, '_blank')
    } catch (error) {
      toast.error('Failed to open Stripe dashboard')
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="animate-pulse">
            <div className="h-8 bg-dark-700 rounded w-32 mb-2"></div>
            <div className="h-4 bg-dark-700 rounded w-48"></div>
          </div>
        </div>
        <div className="card animate-pulse">
          <div className="h-64 bg-dark-700 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Settings</h1>
          <p className="text-gray-400">Configure your POS system and payments</p>
        </div>
      </motion.div>

      {/* Stripe Connect Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card"
      >
        <div className="flex items-center space-x-3 mb-6">
          <div className="w-12 h-12 bg-gradient-to-br from-neon-blue to-neon-purple rounded-lg flex items-center justify-center">
            <CreditCard className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Payment Processing</h2>
            <p className="text-gray-400 text-sm">Connect Stripe to accept card payments</p>
          </div>
        </div>

        {!stripeStatus?.connected ? (
          <div className="space-y-4">
            <div className="bg-dark-800 border border-dark-600 rounded-lg p-6">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <AlertCircle className="w-6 h-6 text-amber-500" />
                </div>
                <div className="flex-1">
                  <h3 className="text-white font-semibold mb-2">Stripe Account Not Connected</h3>
                  <p className="text-gray-400 text-sm mb-4">
                    Connect your Stripe account to accept credit card payments at your POS.
                    Your customers will be able to pay with cards, and funds will be deposited directly to your bank account.
                  </p>
                  <div className="flex flex-col sm:flex-row gap-3">
                    <button
                      onClick={connectStripe}
                      disabled={connecting}
                      className="btn-primary flex items-center justify-center space-x-2"
                    >
                      {connecting ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          <span>Connecting...</span>
                        </>
                      ) : (
                        <>
                          <CreditCard className="w-5 h-5" />
                          <span>Connect Stripe Account</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Benefits */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
              <div className="bg-dark-800 border border-dark-600 rounded-lg p-4">
                <div className="w-10 h-10 bg-neon-green/10 rounded-lg flex items-center justify-center mb-3">
                  <DollarSign className="w-5 h-5 text-neon-green" />
                </div>
                <h4 className="text-white font-semibold text-sm mb-1">Fast Deposits</h4>
                <p className="text-gray-400 text-xs">Money in your bank in 2-7 days</p>
              </div>
              <div className="bg-dark-800 border border-dark-600 rounded-lg p-4">
                <div className="w-10 h-10 bg-neon-blue/10 rounded-lg flex items-center justify-center mb-3">
                  <CheckCircle className="w-5 h-5 text-neon-blue" />
                </div>
                <h4 className="text-white font-semibold text-sm mb-1">Secure Processing</h4>
                <p className="text-gray-400 text-xs">Bank-level security & fraud protection</p>
              </div>
              <div className="bg-dark-800 border border-dark-600 rounded-lg p-4">
                <div className="w-10 h-10 bg-neon-purple/10 rounded-lg flex items-center justify-center mb-3">
                  <CreditCard className="w-5 h-5 text-neon-purple" />
                </div>
                <h4 className="text-white font-semibold text-sm mb-1">All Card Types</h4>
                <p className="text-gray-400 text-xs">Visa, Mastercard, Amex & more</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Connected Status */}
            <div className="bg-gradient-to-br from-neon-green/10 to-transparent border border-neon-green/30 rounded-lg p-6">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <CheckCircle className="w-6 h-6 text-neon-green" />
                </div>
                <div className="flex-1">
                  <h3 className="text-white font-semibold mb-2">Stripe Connected ✓</h3>
                  <p className="text-gray-300 text-sm mb-4">
                    Your Stripe account is active and ready to process payments.
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="bg-dark-900/50 rounded-lg p-3">
                      <p className="text-gray-400 text-xs mb-1">Account Status</p>
                      <p className="text-white font-semibold capitalize">{stripeStatus.status}</p>
                    </div>
                    <div className="bg-dark-900/50 rounded-lg p-3">
                      <p className="text-gray-400 text-xs mb-1">Platform Fee</p>
                      <p className="text-white font-semibold">{stripeStatus.platform_fee_percent}% per transaction</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Fee Breakdown */}
            <div className="bg-dark-800 border border-dark-600 rounded-lg p-6">
              <h3 className="text-white font-semibold mb-4">Fee Breakdown</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Stripe Processing Fee</span>
                  <span className="text-white font-medium">2.9% + $0.30</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">OnyxPOS Platform Fee</span>
                  <span className="text-neon-blue font-medium">{stripeStatus.platform_fee_percent}%</span>
                </div>
                <div className="border-t border-dark-600 pt-3 mt-3">
                  <div className="flex items-center justify-between">
                    <span className="text-white font-semibold">Example: $100 Sale</span>
                  </div>
                  <div className="mt-2 space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Customer Pays</span>
                      <span className="text-white">$100.00</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">- Stripe Fee</span>
                      <span className="text-red-400">-$3.20</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">- Platform Fee</span>
                      <span className="text-red-400">-${(stripeStatus.platform_fee_percent).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between font-semibold pt-1 border-t border-dark-600">
                      <span className="text-neon-green">You Receive</span>
                      <span className="text-neon-green">${(100 - 3.20 - stripeStatus.platform_fee_percent).toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={openStripeDashboard}
                className="btn-secondary flex items-center justify-center space-x-2"
              >
                <ExternalLink className="w-5 h-5" />
                <span>Open Stripe Dashboard</span>
              </button>
            </div>
          </div>
        )}
      </motion.div>

      {/* Other Settings Sections (Coming Soon) */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
      >
        <div className="card text-center py-8">
          <SettingsIcon className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <h3 className="text-white font-semibold mb-1">Tax Settings</h3>
          <p className="text-gray-500 text-sm">Coming soon</p>
        </div>
        <div className="card text-center py-8">
          <SettingsIcon className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <h3 className="text-white font-semibold mb-1">Receipt Templates</h3>
          <p className="text-gray-500 text-sm">Coming soon</p>
        </div>
        <div className="card text-center py-8">
          <SettingsIcon className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <h3 className="text-white font-semibold mb-1">Team Management</h3>
          <p className="text-gray-500 text-sm">Coming soon</p>
        </div>
      </motion.div>
    </div>
  )
}
