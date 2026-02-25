import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      console.log('Unauthorized, clearing auth...')
    }
    return Promise.reject(error)
  }
)

// API types
export interface Product {
  key: string
  name: string
  price: number
  pv: number
  category: string
  line?: string
  price_per_portion?: number
  description?: string
  image_url?: string
  image_count?: number
  referral_link: string
}

export interface Line {
  name: string
  product_count: number
  image_url?: string
}

export interface ProductsResponse {
  total: number
  categories: string[]
  products: Product[]
  referral_catalog: string
}

export interface Category {
  name: string
  product_count: number
}

export interface BusinessPresentation {
  headline: string
  tagline: string
  traditional_model: {
    title: string
    subtitle: string
    items: { icon: string; text: string }[]
  }
  apexflow_model: {
    title: string
    subtitle: string
    items: { icon: string; text: string }[]
  }
  requirements: {
    number: number
    title: string
    items: string[]
  }
  cta: {
    telegram_chat: string
    registration: string
    telegram_username: string
  }
}

// API functions
export const productsApi = {
  getProducts: (params?: { category?: string; line?: string; search?: string; limit?: number; offset?: number }) =>
    api.get<ProductsResponse>('/products', { params }),

  getProduct: (key: string) =>
    api.get<Product>(`/products/${key}`),

  getCategories: () =>
    api.get<{ categories: Category[] }>('/products/categories'),

  getLines: (category?: string) =>
    api.get<{ lines: Line[] }>('/products/lines', { params: category ? { category } : undefined }),

  trackView: (key: string, clickedLink: boolean = false) =>
    api.post(`/products/${key}/view`, null, { params: { clicked_link: clickedLink } }),

  getReferralLinks: () =>
    api.get<{
      registration: string
      catalog: string
      promo: string
      new_products: string
      starter_kits: string
    }>('/products/links/referral'),
}

export const businessApi = {
  getPresentation: () =>
    api.get<BusinessPresentation>('/business/presentation'),

  trackContact: (action: 'telegram_chat' | 'registration' | 'view_business') =>
    api.post<{ success: boolean; redirect: string }>('/business/contact', { action }),

  getPartnerStatus: () =>
    api.get<{
      is_partner: boolean
      partner_registered_at?: string
      has_access_to_panel: boolean
    }>('/business/partner-status'),

  markAsPartner: () =>
    api.post('/business/mark-partner'),
}
