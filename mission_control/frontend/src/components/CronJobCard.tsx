import { useMutation, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { Clock, AlertTriangle, CheckCircle, Zap, Pause, Play } from 'lucide-react'
import type { CronJob } from '../api/client'
import { cronApi } from '../api/client'
import { AGENTS } from '../lib/constants'
import { normalizeStatus, formatDuration } from '../lib/utils'
import StatusDot from './StatusDot'
import TimeAgo from './TimeAgo'

interface CronJobCardProps {
  job: CronJob
}

export default function CronJobCard({ job }: CronJobCardProps) {
  const queryClient = useQueryClient()
  const status = job.last_status ? normalizeStatus(job.last_status) : 'unknown'
  const hasErrors = job.consecutive_errors > 0
  const isOk = job.last_status === 'ok' || status === 'completed'
  const agentName = AGENTS[job.agent_id]?.name ?? job.agent_name

  const toggleMutation = useMutation({
    mutationFn: () => cronApi.toggle(job.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cron'] })
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })

  const triggerMutation = useMutation({
    mutationFn: () => cronApi.trigger(job.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cron'] })
    },
  })

  return (
    <div
      className={clsx(
        'card',
        hasErrors && 'card-error',
        !hasErrors && isOk && 'card-active'
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <StatusDot status={hasErrors ? 'error' : isOk ? 'active' : status} />
        <span className="text-sm font-semibold text-chrome flex-1 truncate">
          {job.name}
        </span>
        {!job.enabled && (
          <span className="badge badge-warning text-[10px]">OFF</span>
        )}
      </div>

      {/* Agent + Schedule */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-oxide">{agentName}</span>
        <span className="text-[10px] font-mono text-alloy flex items-center gap-1">
          <Clock size={10} className="text-oxide" />
          {job.schedule_human}
        </span>
      </div>

      {/* Last run + Duration */}
      <div className="flex items-center justify-between mb-1 text-[10px] font-mono">
        <div className="flex items-center gap-1 text-oxide">
          <span>Посл:</span>
          <TimeAgo date={job.last_run_at} className="text-alloy text-[10px] font-mono" />
        </div>
        <span className="text-alloy">
          {formatDuration(job.last_duration_ms)}
        </span>
      </div>

      {/* Next run */}
      {job.next_run_at && (
        <div className="flex items-center gap-1 text-[10px] font-mono text-oxide mb-1">
          <span>След:</span>
          <TimeAgo date={job.next_run_at} className="text-pulse text-[10px] font-mono" />
        </div>
      )}

      {/* Errors */}
      {hasErrors && (
        <div className="mt-2 pt-2 border-t border-steel">
          <div className="flex items-center gap-1.5 mb-1">
            <AlertTriangle size={12} className="text-alert" />
            <span className="text-xs text-alert font-medium">
              {job.consecutive_errors} ошиб.
            </span>
          </div>
          {job.last_error && (
            <p className="text-[10px] text-alloy font-mono leading-relaxed line-clamp-3">
              {job.last_error}
            </p>
          )}
        </div>
      )}

      {/* Success indicator */}
      {!hasErrors && isOk && (
        <div className="flex items-center gap-1 mt-1 text-[10px] text-signal">
          <CheckCircle size={10} />
          <span>OK</span>
        </div>
      )}

      {/* Control buttons */}
      <div className="flex gap-2 mt-2 pt-2 border-t border-steel/50">
        <button
          onClick={() => toggleMutation.mutate()}
          disabled={toggleMutation.isPending}
          className={clsx(
            'flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg text-[10px] font-medium transition-colors',
            job.enabled
              ? 'glass text-caution hover:bg-caution/10'
              : 'glass text-signal hover:bg-signal/10'
          )}
        >
          {job.enabled ? (
            <>
              <Pause size={10} /> Пауза
            </>
          ) : (
            <>
              <Play size={10} /> Включить
            </>
          )}
        </button>
        <button
          onClick={() => triggerMutation.mutate()}
          disabled={triggerMutation.isPending || !job.enabled}
          className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg glass text-electric text-[10px] font-medium hover:bg-electric/10 disabled:opacity-30 transition-colors"
        >
          <Zap size={10} />
          {triggerMutation.isPending ? '...' : 'Запустить'}
        </button>
      </div>
    </div>
  )
}
