# Quick Frontend Implementation Guide

## Files You Need to Create/Update

### 1. Time-Off Management Page
**File:** `frontend/src/pages/TimeOff.jsx`

```javascript
import { useState, useEffect } from 'react'
import { Calendar, Clock, Check, X } from 'lucide-react'
import { motion } from 'framer-motion'
import api from '../utils/api'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/authStore'

export default function TimeOff() {
  const { user } = useAuthStore()
  const [requests, setRequests] = useState([])
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
      const response = await api.get('/timeoff')
      setRequests(response.data.requests)
    } catch (error) {
      toast.error('Failed to load requests')
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-white">Time Off Requests</h1>
        <button onClick={() => setShowForm(true)} className="btn-primary">
          + Request Time Off
        </button>
      </div>

      {/* Request Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-dark-900 p-6 rounded-xl max-w-md w-full">
            <h2 className="text-xl font-bold text-white mb-4">Request Time Off</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-300 mb-2">Start Date</label>
                <input
                  type="date"
                  required
                  value={formData.start_date}
                  onChange={(e) => setFormData({...formData, start_date: e.target.value})}
                  className="input w-full"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-2">End Date</label>
                <input
                  type="date"
                  required
                  value={formData.end_date}
                  onChange={(e) => setFormData({...formData, end_date: e.target.value})}
                  className="input w-full"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-2">Type</label>
                <select
                  value={formData.request_type}
                  onChange={(e) => setFormData({...formData, request_type: e.target.value})}
                  className="input w-full"
                >
                  <option value="vacation">Vacation</option>
                  <option value="sick">Sick Leave</option>
                  <option value="personal">Personal</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-2">Reason</label>
                <textarea
                  value={formData.reason}
                  onChange={(e) => setFormData({...formData, reason: e.target.value})}
                  className="input w-full"
                  rows="3"
                />
              </div>
              <div className="flex space-x-3">
                <button type="button" onClick={() => setShowForm(false)} className="btn-secondary flex-1">
                  Cancel
                </button>
                <button type="submit" className="btn-primary flex-1">
                  Submit Request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Requests List */}
      <div className="card">
        {requests.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No time-off requests</p>
        ) : (
          <div className="space-y-4">
            {requests.map((req) => (
              <div key={req.id} className="bg-dark-800 p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="font-medium text-white">{req.user_name}</p>
                    <p className="text-sm text-gray-400">
                      {new Date(req.start_date).toLocaleDateString()} - {new Date(req.end_date).toLocaleDateString()}
                    </p>
                    <p className="text-sm text-gray-500 capitalize">{req.request_type}</p>
                    {req.reason && <p className="text-sm text-gray-400 mt-1">{req.reason}</p>}
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      req.status === 'approved' ? 'bg-green-500/20 text-green-500' :
                      req.status === 'denied' ? 'bg-red-500/20 text-red-500' :
                      'bg-amber-500/20 text-amber-500'
                    }`}>
                      {req.status}
                    </span>
                    {isManager && req.status === 'pending' && (
                      <>
                        <button onClick={() => handleApprove(req.id)} className="p-2 bg-green-500/20 text-green-500 rounded hover:bg-green-500/30">
                          <Check className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDeny(req.id)} className="p-2 bg-red-500/20 text-red-500 rounded hover:bg-red-500/30">
                          <X className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
```

### 2. Add Route
**File:** `frontend/src/App.jsx`

Add import:
```javascript
import TimeOff from './pages/TimeOff'
```

Add route:
```javascript
<Route path="/timeoff-requests" element={
  <ProtectedRoute>
    <TimeOff />
  </ProtectedRoute>
} />
```

### 3. Add Navigation Item
**File:** `frontend/src/components/Layout.jsx`

Add to navigation array:
```javascript
{ name: 'Time Off', href: '/timeoff-requests', icon: Calendar }
```

---

## Payroll Period Tracking

**Update:** `frontend/src/pages/Payroll.jsx`

Add at top:
```javascript
const [periods, setPeriods] = useState([])
const [showRunModal, setShowRunModal] = useState(false)

useEffect(() => {
  fetchPeriods()
}, [])

const fetchPeriods = async () => {
  try {
    const response = await api.get('/payroll/periods')
    setPeriods(response.data.periods)
  } catch (error) {
    console.error(error)
  }
}

const handleRunPayroll = async () => {
  try {
    await api.post('/payroll/run-payroll', {
      period_start: startDate,
      period_end: endDate
    })
    toast.success('Payroll processed!')
    fetchPeriods()
    setShowRunModal(false)
  } catch (error) {
    toast.error('Failed to process payroll')
  }
}
```

Add to render:
```jsx
{/* Past Payroll Periods */}
<div className="card">
  <h2 className="text-xl font-bold text-white mb-4">Payroll History</h2>
  <div className="space-y-2">
    {periods.map((period) => (
      <div key={period.id} className="flex items-center justify-between bg-dark-800 p-4 rounded-lg">
        <div>
          <p className="text-white font-medium">
            {new Date(period.period_start).toLocaleDateString()} - {new Date(period.period_end).toLocaleDateString()}
          </p>
          <p className="text-sm text-gray-400">{period.total_hours}h · ${period.total_amount}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
          period.status === 'completed' ? 'bg-green-500/20 text-green-500' : 'bg-amber-500/20 text-amber-500'
        }`}>
          {period.status === 'completed' ? '✓ Processed' : 'Pending'}
        </span>
      </div>
    ))}
  </div>
</div>
```

---

## Build and Test

```bash
cd frontend
npm run build
```

Hard refresh browser and test!
