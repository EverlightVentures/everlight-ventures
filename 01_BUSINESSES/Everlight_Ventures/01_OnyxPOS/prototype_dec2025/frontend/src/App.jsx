import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useEffect } from 'react'
import { useAuthStore } from './store/authStore'

// Pages
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import SalesTerminal from './pages/SalesTerminal'
import Inventory from './pages/Inventory'
import TimeClock from './pages/TimeClock'
import Employees from './pages/Employees'
import Schedule from './pages/Schedule'
import Payroll from './pages/Payroll'
import TimeOff from './pages/TimeOff'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'
import Billing from './pages/Billing'
import PlatformRevenue from './pages/PlatformRevenue'

// Layout
import Layout from './components/Layout'

// Protected Route Component
function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Layout>{children}</Layout>
}

// Owner-only Route
function OwnerRoute({ children }) {
  const { user, isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (user?.role !== 'owner') {
    return <Navigate to="/dashboard" replace />
  }

  return <Layout>{children}</Layout>
}

function App() {
  const initializeAuth = useAuthStore((state) => state.initializeAuth)

  // Initialize auth on app mount to ensure token is set in axios headers
  useEffect(() => {
    initializeAuth()
  }, [initializeAuth])

  return (
    <>
      <Router>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          {/* Protected routes */}
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />

          <Route path="/sales" element={
            <ProtectedRoute>
              <SalesTerminal />
            </ProtectedRoute>
          } />

          <Route path="/inventory" element={
            <ProtectedRoute>
              <Inventory />
            </ProtectedRoute>
          } />

          <Route path="/analytics" element={
            <ProtectedRoute>
              <Analytics />
            </ProtectedRoute>
          } />

          <Route path="/timeclock" element={
            <ProtectedRoute>
              <TimeClock />
            </ProtectedRoute>
          } />

          <Route path="/employees" element={
            <ProtectedRoute>
              <Employees />
            </ProtectedRoute>
          } />

          <Route path="/schedule" element={
            <ProtectedRoute>
              <Schedule />
            </ProtectedRoute>
          } />

          <Route path="/payroll" element={
            <ProtectedRoute>
              <Payroll />
            </ProtectedRoute>
          } />

          <Route path="/timeoff" element={
            <ProtectedRoute>
              <TimeOff />
            </ProtectedRoute>
          } />

          <Route path="/settings" element={
            <ProtectedRoute>
              <Settings />
            </ProtectedRoute>
          } />

          {/* Owner-only routes */}
          <Route path="/billing" element={
            <OwnerRoute>
              <Billing />
            </OwnerRoute>
          } />

          <Route path="/platform-revenue" element={
            <OwnerRoute>
              <PlatformRevenue />
            </OwnerRoute>
          } />

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Router>

      {/* Toast notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1a1a1a',
            color: '#fff',
            border: '1px solid #2d2d2d',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </>
  )
}

export default App
