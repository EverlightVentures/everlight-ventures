import { useState, useEffect } from 'react'
import { Search, Plus, Package, AlertTriangle, Edit, Trash2, Filter, Download, Upload, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import api from '../utils/api'
import toast from 'react-hot-toast'
import { EmptyState } from '../components/LoadingSkeleton'

export default function Inventory() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all') // all, low_stock, out_of_stock
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingProduct, setEditingProduct] = useState(null)
  const [showImportModal, setShowImportModal] = useState(false)
  const [importFile, setImportFile] = useState(null)
  const [importPreview, setImportPreview] = useState(null)
  const [importMapping, setImportMapping] = useState({})
  const [importColumns, setImportColumns] = useState([])
  const [importLoading, setImportLoading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [formData, setFormData] = useState({
    sku: '',
    name: '',
    category: '',
    sell_price: '',
    cost_price: '',
    stock_on_hand: '',
    reorder_point: '',
  })

  useEffect(() => {
    fetchProducts()
  }, [])

  const fetchProducts = async () => {
    try {
      const response = await api.get('/inventory')
      setProducts(response.data.items || [])
    } catch (error) {
      toast.error('Failed to load inventory')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setFormData({
      sku: '',
      name: '',
      category: '',
      sell_price: '',
      cost_price: '',
      stock_on_hand: '',
      reorder_point: '',
    })
    setEditingProduct(null)
  }

  const importFields = [
    { key: 'sku', label: 'SKU', required: true },
    { key: 'name', label: 'Product Name', required: true },
    { key: 'sell_price', label: 'Sell Price', required: true },
    { key: 'cost_price', label: 'Cost Price' },
    { key: 'category', label: 'Category' },
    { key: 'description', label: 'Description' },
    { key: 'stock_on_hand', label: 'Stock On Hand' },
    { key: 'reorder_point', label: 'Reorder Point' },
    { key: 'reorder_quantity', label: 'Reorder Quantity' },
    { key: 'supplier_name', label: 'Supplier Name' },
    { key: 'supplier_sku', label: 'Supplier SKU' },
    { key: 'barcode', label: 'Barcode' },
  ]

  const handleEdit = (product) => {
    setEditingProduct(product)
    setFormData({
      sku: product.sku,
      name: product.name,
      category: product.category || '',
      sell_price: product.sell_price,
      cost_price: product.cost_price || '',
      stock_on_hand: product.stock_on_hand,
      reorder_point: product.reorder_point || 10,
    })
    setShowAddModal(true)
  }

  const handleImportFile = async (file) => {
    setImportFile(file)
    setImportLoading(true)
    setImportPreview(null)
    setImportMapping({})
    setImportColumns([])

    try {
      const form = new FormData()
      form.append('file', file)
      // Don't set Content-Type manually - let axios set it with the proper boundary
      const response = await api.post('/inventory/import/preview', form)
      setImportPreview(response.data)
      setImportColumns(response.data.columns || [])
      setImportMapping(response.data.suggested_mapping || {})
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to preview import')
    } finally {
      setImportLoading(false)
    }
  }

  const handleConfirmImport = async () => {
    if (!importFile) return
    setImporting(true)

    try {
      const cleanedMapping = Object.fromEntries(
        Object.entries(importMapping).filter(([, column]) => column)
      )
      const form = new FormData()
      form.append('file', importFile)
      form.append('mapping', JSON.stringify(cleanedMapping))

      // Don't set Content-Type manually - let axios set it with the proper boundary
      const response = await api.post('/inventory/import/confirm', form)
      toast.success(`Import completed: ${response.data.created} added, ${response.data.updated} updated`)
      setShowImportModal(false)
      setImportFile(null)
      setImportPreview(null)
      setImportMapping({})
      setImportColumns([])
      fetchProducts()
    } catch (error) {
      const message = error.response?.data?.error || 'Import failed'
      toast.error(message)
    } finally {
      setImporting(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this product?')) return

    try {
      await api.delete(`/inventory/${id}`)
      toast.success('Product deleted successfully!')
      fetchProducts()
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to delete product')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (editingProduct) {
        await api.put(`/inventory/${editingProduct.id}`, formData)
        toast.success('Product updated successfully!')
      } else {
        await api.post('/inventory', formData)
        toast.success('Product added successfully!')
      }
      setShowAddModal(false)
      resetForm()
      fetchProducts()
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to save product')
    }
  }

  const filteredProducts = products.filter(product => {
    const matchesSearch = product.name.toLowerCase().includes(search.toLowerCase()) ||
                         product.sku.toLowerCase().includes(search.toLowerCase())

    if (filter === 'low_stock') {
      return matchesSearch && product.stock_on_hand <= product.reorder_point && product.stock_on_hand > 0
    }
    if (filter === 'out_of_stock') {
      return matchesSearch && product.stock_on_hand === 0
    }
    return matchesSearch
  })

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="animate-pulse">
            <div className="h-8 bg-dark-700 rounded w-32 mb-2"></div>
            <div className="h-4 bg-dark-700 rounded w-48"></div>
          </div>
          <div className="h-10 bg-dark-700 rounded w-32 animate-pulse"></div>
        </div>
        <div className="card animate-pulse">
          <div className="h-12 bg-dark-700 rounded mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="p-4 bg-dark-800 rounded-lg">
                <div className="h-32 bg-dark-700 rounded mb-3"></div>
                <div className="h-4 bg-dark-700 rounded w-3/4 mb-2"></div>
                <div className="h-3 bg-dark-700 rounded w-1/2"></div>
              </div>
            ))}
          </div>
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
          <h1 className="text-3xl font-bold text-white mb-1">Inventory</h1>
          <p className="text-gray-400">Manage your products and stock levels</p>
        </div>
        <div className="flex items-center space-x-3">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="btn-secondary flex items-center space-x-2"
          >
            <Download className="w-5 h-5" />
            <span>Export CSV</span>
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setShowImportModal(true)}
            className="btn-secondary flex items-center space-x-2"
          >
            <Upload className="w-5 h-5" />
            <span>Import</span>
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setShowAddModal(true)}
            className="btn-primary flex items-center space-x-2"
          >
            <Plus className="w-5 h-5" />
            <span>Add Product</span>
          </motion.button>
        </div>
      </motion.div>

      {/* Stats */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-1 md:grid-cols-4 gap-4"
      >
        <div className="card bg-gradient-to-br from-neon-blue/10 to-transparent border-neon-blue/30">
          <p className="text-gray-400 text-sm mb-1">Total Products</p>
          <p className="text-3xl font-bold text-white">{products.length}</p>
        </div>
        <div className="card bg-gradient-to-br from-neon-green/10 to-transparent border-neon-green/30">
          <p className="text-gray-400 text-sm mb-1">In Stock</p>
          <p className="text-3xl font-bold text-white">
            {products.filter(p => p.stock_on_hand > p.reorder_point).length}
          </p>
        </div>
        <div className="card bg-gradient-to-br from-neon-amber/10 to-transparent border-neon-amber/30">
          <p className="text-gray-400 text-sm mb-1">Low Stock</p>
          <p className="text-3xl font-bold text-white">
            {products.filter(p => p.stock_on_hand <= p.reorder_point && p.stock_on_hand > 0).length}
          </p>
        </div>
        <div className="card bg-gradient-to-br from-neon-pink/10 to-transparent border-neon-pink/30">
          <p className="text-gray-400 text-sm mb-1">Out of Stock</p>
          <p className="text-3xl font-bold text-white">
            {products.filter(p => p.stock_on_hand === 0).length}
          </p>
        </div>
      </motion.div>

      {/* Filters & Search */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="card"
      >
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input
              type="text"
              className="input pl-12 w-full"
              placeholder="Search by name or SKU..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* Filters */}
          <div className="flex items-center space-x-2">
            <Filter className="w-5 h-5 text-gray-400" />
            {['all', 'low_stock', 'out_of_stock'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  filter === f
                    ? 'bg-neon-blue text-white'
                    : 'bg-dark-800 text-gray-400 hover:bg-dark-700'
                }`}
              >
                {f.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
              </button>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Products Grid */}
      {filteredProducts.length === 0 ? (
        <EmptyState
          icon={Package}
          title={search ? 'No products found' : 'No products yet'}
          description={search ? `No products match "${search}"` : 'Start by adding your first product to your inventory'}
          action={
            !search && (
              <button onClick={() => setShowAddModal(true)} className="btn-primary">
                <Plus className="w-5 h-5 mr-2" />
                Add Your First Product
              </button>
            )
          }
        />
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
        >
          <AnimatePresence>
            {filteredProducts.map((product, index) => (
              <motion.div
                key={product.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ y: -5 }}
                className="card group relative overflow-hidden"
              >
                {/* Stock Badge */}
                {product.stock_on_hand === 0 && (
                  <div className="absolute top-2 right-2 z-10">
                    <span className="px-2 py-1 bg-red-500/20 border border-red-500/30 rounded-md text-red-500 text-xs font-medium">
                      Out of Stock
                    </span>
                  </div>
                )}
                {product.stock_on_hand > 0 && product.stock_on_hand <= product.reorder_point && (
                  <div className="absolute top-2 right-2 z-10">
                    <span className="px-2 py-1 bg-amber-500/20 border border-amber-500/30 rounded-md text-amber-500 text-xs font-medium flex items-center space-x-1">
                      <AlertTriangle className="w-3 h-3" />
                      <span>Low Stock</span>
                    </span>
                  </div>
                )}

                {/* Product Image Placeholder */}
                <div className="h-40 bg-gradient-to-br from-neon-blue/20 to-neon-purple/20 rounded-lg mb-4 flex items-center justify-center group-hover:from-neon-blue/30 group-hover:to-neon-purple/30 transition-all">
                  <Package className="w-16 h-16 text-gray-600 group-hover:text-gray-500 transition-colors" />
                </div>

                {/* Product Info */}
                <div className="space-y-2">
                  <div>
                    <h3 className="text-white font-bold text-lg group-hover:text-neon-blue transition-colors">
                      {product.name}
                    </h3>
                    <p className="text-gray-400 text-sm">SKU: {product.sku}</p>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-gray-400 text-xs">Price</p>
                      <p className="text-white font-bold text-lg">${parseFloat(product.sell_price).toFixed(2)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-gray-400 text-xs">Stock</p>
                      <p className={`font-bold text-lg ${
                        product.stock_on_hand === 0 ? 'text-red-500' :
                        product.stock_on_hand <= product.reorder_point ? 'text-amber-500' :
                        'text-neon-green'
                      }`}>
                        {product.stock_on_hand}
                      </p>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2 pt-2 border-t border-dark-600">
                    <button
                      onClick={() => handleEdit(product)}
                      className="flex-1 btn-secondary text-sm py-2 flex items-center justify-center space-x-1"
                    >
                      <Edit className="w-4 h-4" />
                      <span>Edit</span>
                    </button>
                    <button
                      onClick={() => handleDelete(product.id)}
                      className="btn-secondary text-sm py-2 px-3 hover:bg-red-500/20 hover:border-red-500/30 hover:text-red-500 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Add/Edit Modal */}
      <AnimatePresence>
        {showAddModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => {
                setShowAddModal(false)
                resetForm()
              }}
              className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-0 flex items-center justify-center z-50 p-4"
            >
              <div className="bg-dark-900 border border-dark-600 rounded-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-auto">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold text-white">
                    {editingProduct ? 'Edit Product' : 'Add New Product'}
                  </h2>
                  <button
                    onClick={() => {
                      setShowAddModal(false)
                      resetForm()
                    }}
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        SKU *
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.sku}
                        onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
                        className="input"
                        placeholder="PROD-001"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Category
                      </label>
                      <input
                        type="text"
                        value={formData.category}
                        onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                        className="input"
                        placeholder="e.g. Electronics"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Product Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="input"
                      placeholder="Product name"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Cost Price
                      </label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={formData.cost_price}
                          onChange={(e) => setFormData({ ...formData, cost_price: e.target.value })}
                          className="input pl-8"
                          placeholder="0.00"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Sell Price *
                      </label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          required
                          value={formData.sell_price}
                          onChange={(e) => setFormData({ ...formData, sell_price: e.target.value })}
                          className="input pl-8"
                          placeholder="0.00"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Stock on Hand *
                      </label>
                      <input
                        type="number"
                        min="0"
                        required
                        value={formData.stock_on_hand}
                        onChange={(e) => setFormData({ ...formData, stock_on_hand: e.target.value })}
                        className="input"
                        placeholder="0"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Reorder Point
                      </label>
                      <input
                        type="number"
                        min="0"
                        value={formData.reorder_point}
                        onChange={(e) => setFormData({ ...formData, reorder_point: e.target.value })}
                        className="input"
                        placeholder="10"
                      />
                    </div>
                  </div>

                  <div className="flex space-x-3 pt-4">
                    <button
                      type="button"
                      onClick={() => {
                        setShowAddModal(false)
                        resetForm()
                      }}
                      className="btn-secondary flex-1"
                    >
                      Cancel
                    </button>
                    <button type="submit" className="btn-primary flex-1">
                      {editingProduct ? 'Update' : 'Add'} Product
                    </button>
                  </div>
                </form>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Import Modal */}
      <AnimatePresence>
        {showImportModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => {
                setShowImportModal(false)
                setImportFile(null)
                setImportPreview(null)
                setImportMapping({})
                setImportColumns([])
              }}
              className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-0 flex items-center justify-center z-50 p-4"
            >
              <div className="bg-dark-900 border border-dark-600 rounded-xl p-6 max-w-4xl w-full max-h-[90vh] overflow-auto">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-white">Import Inventory</h2>
                    <p className="text-sm text-gray-400">Upload CSV or Excel files and map columns to fields.</p>
                  </div>
                  <button
                    onClick={() => {
                      setShowImportModal(false)
                      setImportFile(null)
                      setImportPreview(null)
                      setImportMapping({})
                      setImportColumns([])
                    }}
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                <div className="space-y-6">
                  <div className="border border-dashed border-dark-600 rounded-lg p-4">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                      <div>
                        <p className="text-sm text-gray-300">Supported: .csv, .xls, .xlsx</p>
                        {importFile && (
                          <p className="text-xs text-gray-500 mt-1">{importFile.name}</p>
                        )}
                      </div>
                      <label className="btn-secondary cursor-pointer inline-flex items-center space-x-2">
                        <Upload className="w-4 h-4" />
                        <span>{importFile ? 'Replace File' : 'Choose File'}</span>
                        <input
                          type="file"
                          accept=".csv,.xls,.xlsx"
                          className="hidden"
                          onChange={(e) => {
                            const file = e.target.files?.[0]
                            if (file) {
                              handleImportFile(file)
                            }
                          }}
                        />
                      </label>
                    </div>
                    {importLoading && (
                      <p className="text-sm text-gray-400 mt-3">Analyzing file and suggesting mappings...</p>
                    )}
                  </div>

                  {importPreview && (
                    <>
                      {importPreview.missing_required_fields?.length > 0 && (
                        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                          Missing required fields: {importPreview.missing_required_fields.join(', ')}
                        </div>
                      )}

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {importFields.map((field) => (
                          <div key={field.key} className="flex items-center justify-between gap-3 bg-dark-800 rounded-lg p-3">
                            <div>
                              <p className="text-sm text-gray-200">
                                {field.label}{field.required ? ' *' : ''}
                              </p>
                              <p className="text-xs text-gray-500">Map to a column</p>
                            </div>
                            <select
                              value={importMapping[field.key] || ''}
                              onChange={(e) => setImportMapping({
                                ...importMapping,
                                [field.key]: e.target.value
                              })}
                              className={`input text-sm max-w-[220px] ${field.required && !importMapping[field.key] ? 'border-red-500/40' : ''}`}
                            >
                              <option value="">Ignore</option>
                              {importColumns.map((col) => (
                                <option key={col} value={col}>{col}</option>
                              ))}
                            </select>
                          </div>
                        ))}
                      </div>

                      <div className="card">
                        <div className="flex items-center justify-between mb-3">
                          <p className="text-sm text-gray-300">Preview ({importPreview.total_rows} rows)</p>
                          <p className="text-xs text-gray-500">Showing first 20 rows</p>
                        </div>
                        <div className="overflow-auto">
                          <table className="min-w-full text-sm">
                            <thead className="text-gray-400">
                              <tr>
                                <th className="text-left p-2">Row</th>
                                {importFields.map((field) => (
                                  <th key={field.key} className="text-left p-2">{field.label}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {importPreview.preview_rows?.map((row) => (
                                <tr key={row.row} className="border-t border-dark-700">
                                  <td className="p-2 text-gray-500">{row.row}</td>
                                  {importFields.map((field) => (
                                    <td key={field.key} className="p-2 text-gray-300">
                                      {row.data?.[field.key] ?? ''}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </>
                  )}
                </div>

                <div className="flex space-x-3 pt-6">
                  <button
                    type="button"
                    onClick={() => {
                      setShowImportModal(false)
                      setImportFile(null)
                      setImportPreview(null)
                      setImportMapping({})
                      setImportColumns([])
                    }}
                    className="btn-secondary flex-1"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirmImport}
                    disabled={!importPreview || importing || importLoading}
                    className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {importing ? 'Importing...' : 'Confirm Import'}
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
