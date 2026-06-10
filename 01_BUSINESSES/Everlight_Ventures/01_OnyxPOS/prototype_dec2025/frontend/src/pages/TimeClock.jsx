import { useState, useEffect } from 'react'
import { Clock, LogIn, LogOut as LogOutIcon, Coffee, Calendar, User, DollarSign, Users } from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { format } from 'date-fns'
import api from '../utils/api'
import { useAuthStore } from '../store/authStore'

export default function TimeClock() {
  const { user } = useAuthStore()
  const [currentTime, setCurrentTime] = useState(new Date())
  const [clockedIn, setClockedIn] = useState(false)
  const [currentShift, setCurrentShift] = useState(null)
  const [recentShifts, setRecentShifts] = useState([])
  const [onBreak, setOnBreak] = useState(false)
  const [realtimePayroll, setRealtimePayroll] = useState(null)

  // Show payroll to owners and managers only
  const canViewPayroll = user?.role === 'owner' || user?.role === 'manager'

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    fetchCurrentShift()
    fetchRecentShifts()
    if (canViewPayroll) {
      fetchRealtimePayroll()
      // Refresh payroll data every 30 seconds
      const payrollTimer = setInterval(fetchRealtimePayroll, 30000)
      return () => {
        clearInterval(timer)
        clearInterval(payrollTimer)
      }
    }
    return () => clearInterval(timer)
  }, [canViewPayroll])

  const fetchCurrentShift = async () => {
    try {
      const response = await api.get('/timeclock/current')
      if (response.data.shift) {
        setClockedIn(true)
        setCurrentShift(response.data.shift)
        setOnBreak(response.data.shift.on_break)
      }
    } catch (error) {
      console.error('Failed to fetch current shift:', error)
    }
  }

  const fetchRecentShifts = async () => {
    try {
      const response = await api.get('/timeclock/recent')
      setRecentShifts(response.data.shifts || [])
    } catch (error) {
      console.error('Failed to fetch recent shifts:', error)
    }
  }

  const fetchRealtimePayroll = async () => {
    try {
      const response = await api.get('/timeclock/realtime-payroll')
      setRealtimePayroll(response.data)
    } catch (error) {
      console.error('Failed to fetch realtime payroll:', error)
    }
  }

  const handleClockIn = async () => {
    try {
      const response = await api.post('/timeclock/clock-in')
      setClockedIn(true)
      setCurrentShift(response.data.shift)
      toast.success('Clocked in successfully!')
      fetchRecentShifts()
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to clock in')
    }
  }

  const handleClockOut = async () => {
    try {
      const response = await api.post('/timeclock/clock-out')
      setClockedIn(false)
      setCurrentShift(null)
      setOnBreak(false)
      toast.success(`Clocked out! Total hours: ${response.data.total_hours}`)
      fetchRecentShifts()
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to clock out')
    }
  }

  const handleBreak = async (action) => {
    try {
      const endpoint = action === 'start' ? '/timeclock/start-break' : '/timeclock/end-break'
      await api.post(endpoint)
      setOnBreak(action === 'start')
      toast.success(action === 'start' ? 'Break started' : 'Break ended')
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to update break status')
    }
  }

  const calculateShiftDuration = (clockIn, clockOut) => {
    const start = new Date(clockIn)
    const end = clockOut ? new Date(clockOut) : new Date()
    const diff = Math.floor((end - start) / 1000 / 60) // minutes
    const hours = Math.floor(diff / 60)
    const minutes = diff % 60
    return `${hours}h ${minutes}m`
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Time Clock</h1>
          <p className="text-gray-400 mt-1">Track your work hours</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-neon-blue">
            {format(currentTime, 'h:mm:ss a')}
          </p>
          <p className="text-gray-400 text-sm">
            {format(currentTime, 'EEEE, MMMM d, yyyy')}
          </p>
        </div>
      </div>

      {/* Current Status Card */}
      <div className="card">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 bg-gradient-to-br from-neon-blue to-neon-purple rounded-full flex items-center justify-center">
              <User className="w-8 h-8 text-white" />
            </div>
            <div>
              <p className="text-xl font-bold text-white">{user?.full_name}</p>
              <p className="text-gray-400 capitalize">{user?.role}</p>
              {clockedIn && currentShift && (
                <p className="text-neon-green text-sm mt-1">
                  Shift Duration: {calculateShiftDuration(currentShift.clock_in, null)}
                </p>
              )}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            {!clockedIn ? (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleClockIn}
                className="btn-primary flex items-center space-x-2 px-8 py-4 text-lg"
              >
                <LogIn className="w-6 h-6" />
                <span>Clock In</span>
              </motion.button>
            ) : (
              <>
                {!onBreak ? (
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleBreak('start')}
                    className="btn-secondary flex items-center space-x-2 px-6 py-3"
                  >
                    <Coffee className="w-5 h-5" />
                    <span>Start Break</span>
                  </motion.button>
                ) : (
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleBreak('end')}
                    className="btn-primary flex items-center space-x-2 px-6 py-3 bg-neon-amber hover:bg-neon-amber/80"
                  >
                    <Coffee className="w-5 h-5" />
                    <span>End Break</span>
                  </motion.button>
                )}
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleClockOut}
                  className="btn-danger flex items-center space-x-2 px-8 py-3 bg-red-500 hover:bg-red-600"
                >
                  <LogOutIcon className="w-5 h-5" />
                  <span>Clock Out</span>
                </motion.button>
              </>
            )}
          </div>
        </div>

        {onBreak && (
          <div className="mt-4 p-4 bg-neon-amber/10 border border-neon-amber/30 rounded-lg">
            <p className="text-neon-amber font-medium flex items-center space-x-2">
              <Coffee className="w-5 h-5" />
              <span>You are currently on break</span>
            </p>
          </div>
        )}
      </div>

      {/* Real-time Payroll (Owners/Managers Only) */}
      {canViewPayroll && realtimePayroll && realtimePayroll.employee_count > 0 && (
        <div className="card bg-gradient-to-br from-neon-green/5 to-neon-cyan/5 border-neon-green/30">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-white flex items-center space-x-2">
              <DollarSign className="w-5 h-5 text-neon-green" />
              <span>Real-Time Labor Cost</span>
            </h2>
            <div className="text-right">
              <p className="text-3xl font-bold text-neon-green">
                ${realtimePayroll.total_cost.toFixed(2)}
              </p>
              <p className="text-gray-400 text-sm">
                {realtimePayroll.total_hours.toFixed(1)} hours • {realtimePayroll.employee_count} employees
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {realtimePayroll.employees_working.map((emp) => (
              <div
                key={emp.user_id}
                className="bg-dark-800 border border-dark-600 rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <div className="w-8 h-8 bg-gradient-to-br from-neon-blue to-neon-purple rounded-full flex items-center justify-center">
                      <User className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <p className="font-medium text-white text-sm">{emp.name}</p>
                      <p className="text-xs text-gray-500 capitalize">{emp.role}</p>
                    </div>
                  </div>
                  {emp.on_break && (
                    <span className="px-2 py-1 bg-amber-500/10 border border-amber-500/30 rounded text-amber-500 text-xs">
                      Break
                    </span>
                  )}
                </div>
                <div className="mt-3 space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Hours:</span>
                    <span className="text-white font-medium">{emp.hours_worked}h</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Rate:</span>
                    <span className="text-white">${emp.hourly_rate}/hr</span>
                  </div>
                  <div className="flex justify-between text-sm pt-2 border-t border-dark-600">
                    <span className="text-gray-400">Cost:</span>
                    <span className="text-neon-green font-bold">${emp.cost_so_far}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 p-3 bg-dark-800/50 rounded-lg">
            <p className="text-xs text-gray-500 text-center">
              ⏱️ Updates automatically every 30 seconds • Last updated: {format(new Date(realtimePayroll.timestamp), 'h:mm:ss a')}
            </p>
          </div>
        </div>
      )}

      {/* Recent Shifts */}
      <div className="card">
        <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
          <Calendar className="w-5 h-5 text-neon-blue" />
          <span>Recent Shifts</span>
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-dark-700">
                <th className="text-left text-gray-400 font-medium pb-3">Date</th>
                <th className="text-left text-gray-400 font-medium pb-3">Clock In</th>
                <th className="text-left text-gray-400 font-medium pb-3">Clock Out</th>
                <th className="text-left text-gray-400 font-medium pb-3">Duration</th>
                <th className="text-left text-gray-400 font-medium pb-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-700">
              {recentShifts.length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center py-12 text-gray-500">
                    No recent shifts found
                  </td>
                </tr>
              ) : (
                recentShifts.map((shift, index) => (
                  <tr key={index} className="hover:bg-dark-800 transition-colors">
                    <td className="py-4 text-white">
                      {format(new Date(shift.clock_in), 'MMM d, yyyy')}
                    </td>
                    <td className="py-4 text-gray-300">
                      {format(new Date(shift.clock_in), 'h:mm a')}
                    </td>
                    <td className="py-4 text-gray-300">
                      {shift.clock_out ? format(new Date(shift.clock_out), 'h:mm a') : '-'}
                    </td>
                    <td className="py-4 text-neon-blue font-medium">
                      {shift.clock_out ? calculateShiftDuration(shift.clock_in, shift.clock_out) : 'In Progress'}
                    </td>
                    <td className="py-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                        shift.clock_out
                          ? 'bg-neon-green/10 text-neon-green border border-neon-green/30'
                          : 'bg-neon-blue/10 text-neon-blue border border-neon-blue/30'
                      }`}>
                        {shift.clock_out ? 'Completed' : 'Active'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
