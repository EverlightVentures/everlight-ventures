const API_BASE = '/api'

function getHeaders() {
  const tenantId = localStorage.getItem('onyx_tenant_id')
  const token = localStorage.getItem('onyx_token')
  return {
    'Content-Type': 'application/json',
    'X-Tenant-Id': tenantId || '',
    'Authorization': token ? `Bearer ${token}` : '',
  }
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: getHeaders(),
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(err.detail || err.message || 'Request failed')
  }
  return res.json()
}

export const auth = {
  login: (email, password) => api('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  signup: (data) => api('/auth/signup', { method: 'POST', body: JSON.stringify(data) }),
  pinLogin: (tenant_id, pin) => api('/auth/pin-login', { method: 'POST', body: JSON.stringify({ tenant_id, pin }) }),
}

export const employees = {
  list: () => api('/employees'),
  create: (data) => api('/employees', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => api(`/employees/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
}

export const products = {
  list: () => api('/products'),
  create: (data) => api('/products', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => api(`/products/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
}

export const categories = {
  list: () => api('/categories'),
  create: (data) => api('/categories', { method: 'POST', body: JSON.stringify(data) }),
}

export const sales = {
  create: (data) => api('/sales', { method: 'POST', body: JSON.stringify(data) }),
  list: (days = 7) => api(`/sales?days=${days}`),
  get: (id) => api(`/sales/${id}`),
}

export const reports = {
  daily: (date) => api(`/reports/daily${date ? `?report_date=${date}` : ''}`),
  topProducts: (days = 30) => api(`/reports/top-products?days=${days}`),
}

export const timeclock = {
  punch: (data) => api('/timeclock/punch', { method: 'POST', body: JSON.stringify(data) }),
  status: (employeeId) => api(`/timeclock/status/${employeeId}`),
  hours: (days = 7) => api(`/timeclock/hours?days=${days}`),
}

export const chat = {
  send: (message, employee_id) => api('/chat', { method: 'POST', body: JSON.stringify({ message, employee_id }) }),
}

export const billing = {
  createCheckout: () => api('/billing/create-checkout', { method: 'POST' }),
}
