'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { djangoLogin, djangoRegister, djangoGuestLogin, loadProfile, IS_PRODUCTION } from '@/lib/django-sync'
import { useBlackjackStore } from '@/lib/blackjack-store'

/**
 * Vantaris Auth Page
 *
 * Login / Register / Guest / Google OAuth
 * On production: hits Django endpoints
 * On dev: skips to lobby with localStorage data
 */

export default function AuthPage() {
  const router = useRouter()
  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
    if (!username || !password) { setError('Fill in all fields'); return }
    setLoading(true); setError('')

    if (IS_PRODUCTION) {
      const ok = await djangoLogin(username, password)
      if (!ok) { setError('Invalid credentials'); setLoading(false); return }
      // Load profile from server
      const profile = await loadProfile()
      if (profile) {
        useBlackjackStore.setState({
          player: {
            ...useBlackjackStore.getState().player,
            chips: profile.chips,
            gems: profile.gems,
            sweepsCoins: profile.sweeps_coins,
            xp: profile.xp,
            rank: profile.rank,
            handsPlayed: profile.hands_played,
            handsWon: profile.hands_won,
            blackjacks: profile.blackjacks,
            bestStreak: profile.best_streak,
            biggestWin: profile.biggest_win,
            presenceMultiplier: profile.presence_multiplier,
            unlockedAchievements: profile.achievements,
            ownedItems: profile.owned_items,
          },
        })
      }
    }

    localStorage.setItem('vantaris_player_name', username)
    localStorage.setItem('vantaris_welcomed', 'true')
    setLoading(false)
    router.push('/lobby')
  }

  const handleRegister = async () => {
    if (!username || !email || !password) { setError('Fill in all fields'); return }
    setLoading(true); setError('')

    if (IS_PRODUCTION) {
      const ok = await djangoRegister(username, email, password)
      if (!ok) { setError('Registration failed'); setLoading(false); return }
    }

    localStorage.setItem('vantaris_player_name', username)
    localStorage.setItem('vantaris_welcomed', 'true')
    setLoading(false)
    router.push('/lobby')
  }

  const handleGuest = async () => {
    setLoading(true)
    if (IS_PRODUCTION) await djangoGuestLogin()
    localStorage.setItem('vantaris_player_name', 'Guest')
    localStorage.setItem('vantaris_welcomed', 'true')
    setLoading(false)
    router.push('/lobby')
  }

  const handleGoogle = () => {
    if (IS_PRODUCTION) {
      // Django-allauth Google OAuth redirect
      window.location.href = '/accounts/google/login/'
    } else {
      handleGuest()
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'var(--vanta-void)' }}>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md">

        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold tracking-widest mb-2" style={{
            fontFamily: "'Cinzel', serif",
            background: 'linear-gradient(135deg, #c9a84c, #e8c55a)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>VANTARIS</h1>
          <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>The darkest star burns brightest.</p>
        </div>

        {/* Card */}
        <div className="glass-elevated rounded-2xl p-6">
          {/* Tabs */}
          <div className="flex mb-6">
            {(['login', 'register'] as const).map(t => (
              <button key={t} onClick={() => { setTab(t); setError('') }}
                className="flex-1 py-2 text-sm uppercase tracking-wider"
                style={{
                  color: tab === t ? 'var(--gold)' : 'var(--text-tertiary)',
                  borderBottom: tab === t ? '2px solid var(--gold)' : '2px solid transparent',
                  fontFamily: "'Cinzel', serif",
                }}>
                {t === 'login' ? 'SIGN IN' : 'REGISTER'}
              </button>
            ))}
          </div>

          {/* Error */}
          {error && (
            <p className="text-xs text-center mb-4 px-3 py-2 rounded-lg"
              style={{ background: 'rgba(255,45,85,0.1)', color: 'var(--loss)' }}>{error}</p>
          )}

          {/* Form */}
          <div className="space-y-3">
            <input type="text" value={username} onChange={e => setUsername(e.target.value)}
              placeholder="Username" autoComplete="username"
              className="w-full bg-transparent border rounded-xl px-4 py-3 text-sm outline-none"
              style={{ borderColor: 'var(--vanta-border)', color: '#fff' }} />

            {tab === 'register' && (
              <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                placeholder="Email" autoComplete="email"
                className="w-full bg-transparent border rounded-xl px-4 py-3 text-sm outline-none"
                style={{ borderColor: 'var(--vanta-border)', color: '#fff' }} />
            )}

            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="Password" autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
              className="w-full bg-transparent border rounded-xl px-4 py-3 text-sm outline-none"
              style={{ borderColor: 'var(--vanta-border)', color: '#fff' }}
              onKeyDown={e => e.key === 'Enter' && (tab === 'login' ? handleLogin() : handleRegister())} />

            <motion.button
              onClick={tab === 'login' ? handleLogin : handleRegister}
              disabled={loading}
              className="w-full py-3 rounded-xl text-sm font-bold tracking-widest"
              style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif" }}
              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
              {loading ? 'Loading...' : tab === 'login' ? 'SIGN IN' : 'CREATE ACCOUNT'}
            </motion.button>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px" style={{ background: 'var(--vanta-border)' }} />
            <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>or</span>
            <div className="flex-1 h-px" style={{ background: 'var(--vanta-border)' }} />
          </div>

          {/* Social / Guest */}
          <div className="space-y-2">
            <button onClick={handleGoogle}
              className="w-full py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2"
              style={{ background: 'rgba(255,255,255,0.06)', color: '#fff', border: '1px solid var(--vanta-border)' }}>
              <span>G</span> Continue with Google
            </button>

            <button onClick={handleGuest}
              className="w-full py-3 rounded-xl text-sm flex items-center justify-center gap-2"
              style={{ color: 'var(--text-tertiary)' }}>
              Play as Guest
            </button>
          </div>

          <p className="text-[9px] text-center mt-4" style={{ color: 'var(--text-tertiary)' }}>
            By signing in you agree to our Terms of Service and confirm you are 18+.
            Gold Coins have no cash value. See <a href="/rules" className="underline">Sweepstakes Rules</a>.
          </p>
        </div>
      </motion.div>
    </div>
  )
}
