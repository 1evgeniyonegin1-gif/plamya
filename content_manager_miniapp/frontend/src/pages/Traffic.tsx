import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { MessageSquare, Eye, Reply, AlertTriangle } from 'lucide-react'
import { trafficApi } from '../api/client'
import { StatCard } from '../components/StatCard'
import { StatCardSkeleton } from '../components/Skeleton'
import { EmptyState } from '../components/EmptyState'
import clsx from 'clsx'

const statusColors: Record<string, string> = {
  active: 'text-jade',
  warming: 'text-amber',
  banned: 'text-flame',
  cooldown: 'text-blaze',
  disabled: 'text-mist',
}

export function Traffic() {
  const { data: overview, isLoading } = useQuery({
    queryKey: ['traffic-overview'],
    queryFn: () => trafficApi.overview(),
    select: (res) => res.data,
    refetchInterval: 30_000,
  })

  const { data: errors } = useQuery({
    queryKey: ['traffic-errors'],
    queryFn: () => trafficApi.errors(24),
    select: (res) => res.data,
  })

  if (isLoading) {
    return (
      <div className="p-4 space-y-4">
        <h1 className="text-lg font-bold text-silk">Traffic Engine</h1>
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)}
        </div>
      </div>
    )
  }

  if (!overview) {
    return <EmptyState title="Нет данных" description="Traffic Engine не запущен" />
  }

  const stats = overview.today_stats

  return (
    <div className="p-4 pb-24 space-y-5 overflow-y-auto">
      <h1 className="text-lg font-bold text-silk">Traffic Engine</h1>

      {/* Today stats */}
      <div className="grid grid-cols-2 gap-3">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <StatCard label="Комментарии" value={stats.comments_ok} icon={MessageSquare} color="text-jade" />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <StatCard label="Ошибки" value={stats.comments_fail} icon={AlertTriangle} color="text-flame" />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <StatCard label="Сторис" value={stats.stories} icon={Eye} color="text-blaze" />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <StatCard label="Ответы" value={stats.replies} icon={Reply} color="text-gold" />
        </motion.div>
      </div>

      {/* Last comment */}
      {overview.last_comment && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <h3 className="text-xs font-semibold text-pearl mb-2">Последний комментарий</h3>
          <p className="text-sm text-silk/90 leading-relaxed">{overview.last_comment.text}</p>
          <div className="flex gap-3 mt-2 text-[10px] text-mist">
            {overview.last_comment.channel && <span>{overview.last_comment.channel}</span>}
            {overview.last_comment.strategy && (
              <span className="text-blaze">{overview.last_comment.strategy}</span>
            )}
            {overview.last_comment.time && (
              <span>{new Date(overview.last_comment.time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</span>
            )}
          </div>
        </motion.div>
      )}

      {/* Accounts */}
      <div>
        <h3 className="text-sm font-semibold text-silk mb-3">Аккаунты ({overview.accounts.length})</h3>
        <div className="space-y-2">
          {overview.accounts.map((acc, i) => (
            <motion.div
              key={acc.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 + i * 0.04 }}
              className="card flex items-center gap-3"
            >
              <div className={clsx('w-2 h-2 rounded-full', acc.status === 'active' ? 'bg-jade' : acc.status === 'warming' ? 'bg-amber' : 'bg-smoke')}>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-silk">{acc.first_name}</span>
                  {acc.segment && (
                    <span className="text-[10px] text-blaze bg-blaze/10 px-1.5 py-0.5 rounded">{acc.segment}</span>
                  )}
                </div>
                <div className="flex gap-3 text-[10px] text-pearl mt-0.5">
                  <span>{acc.daily_comments} comm</span>
                  <span>{acc.daily_story_views} stories</span>
                  <span>{acc.daily_invites} inv</span>
                </div>
              </div>
              <span className={clsx('text-xs font-medium', statusColors[acc.status] || 'text-mist')}>
                {acc.status}
              </span>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Errors */}
      {errors && errors.total > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-silk mb-3 flex items-center gap-1.5">
            <AlertTriangle size={14} className="text-flame" />
            Ошибки за 24ч ({errors.total})
          </h3>
          <div className="space-y-2">
            {errors.groups.map((g, i) => (
              <div key={i} className="card border-flame/20">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-flame">{g.category}</span>
                  <span className="text-xs text-pearl">{g.count}x</span>
                </div>
                {g.diagnosis && (
                  <p className="text-[11px] text-pearl/80 leading-snug">{g.diagnosis}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
