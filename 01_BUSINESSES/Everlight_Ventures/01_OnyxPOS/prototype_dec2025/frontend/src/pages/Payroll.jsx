import { useState, useEffect } from 'react'
import { Wallet, DollarSign, Clock, TrendingUp, Download, Calendar, ChevronLeft, ChevronRight, CheckCircle, Play } from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { format, startOfMonth, endOfMonth, addMonths, subMonths } from 'date-fns'
import api from '../utils/api'

export default function Payroll() {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [payrollData, setPayrollData] = useState([])
  const [periods, setPeriods] = useState([])
  const [summary, setSummary] = useState({
    total_payroll: 0,
    total_hours: 0,
    employee_count: 0,
  })
  const [loading, setLoading] = useState(false)
  const [showRunModal, setShowRunModal] = useState(false)

  useEffect(() => {
    fetchPayroll()
    fetchPeriods()
  }, [currentMonth])

  const fetchPeriods = async () => {
    try {
      const response = await api.get('/payroll/periods')
      setPeriods(response.data.periods || [])
    } catch (error) {
      console.error('Failed to fetch periods:', error)
    }
  }

  const fetchPayroll = async () => {
    setLoading(true)
    try {
      const monthStart = format(startOfMonth(currentMonth), 'yyyy-MM-dd')
      const monthEnd = format(endOfMonth(currentMonth), 'yyyy-MM-dd')
      const response = await api.get(`/payroll?start_date=${monthStart}&end_date=${monthEnd}`)
      setPayrollData(response.data.employees || [])
      setSummary(response.data.summary || {
        total_payroll: 0,
        total_hours: 0,
        employee_count: 0,
      })
    } catch (error) {
      console.error('Failed to fetch payroll:', error)
      toast.error('Failed to load payroll data')
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    try {
      const monthStart = format(startOfMonth(currentMonth), 'yyyy-MM-dd')
      const monthEnd = format(endOfMonth(currentMonth), 'yyyy-MM-dd')
      const response = await api.get(`/payroll/export?start_date=${monthStart}&end_date=${monthEnd}`, {
        responseType: 'blob'
      })

      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `payroll-${format(currentMonth, 'yyyy-MM')}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()

      toast.success('Payroll exported successfully!')
    } catch (error) {
      toast.error('Failed to export payroll')
    }
  }

  const previousMonth = () => {
    setCurrentMonth(subMonths(currentMonth, 1))
  }

  const nextMonth = () => {
    setCurrentMonth(addMonths(currentMonth, 1))
  }

  const handleRunPayroll = async () => {
    try {
      const monthStart = startOfMonth(currentMonth)
      const monthEnd = endOfMonth(currentMonth)

      await api.post('/payroll/run-payroll', {
        period_start: monthStart.toISOString(),
        period_end: monthEnd.toISOString()
      })

      toast.success('Payroll processed successfully!')
      setShowRunModal(false)
      fetchPeriods()
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to process payroll')
    }
  }

  // Check if payroll has been run for current month
  const currentPeriod = periods.find(p => {
    const periodStart = new Date(p.period_start)
    const currentMonthStart = startOfMonth(currentMonth)
    return periodStart.getMonth() === currentMonthStart.getMonth() &&
           periodStart.getFullYear() === currentMonthStart.getFullYear()
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Payroll Management</h1>
          <p className="text-gray-400 mt-1">Track employee hours and compensation</p>
        </div>
        <div className="flex items-center space-x-3">
          {currentPeriod && currentPeriod.status === 'completed' && (
            <div className="px-4 py-2 bg-green-500/20 text-green-500 rounded-lg border border-green-500/30 flex items-center space-x-2">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm font-medium">Payroll Processed</span>
            </div>
          )}
          {!currentPeriod && (
            <button
              onClick={() => setShowRunModal(true)}
              className="btn-primary flex items-center space-x-2"
            >
              <Play className="w-4 h-4" />
              <span>Run Payroll</span>
            </button>
          )}
          <button
            onClick={handleExport}
            className="btn-secondary flex items-center space-x-2"
          >
            <Download className="w-5 h-5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Run Payroll Confirmation Modal */}
      {showRunModal && (
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
              <Play className="w-5 h-5 mr-2 text-blue-500" />
              Run Payroll for {format(currentMonth, 'MMMM yyyy')}
            </h2>
            <p className="text-gray-400 mb-6">
              This will process payroll for the period {format(startOfMonth(currentMonth), 'MMM d')} - {format(endOfMonth(currentMonth), 'MMM d, yyyy')}.
              Total amount: <span className="text-neon-green font-bold">${summary.total_payroll.toFixed(2)}</span>
            </p>
            <p className="text-sm text-amber-500 mb-6 bg-amber-500/10 p-3 rounded border border-amber-500/30">
              Note: This action will lock in the payroll data for this period. Make sure all time entries are correct.
            </p>
            <div className="flex space-x-3">
              <button
                onClick={() => setShowRunModal(false)}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                onClick={handleRunPayroll}
                className="btn-primary flex-1"
              >
                Process Payroll
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}

      {/* Month Navigator */}
      <div className="card">
        <div className="flex items-center justify-between">
          <button
            onClick={previousMonth}
            className="p-2 text-gray-400 hover:text-white hover:bg-dark-800 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div className="text-center">
            <h2 className="text-2xl font-bold text-white">
              {format(currentMonth, 'MMMM yyyy')}
            </h2>
            <p className="text-gray-400 text-sm">
              {format(startOfMonth(currentMonth), 'MMM d')} - {format(endOfMonth(currentMonth), 'MMM d')}
            </p>
          </div>
          <button
            onClick={nextMonth}
            className="p-2 text-gray-400 hover:text-white hover:bg-dark-800 rounded-lg transition-colors"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <motion.div
          whileHover={{ y: -4 }}
          className="card"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm mb-1">Total Payroll</p>
              <p className="text-3xl font-bold text-neon-green">
                ${summary.total_payroll.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </div>
            <div className="w-14 h-14 bg-gradient-to-br from-neon-green to-neon-blue rounded-lg flex items-center justify-center">
              <DollarSign className="w-8 h-8 text-white" />
            </div>
          </div>
        </motion.div>

        <motion.div
          whileHover={{ y: -4 }}
          className="card"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm mb-1">Total Hours</p>
              <p className="text-3xl font-bold text-neon-blue">
                {summary.total_hours.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
              </p>
            </div>
            <div className="w-14 h-14 bg-gradient-to-br from-neon-blue to-neon-cyan rounded-lg flex items-center justify-center">
              <Clock className="w-8 h-8 text-white" />
            </div>
          </div>
        </motion.div>

        <motion.div
          whileHover={{ y: -4 }}
          className="card"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm mb-1">Employees</p>
              <p className="text-3xl font-bold text-neon-purple">
                {summary.employee_count}
              </p>
            </div>
            <div className="w-14 h-14 bg-gradient-to-br from-neon-purple to-neon-pink rounded-lg flex items-center justify-center">
              <TrendingUp className="w-8 h-8 text-white" />
            </div>
          </div>
        </motion.div>
      </div>

      {/* Employee Payroll Table */}
      <div className="card">
        <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
          <Wallet className="w-5 h-5 text-neon-green" />
          <span>Employee Payroll Breakdown</span>
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-dark-700">
                <th className="text-left text-gray-400 font-medium pb-3">Employee</th>
                <th className="text-left text-gray-400 font-medium pb-3">Role</th>
                <th className="text-right text-gray-400 font-medium pb-3">Hours Worked</th>
                <th className="text-right text-gray-400 font-medium pb-3">Hourly Rate</th>
                <th className="text-right text-gray-400 font-medium pb-3">Regular Pay</th>
                <th className="text-right text-gray-400 font-medium pb-3">Overtime</th>
                <th className="text-right text-gray-400 font-medium pb-3">Total Pay</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-700">
              {loading ? (
                <tr>
                  <td colSpan="7" className="text-center py-12">
                    <div className="flex items-center justify-center space-x-2">
                      <div className="w-5 h-5 border-2 border-neon-blue border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-gray-400">Loading payroll data...</span>
                    </div>
                  </td>
                </tr>
              ) : payrollData.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-12">
                    <Wallet className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                    <p className="text-gray-500 text-lg">No payroll data for this period</p>
                    <p className="text-gray-600 text-sm mt-1">Employees will appear here once they clock in</p>
                  </td>
                </tr>
              ) : (
                payrollData.map((employee, index) => {
                  const regularHours = Math.min(employee.total_hours, 40)
                  const overtimeHours = Math.max(0, employee.total_hours - 40)
                  const regularPay = regularHours * employee.hourly_rate
                  const overtimePay = overtimeHours * employee.hourly_rate * 1.5
                  const totalPay = regularPay + overtimePay

                  return (
                    <motion.tr
                      key={employee.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="hover:bg-dark-800 transition-colors"
                    >
                      <td className="py-4">
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 bg-gradient-to-br from-neon-blue to-neon-purple rounded-full flex items-center justify-center">
                            <span className="text-white font-bold text-sm">
                              {employee.first_name[0]}{employee.last_name[0]}
                            </span>
                          </div>
                          <div>
                            <p className="text-white font-medium">{employee.first_name} {employee.last_name}</p>
                            <p className="text-gray-500 text-sm">{employee.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-4">
                        <span className="inline-block px-3 py-1 rounded-full text-xs font-medium bg-neon-blue/10 text-neon-blue border border-neon-blue/30 capitalize">
                          {employee.role}
                        </span>
                      </td>
                      <td className="py-4 text-right text-white font-medium">
                        {employee.total_hours.toFixed(1)} hrs
                      </td>
                      <td className="py-4 text-right text-gray-300">
                        ${employee.hourly_rate.toFixed(2)}/hr
                      </td>
                      <td className="py-4 text-right text-gray-300">
                        ${regularPay.toFixed(2)}
                      </td>
                      <td className="py-4 text-right">
                        {overtimeHours > 0 ? (
                          <span className="text-neon-amber font-medium">
                            ${overtimePay.toFixed(2)}
                          </span>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                      <td className="py-4 text-right">
                        <span className="text-neon-green font-bold text-lg">
                          ${totalPay.toFixed(2)}
                        </span>
                      </td>
                    </motion.tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Payroll History */}
      {periods.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
            <Calendar className="w-5 h-5 text-purple-500" />
            <span>Payroll History</span>
          </h2>
          <div className="space-y-3">
            {periods.slice(0, 10).map((period, index) => {
              const startDate = new Date(period.period_start)
              const endDate = new Date(period.period_end)

              return (
                <motion.div
                  key={period.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-center justify-between bg-dark-800/50 p-4 rounded-lg hover:bg-dark-800 transition-colors border border-dark-600"
                >
                  <div className="flex-1">
                    <p className="text-white font-medium">
                      {format(startDate, 'MMM d')} - {format(endDate, 'MMM d, yyyy')}
                    </p>
                    <p className="text-sm text-gray-400 mt-1">
                      {period.total_hours?.toFixed(1) || 0} hours · ${period.total_amount?.toFixed(2) || 0}
                    </p>
                  </div>
                  <div className="flex items-center space-x-4">
                    {period.run_date && (
                      <p className="text-xs text-gray-500">
                        Processed {format(new Date(period.run_date), 'MMM d, yyyy')}
                      </p>
                    )}
                    <span className={`px-3 py-1.5 rounded-lg text-xs font-medium border ${
                      period.status === 'completed'
                        ? 'bg-green-500/20 text-green-500 border-green-500/30'
                        : 'bg-amber-500/20 text-amber-500 border-amber-500/30'
                    }`}>
                      {period.status === 'completed' ? '✓ Processed' : 'Pending'}
                    </span>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      )}

      {/* Footer Note */}
      <div className="card bg-neon-blue/5 border-neon-blue/30">
        <div className="flex items-start space-x-3">
          <div className="w-10 h-10 bg-neon-blue/20 rounded-lg flex items-center justify-center flex-shrink-0">
            <Calendar className="w-5 h-5 text-neon-blue" />
          </div>
          <div>
            <p className="text-white font-medium mb-1">Overtime Calculation</p>
            <p className="text-gray-400 text-sm">
              Overtime hours (over 40 hours per month) are calculated at 1.5x the regular hourly rate.
              Export payroll data for detailed time sheets and audit trails.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
