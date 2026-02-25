import axios from 'axios'

// API base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Token is set in useAuth store
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 || error.response?.status === 422) {
      // Handle unauthorized or missing auth - clear token
      console.error('Auth error, clearing token')
      delete api.defaults.headers.common['Authorization']
      // Clear persisted auth state
      try {
        localStorage.removeItem('nl-partner-auth')
        // Reload to trigger re-authentication
        window.location.reload()
      } catch (e) {
        console.error('Failed to clear auth', e)
      }
    }
    return Promise.reject(error)
  }
)

// API functions
export const authApi = {
  authenticate: (initData: string) =>
    api.post('/auth/telegram', { init_data: initData }),
  getMe: () => api.get('/auth/me'),
}

export const credentialsApi = {
  list: () => api.get('/credentials'),
  create: (data: {
    phone: string
    session_string: string
    api_id?: number
    api_hash?: string
    proxy_type?: string
    proxy_host?: string
    proxy_port?: number
    proxy_username?: string
    proxy_password?: string
  }) => api.post('/credentials', data),
  delete: (id: number) => api.delete(`/credentials/${id}`),
  validate: (sessionString: string) =>
    api.post('/credentials/validate', { session_string: sessionString }),
  getSetupProgress: (id: number) =>
    api.get(`/credentials/${id}/setup-progress`),
}

export const channelsApi = {
  list: () => api.get('/channels'),
  create: (data: {
    credentials_id: number
    title?: string
    segment: string
    referral_link?: string
    posts_per_day?: number
  }) => api.post('/channels', data),
  get: (id: number) => api.get(`/channels/${id}`),
  update: (id: number, data: Partial<{
    title: string
    posting_enabled: boolean
    posts_per_day: number
    posting_times: string[]
    referral_link: string
  }>) => api.patch(`/channels/${id}`, data),
  delete: (id: number) => api.delete(`/channels/${id}`),
  pause: (id: number) => api.post(`/channels/${id}/pause`),
  resume: (id: number) => api.post(`/channels/${id}/resume`),
  getStats: (id: number, period?: string) =>
    api.get(`/channels/${id}/stats`, { params: { period } }),
  generatePost: (id: number) => api.post(`/channels/${id}/generate-post`),
  publishNow: (id: number, postId?: number) =>
    api.post(`/channels/${id}/publish-now`, { post_id: postId }),
}

export const statsApi = {
  getOverview: () => api.get('/stats/overview'),
  getDaily: (days?: number) =>
    api.get('/stats/daily', { params: { days } }),
  getLeads: (params?: { status?: string; limit?: number; offset?: number }) =>
    api.get('/stats/leads', { params }),
  getTopPosts: (params?: { period?: string; limit?: number }) =>
    api.get('/stats/top-posts', { params }),
  export: (format: 'csv' | 'xlsx', period?: string) =>
    api.get('/stats/export', { params: { format, period } }),
}

export const trafficApi = {
  getOverview: () => api.get('/traffic/overview'),
  getChannels: () => api.get('/traffic/channels'),
  getStrategies: () => api.get('/traffic/strategies'),
  getDaily: (days?: number) =>
    api.get('/traffic/daily', { params: { days } }),
  getChannel: (username: string) =>
    api.get(`/traffic/channel/${username}`),
}
