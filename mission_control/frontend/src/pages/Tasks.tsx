import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Check, Trash2 } from 'lucide-react'
import clsx from 'clsx'
import { tasksApi } from '../api/client'
import { AGENTS, AGENT_ORDER } from '../lib/constants'

const PRIORITY_COLORS: Record<string, string> = {
  'КРИТИЧНО': 'border-alert/50 bg-alert/5',
  'ВЫСОКИЙ': 'border-caution/50 bg-caution/5',
  'СРЕДНИЙ': 'border-electric/30 bg-electric/5',
  'НИЗКИЙ': 'border-oxide/30 bg-oxide/5',
}

const PRIORITY_BADGE: Record<string, string> = {
  'КРИТИЧНО': 'bg-alert/20 text-alert',
  'ВЫСОКИЙ': 'bg-caution/20 text-caution',
  'СРЕДНИЙ': 'bg-electric/20 text-electric',
  'НИЗКИЙ': 'bg-oxide/20 text-oxide',
}

export default function Tasks() {
  const queryClient = useQueryClient()
  const [showNew, setShowNew] = useState(false)
  const [newText, setNewText] = useState('')
  const [newAssignee, setNewAssignee] = useState('coder')
  const [newPriority, setNewPriority] = useState('СРЕДНИЙ')
  const [filterAgent, setFilterAgent] = useState<string | undefined>()

  const { data, isLoading } = useQuery({
    queryKey: ['tasks', filterAgent],
    queryFn: () => tasksApi.list(filterAgent).then((r) => r.data),
    refetchInterval: 30_000,
  })

  const createMutation = useMutation({
    mutationFn: () => tasksApi.create(newText.trim(), newAssignee, newPriority),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      setShowNew(false)
      setNewText('')
    },
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, done }: { id: number; done: boolean }) =>
      tasksApi.toggleDone(id, done),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  })

  const removeMutation = useMutation({
    mutationFn: (id: number) => tasksApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  })

  const tasks = data?.tasks ?? []
  const pendingTasks = tasks.filter((t) => !t.done)
  const doneTasks = tasks.filter((t) => t.done)

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-signal font-bold text-lg">ЗАДАЧИ</h1>
          <p className="text-oxide text-xs">
            {data ? `${data.total} всего, ${data.done_count} выполнено` : '...'}
          </p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="glass rounded-xl p-2.5 text-signal active:scale-95 transition-transform"
        >
          <Plus size={20} />
        </button>
      </div>

      {/* Filter by agent */}
      <div className="flex gap-1.5 overflow-x-auto pb-1 -mx-4 px-4 no-scrollbar">
        <button
          onClick={() => setFilterAgent(undefined)}
          className={clsx(
            'shrink-0 px-3 py-1 rounded-full text-[11px] font-medium transition-colors',
            !filterAgent ? 'bg-signal/20 text-signal' : 'glass text-oxide'
          )}
        >
          Все
        </button>
        {AGENT_ORDER.map((id) => {
          const agent = AGENTS[id]
          if (!agent) return null
          return (
            <button
              key={id}
              onClick={() => setFilterAgent(id === filterAgent ? undefined : id)}
              className={clsx(
                'shrink-0 px-3 py-1 rounded-full text-[11px] font-medium transition-colors',
                filterAgent === id
                  ? 'bg-signal/20 text-signal'
                  : 'glass text-oxide'
              )}
            >
              {agent.name}
            </button>
          )
        })}
      </div>

      {/* New task form */}
      <AnimatePresence>
        {showNew && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="glass rounded-xl p-4 space-y-3">
              <input
                type="text"
                value={newText}
                onChange={(e) => setNewText(e.target.value)}
                placeholder="Описание задачи..."
                className="w-full glass rounded-lg px-3 py-2.5 text-chrome text-sm bg-transparent outline-none placeholder:text-oxide/50"
                autoFocus
              />
              <div className="flex gap-2">
                <select
                  value={newAssignee}
                  onChange={(e) => setNewAssignee(e.target.value)}
                  className="flex-1 glass rounded-lg px-2 py-2 text-chrome text-xs bg-transparent outline-none"
                >
                  {AGENT_ORDER.map((id) => (
                    <option key={id} value={id}>
                      {AGENTS[id]?.name ?? id}
                    </option>
                  ))}
                </select>
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value)}
                  className="flex-1 glass rounded-lg px-2 py-2 text-chrome text-xs bg-transparent outline-none"
                >
                  <option value="КРИТИЧНО">КРИТИЧНО</option>
                  <option value="ВЫСОКИЙ">ВЫСОКИЙ</option>
                  <option value="СРЕДНИЙ">СРЕДНИЙ</option>
                  <option value="НИЗКИЙ">НИЗКИЙ</option>
                </select>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowNew(false)}
                  className="flex-1 glass rounded-lg py-2 text-oxide text-sm"
                >
                  Отмена
                </button>
                <button
                  onClick={() => {
                    if (newText.trim()) createMutation.mutate()
                  }}
                  disabled={!newText.trim() || createMutation.isPending}
                  className="flex-1 bg-signal/20 rounded-lg py-2 text-signal text-sm font-medium disabled:opacity-50"
                >
                  Создать
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading */}
      {isLoading && (
        <div className="text-center py-8">
          <div className="w-8 h-8 rounded-full border-2 border-signal/30 border-t-signal animate-spin mx-auto" />
        </div>
      )}

      {/* Pending tasks */}
      {pendingTasks.length > 0 && (
        <div className="space-y-2">
          {pendingTasks.map((task, i) => {
            const agent = AGENTS[task.assignee_id]
            const Icon = agent?.icon
            return (
              <motion.div
                key={task.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
                className={clsx(
                  'glass rounded-xl p-3 border-l-2',
                  PRIORITY_COLORS[task.priority] ?? 'border-oxide/30'
                )}
              >
                <div className="flex items-start gap-2">
                  <button
                    onClick={() =>
                      toggleMutation.mutate({ id: task.id, done: true })
                    }
                    className="mt-0.5 w-5 h-5 rounded border border-oxide/40 shrink-0 flex items-center justify-center hover:border-signal transition-colors"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-chrome text-sm">{task.text}</p>
                    <div className="flex items-center gap-2 mt-1.5">
                      {Icon && (
                        <Icon size={12} className={agent?.color ?? 'text-oxide'} />
                      )}
                      <span className="text-oxide text-[10px]">
                        {task.assignee}
                      </span>
                      <span
                        className={clsx(
                          'text-[9px] px-1.5 py-0.5 rounded-full font-mono',
                          PRIORITY_BADGE[task.priority] ?? 'bg-oxide/20 text-oxide'
                        )}
                      >
                        {task.priority}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => removeMutation.mutate(task.id)}
                    className="p-1 text-oxide/40 hover:text-alert transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </motion.div>
            )
          })}
        </div>
      )}

      {/* Done tasks */}
      {doneTasks.length > 0 && (
        <div className="space-y-1">
          <p className="text-oxide text-xs font-medium mb-2">
            Выполнено ({doneTasks.length})
          </p>
          {doneTasks.map((task) => (
            <div
              key={task.id}
              className="glass rounded-lg p-2 flex items-center gap-2 opacity-50"
            >
              <button
                onClick={() =>
                  toggleMutation.mutate({ id: task.id, done: false })
                }
                className="w-4 h-4 rounded bg-signal/30 shrink-0 flex items-center justify-center"
              >
                <Check size={10} className="text-signal" />
              </button>
              <span className="text-oxide text-xs line-through flex-1 truncate">
                {task.text}
              </span>
              <span className="text-oxide text-[10px]">{task.assignee}</span>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && tasks.length === 0 && (
        <div className="glass rounded-xl p-8 text-center">
          <Check size={32} className="text-oxide mx-auto mb-3" />
          <p className="text-oxide text-sm">Нет задач</p>
        </div>
      )}
    </div>
  )
}
