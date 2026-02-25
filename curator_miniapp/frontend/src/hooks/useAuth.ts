import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../api/client'

interface User {
  id: number
  telegram_id: number
  username?: string
  first_name: string
  last_name?: string
  is_partner: boolean
  products_viewed: number
  business_section_viewed: boolean
  visits_count: number
  created_at: string
}

interface AuthState {
  token: string | null
  user: User | null
  isLoading: boolean
  error: string | null
  setToken: (token: string) => void
  setUser: (user: User) => void
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

      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),

      authenticate: async (initData: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await api.post('/auth/telegram', { init_data: initData })
          const { access_token, user } = response.data

          // Set token for future requests
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

          set({
            token: access_token,
            user,
            isLoading: false,
          })
        } catch (error: unknown) {
          console.error('Authentication error:', error)
          set({
            error: 'Ошибка авторизации',
            isLoading: false,
          })
        }
      },

      logout: () => {
        delete api.defaults.headers.common['Authorization']
        set({ token: null, user: null })
      },
    }),
    {
      name: 'curator-auth',
      partialize: (state) => ({ token: state.token }),
    }
  )
)

// Restore token on init
const token = useAuth.getState().token
if (token) {
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`
}
