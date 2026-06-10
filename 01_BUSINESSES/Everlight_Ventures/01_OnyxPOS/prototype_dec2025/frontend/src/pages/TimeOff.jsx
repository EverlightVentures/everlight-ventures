import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Calendar, Clock, Check, X, Plus, AlertCircle } from 'lucide-react'
import api from '../utils/api'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/authStore'

export default function TimeOff() {
  const { user } = useAuthStore()
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    start_date: '',
    end_date: '',
    reason: '',
    request_type: 'vacation'
  })

  const isManager = user?.role === 'owner' || user?.role === 'manager'

  useEffect(() => {
    fetchRequests()
  }, [])

  const fetchRequests = async () => {
    try {
      setLoading(true)
      const response = await api.get('/timeoff')
      setRequests(response.data.requests)
    } catch (error) {
      toast.error('Failed to load requests')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      await api.post('/timeoff', formData)
      toast.success('Time-off request submitted!')
      setShowForm(false)
      fetchRequests()
      setFormData({ start_date: '', end_date: '', reason: '', request_type: 'vacation' })
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to submit request')
    }
  }

  const handleApprove = async (id) => {
    try {
      await api.put(`/timeoff/${id}/approve`)
      toast.success('Request approved!')
      fetchRequests()
    } catch (error) {
      toast.error('Failed to approve request')
    }
  }

  const handleDeny = async (id) => {
    try {
      const reason = prompt('Reason for denial (optional):')
      await api.put(`/timeoff/${id}/deny`, { reason })
      toast.success('Request denied')
      fetchRequests()
    } catch (error) {
      toast.error('Failed to deny request')
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this time-off request?')) return
    try {
      await api.delete(`/timeoff/${id}`)
      toast.success('Request deleted')
      fetchRequests()
    } catch (error) {
      toast.error('Failed to delete request')
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'approved':
        return 'bg-green-500/20 text-green-500 border-green-500/30'
      case 'denied':
        return 'bg-red-500/20 text-red-500 border-red-500/30'
      default:
        return 'bg-amber-500/20 text-amber-500 border-amber-500/30'
    }
  }

  const getTypeIcon = (type) => {
    switch (type) {
      case 'vacation':
        return '🏖️'
      case 'sick':
        return '🤒'
      case 'personal':
        return '👤'
      default:
        return '📅'
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-white">Time Off Requests</h1>
        <div className="card animate-pulse">
          <div className="h-48 bg-dark-700 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Time Off Requests</h1>
          <p className="text-gray-400">
            {isManager ? 'Manage employee time-off requests' : 'Request time off and view status'}
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="btn-primary flex items-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>Request Time Off</span>
        </button>
      </div>

      {/* Request Form Modal */}
      {showForm && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-dark-900 p-6 rounded-xl max-w-md w-full border border-dark-600 shadow-2xl"
          >
            <h2 className="text-xl font-bold text-white mb-4 flex items-center">
              <Calendar className="w-5 h-5 mr-2 text-blue-500" />
              Request Time Off
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Request Type
                </label>
                <select
                  value={formData.request_type}
                  onChange={(e) => setFormData({ ...formData, request_type: e.target.value })}
                  className="input w-full"
                >
                  <option value="vacation">🏖️ Vacation</option>
                  <option value="sick">🤒 Sick Leave</option>
                  <option value="personal">👤 Personal</option>
                  <option value="other">📅 Other</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Start Date
                  </label>
                  <input
                    type="date"
                    required
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    className="input w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    End Date
                  </label>
                  <input
                    type="date"
                    required
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                    className="input w-full"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Reason (optional)
                </label>
                <textarea
                  value={formData.reason}
                  onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  className="input w-full"
                  rows="3"
                  placeholder="Provide additional details..."
                />
              </div>
              <div className="flex space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary flex-1">
                  Submit Request
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}

      {/* Requests List */}
      <div className="card">
        {requests.length === 0 ? (
          <div className="text-center py-16">
            <Calendar className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-lg mb-2">No time-off requests</p>
            <p className="text-gray-500 text-sm">
              Click "Request Time Off" to submit your first request
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {requests.map((req, index) => {
              const startDate = new Date(req.start_date)
              const endDate = new Date(req.end_date)
              const duration = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24)) + 1

              return (
                <motion.div
                  key={req.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-dark-800/50 p-5 rounded-lg border border-dark-600 hover:border-dark-500 transition-all group"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <span className="text-2xl">{getTypeIcon(req.request_type)}</span>
                        <div>
                          <p className="font-medium text-white capitalize">
                            {req.user_name}
                          </p>
                          <p className="text-sm text-gray-400 capitalize">
                            {req.request_type}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center space-x-6 text-sm text-gray-400 mb-2">
                        <div className="flex items-center space-x-2">
                          <Calendar className="w-4 h-4" />
                          <span>
                            {startDate.toLocaleDateString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric'
                            })}
                            {' → '}
                            {endDate.toLocaleDateString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric'
                            })}
                          </span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Clock className="w-4 h-4" />
                          <span>{duration} {duration === 1 ? 'day' : 'days'}</span>
                        </div>
                      </div>

                      {req.reason && (
                        <p className="text-sm text-gray-400 bg-dark-700/50 p-3 rounded mt-2">
                          {req.reason}
                        </p>
                      )}

                      {req.denial_reason && (
                        <div className="mt-2 flex items-start space-x-2 text-sm text-red-400 bg-red-500/10 p-3 rounded">
                          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="font-medium">Denial Reason:</p>
                            <p>{req.denial_reason}</p>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center space-x-3 ml-4">
                      <span
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border ${getStatusColor(
                          req.status
                        )}`}
                      >
                        {req.status.toUpperCase()}
                      </span>

                      {isManager && req.status === 'pending' && (
                        <>
                          <button
                            onClick={() => handleApprove(req.id)}
                            className="p-2 bg-green-500/20 text-green-500 rounded-lg hover:bg-green-500/30 transition-colors border border-green-500/30"
                            title="Approve"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeny(req.id)}
                            className="p-2 bg-red-500/20 text-red-500 rounded-lg hover:bg-red-500/30 transition-colors border border-red-500/30"
                            title="Deny"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </>
                      )}

                      {(req.user_id === user?.id || isManager) && req.status === 'pending' && (
                        <button
                          onClick={() => handleDelete(req.id)}
                          className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                          title="Delete"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  {req.approved_at && (
                    <p className="text-xs text-gray-500 mt-3 pt-3 border-t border-dark-600">
                      {req.status === 'approved' ? 'Approved' : 'Denied'} on{' '}
                      {new Date(req.approved_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit'
                      })}
                    </p>
                  )}
                </motion.div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
