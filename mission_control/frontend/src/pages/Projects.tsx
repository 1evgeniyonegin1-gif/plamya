import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronLeft, ChevronDown, ChevronUp, BarChart2 } from 'lucide-react'
import clsx from 'clsx'
import { projectsApi } from '../api/client'
import type { Project, SubProject } from '../api/client'
import ProjectCard from '../components/ProjectCard'

// ── Sub-project row ──────────────────────────────────────────

function SubProjectRow({ sub }: { sub: SubProject }) {
  const pct = Math.min(100, Math.max(0, sub.completion_pct))
  const colors: Record<string, string> = {
    production: 'bg-emerald-400', mvp: 'bg-blue-400',
    ready: 'bg-violet-400', wip: 'bg-amber-400',
    dev: 'bg-zinc-500', setup: 'bg-zinc-500',
  }
  const barColor = colors[sub.category] ?? 'bg-zinc-500'

  return (
    <div className="py-2 border-b border-white/5 last:border-0">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-alloy">{sub.name}</span>
        <span className="text-[10px] font-mono text-oxide">{pct}%</span>
      </div>
      <div className="h-0.5 rounded-full bg-white/5 overflow-hidden">
        <div className={clsx('h-full rounded-full', barColor)} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-[10px] text-oxide/60 mt-0.5">{sub.description}</p>
    </div>
  )
}

// ── Project detail view ──────────────────────────────────────

function ProjectDetail({ project, onBack }: { project: Project; onBack: () => void }) {
  const [showSubs, setShowSubs] = useState(true)
  const pct = Math.min(100, Math.max(0, project.completion_pct))

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.15 }}
      className="px-4 pt-4 pb-4"
    >
      {/* Back */}
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-xs text-oxide mb-4 hover:text-alloy transition-colors"
      >
        <ChevronLeft size={14} /> Все проекты
      </button>

      {/* Title */}
      <h2 className="text-lg font-bold text-chrome mb-1">{project.name}</h2>
      <p className="text-sm text-oxide mb-4">{project.description}</p>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="glass rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-chrome font-mono">{pct}%</div>
          <div className="text-[10px] text-oxide">готовность</div>
        </div>
        <div className="glass rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-chrome font-mono">
            {project.mrr > 0 ? `${project.mrr / 1000}K` : '—'}
          </div>
          <div className="text-[10px] text-oxide">MRR ₽</div>
        </div>
        <div className="glass rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-chrome font-mono">
            {project.subprojects.length || '—'}
          </div>
          <div className="text-[10px] text-oxide">модулей</div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="glass rounded-lg p-3 mb-4">
        <div className="flex justify-between text-[10px] font-mono text-oxide mb-2">
          <span>completion</span><span>{pct}%</span>
        </div>
        <div className="h-2 rounded-full bg-white/5 overflow-hidden">
          <motion.div
            className={clsx('h-full rounded-full', {
              'bg-emerald-400': pct >= 80,
              'bg-blue-400': pct >= 60 && pct < 80,
              'bg-amber-400': pct >= 30 && pct < 60,
              'bg-zinc-500': pct < 30,
            })}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Next step */}
      <div className="glass rounded-lg p-3 mb-4">
        <div className="text-[10px] text-oxide mb-1 font-mono">СЛЕДУЮЩИЙ ШАГ</div>
        <p className="text-sm text-alloy">{project.next_step}</p>
      </div>

      {/* Stack */}
      <div className="glass rounded-lg p-3 mb-4">
        <div className="text-[10px] text-oxide mb-2 font-mono">СТЕК</div>
        <div className="flex flex-wrap gap-1.5">
          {project.stack.map(s => (
            <span key={s} className="text-[10px] font-mono text-alloy bg-white/5 px-2 py-0.5 rounded-full">
              {s}
            </span>
          ))}
        </div>
      </div>

      {/* Subprojects */}
      {project.subprojects.length > 0 && (
        <div className="glass rounded-lg p-3">
          <button
            onClick={() => setShowSubs(v => !v)}
            className="flex items-center justify-between w-full mb-2"
          >
            <div className="text-[10px] text-oxide font-mono">
              ПОДМОДУЛИ ({project.subprojects.length})
            </div>
            {showSubs
              ? <ChevronUp size={12} className="text-oxide" />
              : <ChevronDown size={12} className="text-oxide" />
            }
          </button>
          {showSubs && project.subprojects.map(sub => (
            <SubProjectRow key={sub.id} sub={sub} />
          ))}
        </div>
      )}
    </motion.div>
  )
}

// ── Main Projects page ───────────────────────────────────────

export default function Projects() {
  const [selected, setSelected] = useState<Project | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list().then(r => r.data),
    staleTime: 60_000,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-signal/30 border-t-signal rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="px-4 pt-6 text-center">
        <p className="text-oxide text-sm">Не удалось загрузить проекты</p>
      </div>
    )
  }

  const projects = data.projects ?? []
  const total = projects.length
  const avgPct = total
    ? Math.round(projects.reduce((s, p) => s + p.completion_pct, 0) / total)
    : 0
  const production = projects.filter(p => p.category === 'production').length

  return (
    <AnimatePresence mode="wait">
      {selected ? (
        <ProjectDetail
          key="detail"
          project={selected}
          onBack={() => setSelected(null)}
        />
      ) : (
        <motion.div
          key="list"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          {/* Header */}
          <div className="px-4 pt-4 pb-2">
            <div className="flex items-center gap-2 mb-1">
              <BarChart2 size={16} className="text-signal" />
              <h1 className="text-base font-bold text-chrome tracking-wide">Проекты</h1>
            </div>

            {/* Summary stats */}
            <div className="grid grid-cols-3 gap-2 mt-3 mb-2">
              <div className="glass rounded-lg p-2 text-center">
                <div className="text-lg font-bold text-chrome font-mono">{total}</div>
                <div className="text-[9px] text-oxide">всего</div>
              </div>
              <div className="glass rounded-lg p-2 text-center">
                <div className="text-lg font-bold text-emerald-400 font-mono">{production}</div>
                <div className="text-[9px] text-oxide">production</div>
              </div>
              <div className="glass rounded-lg p-2 text-center">
                <div className="text-lg font-bold text-chrome font-mono">{avgPct}%</div>
                <div className="text-[9px] text-oxide">avg готовность</div>
              </div>
            </div>
          </div>

          {/* Cards */}
          <div className="px-4 pb-4 flex flex-col gap-3">
            {projects.map((project, i) => (
              <motion.div
                key={project.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04, duration: 0.2 }}
              >
                <ProjectCard
                  project={project}
                  onClick={() => setSelected(project)}
                />
              </motion.div>
            ))}
          </div>

          {/* Archived */}
          {data.archived && data.archived.length > 0 && (
            <div className="px-4 pb-4">
              <div className="text-[10px] text-oxide/50 font-mono mb-2">АРХИВ ({data.archived.length})</div>
              <div className="glass rounded-lg divide-y divide-white/5">
                {data.archived.map(a => (
                  <div key={a.id} className="px-3 py-2 flex items-center justify-between">
                    <span className="text-xs text-oxide/50">{a.name}</span>
                    <span className="text-[10px] text-oxide/30 font-mono">{a.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
