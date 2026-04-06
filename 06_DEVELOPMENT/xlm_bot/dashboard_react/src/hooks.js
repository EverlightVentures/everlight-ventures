import { useState, useEffect, useRef, useCallback } from "react"

export function useApi(path, interval = 5000) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const mounted = useRef(true)

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(path)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      if (mounted.current) {
        setData(json)
        setError(null)
      }
    } catch (err) {
      if (mounted.current) setError(err.message)
    }
  }, [path])

  useEffect(() => {
    mounted.current = true
    fetchData()
    const timer = setInterval(fetchData, interval)
    return () => {
      mounted.current = false
      clearInterval(timer)
    }
  }, [fetchData, interval])

  return { data, error }
}

export function formatUSD(val) {
  if (val == null || isNaN(val)) return "$0.00"
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val)
}

export function formatPrice(val) {
  if (val == null || isNaN(val)) return "0.0000"
  return parseFloat(val).toFixed(4)
}

export function formatTime(ts) {
  if (!ts) return "--"
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false, timeZone: "America/Los_Angeles" })
  } catch { return "--" }
}

export function timeAgo(ts) {
  if (!ts) return "--"
  const now = Date.now()
  const then = new Date(ts).getTime()
  const diff = Math.max(0, now - then)
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}
