import { useState, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  Cpu,
  Clock,
  MessageCircle,
  Info,
  Zap,
  Database,
  AlertTriangle,
  Factory,
  Target,
  BookOpen,
} from 'lucide-react'
import { agentsApi } from '../api/client'
import { AGENTS } from '../lib/constants'
import {
  normalizeStatus,
  timeAgo,
  formatTimestamp,
} from '../lib/utils'
import StatusDot from '../components/StatusDot'
import CronJobCard from '../components/CronJobCard'
import ChatPanel from '../components/ChatPanel'

interface AgentDetailProps {
  agentId: string
  onBack: () => void
}

function SkeletonBlock({ h }: { h: string }) {
  return <div className={`shimmer-skeleton w-full rounded-lg ${h}`} />
}

export default function AgentDetail({ agentId, onBack }: AgentDetailProps) {
  const webApp = window.Telegram?.WebApp
  const [tab, setTab] = useState<'chat' | 'info'>('chat')

  const handleBack = useCallback(() => {
    onBack()
  }, [onBack])

  useEffect(() => {
    if (webApp?.BackButton) {
      webApp.BackButton.show()
      webApp.BackButton.onClick(handleBack)
      return () => {
        webApp.BackButton.offClick(handleBack)
        webApp.BackButton.hide()
      }
    }
  }, [webApp, handleBack])

  const { data: agent, isLoading, error } = useQuery({
    queryKey: ['agent', agentId],
    queryFn: () => agentsApi.detail(agentId).then((r) => r.data),
    refetchInterval: 30_000,
  })

  const meta = AGENTS[agentId] ?? {
    name: agentId,
    icon: Cpu,
    color: 'text-alloy',
    role: 'Agent',
  }
  const Icon = meta.icon

  if (isLoading) {
    return (
      <div className="px-3 pt-3 safe-bottom space-y-3">
        <SkeletonBlock h="h-24" />
        <SkeletonBlock h="h-32" />
        <SkeletonBlock h="h-20" />
      </div>
    )
  }

  if (error || !agent) {
    return (
      <div className="px-3 pt-3 safe-bottom">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-oxide text-sm mb-4"
        >
          <ArrowLeft size={16} />
          Назад
        </button>
        <div className="card card-error text-center py-8">
          <p className="text-alert text-sm">Ошибка загрузки агента</p>
        </div>
      </div>
    )
  }

  const status = normalizeStatus(agent.status)
  const apiEntries = Object.entries(agent.api_usage ?? {})

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.2 }}
      className="px-3 pt-3 safe-bottom"
    >
      {/* Back (fallback for non-Telegram) */}
      {!webApp && (
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-oxide text-sm mb-3 hover:text-chrome transition-colors"
        >
          <ArrowLeft size={16} />
          Назад
        </button>
      )}

      {/* === Header Card === */}
      <div className="card card-active mb-3">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-lg bg-steel flex items-center justify-center">
            <Icon size={22} className={meta.color} />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <StatusDot status={status} size="md" />
              <h1 className="text-lg font-bold text-chrome">{meta.name}</h1>
            </div>
            <p className="text-xs text-oxide">{meta.role}</p>
          </div>
        </div>

        {/* Status */}
        <div className="flex items-center gap-1.5 mb-2">
          <span className="text-xs text-oxide">Статус:</span>
          <span className="text-xs font-mono text-chrome">
            {agent.status_emoji} {agent.status}
          </span>
        </div>

        {/* Model */}
        <div className="flex items-center gap-1.5 mb-2">
          <Cpu size={12} className="text-oxide" />
          <span className="text-xs text-oxide">Модель:</span>
          <span className="text-xs font-mono text-alloy">
            {agent.model_primary ?? '—'}
          </span>
        </div>
        {agent.model_fallbacks && agent.model_fallbacks.length > 0 && (
          <div className="ml-5 text-[10px] font-mono text-oxide mb-2">
            fallback: {agent.model_fallbacks.join(', ')}
          </div>
        )}

        {/* Current task */}
        {agent.current_task && (
          <div className="mt-2 p-2 bg-steel/50 rounded-lg">
            <span className="text-[10px] text-oxide uppercase tracking-wider">
              Текущая задача
            </span>
            <p className="text-xs text-chrome mt-0.5 leading-relaxed">
              {agent.current_task}
            </p>
          </div>
        )}

        {/* Heartbeat */}
        <div className="mt-2 text-[10px] font-mono text-oxide">
          Последний heartbeat: {timeAgo(agent.last_heartbeat)}
        </div>
      </div>

      {/* === Tab Switcher === */}
      <div className="flex gap-1 mb-3">
        <button
          onClick={() => setTab('chat')}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition-all ${
            tab === 'chat'
              ? 'bg-signal/10 text-signal border border-signal/30'
              : 'bg-steel/50 text-oxide border border-transparent'
          }`}
        >
          <MessageCircle size={14} />
          Чат
        </button>
        <button
          onClick={() => setTab('info')}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition-all ${
            tab === 'info'
              ? 'bg-signal/10 text-signal border border-signal/30'
              : 'bg-steel/50 text-oxide border border-transparent'
          }`}
        >
          <Info size={14} />
          Инфо
        </button>
      </div>

      {/* === Chat Tab === */}
      {tab === 'chat' && <ChatPanel agentId={agentId} />}

      {/* === Info Tab === */}
      {tab === 'info' && (
        <>
          {/* CRM Summary */}
          {agent.crm_summary && (
            <div className="card mb-3">
              <div className="flex items-center gap-2 mb-2">
                <Database size={14} className="text-electric" />
                <span className="text-sm font-semibold text-chrome">CRM</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="text-lg font-bold font-mono text-chrome">
                    {agent.crm_summary.total_leads}
                  </div>
                  <div className="text-[10px] text-oxide">Лидов</div>
                </div>
                <div>
                  <div className="text-lg font-bold font-mono text-signal">
                    {agent.crm_summary.qualified}
                  </div>
                  <div className="text-[10px] text-oxide">Квалиф.</div>
                </div>
                <div>
                  <div className="text-xs font-mono text-alloy mt-1">
                    {timeAgo(agent.crm_summary.last_scan)}
                  </div>
                  <div className="text-[10px] text-oxide">Посл. скан</div>
                </div>
              </div>
            </div>
          )}

          {/* ПРОДЮСЕР Pipeline */}
          {agent.producer_data && (
            <div className="card mb-3">
              <div className="flex items-center gap-2 mb-3">
                <Factory size={14} className="text-caution" />
                <span className="text-sm font-semibold text-chrome">
                  Пайплайн инфопродуктов
                </span>
              </div>

              {/* Pipeline stages */}
              {agent.producer_data.pipeline && (
                <div className="flex items-center gap-0.5 mb-3">
                  {[
                    { key: 'research', label: 'Ресёрч', color: 'bg-electric' },
                    { key: 'content', label: 'Контент', color: 'bg-signal' },
                    { key: 'landing', label: 'Лендинг', color: 'bg-pulse' },
                    { key: 'payment', label: 'Оплата', color: 'bg-caution' },
                    { key: 'sales', label: 'Продажи', color: 'bg-alert' },
                  ].map((stage, idx) => {
                    const count =
                      agent.producer_data?.pipeline?.[stage.key] ?? 0
                    return (
                      <div key={stage.key} className="flex-1 text-center">
                        <div
                          className={`h-1.5 rounded-full ${count > 0 ? stage.color : 'bg-steel'} ${idx > 0 ? 'ml-0.5' : ''}`}
                        />
                        <div className="text-[9px] text-oxide mt-1">
                          {stage.label}
                        </div>
                        <div className="text-xs font-mono font-bold text-chrome">
                          {count}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Niches + Products counters */}
              <div className="grid grid-cols-2 gap-2">
                {agent.producer_data.total_niches != null && (
                  <div className="bg-steel/50 rounded-lg p-2 text-center">
                    <div className="text-lg font-bold font-mono text-chrome">
                      {agent.producer_data.qualified_niches ?? 0}
                      <span className="text-oxide text-xs font-normal">
                        /{agent.producer_data.total_niches}
                      </span>
                    </div>
                    <div className="text-[10px] text-oxide">Ниш (квалиф.)</div>
                  </div>
                )}
                {agent.producer_data.total_products != null && (
                  <div className="bg-steel/50 rounded-lg p-2 text-center">
                    <div className="text-lg font-bold font-mono text-chrome">
                      {agent.producer_data.total_products}
                    </div>
                    <div className="text-[10px] text-oxide">Продуктов</div>
                  </div>
                )}
              </div>

              {/* Recent products */}
              {agent.producer_data.products &&
                agent.producer_data.products.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {agent.producer_data.products
                      .slice(0, 3)
                      .map((p: any, i: number) => (
                        <div
                          key={i}
                          className="flex items-center gap-2 text-xs py-1"
                        >
                          <div className="w-1 h-1 rounded-full bg-caution shrink-0" />
                          <span className="text-chrome truncate">
                            {p.name ?? p.title ?? 'Без названия'}
                          </span>
                          {p.status && (
                            <span className="text-oxide text-[10px] font-mono ml-auto shrink-0">
                              {p.status}
                            </span>
                          )}
                        </div>
                      ))}
                  </div>
                )}
            </div>
          )}

          {/* ХАНТЕР CRM Funnel */}
          {agent.hunter_data && (
            <div className="card mb-3">
              <div className="flex items-center gap-2 mb-3">
                <Target size={14} className="text-signal" />
                <span className="text-sm font-semibold text-chrome">
                  Воронка лидов
                </span>
              </div>

              {/* Funnel bars */}
              <div className="space-y-2 mb-3">
                {[
                  {
                    label: 'Всего',
                    value: agent.hunter_data.total_leads,
                    color: 'bg-electric',
                    max: agent.hunter_data.total_leads,
                  },
                  {
                    label: 'Квалиф.',
                    value: agent.hunter_data.qualified,
                    color: 'bg-signal',
                    max: agent.hunter_data.total_leads,
                  },
                  {
                    label: 'Proposal',
                    value: agent.hunter_data.proposed,
                    color: 'bg-caution',
                    max: agent.hunter_data.total_leads,
                  },
                  {
                    label: 'Выиграно',
                    value: agent.hunter_data.won,
                    color: 'bg-pulse',
                    max: agent.hunter_data.total_leads,
                  },
                ].map((stage) => {
                  const pct =
                    stage.max > 0
                      ? Math.max(
                          2,
                          Math.round((stage.value / stage.max) * 100)
                        )
                      : 0
                  return (
                    <div key={stage.label}>
                      <div className="flex justify-between text-[10px] mb-0.5">
                        <span className="text-oxide">{stage.label}</span>
                        <span className="font-mono text-chrome">
                          {stage.value}
                        </span>
                      </div>
                      <div className="h-2 bg-steel rounded-full overflow-hidden">
                        <div
                          className={`h-full ${stage.color} rounded-full transition-all`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Recent leads */}
              {agent.hunter_data.recent_leads &&
                (agent.hunter_data as any).recent_leads.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-[10px] text-oxide font-medium">
                      Последние лиды
                    </p>
                    {(agent.hunter_data as any).recent_leads
                      .slice(0, 3)
                      .map((lead: any, i: number) => (
                        <div
                          key={i}
                          className="flex items-center gap-2 text-xs py-0.5"
                        >
                          <div className="w-1 h-1 rounded-full bg-signal shrink-0" />
                          <span className="text-chrome truncate flex-1">
                            {lead.title}
                          </span>
                          <span className="text-oxide text-[10px] font-mono shrink-0">
                            {lead.score ?? '—'}
                          </span>
                        </div>
                      ))}
                  </div>
                )}
            </div>
          )}

          {/* ЧАППИ Knowledge */}
          {agent.chappie_data && (
            <div className="card mb-3">
              <div className="flex items-center gap-2 mb-3">
                <BookOpen size={14} className="text-pulse" />
                <span className="text-sm font-semibold text-chrome">
                  База знаний
                </span>
              </div>

              {agent.chappie_data.goals && (
                <div className="mb-2">
                  <p className="text-[10px] text-oxide font-medium mb-1">
                    Цели
                  </p>
                  <p className="text-xs text-chrome leading-relaxed whitespace-pre-wrap">
                    {typeof agent.chappie_data.goals === 'string'
                      ? agent.chappie_data.goals
                      : JSON.stringify(agent.chappie_data.goals, null, 2)}
                  </p>
                </div>
              )}

              {agent.chappie_data.state && (
                <div>
                  <p className="text-[10px] text-oxide font-medium mb-1">
                    Состояние
                  </p>
                  <p className="text-xs text-chrome leading-relaxed whitespace-pre-wrap">
                    {typeof agent.chappie_data.state === 'string'
                      ? agent.chappie_data.state
                      : JSON.stringify(agent.chappie_data.state, null, 2)}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Cron Jobs */}
          {agent.cron_jobs && agent.cron_jobs.length > 0 && (
            <div className="mb-3">
              <div className="flex items-center gap-2 mb-2 px-1">
                <Clock size={14} className="text-pulse" />
                <span className="text-sm font-semibold text-chrome">
                  Cron ({agent.cron_jobs.length})
                </span>
              </div>
              <div className="space-y-2">
                {agent.cron_jobs.map((job) => (
                  <CronJobCard key={job.id} job={job} />
                ))}
              </div>
            </div>
          )}

          {/* API Usage */}
          {apiEntries.length > 0 && (
            <div className="mb-3">
              <div className="flex items-center gap-2 mb-2 px-1">
                <Zap size={14} className="text-caution" />
                <span className="text-sm font-semibold text-chrome">
                  API Usage
                </span>
              </div>
              <div className="card">
                <div className="space-y-2">
                  {apiEntries.map(([provider, usage]) => (
                    <div
                      key={provider}
                      className="flex items-center justify-between text-xs"
                    >
                      <span className="font-mono text-alloy">{provider}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-oxide text-[10px]">
                          {usage.last_used
                            ? formatTimestamp(usage.last_used)
                            : '\u2014'}
                        </span>
                        {usage.error_count > 0 && (
                          <span className="flex items-center gap-0.5 text-alert text-[10px]">
                            <AlertTriangle size={9} />
                            {usage.error_count}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </motion.div>
  )
}
