import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../api/client'

interface User {
  telegram_id: number
  username?: string
  first_name: string
  is_admin: boolean
}

interface AuthState {
  token: string | null
  user: User | null
  isLoading: boolean
  error: string | null
  authenticate: (initData: string) => Promise<void>
  logout: () => void
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isLoading: false,
      error: null,

      authenticate: async (initData: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await api.post('/auth/telegram', {
            init_data: initData,
          })
          const { access_token, user } = response.data
          api.defaults.headers.common['Authorization'] =
            `Bearer ${access_token}`
          set({ token: access_token, user, isLoading: false })
        } catch (error: unknown) {
          console.error('Auth error:', error)
          set({ error: 'Authentication failed', isLoading: false })
        }
      },

      logout: () => {
        delete api.defaults.headers.common['Authorization']
        set({ token: null, user: null })
      },
    }),
    {
      name: 'mission-control-auth',
      partialize: (state) => ({ token: state.token }),
    }
  )
)

// Restore token from persisted state on load
const token = useAuth.getState().token
if (token) {
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`
}
