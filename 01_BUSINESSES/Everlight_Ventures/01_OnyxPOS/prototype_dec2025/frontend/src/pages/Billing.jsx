import { useState, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'
import { CreditCard, Zap, Crown, ExternalLink, TrendingUp, Users, MapPin } from 'lucide-react'
import api from '../utils/api'
import toast from 'react-hot-toast'

export default function Billing() {
  const { tenant } = useAuthStore()
  const [subscriptionStatus, setSubscriptionStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  const plans = [
    {
      name: 'Starter',
      tier: 'starter',
      price: 29,
      features: ['1 location', '2 users', '1,000 transactions/month', 'Basic reporting'],
    },
    {
      name: 'Professional',
      tier: 'professional',
      price: 79,
      features: ['3 locations', '10 users', '10,000 transactions/month', 'Advanced analytics', 'Crypto payments'],
      popular: true,
    },
    {
      name: 'Enterprise',
      tier: 'enterprise',
      price: 199,
      features: ['Unlimited locations', 'Unlimited users', 'Unlimited transactions', 'API access', 'Priority support'],
    },
  ]

  useEffect(() => {
    fetchSubscriptionStatus()
  }, [])

  const fetchSubscriptionStatus = async () => {
    try {
      const response = await api.get('/billing/subscription-status')
      setSubscriptionStatus(response.data)
    } catch (error) {
      console.error('Failed to fetch subscription status:', error)
      toast.error('Failed to load subscription details')
    } finally {
      setLoading(false)
    }
  }

  const handleUpgrade = async (planTier) => {
    if (tenant?.plan_tier === planTier) {
      toast.error('You are already on this plan')
      return
    }

    try {
      const response = await api.post('/billing/create-checkout-session', {
        plan_tier: planTier,
        success_url: `${window.location.origin}/billing?success=true`,
        cancel_url: `${window.location.origin}/billing?canceled=true`,
      })

      // Redirect to Stripe Checkout
      window.location.href = response.data.checkout_url
    } catch (error) {
      console.error('Failed to create checkout session:', error)
      toast.error('Failed to start checkout. Please try again.')
    }
  }

  const handleManageBilling = async () => {
    try {
      const response = await api.post('/billing/create-portal-session', {
        return_url: window.location.href,
      })

      // Redirect to Stripe Customer Portal
      window.location.href = response.data.portal_url
    } catch (error) {
      console.error('Failed to open billing portal:', error)
      toast.error('Failed to open billing portal. Please try again.')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-neon-blue"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">Billing & Subscription</h1>
        <p className="text-gray-400">Manage your plan and payment method</p>
      </div>

      {/* Current Plan */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white">Current Plan</h2>
          <div className="flex items-center space-x-3">
            <div className="px-4 py-2 bg-neon-blue/20 border border-neon-blue/30 rounded-lg">
              <span className="text-neon-blue font-medium capitalize">{subscriptionStatus?.plan_tier}</span>
            </div>
            {subscriptionStatus?.subscription_status === 'active' && (
              <button
                onClick={handleManageBilling}
                className="btn-secondary flex items-center space-x-2"
              >
                <CreditCard className="w-4 h-4" />
                <span>Manage Billing</span>
                <ExternalLink className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {subscriptionStatus?.subscription_status === 'trial' && (
          <div className="p-4 bg-neon-amber/10 border border-neon-amber/30 rounded-lg flex items-center space-x-3 mb-4">
            <Zap className="w-5 h-5 text-neon-amber" />
            <div>
              <p className="text-neon-amber font-medium">{subscriptionStatus?.trial_days_remaining} days left in your free trial</p>
              <p className="text-gray-400 text-sm">Choose a plan below to continue after your trial ends</p>
            </div>
          </div>
        )}

        {/* Usage Stats */}
        {subscriptionStatus?.usage && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
            <div className="p-4 bg-dark-800 rounded-lg border border-dark-600">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-neon-blue/20 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-neon-blue" />
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Transactions</p>
                  <p className="text-white font-bold text-lg">
                    {subscriptionStatus.usage.transactions_this_month.toLocaleString()}
                    <span className="text-gray-500 text-sm font-normal">
                      {' / '}{subscriptionStatus.limits.max_transactions.toLocaleString()}
                    </span>
                  </p>
                </div>
              </div>
            </div>

            <div className="p-4 bg-dark-800 rounded-lg border border-dark-600">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-neon-green/20 rounded-lg flex items-center justify-center">
                  <Users className="w-5 h-5 text-neon-green" />
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Active Users</p>
                  <p className="text-white font-bold text-lg">
                    {subscriptionStatus.usage.active_users}
                    <span className="text-gray-500 text-sm font-normal">
                      {' / '}{subscriptionStatus.limits.max_users}
                    </span>
                  </p>
                </div>
              </div>
            </div>

            <div className="p-4 bg-dark-800 rounded-lg border border-dark-600">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-neon-purple/20 rounded-lg flex items-center justify-center">
                  <MapPin className="w-5 h-5 text-neon-purple" />
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Locations</p>
                  <p className="text-white font-bold text-lg">
                    {subscriptionStatus.usage.locations}
                    <span className="text-gray-500 text-sm font-normal">
                      {' / '}{subscriptionStatus.limits.max_locations}
                    </span>
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Plans */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={`card relative ${plan.popular ? 'border-2 border-neon-blue' : ''}`}
          >
            {plan.popular && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <div className="px-4 py-1 bg-neon-blue rounded-full flex items-center space-x-1">
                  <Crown className="w-4 h-4 text-white" />
                  <span className="text-white text-sm font-medium">Popular</span>
                </div>
              </div>
            )}

            <div className="text-center mb-6">
              <h3 className="text-xl font-bold text-white mb-2">{plan.name}</h3>
              <div className="flex items-baseline justify-center space-x-1">
                <span className="text-4xl font-bold text-white">${plan.price}</span>
                <span className="text-gray-400">/month</span>
              </div>
            </div>

            <ul className="space-y-3 mb-6">
              {plan.features.map((feature) => (
                <li key={feature} className="flex items-center space-x-2">
                  <div className="w-5 h-5 bg-neon-green/20 rounded-full flex items-center justify-center flex-shrink-0">
                    <div className="w-2 h-2 bg-neon-green rounded-full" />
                  </div>
                  <span className="text-gray-300 text-sm">{feature}</span>
                </li>
              ))}
            </ul>

            <button
              onClick={() => handleUpgrade(plan.tier)}
              disabled={subscriptionStatus?.plan_tier === plan.tier}
              className={`w-full ${
                plan.popular
                  ? 'btn-primary'
                  : 'btn-secondary'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {subscriptionStatus?.plan_tier === plan.tier ? 'Current Plan' : 'Upgrade'}
            </button>
          </div>
        ))}
      </div>

      {/* Payment Method */}
      <div className="card">
        <h2 className="text-xl font-bold text-white mb-4">Payment Method</h2>
        {subscriptionStatus?.subscription_status === 'active' ? (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-neon-green/20 rounded-full flex items-center justify-center mx-auto mb-3">
              <CreditCard className="w-8 h-8 text-neon-green" />
            </div>
            <p className="text-white font-medium mb-2">Payment method on file</p>
            <p className="text-gray-400 text-sm mb-4">Manage your payment methods through the billing portal</p>
            <button onClick={handleManageBilling} className="btn-secondary">
              Manage Payment Methods
            </button>
          </div>
        ) : (
          <div className="text-center py-8">
            <CreditCard className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400 mb-2">No payment method added yet</p>
            <p className="text-gray-500 text-sm mb-4">Add a payment method by subscribing to a plan</p>
          </div>
        )}
      </div>
    </div>
  )
}
