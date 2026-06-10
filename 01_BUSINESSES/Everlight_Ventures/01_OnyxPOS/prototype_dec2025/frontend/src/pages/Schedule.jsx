import { useState, useEffect } from 'react'
import { Calendar as CalendarIcon, Plus, Edit2, Trash2, ChevronLeft, ChevronRight, Clock, User, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { format, startOfWeek, addDays, isSameDay, parseISO } from 'date-fns'
import api from '../utils/api'
import { useAuthStore } from '../store/authStore'

export default function Schedule() {
  const { user } = useAuthStore()
  const [currentWeek, setCurrentWeek] = useState(new Date())
  const [shifts, setShifts] = useState([])
  const [employees, setEmployees] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [editingShift, setEditingShift] = useState(null)
  const [formData, setFormData] = useState({
    employee_id: '',
    date: '',
    start_time: '',
    end_time: '',
    notes: '',
  })

  useEffect(() => {
    fetchEmployees()
    fetchShifts()
  }, [currentWeek])

  const fetchEmployees = async () => {
    try {
      const response = await api.get('/employees')
      setEmployees(response.data.employees || [])
    } catch (error) {
      console.error('Failed to fetch employees:', error)
    }
  }

  const fetchShifts = async () => {
    try {
      const weekStart = format(startOfWeek(currentWeek), 'yyyy-MM-dd')
      const response = await api.get(`/schedule?week_start=${weekStart}`)
      setShifts(response.data.shifts || [])
    } catch (error) {
      console.error('Failed to fetch shifts:', error)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (editingShift) {
        await api.put(`/schedule/${editingShift.id}`, formData)
        toast.success('Shift updated successfully!')
      } else {
        await api.post('/schedule', formData)
        toast.success('Shift added successfully!')
      }
      setShowModal(false)
      resetForm()
      fetchShifts()
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to save shift')
    }
  }

  const handleEdit = (shift) => {
    setEditingShift(shift)
    setFormData({
      employee_id: shift.employee_id,
      date: format(parseISO(shift.date), 'yyyy-MM-dd'),
      start_time: shift.start_time,
      end_time: shift.end_time,
      notes: shift.notes || '',
    })
    setShowModal(true)
  }

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this shift?')) return

    try {
      await api.delete(`/schedule/${id}`)
      toast.success('Shift deleted successfully!')
      fetchShifts()
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to delete shift')
    }
  }

  const resetForm = () => {
    setFormData({
      employee_id: '',
      date: '',
      start_time: '',
      end_time: '',
      notes: '',
    })
    setEditingShift(null)
  }

  const getWeekDays = () => {
    const weekStart = startOfWeek(currentWeek)
    return Array.from({ length: 7 }, (_, i) => addDays(weekStart, i))
  }

  const getShiftsForDay = (date) => {
    return shifts.filter(shift => isSameDay(parseISO(shift.date), date))
  }

  const getEmployeeName = (employeeId) => {
    const emp = employees.find(e => e.id === employeeId)
    return emp ? `${emp.first_name} ${emp.last_name}` : 'Unknown'
  }

  const getEmployeeInitials = (employeeId) => {
    const emp = employees.find(e => e.id === employeeId)
    return emp ? `${emp.first_name[0]}${emp.last_name[0]}` : '??'
  }

  const previousWeek = () => {
    setCurrentWeek(addDays(currentWeek, -7))
  }

  const nextWeek = () => {
    setCurrentWeek(addDays(currentWeek, 7))
  }

  const weekDays = getWeekDays()

  const shiftColors = [
    'from-neon-blue to-neon-cyan',
    'from-neon-purple to-neon-pink',
    'from-neon-green to-neon-blue',
    'from-neon-amber to-neon-orange',
    'from-neon-pink to-neon-purple',
    'from-neon-cyan to-neon-green',
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Work Schedule</h1>
          <p className="text-gray-400 mt-1">Manage employee shifts and schedules</p>
        </div>
        {(user?.role === 'owner' || user?.role === 'manager') && (
          <button
            onClick={() => {
              resetForm()
              setShowModal(true)
            }}
            className="btn-primary flex items-center space-x-2"
          >
            <Plus className="w-5 h-5" />
            <span>Add Shift</span>
          </button>
        )}
      </div>

      {/* Week Navigator */}
      <div className="card">
        <div className="flex items-center justify-between">
          <button
            onClick={previousWeek}
            className="p-2 text-gray-400 hover:text-white hover:bg-dark-800 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <h2 className="text-xl font-bold text-white">
            {format(weekDays[0], 'MMM d')} - {format(weekDays[6], 'MMM d, yyyy')}
          </h2>
          <button
            onClick={nextWeek}
            className="p-2 text-gray-400 hover:text-white hover:bg-dark-800 rounded-lg transition-colors"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
        {weekDays.map((day, dayIndex) => {
          const dayShifts = getShiftsForDay(day)
          const isToday = isSameDay(day, new Date())

          return (
            <div
              key={dayIndex}
              className={`card min-h-[300px] ${isToday ? 'border-neon-blue' : ''}`}
            >
              <div className="text-center mb-4 pb-3 border-b border-dark-700">
                <p className="text-gray-400 text-sm uppercase">{format(day, 'EEE')}</p>
                <p className={`text-2xl font-bold ${isToday ? 'text-neon-blue' : 'text-white'}`}>
                  {format(day, 'd')}
                </p>
                {isToday && (
                  <span className="text-xs text-neon-blue">Today</span>
                )}
              </div>

              <div className="space-y-2">
                {dayShifts.length === 0 ? (
                  <p className="text-gray-600 text-center text-sm py-8">No shifts</p>
                ) : (
                  dayShifts.map((shift, shiftIndex) => (
                    <motion.div
                      key={shift.id}
                      whileHover={{ scale: 1.02 }}
                      className="group relative"
                    >
                      <div className={`p-3 bg-gradient-to-br ${shiftColors[shiftIndex % shiftColors.length]} rounded-lg cursor-pointer`}>
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
                              <span className="text-white text-xs font-bold">
                                {getEmployeeInitials(shift.employee_id)}
                              </span>
                            </div>
                            <p className="text-white font-medium text-sm">
                              {getEmployeeName(shift.employee_id).split(' ')[0]}
                            </p>
                          </div>
                          {(user?.role === 'owner' || user?.role === 'manager') && (
                            <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={() => handleEdit(shift)}
                                className="p-1 bg-white/20 hover:bg-white/30 rounded transition-colors"
                              >
                                <Edit2 className="w-3 h-3 text-white" />
                              </button>
                              <button
                                onClick={() => handleDelete(shift.id)}
                                className="p-1 bg-white/20 hover:bg-red-500 rounded transition-colors"
                              >
                                <Trash2 className="w-3 h-3 text-white" />
                              </button>
                            </div>
                          )}
                        </div>
                        <div className="flex items-center space-x-1 text-white/90 text-xs">
                          <Clock className="w-3 h-3" />
                          <span>{shift.start_time} - {shift.end_time}</span>
                        </div>
                        {shift.notes && (
                          <p className="text-white/70 text-xs mt-1 truncate">{shift.notes}</p>
                        )}
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Add/Edit Modal */}
      <AnimatePresence>
        {showModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowModal(false)}
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
                  <h2 className="text-2xl font-bold text-white">
                    {editingShift ? 'Edit Shift' : 'Add New Shift'}
                  </h2>
                  <button
                    onClick={() => setShowModal(false)}
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Employee
                    </label>
                    <select
                      required
                      value={formData.employee_id}
                      onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
                      className="input"
                    >
                      <option value="">Select an employee</option>
                      {employees.map(emp => (
                        <option key={emp.id} value={emp.id}>
                          {emp.first_name} {emp.last_name} ({emp.role})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Date
                    </label>
                    <input
                      type="date"
                      required
                      value={formData.date}
                      onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                      className="input"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Start Time
                      </label>
                      <input
                        type="time"
                        required
                        value={formData.start_time}
                        onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                        className="input"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        End Time
                      </label>
                      <input
                        type="time"
                        required
                        value={formData.end_time}
                        onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                        className="input"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Notes (optional)
                    </label>
                    <textarea
                      value={formData.notes}
                      onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                      className="input"
                      rows="3"
                      placeholder="Any special instructions or notes..."
                    />
                  </div>

                  <div className="flex space-x-3 pt-4">
                    <button
                      type="button"
                      onClick={() => setShowModal(false)}
                      className="btn-secondary flex-1"
                    >
                      Cancel
                    </button>
                    <button type="submit" className="btn-primary flex-1">
                      {editingShift ? 'Update' : 'Add'} Shift
                    </button>
                  </div>
                </form>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
