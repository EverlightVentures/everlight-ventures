import { useState, useEffect } from 'react'
import { Users, Plus, Edit2, Trash2, Search, Mail, Phone, Shield, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { format } from 'date-fns'
import api from '../utils/api'
import { useAuthStore } from '../store/authStore'

export default function Employees() {
  const { user } = useAuthStore()
  const [employees, setEmployees] = useState([])
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingEmployee, setEditingEmployee] = useState(null)
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    role: 'cashier',
    phone: '',
    hourly_rate: '',
  })

  useEffect(() => {
    fetchEmployees()
  }, [])

  const fetchEmployees = async () => {
    try {
      const response = await api.get('/employees')
      setEmployees(response.data.employees || [])
    } catch (error) {
      console.error('Failed to fetch employees:', error)
      toast.error('Failed to load employees')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (editingEmployee) {
        await api.put(`/employees/${editingEmployee.id}`, formData)
        toast.success('Employee updated successfully!')
      } else {
        await api.post('/employees', formData)
        toast.success('Employee added successfully!')
      }
      setShowModal(false)
      resetForm()
      fetchEmployees()
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to save employee')
    }
  }

  const handleEdit = (employee) => {
    setEditingEmployee(employee)
    setFormData({
      email: employee.email,
      password: '',
      first_name: employee.first_name,
      last_name: employee.last_name,
      role: employee.role,
      phone: employee.phone || '',
      hourly_rate: employee.hourly_rate || '',
    })
    setShowModal(true)
  }

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this employee?')) return

    try {
      await api.delete(`/employees/${id}`)
      toast.success('Employee deleted successfully!')
      fetchEmployees()
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to delete employee')
    }
  }

  const resetForm = () => {
    setFormData({
      email: '',
      password: '',
      first_name: '',
      last_name: '',
      role: 'cashier',
      phone: '',
      hourly_rate: '',
    })
    setEditingEmployee(null)
  }

  const filteredEmployees = employees.filter(emp =>
    `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(search.toLowerCase()) ||
    emp.email.toLowerCase().includes(search.toLowerCase()) ||
    emp.role.toLowerCase().includes(search.toLowerCase())
  )

  const roleColors = {
    owner: 'from-neon-purple to-neon-pink',
    manager: 'from-neon-blue to-neon-cyan',
    cashier: 'from-neon-green to-neon-blue',
    laborer: 'from-neon-amber to-neon-orange',
  }

  const roleBadgeColors = {
    owner: 'bg-neon-purple/10 text-neon-purple border-neon-purple/30',
    manager: 'bg-neon-blue/10 text-neon-blue border-neon-blue/30',
    cashier: 'bg-neon-green/10 text-neon-green border-neon-green/30',
    laborer: 'bg-neon-amber/10 text-neon-amber border-neon-amber/30',
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Employee Management</h1>
          <p className="text-gray-400 mt-1">Manage your team members</p>
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
            <span>Add Employee</span>
          </button>
        )}
      </div>

      {/* Search */}
      <div className="card">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-12"
            placeholder="Search by name, email, or role..."
          />
        </div>
      </div>

      {/* Employee Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredEmployees.map((employee) => (
          <motion.div
            key={employee.id}
            whileHover={{ y: -4 }}
            className="card group"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center space-x-3">
                <div className={`w-14 h-14 bg-gradient-to-br ${roleColors[employee.role]} rounded-full flex items-center justify-center shadow-lg`}>
                  <span className="text-white font-bold text-lg">
                    {employee.first_name[0]}{employee.last_name[0]}
                  </span>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">
                    {employee.first_name} {employee.last_name}
                  </h3>
                  <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium border ${roleBadgeColors[employee.role]}`}>
                    {employee.role}
                  </span>
                </div>
              </div>

              {(user?.role === 'owner' || user?.role === 'manager') && employee.role !== 'owner' && (
                <div className="flex space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleEdit(employee)}
                    className="p-2 text-gray-400 hover:text-neon-blue hover:bg-dark-800 rounded-lg transition-colors"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(employee.id)}
                    className="p-2 text-gray-400 hover:text-red-500 hover:bg-dark-800 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center space-x-2 text-gray-400 text-sm">
                <Mail className="w-4 h-4" />
                <span>{employee.email}</span>
              </div>
              {employee.phone && (
                <div className="flex items-center space-x-2 text-gray-400 text-sm">
                  <Phone className="w-4 h-4" />
                  <span>{employee.phone}</span>
                </div>
              )}
              {employee.hourly_rate && (
                <div className="flex items-center justify-between pt-2 border-t border-dark-700">
                  <span className="text-gray-400 text-sm">Hourly Rate</span>
                  <span className="text-neon-green font-medium">${employee.hourly_rate}/hr</span>
                </div>
              )}
              <div className="flex items-center justify-between pt-2 border-t border-dark-700">
                <span className="text-gray-400 text-sm">Status</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  employee.is_active
                    ? 'bg-neon-green/10 text-neon-green border border-neon-green/30'
                    : 'bg-red-500/10 text-red-500 border border-red-500/30'
                }`}>
                  {employee.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </motion.div>
        ))}

        {filteredEmployees.length === 0 && (
          <div className="col-span-full text-center py-12 card">
            <Users className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-500 text-lg">No employees found</p>
            <p className="text-gray-600 text-sm mt-1">Try adjusting your search</p>
          </div>
        )}
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
              <div className="bg-dark-900 border border-dark-600 rounded-xl p-6 max-w-md w-full max-h-[90vh] overflow-auto">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold text-white">
                    {editingEmployee ? 'Edit Employee' : 'Add New Employee'}
                  </h2>
                  <button
                    onClick={() => setShowModal(false)}
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        First Name
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.first_name}
                        onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                        className="input"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Last Name
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.last_name}
                        onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                        className="input"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Email
                    </label>
                    <input
                      type="email"
                      required
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="input"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Password {editingEmployee && '(leave blank to keep current)'}
                    </label>
                    <input
                      type="password"
                      required={!editingEmployee}
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      className="input"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Phone (optional)
                    </label>
                    <input
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      className="input"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Role
                      </label>
                      <select
                        value={formData.role}
                        onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                        className="input"
                      >
                        <option value="cashier">Cashier</option>
                        <option value="laborer">Laborer</option>
                        {user?.role === 'owner' && <option value="manager">Manager</option>}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Hourly Rate ($)
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={formData.hourly_rate}
                        onChange={(e) => setFormData({ ...formData, hourly_rate: e.target.value })}
                        className="input"
                      />
                    </div>
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
                      {editingEmployee ? 'Update' : 'Add'} Employee
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
