import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../api/client'

interface Partner {
  id: number
  telegram_id: number
  username: string | null
  first_name: string
  last_name: string | null
  status: string
  segment: string
  total_channels: number
  total_posts: number
  total_subscribers: number
  total_leads: number
  created_at: string
}

interface AuthState {
  token: string | null
  partner: Partner | null
  isLoading: boolean
  error: string | null
  isAuthenticated: boolean
  authenticate: (initData: string) => Promise<void>
  logout: () => void
  updatePartner: (partner: Partial<Partner>) => void
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      partner: null,
      isLoading: false,
      error: null,
      isAuthenticated: false,

      authenticate: async (initData: string) => {
        set({ isLoading: true, error: null })

        try {
          const response = await api.post('/auth/telegram', {
            init_data: initData,
          })

          const { access_token, partner } = response.data

          set({
            token: access_token,
            partner,
            isAuthenticated: true,
            isLoading: false,
          })

          // Set token for future requests
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

        } catch (error: any) {
          console.error('Auth error:', error)
          set({
            error: error.response?.data?.detail || 'Authentication failed',
            isLoading: false,
          })
        }
      },

      logout: () => {
        set({
          token: null,
          partner: null,
          isAuthenticated: false,
        })
        delete api.defaults.headers.common['Authorization']
      },

      updatePartner: (partialPartner: Partial<Partner>) => {
        const currentPartner = get().partner
        if (currentPartner) {
          set({
            partner: { ...currentPartner, ...partialPartner },
          })
        }
      },
    }),
    {
      name: 'nl-partner-auth',
      partialize: (state) => ({
        token: state.token,
        partner: state.partner,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        // Restore token in axios headers after rehydration
        if (state?.token) {
          api.defaults.headers.common['Authorization'] = `Bearer ${state.token}`
        }
      },
    }
  )
)
