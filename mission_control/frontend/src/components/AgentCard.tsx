import { motion } from 'framer-motion'
import clsx from 'clsx'
import { Cpu, AlertTriangle } from 'lucide-react'
import type { AgentStatus } from '../api/client'
import { AGENTS } from '../lib/constants'
import { normalizeStatus, truncate } from '../lib/utils'
import StatusDot from './StatusDot'
import TimeAgo from './TimeAgo'

interface AgentCardProps {
  agent: AgentStatus
  onClick: () => void
}

export default function AgentCard({ agent, onClick }: AgentCardProps) {
  const meta = AGENTS[agent.id] ?? {
    name: agent.name,
    icon: Cpu,
    color: 'text-alloy',
    role: 'Agent',
  }
  const Icon = meta.icon
  const status = normalizeStatus(agent.status)

  return (
    <motion.div
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      className={clsx(
        'card cursor-pointer',
        status === 'active' && 'card-active',
        status === 'error' && 'card-error'
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <StatusDot status={status} />
        <Icon size={16} className={meta.color} />
        <span className="font-semibold text-sm text-chrome tracking-wide">
          {meta.name}
        </span>
      </div>

      {/* Role + Model */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-oxide">{meta.role}</span>
        <span className="text-[10px] font-mono text-alloy">
          {agent.model_primary
            ? agent.model_primary.split('/').pop()?.split('-').slice(0, 2).join('-')
            : '—'}
        </span>
      </div>

      {/* Current Task */}
      {agent.current_task && (
        <p className="text-xs text-alloy mb-2 leading-relaxed">
          {truncate(agent.current_task, 80)}
        </p>
      )}

      {/* Footer: stats */}
      <div className="flex items-center justify-between text-[10px] font-mono">
        <TimeAgo date={agent.last_heartbeat} />
        <div className="flex items-center gap-2">
          <span className="text-oxide">
            cron: <span className="text-alloy">{agent.cron_jobs_count}</span>
          </span>
          {agent.cron_errors > 0 && (
            <span className="flex items-center gap-0.5 text-alert">
              <AlertTriangle size={10} />
              {agent.cron_errors}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  )
}
