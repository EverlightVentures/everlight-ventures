import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../utils/api'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      tenant: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      // Login
      login: async (email, password) => {
        try {
          const response = await api.post('/auth/login', { email, password })
          const { access_token, refresh_token, user, tenant } = response.data

          set({
            user,
            tenant,
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
          })

          // Set token in axios defaults
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

          return { success: true }
        } catch (error) {
          return {
            success: false,
            error: error.response?.data?.error || 'Login failed',
          }
        }
      },

      // Register
      register: async (data) => {
        try {
          const response = await api.post('/auth/register', data)
          const { access_token, refresh_token, user, tenant } = response.data

          set({
            user,
            tenant,
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
          })

          // Set token in axios defaults
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

          return { success: true }
        } catch (error) {
          return {
            success: false,
            error: error.response?.data?.error || 'Registration failed',
          }
        }
      },

      // Logout
      logout: () => {
        set({
          user: null,
          tenant: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })

        // Remove token from axios defaults
        delete api.defaults.headers.common['Authorization']
      },

      // Refresh token
      refreshAccessToken: async () => {
        try {
          const { refreshToken } = get()
          const response = await api.post('/auth/refresh', null, {
            headers: { Authorization: `Bearer ${refreshToken}` },
          })

          const { access_token } = response.data
          set({ accessToken: access_token })
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

          return true
        } catch (error) {
          get().logout()
          return false
        }
      },

      // Initialize auth from stored data
      initializeAuth: () => {
        const { accessToken } = get()
        if (accessToken) {
          api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
        }
      },
    }),
    {
      name: 'onyx-auth-storage',
      partialize: (state) => ({
        user: state.user,
        tenant: state.tenant,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
