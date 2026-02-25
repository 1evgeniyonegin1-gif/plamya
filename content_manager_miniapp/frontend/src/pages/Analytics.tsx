import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FileText, Eye, TrendingUp, Clock, Trophy } from 'lucide-react'
import { analyticsApi } from '../api/client'
import { StatCard } from '../components/StatCard'
import { StatCardSkeleton } from '../components/Skeleton'
import { EmptyState } from '../components/EmptyState'

export function Analytics() {
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['analytics-dashboard'],
    queryFn: () => analyticsApi.dashboard(7),
    select: (res) => res.data,
  })

  const { data: topPosts } = useQuery({
    queryKey: ['analytics-top'],
    queryFn: () => analyticsApi.topPosts({ limit: 5, days: 30 }),
    select: (res) => res.data,
  })

  const { data: engagement } = useQuery({
    queryKey: ['analytics-engagement'],
    queryFn: () => analyticsApi.engagement(14),
    select: (res) => res.data,
  })

  if (isLoading) {
    return (
      <div className="p-4 space-y-4">
        <h1 className="text-lg font-bold text-silk">Аналитика</h1>
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)}
        </div>
      </div>
    )
  }

  if (!dashboard) {
    return <EmptyState title="Нет данных" description="Статистика появится после публикации постов" />
  }

  return (
    <div className="p-4 pb-24 space-y-5 overflow-y-auto">
      <h1 className="text-lg font-bold text-silk">Аналитика</h1>

      {/* Stats cards */}
      <div className="grid grid-cols-2 gap-3">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0 }}>
          <StatCard label="Всего постов" value={dashboard.total_posts} icon={FileText} />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <StatCard label="Сегодня" value={dashboard.published_today} icon={Clock} color="text-jade" />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <StatCard
            label="Ср. ER"
            value={dashboard.avg_engagement ? `${dashboard.avg_engagement.toFixed(1)}%` : '—'}
            icon={TrendingUp}
            color="text-gold"
          />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <StatCard label="На модерации" value={dashboard.pending_count} icon={Eye} color="text-amber" />
        </motion.div>
      </div>

      {/* Engagement chart - simple bar chart */}
      {engagement && engagement.timeline.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <h3 className="text-sm font-semibold text-silk mb-3">Engagement за 14 дней</h3>
          <div className="flex items-end gap-1 h-20">
            {engagement.timeline.map((point, i) => {
              const maxEr = Math.max(...engagement.timeline.map(p => p.engagement_rate || 0), 1)
              const height = ((point.engagement_rate || 0) / maxEr) * 100
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
                  <div
                    className="w-full rounded-t bg-gradient-to-t from-flame to-blaze min-h-[2px] transition-all"
                    style={{ height: `${Math.max(height, 3)}%` }}
                  />
                </div>
              )
            })}
          </div>
          <div className="flex justify-between mt-1 text-[9px] text-mist">
            <span>{engagement.timeline[0]?.date?.slice(5)}</span>
            <span>{engagement.timeline[engagement.timeline.length - 1]?.date?.slice(5)}</span>
          </div>
        </motion.div>
      )}

      {/* Type breakdown */}
      {dashboard.type_breakdown.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="card"
        >
          <h3 className="text-sm font-semibold text-silk mb-3">По типам (7 дней)</h3>
          <div className="space-y-2">
            {dashboard.type_breakdown.map((t) => {
              const maxCount = Math.max(...dashboard.type_breakdown.map(x => x.count), 1)
              const width = (t.count / maxCount) * 100
              return (
                <div key={t.type} className="flex items-center gap-2">
                  <span className="text-xs text-pearl w-20 truncate">{t.type}</span>
                  <div className="flex-1 h-4 bg-ash rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-flame/60 to-blaze/60 rounded-full"
                      style={{ width: `${width}%` }}
                    />
                  </div>
                  <span className="text-xs text-silk font-medium w-6 text-right">{t.count}</span>
                </div>
              )
            })}
          </div>
        </motion.div>
      )}

      {/* Top posts */}
      {topPosts && topPosts.posts.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <h3 className="text-sm font-semibold text-silk mb-3 flex items-center gap-1.5">
            <Trophy size={14} className="text-gold" /> Топ постов
          </h3>
          <div className="space-y-2">
            {topPosts.posts.map((p, i) => (
              <div key={p.id} className="flex items-start gap-2 py-1.5 border-b border-smoke/20 last:border-0">
                <span className="text-xs font-bold text-flame/60 w-4">{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-silk/80 truncate">{p.preview}</p>
                  <div className="flex gap-3 mt-0.5 text-[10px] text-pearl">
                    <span>{p.views} views</span>
                    <span>{p.reactions} reactions</span>
                    {p.engagement_rate != null && (
                      <span className="text-gold">{p.engagement_rate.toFixed(1)}% ER</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  )
}
