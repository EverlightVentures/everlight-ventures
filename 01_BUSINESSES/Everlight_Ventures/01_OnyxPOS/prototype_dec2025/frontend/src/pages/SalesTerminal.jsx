import { useState, useEffect } from 'react'
import { Search, Plus, Minus, Trash2, CreditCard, DollarSign, Zap, Bitcoin, X, Mail, Printer, CheckCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { format } from 'date-fns'
import api from '../utils/api'

export default function SalesTerminal() {
  const [cart, setCart] = useState([])
  const [search, setSearch] = useState('')
  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const [showReceiptModal, setShowReceiptModal] = useState(false)
  const [paymentMethod, setPaymentMethod] = useState(null)
  const [customerEmail, setCustomerEmail] = useState('')
  const [cashReceived, setCashReceived] = useState('')
  const [completedSale, setCompletedSale] = useState(null)
  const [showCryptoModal, setShowCryptoModal] = useState(false)
  const [cryptoCurrencies, setCryptoCurrencies] = useState([])
  const [exchangeRates, setExchangeRates] = useState({})
  const [selectedCrypto, setSelectedCrypto] = useState(null)
  const [cryptoCharge, setCryptoCharge] = useState(null)
  const [inventory, setInventory] = useState([])

  useEffect(() => {
    fetchInventory()
    fetchCryptoCurrencies()
    fetchExchangeRates()
  }, [])

  const fetchInventory = async () => {
    try {
      const response = await api.get('/inventory')
      setInventory(response.data.items || [])
    } catch (error) {
      console.error('Failed to fetch inventory:', error)
    }
  }

  const fetchCryptoCurrencies = async () => {
    try {
      const response = await api.get('/crypto/supported-currencies')
      setCryptoCurrencies(response.data.currencies)
    } catch (error) {
      console.error('Failed to fetch crypto currencies:', error)
    }
  }

  const fetchExchangeRates = async () => {
    try {
      const response = await api.get('/crypto/exchange-rates')
      setExchangeRates(response.data)
    } catch (error) {
      console.error('Failed to fetch exchange rates:', error)
    }
  }

  const addToCart = (product) => {
    const existing = cart.find(item => item.id === product.id)
    if (existing) {
      setCart(cart.map(item =>
        item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
      ))
    } else {
      setCart([...cart, { ...product, quantity: 1 }])
    }
    toast.success(`Added ${product.name}`)
  }

  const updateQuantity = (id, change) => {
    setCart(cart.map(item => {
      if (item.id === id) {
        const newQty = Math.max(0, item.quantity + change)
        return { ...item, quantity: newQty }
      }
      return item
    }).filter(item => item.quantity > 0))
  }

  const subtotal = cart.reduce((sum, item) => sum + (item.sell_price * item.quantity), 0)
  const tax = subtotal * 0.0725
  const total = subtotal + tax

  const handlePaymentMethodSelect = (method) => {
    if (cart.length === 0) {
      toast.error('Cart is empty')
      return
    }
    if (method === 'crypto') {
      setShowCryptoModal(true)
    } else {
      setPaymentMethod(method)
      setShowPaymentModal(true)
    }
  }

  const handleCompleteSale = async () => {
    try {
      // Validate cash payment
      if (paymentMethod === 'cash') {
        const received = parseFloat(cashReceived)
        if (!received || received < total) {
          toast.error('Insufficient cash received')
          return
        }
      }

      const saleData = {
        items: cart.map(item => ({
          item_id: item.id,
          quantity: item.quantity,
          price: item.sell_price,
        })),
        payment_method: paymentMethod,
        tax_amount: tax,
        customer_email: customerEmail || null,
        cash_received: paymentMethod === 'cash' ? parseFloat(cashReceived) : null,
      }

      const response = await api.post('/sales', saleData)

      setCompletedSale({
        ...response.data.sale,
        change: paymentMethod === 'cash' ? parseFloat(cashReceived) - total : 0,
        items: cart, // Preserve cart items for receipt
        subtotal,
        tax,
        total,
      })

      setShowPaymentModal(false)
      setShowReceiptModal(true)

      // Clear cart and form (after a delay so receipt can use cart)
      setTimeout(() => {
        setCart([])
        setCustomerEmail('')
        setCashReceived('')
        setPaymentMethod(null)
      }, 100)

      // Refresh inventory
      fetchInventory()

      toast.success('Sale completed successfully!')
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to process sale')
    }
  }

  const handlePrintReceipt = () => {
    window.print()
    toast.success('Printing receipt...')
  }

  const handleEmailReceipt = async () => {
    try {
      await api.post(`/sales/${completedSale.id}/email-receipt`, {
        email: customerEmail,
      })
      toast.success(`Receipt sent to ${customerEmail}`)
    } catch (error) {
      toast.error('Failed to send receipt')
    }
  }

  const handleNewSale = () => {
    setCompletedSale(null)
    setShowReceiptModal(false)
  }

  const handleCryptoCheckout = async () => {
    if (cart.length === 0) {
      toast.error('Cart is empty')
      return
    }
    setShowCryptoModal(true)
  }

  const createCryptoCharge = async (currency) => {
    try {
      const response = await api.post('/crypto/create-charge', {
        amount: total,
        description: `POS Sale - ${cart.length} items`,
        transaction_data: {
          items: cart.map(item => ({
            name: item.name,
            quantity: item.quantity,
            price: item.price,
          })),
        },
        redirect_url: `${window.location.origin}/sales?payment=success`,
        cancel_url: `${window.location.origin}/sales?payment=canceled`,
      })

      setCryptoCharge(response.data)
      setSelectedCrypto(currency)

      // Open Coinbase Commerce hosted page
      window.open(response.data.hosted_url, '_blank')

      toast.success(`Crypto payment initiated! Opening ${currency} payment page...`)
    } catch (error) {
      console.error('Failed to create crypto charge:', error)
      toast.error('Failed to initiate crypto payment. Please try again.')
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-180px)]">
      {/* Products */}
      <div className="lg:col-span-2 space-y-4">
        <div className="card">
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-12"
              placeholder="Search products by name or SKU..."
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {inventory.filter(item => item.stock_on_hand > 0).map((product) => (
              <motion.button
                key={product.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => addToCart(product)}
                className="p-4 bg-dark-800 hover:bg-dark-700 rounded-lg border border-dark-600 hover:border-neon-blue transition-all text-left group"
              >
                <div className="w-full h-24 bg-gradient-to-br from-neon-blue/20 to-neon-purple/20 rounded-lg mb-3 flex items-center justify-center">
                  <Zap className="w-10 h-10 text-neon-blue opacity-50" />
                </div>
                <p className="text-white font-medium mb-1">{product.name}</p>
                <p className="text-neon-blue font-bold text-lg">${product.sell_price.toFixed(2)}</p>
                <p className="text-gray-500 text-xs">{product.sku}</p>
                <p className="text-gray-600 text-xs mt-1">Stock: {product.stock_on_hand}</p>
              </motion.button>
            ))}
            {inventory.filter(item => item.stock_on_hand > 0).length === 0 && (
              <div className="col-span-full text-center py-12">
                <p className="text-gray-500">No products in stock</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Cart */}
      <div className="card flex flex-col h-full">
        <h2 className="text-xl font-bold text-white mb-4">Current Sale</h2>

        <div className="flex-1 overflow-auto space-y-2 mb-4">
          {cart.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">Cart is empty</p>
              <p className="text-gray-600 text-sm mt-1">Scan or click products to add</p>
            </div>
          ) : (
            cart.map((item) => (
              <div key={item.id} className="p-3 bg-dark-800 rounded-lg border border-dark-600">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <p className="text-white font-medium">{item.name}</p>
                    <p className="text-gray-400 text-sm">${item.sell_price.toFixed(2)} each</p>
                  </div>
                  <button
                    onClick={() => setCart(cart.filter(i => i.id !== item.id))}
                    className="text-gray-500 hover:text-red-500 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => updateQuantity(item.id, -1)}
                      className="w-8 h-8 bg-dark-700 hover:bg-dark-600 rounded-lg flex items-center justify-center text-white"
                    >
                      <Minus className="w-4 h-4" />
                    </button>
                    <span className="text-white font-medium w-8 text-center">{item.quantity}</span>
                    <button
                      onClick={() => updateQuantity(item.id, 1)}
                      className="w-8 h-8 bg-dark-700 hover:bg-dark-600 rounded-lg flex items-center justify-center text-white"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                  <p className="text-white font-bold">${(item.sell_price * item.quantity).toFixed(2)}</p>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="border-t border-dark-600 pt-4 space-y-2 mb-4">
          <div className="flex justify-between text-gray-400">
            <span>Subtotal</span>
            <span>${subtotal.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-gray-400">
            <span>Tax (7.25%)</span>
            <span>${tax.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-white text-xl font-bold">
            <span>Total</span>
            <span>${total.toFixed(2)}</span>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-gray-400 text-sm mb-3">Select Payment Method:</p>

          <button
            onClick={() => handlePaymentMethodSelect('cash')}
            disabled={cart.length === 0}
            className="btn-primary w-full flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed bg-neon-green hover:bg-neon-green/80"
          >
            <DollarSign className="w-5 h-5" />
            <span>Cash</span>
          </button>

          <button
            onClick={() => handlePaymentMethodSelect('card')}
            disabled={cart.length === 0}
            className="btn-primary w-full flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <CreditCard className="w-5 h-5" />
            <span>Credit/Debit Card</span>
          </button>

          <button
            onClick={() => handlePaymentMethodSelect('crypto')}
            disabled={cart.length === 0}
            className="btn-secondary w-full flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed border-neon-cyan hover:border-neon-cyan hover:bg-neon-cyan/10"
          >
            <Bitcoin className="w-5 h-5" />
            <span>Cryptocurrency</span>
          </button>
        </div>
      </div>

      {/* Crypto Payment Modal */}
      <AnimatePresence>
        {showCryptoModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowCryptoModal(false)}
              className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-0 flex items-center justify-center z-50 p-4"
            >
              <div className="bg-dark-900 border border-dark-600 rounded-xl p-6 max-w-2xl w-full max-h-[80vh] overflow-auto">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-white">Pay with Cryptocurrency</h2>
                    <p className="text-gray-400 mt-1">Select your preferred crypto to complete payment</p>
                  </div>
                  <button
                    onClick={() => setShowCryptoModal(false)}
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                <div className="p-4 bg-dark-800 rounded-lg border border-dark-600 mb-6">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Total Amount (USD)</span>
                    <span className="text-2xl font-bold text-white">${total.toFixed(2)}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {cryptoCurrencies.map((currency) => {
                    const cryptoAmount = exchangeRates[currency.code]
                      ? (total * exchangeRates[currency.code]).toFixed(8)
                      : '...'

                    return (
                      <motion.button
                        key={currency.code}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => createCryptoCharge(currency.code)}
                        className="p-4 bg-dark-800 hover:bg-dark-700 rounded-lg border border-dark-600 hover:border-neon-cyan transition-all text-left group"
                      >
                        <div className="flex items-center space-x-3 mb-3">
                          <div className="w-10 h-10 bg-gradient-to-br from-neon-cyan/20 to-neon-blue/20 rounded-full flex items-center justify-center">
                            <Bitcoin className="w-6 h-6 text-neon-cyan" />
                          </div>
                          <div>
                            <p className="text-white font-bold">{currency.code}</p>
                            <p className="text-gray-400 text-xs">{currency.name}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-neon-cyan font-mono text-sm">{cryptoAmount}</p>
                          <p className="text-gray-500 text-xs capitalize">{currency.type}</p>
                        </div>
                      </motion.button>
                    )
                  })}
                </div>

                <div className="mt-6 p-4 bg-neon-cyan/10 border border-neon-cyan/30 rounded-lg">
                  <p className="text-neon-cyan text-sm">
                    <strong>Note:</strong> Clicking a cryptocurrency will open a secure payment page where you can complete your transaction. The payment will be confirmed automatically.
                  </p>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Payment Modal (Cash/Card) */}
      <AnimatePresence>
        {showPaymentModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowPaymentModal(false)}
              className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-0 flex items-center justify-center z-50 p-4"
            >
              <div className="bg-dark-900 border border-dark-600 rounded-xl p-6 max-w-md w-full">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold text-white capitalize">
                    {paymentMethod} Payment
                  </h2>
                  <button
                    onClick={() => setShowPaymentModal(false)}
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                <div className="space-y-4">
                  <div className="p-4 bg-dark-800 rounded-lg border border-dark-600">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-400">Total Amount</span>
                      <span className="text-3xl font-bold text-white">${total.toFixed(2)}</span>
                    </div>
                  </div>

                  {paymentMethod === 'cash' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Cash Received
                        </label>
                        <div className="relative">
                          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
                          <input
                            type="number"
                            step="0.01"
                            min={total}
                            value={cashReceived}
                            onChange={(e) => setCashReceived(e.target.value)}
                            className="input pl-8"
                            placeholder="0.00"
                            autoFocus
                          />
                        </div>
                      </div>

                      {cashReceived && parseFloat(cashReceived) >= total && (
                        <div className="p-4 bg-neon-green/10 border border-neon-green/30 rounded-lg">
                          <div className="flex justify-between items-center">
                            <span className="text-neon-green font-medium">Change Due</span>
                            <span className="text-2xl font-bold text-neon-green">
                              ${(parseFloat(cashReceived) - total).toFixed(2)}
                            </span>
                          </div>
                        </div>
                      )}
                    </>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Customer Email (optional)
                    </label>
                    <input
                      type="email"
                      value={customerEmail}
                      onChange={(e) => setCustomerEmail(e.target.value)}
                      className="input"
                      placeholder="customer@example.com"
                    />
                    <p className="text-gray-500 text-xs mt-1">For email receipt</p>
                  </div>

                  <div className="flex space-x-3 pt-4">
                    <button
                      type="button"
                      onClick={() => setShowPaymentModal(false)}
                      className="btn-secondary flex-1"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleCompleteSale}
                      className="btn-primary flex-1"
                    >
                      Complete Sale
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Receipt Modal */}
      <AnimatePresence>
        {showReceiptModal && completedSale && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-0 flex items-center justify-center z-50 p-4"
            >
              <div className="bg-dark-900 border border-dark-600 rounded-xl p-6 max-w-md w-full">
                <div className="text-center mb-6">
                  <div className="w-16 h-16 bg-neon-green/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-10 h-10 text-neon-green" />
                  </div>
                  <h2 className="text-2xl font-bold text-white mb-2">Sale Complete!</h2>
                  <p className="text-gray-400">Transaction ID: {completedSale.id}</p>
                </div>

                {/* Receipt Preview */}
                <div className="bg-white text-black p-6 rounded-lg mb-6 font-mono text-sm">
                  <div className="text-center mb-4">
                    <h3 className="font-bold text-lg">OnyxPOS</h3>
                    <p className="text-xs">{format(new Date(), 'MMM d, yyyy h:mm a')}</p>
                  </div>

                  <div className="border-t border-b border-gray-300 py-3 mb-3">
                    {completedSale.items.map((item, idx) => (
                      <div key={idx} className="flex justify-between mb-1">
                        <span>{item.quantity}x {item.name}</span>
                        <span>${(item.sell_price * item.quantity).toFixed(2)}</span>
                      </div>
                    ))}
                  </div>

                  <div className="space-y-1 mb-3">
                    <div className="flex justify-between">
                      <span>Subtotal:</span>
                      <span>${completedSale.subtotal.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Tax:</span>
                      <span>${completedSale.tax.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between font-bold text-lg border-t border-gray-300 pt-2">
                      <span>Total:</span>
                      <span>${completedSale.total.toFixed(2)}</span>
                    </div>
                  </div>

                  <div className="border-t border-gray-300 pt-2">
                    <div className="flex justify-between capitalize">
                      <span>Payment Method:</span>
                      <span>{completedSale.payment_method}</span>
                    </div>
                    {completedSale.change > 0 && (
                      <div className="flex justify-between font-bold">
                        <span>Change:</span>
                        <span>${completedSale.change.toFixed(2)}</span>
                      </div>
                    )}
                  </div>

                  <p className="text-center text-xs mt-4">Thank you for your business!</p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={handlePrintReceipt}
                    className="btn-primary flex items-center justify-center space-x-2"
                  >
                    <Printer className="w-5 h-5" />
                    <span>Print</span>
                  </button>
                  {customerEmail && (
                    <button
                      onClick={handleEmailReceipt}
                      className="btn-primary flex items-center justify-center space-x-2"
                    >
                      <Mail className="w-5 h-5" />
                      <span>Email</span>
                    </button>
                  )}
                </div>

                <button
                  onClick={handleNewSale}
                  className="btn-secondary w-full mt-3"
                >
                  New Sale
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
