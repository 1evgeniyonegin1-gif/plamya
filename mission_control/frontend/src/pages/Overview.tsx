import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Radio, RefreshCw } from 'lucide-react'
import { agentsApi } from '../api/client'
import type { AgentStatus } from '../api/client'
import { AGENT_ORDER } from '../lib/constants'
import { timeAgo } from '../lib/utils'
import AgentCard from '../components/AgentCard'

interface OverviewProps {
  onSelectAgent: (id: string) => void
}

function SkeletonCard() {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <div className="shimmer-skeleton w-2 h-2 rounded-full" />
        <div className="shimmer-skeleton w-4 h-4 rounded" />
        <div className="shimmer-skeleton h-4 w-20 rounded" />
      </div>
      <div className="shimmer-skeleton h-3 w-full rounded mb-2" />
      <div className="shimmer-skeleton h-3 w-2/3 rounded mb-3" />
      <div className="flex justify-between">
        <div className="shimmer-skeleton h-3 w-16 rounded" />
        <div className="shimmer-skeleton h-3 w-12 rounded" />
      </div>
    </div>
  )
}

export default function Overview({ onSelectAgent }: OverviewProps) {
  const { data, isLoading, error, dataUpdatedAt } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agentsApi.list().then((r) => r.data),
    refetchInterval: 30_000,
  })

  // Sort agents by predefined order
  const sortedAgents: AgentStatus[] = data
    ? [...data.agents].sort((a, b) => {
        const ai = AGENT_ORDER.indexOf(a.id)
        const bi = AGENT_ORDER.indexOf(b.id)
        return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
      })
    : []

  const updatedAgo = dataUpdatedAt ? timeAgo(new Date(dataUpdatedAt).toISOString()) : ''

  return (
    <div className="px-3 pt-3 safe-bottom">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <Radio size={18} className="text-signal" />
        <h1 className="text-lg font-bold text-chrome tracking-wide">
          Mission Control
        </h1>
      </div>

      {/* Summary bar */}
      {data && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-lg px-3 py-2 mb-4 flex items-center justify-between text-[10px] font-mono text-oxide"
        >
          <div className="flex items-center gap-3">
            <span>
              <span className="text-chrome">{data.agents.length}</span> агентов
            </span>
            <span>
              <span className="text-chrome">{data.total_cron_jobs}</span> cron
            </span>
            {data.total_cron_errors > 0 && (
              <span className="text-alert">
                <span className="font-semibold">{data.total_cron_errors}</span>{' '}
                ошиб.
              </span>
            )}
          </div>
          <div className="flex items-center gap-1 text-oxide">
            <RefreshCw size={9} />
            {updatedAgo}
          </div>
        </motion.div>
      )}

      {/* Error state */}
      {error && (
        <div className="card card-error text-center py-6 mb-4">
          <p className="text-alert text-sm font-medium mb-1">
            Ошибка загрузки
          </p>
          <p className="text-oxide text-xs font-mono">
            {(error as Error).message}
          </p>
        </div>
      )}

      {/* Agent grid */}
      <div className="grid grid-cols-2 gap-2.5">
        {isLoading
          ? Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)
          : sortedAgents.map((agent, i) => (
              <motion.div
                key={agent.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05, duration: 0.25 }}
              >
                <AgentCard
                  agent={agent}
                  onClick={() => onSelectAgent(agent.id)}
                />
              </motion.div>
            ))}
      </div>

      {/* Total inbox */}
      {data && data.total_inbox_messages > 0 && (
        <div className="mt-4 text-center text-[10px] font-mono text-oxide">
          {data.total_inbox_messages} сообщ. в INBOX
        </div>
      )}
    </div>
  )
}
