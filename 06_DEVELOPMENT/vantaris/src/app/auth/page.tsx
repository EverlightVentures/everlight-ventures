'use client'

import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase, signInWithGoogle, getSession } from '@/lib/supabase'
import { useBlackjackStore } from '@/lib/blackjack-store'

export default function AuthPage() {
  const router = useRouter()
  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Check if already logged in
  useEffect(() => {
    getSession().then(session => {
      if (session) {
        const name = session.user.user_metadata?.display_name || session.user.email?.split('@')[0] || 'Player'
        localStorage.setItem('vantaris_player_name', name)
        localStorage.setItem('vantaris_welcomed', 'true')
        // VIP handled by AuthProvider
        router.push('/vantaris')
      }
    })
  }, [router])

  const handleLogin = async () => {
    if (!email || !password) { setError('Fill in all fields'); return }
    setLoading(true); setError('')
    try {
      const { data } = await supabase.auth.signInWithPassword({ email, password })
      if (data.user) {
        const name = data.user.user_metadata?.display_name || email.split('@')[0]
        localStorage.setItem('vantaris_player_name', name)
        localStorage.setItem('vantaris_welcomed', 'true')
        // VIP handled by AuthProvider
        router.push('/vantaris')
      }
    } catch (e: any) {
      setError(e.message || 'Login failed')
    }
    setLoading(false)
  }

  const handleRegister = async () => {
    if (!email || !password || !displayName) { setError('Fill in all fields'); return }
    setLoading(true); setError('')
    try {
      const { data, error: err } = await supabase.auth.signUp({
        email,
        password,
        options: { data: { display_name: displayName } },
      })
      if (err) throw err
      if (data.user) {
        localStorage.setItem('vantaris_player_name', displayName)
        localStorage.setItem('vantaris_welcomed', 'true')
        router.push('/vantaris')
      }
    } catch (e: any) {
      setError(e.message || 'Registration failed')
    }
    setLoading(false)
  }

  const handleGuest = () => {
    localStorage.setItem('vantaris_player_name', 'Guest')
    localStorage.setItem('vantaris_welcomed', 'true')
    router.push('/vantaris')
  }

  const handleGoogle = async () => {
    setLoading(true)
    try {
      await signInWithGoogle()
    } catch (e: any) {
      setError(e.message || 'Google login failed')
      setLoading(false)
    }
  }

  const inputStyle = {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.08)',
    color: '#eee',
    borderRadius: '12px',
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'linear-gradient(180deg, #08080c, #0a0a10)' }}>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">

        {/* Logo */}
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold tracking-[0.3em] mb-2" style={{
            fontFamily: "'Cormorant Garamond', serif",
            background: 'linear-gradient(180deg, #E8D48B, #D4AF37, #996515)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>VANTARIS</h1>
          <p className="text-[10px] uppercase tracking-[0.3em]" style={{ color: '#555' }}>The darkest star burns brightest.</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl p-7 relative overflow-hidden" style={{
          background: 'linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015))',
          backdropFilter: 'blur(40px)',
          border: '1px solid rgba(255,255,255,0.06)',
          boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06)',
        }}>
          <div className="absolute top-0 left-0 right-0 h-px" style={{ background: 'linear-gradient(90deg, transparent 10%, rgba(255,255,255,0.08) 50%, transparent 90%)' }} />

          {/* Google OAuth -- primary CTA */}
          <motion.button onClick={handleGoogle} disabled={loading}
            className="w-full py-3.5 rounded-xl text-sm font-semibold tracking-wide flex items-center justify-center gap-3 mb-6"
            style={{ background: '#fff', color: '#333' }}
            whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.98 }}>
            <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            Continue with Google
          </motion.button>

          {/* Divider */}
          <div className="flex items-center gap-3 mb-6">
            <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.06)' }} />
            <span className="text-[10px] uppercase tracking-[0.2em]" style={{ color: '#555' }}>or</span>
            <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.06)' }} />
          </div>

          {/* Tabs */}
          <div className="flex mb-6">
            {(['login', 'register'] as const).map(t => (
              <button key={t} onClick={() => { setTab(t); setError('') }}
                className="flex-1 py-2 text-[11px] uppercase tracking-[0.2em]"
                style={{
                  color: tab === t ? '#D4AF37' : '#555',
                  borderBottom: tab === t ? '1px solid #D4AF37' : '1px solid transparent',
                }}>
                {t === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          {/* Error */}
          {error && (
            <p className="text-xs text-red-400 mb-4 text-center">{error}</p>
          )}

          {/* Form */}
          <div className="space-y-3">
            {tab === 'register' && (
              <input type="text" placeholder="Display name" value={displayName}
                onChange={e => setDisplayName(e.target.value)}
                className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />
            )}
            <input type="email" placeholder="Email" value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />
            <input type="password" placeholder="Password" value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && (tab === 'login' ? handleLogin() : handleRegister())}
              className="w-full px-4 py-3 text-sm outline-none" style={inputStyle} />

            <motion.button
              onClick={tab === 'login' ? handleLogin : handleRegister}
              disabled={loading}
              className="w-full py-3 rounded-xl text-xs font-semibold tracking-[0.2em] uppercase"
              style={{ background: '#D4AF37', color: '#0A0A0A', opacity: loading ? 0.6 : 1 }}
              whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.98 }}>
              {loading ? '...' : tab === 'login' ? 'Sign In' : 'Create Account'}
            </motion.button>
          </div>

          {/* Guest */}
          <div className="mt-4 text-center">
            <button onClick={handleGuest} className="text-[11px] tracking-wide" style={{ color: '#555' }}>
              Continue as Guest
            </button>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center mt-6 text-[10px]" style={{ color: '#333' }}>
          An Everlight Ventures Experience
        </p>
      </motion.div>
    </div>
  )
}
