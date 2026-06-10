// Typed-ish API client for the Hive Directory backend on :8503.
// API_BASE honors Vite base so requests work both at root and behind /hive/.

const API_BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '') + '/api'

export async function fetchTeam() {
  const r = await fetch(API_BASE + '/team')
  if (!r.ok) throw new Error('fetchTeam failed: ' + r.status)
  return r.json()
}

export async function fetchEmployee(slug) {
  const r = await fetch(API_BASE + '/team/' + encodeURIComponent(slug))
  if (!r.ok) throw new Error('fetchEmployee failed: ' + r.status)
  return r.json()
}

export async function fetchDossier(slug) {
  const r = await fetch(API_BASE + '/team/' + encodeURIComponent(slug) + '/dossier')
  if (!r.ok) throw new Error('fetchDossier failed: ' + r.status)
  return r.json()
}

export async function searchTeam(params = {}) {
  const u = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return
    u.set(k, String(v))
  })
  const r = await fetch(API_BASE + '/team/search?' + u.toString())
  if (!r.ok) throw new Error('searchTeam failed: ' + r.status)
  return r.json()
}

export async function dispatchAgent(slug, body = {}) {
  const r = await fetch(API_BASE + '/team/' + encodeURIComponent(slug) + '/dispatch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error('dispatchAgent failed: ' + r.status)
  return r.json()
}

export async function fetchDepartments() {
  const r = await fetch(API_BASE + '/departments')
  if (!r.ok) throw new Error('fetchDepartments failed: ' + r.status)
  return r.json()
}

export async function fetchZodiacArchetypes() {
  const r = await fetch(API_BASE + '/archetypes/zodiac')
  if (!r.ok) return {}
  return r.json()
}

export async function fetchMbtiArchetypes() {
  const r = await fetch(API_BASE + '/archetypes/mbti')
  if (!r.ok) return {}
  return r.json()
}
