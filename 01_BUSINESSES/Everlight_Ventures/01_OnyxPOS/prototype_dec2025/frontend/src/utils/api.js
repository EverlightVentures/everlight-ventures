import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor to handle FormData
api.interceptors.request.use(
  (config) => {
    // If sending FormData, remove Content-Type to let browser set it with boundary
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If 401 and not already retried, check for specific error codes
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      // Check if it's an invalid role error
      const errorCode = error.response?.data?.code
      if (errorCode === 'INVALID_ROLE') {
        // Force logout - the token is invalid
        const { useAuthStore } = await import('../store/authStore')
        useAuthStore.getState().logout()
        window.location.href = '/login'
        return Promise.reject(error)
      }

      // Try to refresh token
      try {
        const { useAuthStore } = await import('../store/authStore')
        const success = await useAuthStore.getState().refreshAccessToken()

        if (success) {
          return api(originalRequest)
        }
      } catch (refreshError) {
        const { useAuthStore } = await import('../store/authStore')
        useAuthStore.getState().logout()
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

export default api
