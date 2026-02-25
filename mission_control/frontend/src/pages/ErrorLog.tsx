import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { AlertTriangle, ShieldCheck } from 'lucide-react'
import { errorsApi } from '../api/client'
import ErrorCard from '../components/ErrorCard'

function SkeletonError() {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="shimmer-skeleton h-5 w-16 rounded-full" />
          <div className="shimmer-skeleton h-3 w-20 rounded" />
        </div>
        <div className="shimmer-skeleton h-3 w-14 rounded" />
      </div>
      <div className="shimmer-skeleton h-3 w-3/4 rounded mb-2" />
      <div className="shimmer-skeleton h-10 w-full rounded" />
    </div>
  )
}

export default function ErrorLog() {
  const { data, isLoading, error: fetchError } = useQuery({
    queryKey: ['errors'],
    queryFn: () => errorsApi.list().then((r) => r.data),
    refetchInterval: 30_000,
  })

  // Group by severity
  const errorItems = data?.groups.filter((g) => g.severity === 'error') ?? []
  const warningItems =
    data?.groups.filter((g) => g.severity === 'warning') ?? []
  const infoItems = data?.groups.filter((g) => g.severity === 'info') ?? []

  const hasErrors = (data?.total_errors ?? 0) > 0

  return (
    <div className="px-3 pt-3 safe-bottom">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle size={18} className="text-alert" />
        <h1 className="text-lg font-bold text-chrome">Ошибки</h1>
        {data && (
          <span className="text-xs font-mono text-oxide ml-auto">
            {data.total_errors} всего
          </span>
        )}
      </div>

      {/* Fetch error */}
      {fetchError && (
        <div className="card card-error text-center py-6 mb-4">
          <p className="text-alert text-sm">Ошибка загрузки</p>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonError key={i} />
          ))}
        </div>
      )}

      {/* Empty state - all clear */}
      {!isLoading && !hasErrors && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center justify-center py-20"
        >
          <div className="w-16 h-16 rounded-full bg-signal/10 flex items-center justify-center mb-4">
            <ShieldCheck size={32} className="text-signal" />
          </div>
          <p className="text-chrome font-semibold mb-1">Всё чисто</p>
          <p className="text-oxide text-xs">Ошибок не обнаружено</p>
        </motion.div>
      )}

      {/* Error groups */}
      {!isLoading && hasErrors && (
        <div className="space-y-4">
          {/* Critical errors */}
          {errorItems.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2 px-1">
                <span className="badge badge-error">
                  ERRORS ({errorItems.length})
                </span>
              </div>
              <div className="space-y-2">
                {errorItems.map((item, i) => (
                  <motion.div
                    key={`error-${i}`}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03, duration: 0.2 }}
                  >
                    <ErrorCard error={item} />
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Warnings */}
          {warningItems.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2 px-1">
                <span className="badge badge-warning">
                  WARNINGS ({warningItems.length})
                </span>
              </div>
              <div className="space-y-2">
                {warningItems.map((item, i) => (
                  <motion.div
                    key={`warn-${i}`}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03, duration: 0.2 }}
                  >
                    <ErrorCard error={item} />
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Info */}
          {infoItems.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2 px-1">
                <span className="badge badge-info">
                  INFO ({infoItems.length})
                </span>
              </div>
              <div className="space-y-2">
                {infoItems.map((item, i) => (
                  <motion.div
                    key={`info-${i}`}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03, duration: 0.2 }}
                  >
                    <ErrorCard error={item} />
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
