import React from 'react'
import { Link, Route, Routes, useNavigate, useSearchParams } from 'react-router-dom'
import TeamDirectory from './pages/TeamDirectory.jsx'
import EmployeeProfile from './pages/EmployeeProfile.jsx'

function HeaderSearch() {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const value = params.get('q') || ''
  const onChange = (e) => {
    const v = e.target.value
    if (window.location.pathname !== '/') navigate('/')
    const next = new URLSearchParams(params)
    if (v) next.set('q', v)
    else next.delete('q')
    setParams(next, { replace: true })
  }
  return (
    <input
      type="text"
      value={value}
      onChange={onChange}
      placeholder="Search the Hive..."
      className="bg-[#12121a] border border-[#1e1e2e] rounded-lg px-3 py-1.5 text-xs placeholder:text-gray-600 focus:outline-none focus:border-amber-400/40 min-w-[220px]"
    />
  )
}

function Header() {
  return (
    <header className="sticky top-0 z-40 backdrop-blur-md bg-[#0a0a0f]/85 border-b border-white/5">
      <div className="max-w-7xl mx-auto px-5 py-3 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2">
          <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-amber-400 to-amber-700 flex items-center justify-center text-black font-bold text-xs">
            H
          </span>
          <div className="leading-tight">
            <div className="text-sm font-bold tracking-wide">
              HIVE <span className="text-amber-400">DIRECTORY</span>
            </div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-gray-600">
              Everlight Ventures
            </div>
          </div>
        </Link>
        <HeaderSearch />
      </div>
    </header>
  )
}

export default function App() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="max-w-7xl mx-auto px-5 py-6">
        <Routes>
          <Route path="/" element={<TeamDirectory />} />
          <Route path="/team/:slug" element={<EmployeeProfile />} />
          <Route
            path="*"
            element={
              <div className="text-gray-500 text-sm">
                Not found. <Link to="/" className="text-amber-400">Back.</Link>
              </div>
            }
          />
        </Routes>
      </main>
    </div>
  )
}
