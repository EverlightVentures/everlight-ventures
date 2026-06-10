import { useCallback, useEffect, useState } from 'react'

// Prefix API calls with the Vite base so the app works both at root (/) and
// behind nginx subpath routing (/hive/). BASE_URL always has a trailing slash.
const API_BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '') + '/api'

export function useApi(endpoint, pollMs = 0) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const r = await fetch(API_BASE + endpoint)
      if (!r.ok) throw new Error(String(r.status))
      const j = await r.json()
      setData(j)
      setError(null)
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }, [endpoint])

  useEffect(() => {
    let alive = true
    const run = async () => {
      await load()
      if (!alive) return
    }
    run()
    if (pollMs > 0) {
      const t = setInterval(load, pollMs)
      return () => {
        alive = false
        clearInterval(t)
      }
    }
    return () => {
      alive = false
    }
  }, [load, pollMs])

  return { data, error, loading, refetch: load }
}

export function useQueryParamState(key, initial = '') {
  const url = new URL(window.location.href)
  const [value, setValue] = useState(url.searchParams.get(key) ?? initial)
  useEffect(() => {
    const u = new URL(window.location.href)
    if (value) u.searchParams.set(key, value)
    else u.searchParams.delete(key)
    window.history.replaceState(null, '', u.toString())
  }, [key, value])
  return [value, setValue]
}
