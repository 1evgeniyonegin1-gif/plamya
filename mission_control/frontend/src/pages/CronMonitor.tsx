import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Clock, Timer, CheckCircle, AlertTriangle } from 'lucide-react'
import { cronApi } from '../api/client'
import CronJobCard from '../components/CronJobCard'

function SkeletonJob() {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <div className="shimmer-skeleton w-2 h-2 rounded-full" />
        <div className="shimmer-skeleton h-4 w-32 rounded" />
      </div>
      <div className="flex justify-between mb-2">
        <div className="shimmer-skeleton h-3 w-20 rounded" />
        <div className="shimmer-skeleton h-3 w-24 rounded" />
      </div>
      <div className="shimmer-skeleton h-3 w-full rounded" />
    </div>
  )
}

export default function CronMonitor() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['cron-jobs'],
    queryFn: () => cronApi.list().then((r) => r.data),
    refetchInterval: 30_000,
  })

  // Sort: errors first, then by next_run_at
  const sortedJobs = data
    ? [...data.jobs].sort((a, b) => {
        if (a.consecutive_errors > 0 && b.consecutive_errors === 0) return -1
        if (a.consecutive_errors === 0 && b.consecutive_errors > 0) return 1
        if (a.next_run_at && b.next_run_at) {
          return (
            new Date(a.next_run_at).getTime() -
            new Date(b.next_run_at).getTime()
          )
        }
        return 0
      })
    : []

  return (
    <div className="px-3 pt-3 safe-bottom">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <Clock size={18} className="text-pulse" />
        <h1 className="text-lg font-bold text-chrome">Cron Jobs</h1>
      </div>

      {/* Summary */}
      {data && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-lg px-3 py-2.5 mb-4"
        >
          <div className="flex items-center justify-between text-xs mb-2">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1 text-oxide">
                <CheckCircle size={12} className="text-signal" />
                <span className="font-mono text-chrome">
                  {data.total_enabled}
                </span>{' '}
                активных
              </span>
              {data.total_errors > 0 && (
                <span className="flex items-center gap-1 text-alert">
                  <AlertTriangle size={12} />
                  <span className="font-mono font-semibold">
                    {data.total_errors}
                  </span>{' '}
                  ошиб.
                </span>
              )}
            </div>
          </div>

          {/* Next job */}
          {data.next_job_name && (
            <div className="flex items-center gap-1.5 text-[10px] font-mono">
              <Timer size={10} className="text-pulse" />
              <span className="text-oxide">Следующий:</span>
              <span className="text-chrome">{data.next_job_name}</span>
              {data.next_job_in && (
                <span className="text-pulse ml-auto">
                  через {data.next_job_in}
                </span>
              )}
            </div>
          )}
        </motion.div>
      )}

      {/* Error */}
      {error && (
        <div className="card card-error text-center py-6 mb-4">
          <p className="text-alert text-sm">Ошибка загрузки</p>
        </div>
      )}

      {/* Job list */}
      <div className="space-y-2">
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => <SkeletonJob key={i} />)
          : sortedJobs.map((job, i) => (
              <motion.div
                key={job.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03, duration: 0.2 }}
              >
                <CronJobCard job={job} />
              </motion.div>
            ))}
      </div>

      {/* Empty state */}
      {!isLoading && sortedJobs.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-oxide">
          <Clock size={40} className="mb-3 opacity-30" />
          <p className="text-sm">Нет cron задач</p>
        </div>
      )}
    </div>
  )
}
