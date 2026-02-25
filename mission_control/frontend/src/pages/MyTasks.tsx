import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, Zap, Check, X, Send, MessageSquare } from 'lucide-react'
import clsx from 'clsx'
import { projectsApi } from '../api/client'
import type { MyTask } from '../api/client'

const PRIORITY_LABELS: Record<string, { label: string; color: string }> = {
  high: { label: 'СРОЧНО', color: 'text-red-400 bg-red-400/10' },
  medium: { label: 'ВАЖНО', color: 'text-amber-400 bg-amber-400/10' },
  low: { label: 'КОГДА УСПЕЕШЬ', color: 'text-zinc-400 bg-zinc-400/10' },
}

const ACTION_LABELS: Record<string, string> = {
  approve: 'Нужно одобрение',
  decide: 'Нужно решение',
  manual: 'Нужно сделать руками',
}

// ── Task Card ────────────────────────────────────

function TaskCard({
  task,
  onRespond,
}: {
  task: MyTask
  onRespond: (id: string, decision: string, message: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [showInput, setShowInput] = useState(false)
  const [message, setMessage] = useState('')
  const priority = PRIORITY_LABELS[task.priority] ?? PRIORITY_LABELS.medium
  const actionType = task.action_type ?? 'manual'

  const handleApprove = () => {
    onRespond(task.id, 'approve', '')
  }

  const handleReject = () => {
    setShowInput(true)
  }

  const handleSendMessage = () => {
    if (!message.trim()) return
    onRespond(task.id, showInput ? 'reject' : 'custom', message.trim())
    setMessage('')
    setShowInput(false)
  }

  const handleDone = () => {
    onRespond(task.id, 'done', '')
  }

  // Already responded
  if (task.done && task.response) {
    const decisionMap: Record<string, { text: string; color: string }> = {
      approve: { text: 'ОДОБРЕНО', color: 'text-emerald-400' },
      reject: { text: 'ОТКЛОНЕНО', color: 'text-red-400' },
      done: { text: 'СДЕЛАНО', color: 'text-emerald-400' },
    }
    const d = decisionMap[task.response.decision] ?? { text: task.response.decision, color: 'text-alloy' }

    return (
      <div className="glass rounded-xl p-3 opacity-50">
        <div className="flex items-center gap-2 mb-1">
          <span className={clsx('text-[9px] font-bold font-mono px-1.5 py-0.5 rounded', priority.color)}>
            {priority.label}
          </span>
          <span className="text-[9px] text-oxide font-mono">{task.project}</span>
        </div>
        <p className="text-sm text-oxide line-through mb-1">{task.text}</p>
        <div className="flex items-center gap-2">
          <span className={clsx('text-xs font-bold font-mono', d.color)}>{d.text}</span>
          {task.response.message && (
            <span className="text-[10px] text-oxide/60">— {task.response.message}</span>
          )}
        </div>
      </div>
    )
  }

  return (
    <motion.div layout className="glass rounded-xl p-3">
      {/* Header */}
      <div className="flex items-center gap-2 flex-wrap mb-1.5">
        <span className={clsx('text-[9px] font-bold font-mono px-1.5 py-0.5 rounded', priority.color)}>
          {priority.label}
        </span>
        <span className="text-[9px] text-oxide font-mono">{task.project}</span>
        <span className="text-[9px] text-signal/60 font-mono ml-auto">
          {ACTION_LABELS[actionType]}
        </span>
      </div>

      {/* Task text */}
      <p className="text-sm text-alloy leading-snug mb-2">{task.text}</p>

      {/* Why section */}
      {task.why && (
        <div className="mb-3">
          <button
            onClick={() => setExpanded(v => !v)}
            className="flex items-center gap-1 text-[10px] text-oxide hover:text-alloy transition-colors"
          >
            {expanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
            зачем?
          </button>
          <AnimatePresence>
            {expanded && (
              <motion.p
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="text-[11px] text-oxide/80 mt-1 pl-2 border-l border-white/10"
              >
                {task.why}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Action buttons */}
      {actionType === 'approve' && !showInput && (
        <div className="flex gap-2">
          <button
            onClick={handleApprove}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-emerald-500/20 text-emerald-400 text-xs font-bold hover:bg-emerald-500/30 transition-colors"
          >
            <Check size={14} /> Одобряю
          </button>
          <button
            onClick={handleReject}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-red-500/20 text-red-400 text-xs font-bold hover:bg-red-500/30 transition-colors"
          >
            <X size={14} /> Нет
          </button>
          <button
            onClick={() => setShowInput(v => !v)}
            className="flex items-center justify-center px-3 py-2 rounded-lg bg-white/5 text-oxide text-xs hover:bg-white/10 transition-colors"
          >
            <MessageSquare size={14} />
          </button>
        </div>
      )}

      {actionType === 'decide' && !showInput && (
        <div className="flex gap-2">
          <button
            onClick={handleApprove}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-emerald-500/20 text-emerald-400 text-xs font-bold hover:bg-emerald-500/30 transition-colors"
          >
            <Check size={14} /> Да, делайте
          </button>
          <button
            onClick={() => setShowInput(true)}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-signal/20 text-signal text-xs font-bold hover:bg-signal/30 transition-colors"
          >
            <MessageSquare size={14} /> Ответить
          </button>
        </div>
      )}

      {actionType === 'manual' && !showInput && (
        <div className="flex gap-2">
          <button
            onClick={handleDone}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-emerald-500/20 text-emerald-400 text-xs font-bold hover:bg-emerald-500/30 transition-colors"
          >
            <Check size={14} /> Сделано
          </button>
          <button
            onClick={() => setShowInput(true)}
            className="flex items-center justify-center px-3 py-2 rounded-lg bg-white/5 text-oxide text-xs hover:bg-white/10 transition-colors"
          >
            <MessageSquare size={14} />
          </button>
        </div>
      )}

      {/* Text input for response */}
      <AnimatePresence>
        {showInput && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-2"
          >
            <div className="flex gap-2">
              <input
                type="text"
                value={message}
                onChange={e => setMessage(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSendMessage()}
                placeholder="Написать ответ..."
                autoFocus
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-alloy placeholder:text-oxide/40 focus:outline-none focus:border-signal/50"
              />
              <button
                onClick={handleSendMessage}
                disabled={!message.trim()}
                className="flex items-center justify-center px-3 py-2 rounded-lg bg-signal/20 text-signal hover:bg-signal/30 transition-colors disabled:opacity-30"
              >
                <Send size={14} />
              </button>
              <button
                onClick={() => { setShowInput(false); setMessage('') }}
                className="flex items-center justify-center px-2 py-2 rounded-lg bg-white/5 text-oxide hover:bg-white/10 transition-colors"
              >
                <X size={14} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ── Main Page ────────────────────────────────────

export default function MyTasks() {
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['my-tasks'],
    queryFn: () => projectsApi.myTasks().then(r => r.data),
    staleTime: 30_000,
  })

  const respondMutation = useMutation({
    mutationFn: ({ taskId, decision, message }: { taskId: string; decision: string; message: string }) =>
      projectsApi.respondTask(taskId, decision, message),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['my-tasks'] })
      queryClient.invalidateQueries({ queryKey: ['my-tasks-badge'] })
    },
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
        <p className="text-oxide text-sm">Не удалось загрузить задачи</p>
      </div>
    )
  }

  const tasks = data.tasks ?? []
  const pending = tasks.filter(t => !t.done)
  const done = tasks.filter(t => t.done)

  const priorityOrder = { high: 0, medium: 1, low: 2 }
  const sortedPending = [...pending].sort(
    (a, b) => (priorityOrder[a.priority] ?? 2) - (priorityOrder[b.priority] ?? 2)
  )

  return (
    <div className="px-4 pt-4 pb-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-1">
        <Zap size={16} className="text-signal" />
        <h1 className="text-base font-bold text-chrome tracking-wide">Мне сделать</h1>
      </div>
      <p className="text-[11px] text-oxide mb-4 font-mono">
        Задачи от NEXUS — агенты ждут твоего решения
      </p>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="glass rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-red-400 font-mono">{pending.length}</div>
          <div className="text-[9px] text-oxide">ожидает</div>
        </div>
        <div className="glass rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-emerald-400 font-mono">{done.length}</div>
          <div className="text-[9px] text-oxide">решено</div>
        </div>
      </div>

      {/* Pending tasks */}
      {sortedPending.length > 0 ? (
        <div className="flex flex-col gap-3 mb-4">
          {sortedPending.map((task, i) => (
            <motion.div
              key={task.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
            >
              <TaskCard
                task={task}
                onRespond={(id, d, m) => respondMutation.mutate({ taskId: id, decision: d, message: m })}
              />
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="glass rounded-xl p-6 text-center mb-4">
          <p className="text-emerald-400 text-sm font-mono">All clear</p>
          <p className="text-oxide text-xs mt-1">Агенты работают без тебя</p>
        </div>
      )}

      {/* Done tasks */}
      {done.length > 0 && (
        <div>
          <div className="text-[10px] text-oxide/50 font-mono mb-2">
            РЕШЕНО ({done.length})
          </div>
          <div className="flex flex-col gap-2">
            {done.map(task => (
              <TaskCard
                key={task.id}
                task={task}
                onRespond={() => {}}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
