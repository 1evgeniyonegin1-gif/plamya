import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { MessageSquare, Inbox as InboxIcon } from 'lucide-react'
import clsx from 'clsx'
import { inboxApi } from '../api/client'
import { AGENTS } from '../lib/constants'
import MessageBubble from '../components/MessageBubble'

function SkeletonMessage() {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="shimmer-skeleton h-3 w-16 rounded" />
          <div className="shimmer-skeleton h-3 w-3 rounded-full" />
          <div className="shimmer-skeleton h-3 w-16 rounded" />
        </div>
        <div className="shimmer-skeleton h-3 w-12 rounded" />
      </div>
      <div className="shimmer-skeleton h-4 w-3/4 rounded mb-2" />
      <div className="shimmer-skeleton h-3 w-full rounded mb-1" />
      <div className="shimmer-skeleton h-3 w-2/3 rounded" />
    </div>
  )
}

const ALL_FILTER = '__all__'

export default function Inbox() {
  const [agentFilter, setAgentFilter] = useState(ALL_FILTER)

  const { data, isLoading, error } = useQuery({
    queryKey: ['inbox', agentFilter],
    queryFn: () =>
      inboxApi
        .list(agentFilter !== ALL_FILTER ? { agent: agentFilter } : undefined)
        .then((r) => r.data),
    refetchInterval: 30_000,
  })

  const agentEntries = Object.entries(AGENTS)

  return (
    <div className="px-3 pt-3 safe-bottom">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <MessageSquare size={18} className="text-electric" />
        <h1 className="text-lg font-bold text-chrome">Почта</h1>
        {data && (
          <span className="text-xs font-mono text-oxide ml-auto">
            {data.total} сообщ.
          </span>
        )}
      </div>

      {/* Filter chips */}
      <div className="flex gap-1.5 mb-4 overflow-x-auto no-scrollbar pb-1">
        <button
          onClick={() => setAgentFilter(ALL_FILTER)}
          className={clsx('chip', agentFilter === ALL_FILTER && 'chip-active')}
        >
          Все
        </button>
        {agentEntries.map(([id, meta]) => (
          <button
            key={id}
            onClick={() => setAgentFilter(id)}
            className={clsx('chip', agentFilter === id && 'chip-active')}
          >
            {meta.name}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="card card-error text-center py-6 mb-4">
          <p className="text-alert text-sm">Ошибка загрузки</p>
        </div>
      )}

      {/* Messages */}
      <div className="space-y-2">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => (
              <SkeletonMessage key={i} />
            ))
          : data?.messages.map((msg, i) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03, duration: 0.2 }}
              >
                <MessageBubble message={msg} />
              </motion.div>
            ))}
      </div>

      {/* Empty state */}
      {!isLoading && data?.messages.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-oxide">
          <InboxIcon size={40} className="mb-3 opacity-30" />
          <p className="text-sm">Нет сообщений</p>
          {agentFilter !== ALL_FILTER && (
            <p className="text-xs mt-1">
              Попробуйте другой фильтр
            </p>
          )}
        </div>
      )}
    </div>
  )
}
