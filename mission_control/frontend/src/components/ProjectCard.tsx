import { motion } from 'framer-motion'
import clsx from 'clsx'
import { ChevronRight } from 'lucide-react'
import type { Project } from '../api/client'

const CATEGORY_STYLES: Record<string, { label: string; color: string; dot: string }> = {
  production: { label: 'Production', color: 'text-emerald-400', dot: 'bg-emerald-400' },
  mvp:        { label: 'MVP',        color: 'text-blue-400',    dot: 'bg-blue-400' },
  ready:      { label: 'Ready',      color: 'text-violet-400',  dot: 'bg-violet-400' },
  wip:        { label: 'WIP',        color: 'text-amber-400',   dot: 'bg-amber-400' },
  dev:        { label: 'Dev',        color: 'text-zinc-400',    dot: 'bg-zinc-500' },
  setup:      { label: 'Setup',      color: 'text-zinc-400',    dot: 'bg-zinc-500' },
  archived:   { label: 'Archived',   color: 'text-zinc-600',    dot: 'bg-zinc-700' },
}

interface ProjectCardProps {
  project: Project
  onClick: () => void
}

export default function ProjectCard({ project, onClick }: ProjectCardProps) {
  const style = CATEGORY_STYLES[project.category] ?? CATEGORY_STYLES.dev
  const pct = Math.min(100, Math.max(0, project.completion_pct))

  return (
    <motion.div
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      className="card cursor-pointer"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={clsx('w-2 h-2 rounded-full flex-shrink-0', style.dot)} />
          <span className="font-semibold text-sm text-chrome tracking-wide truncate">
            {project.name}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={clsx('text-[10px] font-mono', style.color)}>
            {style.label}
          </span>
          <ChevronRight size={12} className="text-oxide" />
        </div>
      </div>

      {/* Description */}
      <p className="text-xs text-oxide mb-3 leading-relaxed line-clamp-1">
        {project.description}
      </p>

      {/* Progress bar */}
      <div className="mb-2">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-oxide font-mono">completion</span>
          <span className="text-[10px] font-mono text-alloy">{pct}%</span>
        </div>
        <div className="h-1 rounded-full bg-white/5 overflow-hidden">
          <motion.div
            className={clsx('h-full rounded-full', {
              'bg-emerald-400': pct >= 80,
              'bg-blue-400': pct >= 60 && pct < 80,
              'bg-amber-400': pct >= 30 && pct < 60,
              'bg-zinc-500': pct < 30,
            })}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-[10px] font-mono">
        <span className="text-oxide truncate max-w-[60%]">
          → <span className="text-alloy">{project.next_step}</span>
        </span>
        <div className="flex items-center gap-2">
          {project.mrr > 0 && (
            <span className="text-emerald-400">
              {project.mrr.toLocaleString('ru')}₽/мес
            </span>
          )}
          {project.subprojects.length > 0 && (
            <span className="text-oxide">
              {project.subprojects.length} модулей
            </span>
          )}
          {project.stack.slice(0, 2).map(s => (
            <span key={s} className="text-oxide/60">{s}</span>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
