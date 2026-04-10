import React, { useState } from "react"

/**
 * AuthGate -- Login/signup overlay for Stark AI.
 * Handles Supabase auth via the Stark API backend.
 */

const STARK_API = window.location.hostname === "localhost"
  ? "http://localhost:8511"
  : ""  // same origin on Oracle

export default function AuthGate({ onAuth, onSkip }) {
  const [mode, setMode] = useState("login") // login | signup
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [displayName, setDisplayName] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    try {
      const endpoint = mode === "login" ? "/api/stark/auth/login" : "/api/stark/auth/signup"
      const body = mode === "login"
        ? { email, password }
        : { email, password, display_name: displayName || email.split("@")[0] }

      const resp = await fetch(`${STARK_API}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      const data = await resp.json()

      if (!resp.ok || !data.ok) {
        setError(data.detail || data.error || "Authentication failed")
        return
      }

      if (mode === "login") {
        localStorage.setItem("stark_token", data.access_token)
        localStorage.setItem("stark_refresh", data.refresh_token || "")
        localStorage.setItem("stark_user", JSON.stringify({
          ...data.user,
          ...data.stark_profile,
        }))
        onAuth({
          token: data.access_token,
          user: { ...data.user, ...data.stark_profile },
        })
      } else {
        setMode("login")
        setError("")
        alert("Account created. Check your email to confirm, then log in.")
      }
    } catch (err) {
      setError("Connection failed. Is the Stark AI backend running?")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-[#0a0a0f]/95 backdrop-blur-md z-50 flex items-center justify-center">
      {/* Background effects */}
      <div className="absolute w-[500px] h-[500px] rounded-full bg-amber-500/[0.03] blur-[120px] animate-pulse" />
      <div className="absolute w-[300px] h-[300px] rounded-full bg-purple-500/[0.02] blur-[80px] animate-pulse" style={{ animationDelay: "1.5s" }} />

      <div className="relative w-full max-w-sm mx-4">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-amber-400 via-orange-500 to-red-600 flex items-center justify-center text-2xl font-black text-black shadow-2xl shadow-amber-500/20 mb-4">
            L
          </div>
          <div className="text-xl font-bold tracking-[0.3em] bg-gradient-to-r from-amber-300 via-orange-400 to-amber-300 bg-clip-text text-transparent">
            STARK AI
          </div>
          <div className="text-[10px] tracking-[0.2em] text-gray-600 mt-0.5">VOICE COMMAND CENTER</div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-6 space-y-4 backdrop-blur-sm">
          {/* Mode toggle */}
          <div className="flex rounded-lg bg-white/[0.03] border border-white/[0.04] p-0.5">
            {["login", "signup"].map(m => (
              <button
                key={m}
                type="button"
                onClick={() => { setMode(m); setError("") }}
                className={`flex-1 py-1.5 rounded-md text-[11px] font-medium tracking-wider transition-all ${
                  mode === m ? "bg-amber-400/10 text-amber-400 border border-amber-400/20" : "text-gray-500 hover:text-gray-300"
                }`}
              >
                {m === "login" ? "LOGIN" : "SIGN UP"}
              </button>
            ))}
          </div>

          {mode === "signup" && (
            <div>
              <label className="text-[9px] tracking-[0.15em] text-gray-500 block mb-1">DISPLAY NAME</label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Lucrex Jr."
                className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2 text-[12px] text-gray-200 placeholder:text-gray-600 outline-none focus:border-amber-400/20"
              />
            </div>
          )}

          <div>
            <label className="text-[9px] tracking-[0.15em] text-gray-500 block mb-1">EMAIL</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="king@everlightventures.io"
              className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2 text-[12px] text-gray-200 placeholder:text-gray-600 outline-none focus:border-amber-400/20"
            />
          </div>

          <div>
            <label className="text-[9px] tracking-[0.15em] text-gray-500 block mb-1">PASSWORD</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              placeholder="••••••••"
              className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2 text-[12px] text-gray-200 placeholder:text-gray-600 outline-none focus:border-amber-400/20"
            />
          </div>

          {error && (
            <div className="text-[10px] text-red-400 bg-red-400/5 border border-red-400/10 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg bg-gradient-to-r from-amber-500 to-orange-600 text-black text-[12px] font-bold tracking-wider hover:from-amber-400 hover:to-orange-500 disabled:opacity-50 transition-all shadow-lg shadow-amber-500/10"
          >
            {loading ? "AUTHENTICATING..." : mode === "login" ? "ENTER THE HIVE" : "CREATE ACCOUNT"}
          </button>
        </form>

        {/* Skip to demo */}
        <button
          onClick={onSkip}
          className="w-full mt-3 py-2 text-[10px] text-gray-600 hover:text-gray-400 transition-colors tracking-wider"
        >
          CONTINUE AS GUEST (LIMITED)
        </button>
      </div>
    </div>
  )
}
