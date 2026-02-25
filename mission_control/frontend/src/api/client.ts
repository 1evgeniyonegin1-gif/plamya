import axios from 'axios'

// ============================================
// Axios instance
// ============================================

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ============================================
// Types
// ============================================

export interface AgentStatus {
  id: string
  name: string
  model_primary: string | null
  model_fallbacks: string[] | null
  status: string | null
  status_emoji: string | null
  last_heartbeat: string | null
  current_task: string | null
  cron_jobs_count: number
  cron_errors: number
  inbox_messages_count: number
  api_usage: Record<
    string,
    { last_used: number; error_count: number; last_failure_at?: number }
  >
}

export interface AgentsResponse {
  agents: AgentStatus[]
  total_cron_jobs: number
  total_cron_errors: number
  total_inbox_messages: number
  last_updated: string
}

export interface AgentDetail extends AgentStatus {
  cron_jobs: CronJob[]
  recent_inbox: InboxMessage[]
  chappie_data?: { goals: any; problems: any; state: any }
  producer_data?: {
    state?: any
    pipeline?: Record<string, number>
    total_niches?: number
    qualified_niches?: number
    total_products?: number
    products?: any[]
  }
  hunter_data?: {
    total_leads: number
    qualified: number
    proposed: number
    won: number
    recent_leads?: { id: number; title: string; source: string; score: number; status: string; created_at: string }[]
  }
  crm_summary?: { total_leads: number; qualified: number; last_scan: string }
}

export interface InboxMessage {
  id: number
  timestamp: string
  sender: string
  recipient: string
  subject: string
  preview: string
  full_text: string
  priority: string | null
}

export interface InboxResponse {
  messages: InboxMessage[]
  total: number
}

export interface CronJob {
  id: string
  name: string
  agent_id: string
  agent_name: string
  enabled: boolean
  schedule_human: string
  last_status: string | null
  last_run_at: string | null
  last_duration_ms: number | null
  next_run_at: string | null
  consecutive_errors: number
  last_error: string | null
}

export interface CronResponse {
  jobs: CronJob[]
  total_enabled: number
  total_errors: number
  next_job_name: string | null
  next_job_in: string | null
}

export interface ErrorItem {
  source: string
  job_name: string | null
  agent: string
  agent_name: string
  provider: string | null
  error: string
  consecutive: number
  last_at: string | null
  severity: string
}

export interface ErrorsResponse {
  total_errors: number
  groups: ErrorItem[]
}

export interface ChatSendRequest {
  agent_id: string
  message: string
  subject?: string
}

export interface ChatSendResponse {
  ok: boolean
  timestamp: string
}

// ── Council types ──────────────────────────────

export interface CouncilResponse {
  agent_name: string
  agent_id: string
  timestamp: string
  text: string
}

export interface CouncilTopicSummary {
  id: number
  title: string
  author: string
  author_id: string
  created_at: string
  status: string
  response_count: number
}

export interface CouncilTopicDetail {
  id: number
  title: string
  author: string
  author_id: string
  created_at: string
  status: string
  responses: CouncilResponse[]
}

export interface CouncilTopicsResponse {
  topics: CouncilTopicSummary[]
  total: number
}

// ── Tasks types ────────────────────────────────

export interface TaskItem {
  id: number
  text: string
  assignee: string
  assignee_id: string
  priority: string
  done: boolean
  section: string
}

export interface TasksListResponse {
  tasks: TaskItem[]
  total: number
  done_count: number
}

// ============================================
// API functions
// ============================================

export const agentsApi = {
  list: () => api.get<AgentsResponse>('/agents'),
  detail: (id: string) => api.get<AgentDetail>(`/agents/${id}`),
}

export const inboxApi = {
  list: (params?: { agent?: string; limit?: number; offset?: number }) =>
    api.get<InboxResponse>('/inbox', { params }),
}

export const cronApi = {
  list: () => api.get<CronResponse>('/cron/jobs'),
  toggle: (jobId: string) => api.post(`/cron/jobs/${jobId}/toggle`),
  trigger: (jobId: string) => api.post(`/cron/jobs/${jobId}/trigger`),
}

export const errorsApi = {
  list: () => api.get<ErrorsResponse>('/errors'),
}

export const chatApi = {
  send: (data: ChatSendRequest) =>
    api.post<ChatSendResponse>('/chat/send', data),
}

export const councilApi = {
  listTopics: (limit = 20) =>
    api.get<CouncilTopicsResponse>('/council/topics', { params: { limit } }),
  getTopic: (id: number) =>
    api.get<CouncilTopicDetail>(`/council/topics/${id}`),
  createTopic: (title: string, author = 'ДАНИЛ') =>
    api.post<{ ok: boolean; topic_id: number }>('/council/topics', { author, title }),
  askAll: (topicId: number) =>
    api.post<{ ok: boolean; agents_notified: number }>(`/council/topics/${topicId}/ask`),
  reply: (topicId: number, agentId: string, text: string) =>
    api.post(`/council/topics/${topicId}/reply`, { agent_id: agentId, text }),
}

// ── Projects types ─────────────────────────────

export interface SubProject {
  id: string
  name: string
  description: string
  category: string
  completion_pct: number
}

export interface Project {
  id: string
  name: string
  description: string
  path: string
  category: string
  stack: string[]
  completion_pct: number
  mrr: number
  next_step: string
  subprojects: SubProject[]
}

export interface ProjectsRegistry {
  updated_at: string
  projects: Project[]
  archived: { id: string; name: string; reason: string }[]
  category_colors: Record<string, string>
}

export interface ProjectsSummary {
  total: number
  avg_completion: number
  by_category: Record<string, number>
  updated_at: string
}

// ── My Tasks types ──────────────────────────────
export interface MyTaskResponse {
  decision: string
  message: string
  responded_at: string
}

export interface MyTask {
  id: string
  text: string
  project: string
  priority: 'high' | 'medium' | 'low'
  done: boolean
  action_type?: 'approve' | 'decide' | 'manual'
  why?: string
  response?: MyTaskResponse | null
}

export interface MyTasksResponse {
  tasks: MyTask[]
  total: number
  pending: number
}

export const projectsApi = {
  list: () => api.get<ProjectsRegistry>('/projects'),
  summary: () => api.get<ProjectsSummary>('/projects/summary'),
  detail: (id: string) => api.get<Project>(`/projects/${id}`),
  update: (id: string, data: Partial<Pick<Project, 'completion_pct' | 'next_step' | 'mrr' | 'category'>>) =>
    api.put<{ ok: boolean; project: Project }>(`/projects/${id}`, data),
  myTasks: () => api.get<MyTasksResponse>('/projects/my-tasks'),
  markTaskDone: (taskId: string, done = true) =>
    api.post<{ ok: boolean; task: MyTask }>(`/projects/my-tasks/${taskId}/done`, null, { params: { done } }),
  respondTask: (taskId: string, decision: string, message = '') =>
    api.post<{ ok: boolean; task: MyTask }>(`/projects/my-tasks/${taskId}/respond`, { decision, message }),
}

// ── Leads types ────────────────────────────────

export interface LeadContacts {
  phone?: string
  email?: string
  website?: string
  telegram?: string
  whatsapp?: string
  vk?: string
  instagram?: string
}

export interface Lead {
  id: number
  name: string
  city: string
  category: string
  address: string
  status: string
  priority: 'hot' | 'warm' | 'cold'
  priority_score: number
  audit_score: number
  match_score: number
  contacts: LeadContacts
  problems: string[]
  capabilities: { name: string; reason?: string; result?: string }[]
  proposal_telegram: string
  proposal_email: string
  proposal_phone_script: string
  estimated_check: string
  contact_method: string
  contact_date: string
  reply_date: string
  notes: string
  created_at: string
  updated_at: string
  dialog_history?: DialogMessage[]
}

export interface LeadsResponse {
  leads: Lead[]
  total: number
}

export interface LeadsStats {
  total: number
  statuses: Record<string, number>
  cities: Record<string, number>
  priorities: { hot: number; warm: number; cold: number }
}

export interface DialogMessage {
  id: number
  business_id: number
  platform: string
  direction: 'incoming' | 'outgoing'
  message_text: string
  ai_classification: string
  sent_at: string
}

export interface DialogResponse {
  ai_response: string
  tips: string
  history_count: number
}

export const leadsApi = {
  list: (params?: { status?: string; city?: string; category?: string; priority?: string; limit?: number; offset?: number }) =>
    api.get<LeadsResponse>('/leads', { params }),
  detail: (id: number) =>
    api.get<Lead>(`/leads/${id}`),
  stats: () =>
    api.get<LeadsStats>('/leads/stats'),
  updateStatus: (id: number, status: string, notes = '') =>
    api.post<{ ok: boolean; status: string }>(`/leads/${id}/status`, { status, notes }),
  dialog: (id: number, clientMessage: string, platform = 'telegram') =>
    api.post<DialogResponse>(`/leads/${id}/dialog`, { client_message: clientMessage, platform }),
  history: (id: number) =>
    api.get<{ lead_id: number; messages: DialogMessage[] }>(`/leads/${id}/history`),
}

export const tasksApi = {
  list: (assignee?: string) =>
    api.get<TasksListResponse>('/tasks', { params: assignee ? { assignee } : {} }),
  create: (text: string, assigneeId: string, priority = 'СРЕДНИЙ') =>
    api.post<{ ok: boolean; task_position: number }>('/tasks', {
      text,
      assignee_id: assigneeId,
      priority,
    }),
  toggleDone: (taskId: number, done: boolean) =>
    api.put(`/tasks/${taskId}/status`, null, { params: { done } }),
  remove: (taskId: number) => api.delete(`/tasks/${taskId}`),
}
