import clsx from 'clsx'
import { AlertOctagon, AlertTriangle, Info } from 'lucide-react'
import type { ErrorItem } from '../api/client'
import { AGENTS } from '../lib/constants'
import TimeAgo from './TimeAgo'

interface ErrorCardProps {
  error: ErrorItem
}

const SEVERITY_CONFIG: Record<
  string,
  { icon: typeof AlertOctagon; badge: string; bg: string }
> = {
  error: {
    icon: AlertOctagon,
    badge: 'badge-error',
    bg: 'bg-alert/5',
  },
  warning: {
    icon: AlertTriangle,
    badge: 'badge-warning',
    bg: 'bg-caution/5',
  },
  info: {
    icon: Info,
    badge: 'badge-info',
    bg: 'bg-electric/5',
  },
}

export default function ErrorCard({ error }: ErrorCardProps) {
  const config = SEVERITY_CONFIG[error.severity] ?? SEVERITY_CONFIG.info
  const Icon = config.icon
  const agentName = AGENTS[error.agent]?.name ?? error.agent_name

  return (
    <div className={clsx('card', config.bg)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={clsx('badge', config.badge)}>
            <Icon size={10} />
            {error.severity.toUpperCase()}
          </span>
          <span className="text-xs text-oxide">{error.source}</span>
        </div>
        <TimeAgo date={error.last_at} />
      </div>

      {/* Agent + Job */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium text-chrome">{agentName}</span>
        {error.job_name && (
          <>
            <span className="text-oxide text-xs">/</span>
            <span className="text-xs font-mono text-alloy">
              {error.job_name}
            </span>
          </>
        )}
        {error.provider && (
          <span className="text-[10px] font-mono text-oxide ml-auto">
            {error.provider}
          </span>
        )}
      </div>

      {/* Error text */}
      <p className="text-xs text-alloy font-mono leading-relaxed whitespace-pre-wrap">
        {error.error}
      </p>

      {/* Consecutive count */}
      {error.consecutive > 1 && (
        <div className="mt-2 pt-1.5 border-t border-steel flex items-center gap-1 text-[10px] text-oxide font-mono">
          <span>Подряд:</span>
          <span className="text-alert font-semibold">{error.consecutive}</span>
        </div>
      )}
    </div>
  )
}
