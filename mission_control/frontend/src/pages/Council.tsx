import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Users, Send, ArrowLeft, MessageCircle } from 'lucide-react'
import clsx from 'clsx'
import { councilApi } from '../api/client'
import { AGENTS } from '../lib/constants'
import TimeAgo from '../components/TimeAgo'

export default function Council() {
  const queryClient = useQueryClient()
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null)
  const [showNewTopic, setShowNewTopic] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [replyText, setReplyText] = useState('')

  // List topics
  const { data: topicsData, isLoading } = useQuery({
    queryKey: ['council', 'topics'],
    queryFn: () => councilApi.listTopics(20).then((r) => r.data),
    refetchInterval: 30_000,
  })

  // Get single topic detail
  const { data: topicDetail } = useQuery({
    queryKey: ['council', 'topic', selectedTopicId],
    queryFn: () =>
      selectedTopicId
        ? councilApi.getTopic(selectedTopicId).then((r) => r.data)
        : null,
    enabled: !!selectedTopicId,
    refetchInterval: 10_000,
  })

  // Create topic
  const createMutation = useMutation({
    mutationFn: (title: string) => councilApi.createTopic(title),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['council'] })
      setShowNewTopic(false)
      setNewTitle('')
      setSelectedTopicId(res.data.topic_id)
    },
  })

  // Ask all agents
  const askAllMutation = useMutation({
    mutationFn: (topicId: number) => councilApi.askAll(topicId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['council'] })
    },
  })

  // Reply
  const replyMutation = useMutation({
    mutationFn: ({ topicId, text }: { topicId: number; text: string }) =>
      councilApi.reply(topicId, 'admin', text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['council'] })
      setReplyText('')
    },
  })

  const topics = topicsData?.topics ?? []

  // ── Topic detail view ──
  if (selectedTopicId) {
    // Show loading while topic detail is being fetched
    if (!topicDetail) {
      return (
        <div className="p-4 space-y-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSelectedTopicId(null)}
              className="p-2 rounded-lg glass"
            >
              <ArrowLeft size={18} className="text-oxide" />
            </button>
            <span className="text-oxide text-sm">Загрузка...</span>
          </div>
          <div className="text-center py-8">
            <div className="w-8 h-8 rounded-full border-2 border-signal/30 border-t-signal animate-spin mx-auto" />
          </div>
        </div>
      )
    }

    return (
      <div className="p-4 space-y-4">
        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSelectedTopicId(null)}
            className="p-2 rounded-lg glass"
          >
            <ArrowLeft size={18} className="text-oxide" />
          </button>
          <div className="flex-1 min-w-0">
            <h2 className="text-signal font-bold text-sm truncate">
              {topicDetail.title}
            </h2>
            <p className="text-oxide text-xs">
              {topicDetail.author} &middot; {topicDetail.created_at}
            </p>
          </div>
          <span
            className={clsx(
              'text-[10px] px-2 py-0.5 rounded-full font-mono',
              topicDetail.status === 'open'
                ? 'bg-signal/20 text-signal'
                : 'bg-oxide/20 text-oxide'
            )}
          >
            {topicDetail.status}
          </span>
        </div>

        {/* Responses */}
        <div className="space-y-3">
          {topicDetail.responses.length === 0 && (
            <div className="glass rounded-xl p-6 text-center">
              <Users size={24} className="text-oxide mx-auto mb-2" />
              <p className="text-oxide text-sm">
                Пока нет ответов. Нажми "Спросить всех" чтобы агенты высказались.
              </p>
            </div>
          )}

          {topicDetail.responses.map((r, i) => {
            const agentMeta =
              AGENTS[r.agent_id] ??
              (r.agent_id === 'admin'
                ? { name: 'ДАНИЛ', color: 'text-amber-400', icon: null, role: 'Owner' }
                : null)
            const Icon = agentMeta && 'icon' in agentMeta ? agentMeta.icon : null
            const isAdmin = r.agent_id === 'admin'

            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className={clsx(
                  'glass rounded-xl p-3',
                  isAdmin && 'border border-amber-500/30'
                )}
              >
                <div className="flex items-center gap-2 mb-2">
                  {Icon && (
                    <Icon
                      size={16}
                      className={agentMeta?.color ?? 'text-oxide'}
                    />
                  )}
                  {isAdmin && (
                    <div className="w-4 h-4 rounded-full bg-amber-500/30 flex items-center justify-center">
                      <span className="text-[8px] text-amber-400 font-bold">D</span>
                    </div>
                  )}
                  <span
                    className={clsx(
                      'text-xs font-bold',
                      isAdmin ? 'text-amber-400' : agentMeta?.color ?? 'text-oxide'
                    )}
                  >
                    {r.agent_name}
                  </span>
                  <span className="text-oxide text-[10px] ml-auto font-mono">
                    {r.timestamp.split(' ')[1] || r.timestamp}
                  </span>
                </div>
                <p className="text-chrome text-sm leading-relaxed whitespace-pre-wrap">
                  {r.text}
                </p>
              </motion.div>
            )
          })}
        </div>

        {/* Actions */}
        <div className="space-y-2">
          <button
            onClick={() => askAllMutation.mutate(selectedTopicId)}
            disabled={askAllMutation.isPending}
            className="w-full glass rounded-xl p-3 text-center text-signal text-sm font-medium active:scale-[0.98] transition-transform"
          >
            <Users size={16} className="inline mr-2" />
            {askAllMutation.isPending
              ? 'Отправляю...'
              : `Спросить всех агентов`}
          </button>

          {/* Reply input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder="Написать от имени Данила..."
              className="flex-1 glass rounded-xl px-3 py-2.5 text-chrome text-sm bg-transparent outline-none placeholder:text-oxide/50"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && replyText.trim()) {
                  replyMutation.mutate({
                    topicId: selectedTopicId,
                    text: replyText.trim(),
                  })
                }
              }}
            />
            <button
              onClick={() => {
                if (replyText.trim()) {
                  replyMutation.mutate({
                    topicId: selectedTopicId,
                    text: replyText.trim(),
                  })
                }
              }}
              disabled={!replyText.trim() || replyMutation.isPending}
              className="glass rounded-xl p-2.5 text-signal disabled:text-oxide/30"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Topics list view ──
  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-signal font-bold text-lg">СОВЕТ</h1>
          <p className="text-oxide text-xs">Обсуждения агентов</p>
        </div>
        <button
          onClick={() => setShowNewTopic(true)}
          className="glass rounded-xl p-2.5 text-signal active:scale-95 transition-transform"
        >
          <Plus size={20} />
        </button>
      </div>

      {/* New topic modal */}
      <AnimatePresence>
        {showNewTopic && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="glass rounded-xl p-4 space-y-3">
              <p className="text-chrome text-sm font-medium">Новая тема</p>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="О чём хочешь спросить агентов?"
                className="w-full glass rounded-lg px-3 py-2.5 text-chrome text-sm bg-transparent outline-none placeholder:text-oxide/50"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && newTitle.trim()) {
                    createMutation.mutate(newTitle.trim())
                  }
                }}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => setShowNewTopic(false)}
                  className="flex-1 glass rounded-lg py-2 text-oxide text-sm"
                >
                  Отмена
                </button>
                <button
                  onClick={() => {
                    if (newTitle.trim()) createMutation.mutate(newTitle.trim())
                  }}
                  disabled={!newTitle.trim() || createMutation.isPending}
                  className="flex-1 bg-signal/20 rounded-lg py-2 text-signal text-sm font-medium disabled:opacity-50"
                >
                  {createMutation.isPending ? '...' : 'Создать'}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Topics list */}
      {isLoading && (
        <div className="text-center py-8">
          <div className="w-8 h-8 rounded-full border-2 border-signal/30 border-t-signal animate-spin mx-auto" />
        </div>
      )}

      {!isLoading && topics.length === 0 && (
        <div className="glass rounded-xl p-8 text-center">
          <MessageCircle size={32} className="text-oxide mx-auto mb-3" />
          <p className="text-oxide text-sm">Нет обсуждений</p>
          <p className="text-oxide/50 text-xs mt-1">
            Создай тему — агенты ответят из своей экспертизы
          </p>
        </div>
      )}

      <div className="space-y-2">
        {topics.map((topic, i) => (
          <motion.button
            key={topic.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03 }}
            onClick={() => setSelectedTopicId(topic.id)}
            className="w-full glass rounded-xl p-3 text-left active:scale-[0.98] transition-transform"
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-chrome text-sm font-medium line-clamp-2">
                {topic.title}
              </h3>
              <span
                className={clsx(
                  'shrink-0 text-[10px] px-1.5 py-0.5 rounded-full font-mono',
                  topic.status === 'open'
                    ? 'bg-signal/20 text-signal'
                    : 'bg-oxide/20 text-oxide'
                )}
              >
                {topic.status}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-2 text-oxide text-[10px]">
              <span>{topic.author}</span>
              <span>&middot;</span>
              <TimeAgo date={topic.created_at} />
              <span className="ml-auto flex items-center gap-1">
                <MessageCircle size={10} />
                {topic.response_count}
              </span>
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  )
}
