import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.log('Unauthorized, clearing auth...')
    }
    return Promise.reject(error)
  }
)

// ── Types ──

export interface Post {
  id: number
  content: string
  post_type: string
  status: string
  segment?: string
  views_count: number
  reactions_count: number
  forwards_count: number
  engagement_rate?: number
  generated_at?: string
  published_at?: string
  scheduled_for?: string
  ai_model?: string
}

export interface DashboardData {
  total_posts: number
  published_today: number
  avg_engagement?: number
  pending_count: number
  type_breakdown: { type: string; count: number; avg_engagement?: number }[]
}

export interface TimelinePoint {
  date: string
  engagement_rate?: number
  posts_count: number
}

export interface TopPost {
  id: number
  post_type: string
  preview: string
  views: number
  reactions: number
  engagement_rate?: number
}

export interface Account {
  id: number
  phone: string
  first_name: string
  username?: string
  segment?: string
  status: string
  daily_comments: number
  daily_invites: number
  daily_story_views: number
  daily_story_reactions: number
  last_used_at?: string
  warmup_completed: boolean
  linked_channel_username?: string
}

export interface TodayStats {
  comments_ok: number
  comments_fail: number
  stories: number
  invites: number
  replies: number
}

export interface TrafficOverview {
  accounts: Account[]
  today_stats: TodayStats
  last_comment?: { text: string; channel?: string; strategy?: string; time?: string }
}

export interface ErrorGroup {
  category: string
  count: number
  last_at?: string
  diagnosis?: string
  accounts: string[]
  channels: string[]
}

export interface PlanSlot {
  day: string
  post_type: string
  topic?: string
  status: string
}

export interface PlanData {
  plan_id?: number
  week_start?: string
  slots: PlanSlot[]
  used: number
  total: number
}

export interface ReviewData {
  posts_reviewed: number
  created_at?: string
  strengths: string[]
  weaknesses: string[]
  recommendations: string[]
  topics: string[]
  avoid: string[]
}

export interface DiaryEntry {
  id: number
  entry_text: string
  created_at: string
}

// ── API Functions ──

export const postsApi = {
  list: (params?: { status?: string; type?: string; limit?: number; offset?: number }) =>
    api.get<{ posts: Post[]; total: number }>('/posts', { params }),
  get: (id: number) => api.get<Post>(`/posts/${id}`),
  generate: (data: { post_type?: string; custom_topic?: string; segment?: string }) =>
    api.post<Post>('/posts/generate', data),
  moderate: (id: number, data: { action: string; scheduled_at?: string }) =>
    api.patch<Post>(`/posts/${id}`, data),
  editContent: (id: number, content: string) =>
    api.patch<Post>(`/posts/${id}/content`, { content }),
  regenerate: (id: number, feedback?: string) =>
    api.post<Post>(`/posts/${id}/regenerate`, { feedback }),
  aiEdit: (id: number, instructions: string) =>
    api.post<Post>(`/posts/${id}/ai-edit`, { instructions }),
}

export const analyticsApi = {
  dashboard: (days?: number) =>
    api.get<DashboardData>('/analytics/dashboard', { params: { days } }),
  engagement: (days?: number) =>
    api.get<{ timeline: TimelinePoint[] }>('/analytics/engagement', { params: { days } }),
  topPosts: (params?: { sort?: string; limit?: number; days?: number }) =>
    api.get<{ posts: TopPost[] }>('/analytics/top-posts', { params }),
}

export const trafficApi = {
  overview: () => api.get<TrafficOverview>('/traffic/overview'),
  errors: (hours?: number) =>
    api.get<{ total: number; groups: ErrorGroup[] }>('/traffic/errors', { params: { hours } }),
}

export const directorApi = {
  getPlan: (segment: string) => api.get<PlanData>(`/director/plan/${segment}`),
  generatePlan: (segment: string) => api.post<PlanData>(`/director/plan/${segment}/generate`),
  getReview: (segment: string) => api.get<ReviewData>(`/director/review/${segment}`),
  getInsights: (segment: string) => api.get<any>(`/director/insights/${segment}`),
  getCompetitors: (segment: string) => api.get<any>(`/director/competitors/${segment}`),
}

export const diaryApi = {
  list: (limit?: number) => api.get<{ entries: DiaryEntry[] }>('/diary', { params: { limit } }),
  create: (text: string) => api.post<DiaryEntry>('/diary', { text }),
}

export const scheduleApi = {
  list: () => api.get<{ schedules: any[] }>('/schedule'),
  update: (id: number, is_active: boolean) => api.patch(`/schedule/${id}`, { is_active }),
}
