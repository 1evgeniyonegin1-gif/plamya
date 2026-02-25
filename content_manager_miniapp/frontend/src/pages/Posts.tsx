import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { Plus } from 'lucide-react'
import { postsApi, type Post } from '../api/client'
import { PostCard } from '../components/PostCard'
import { PostDetail } from '../components/PostDetail'
import { PostCardSkeleton } from '../components/Skeleton'
import { EmptyState } from '../components/EmptyState'
import { useToast } from '../components/Toast'
import { useTelegram } from '../hooks/useTelegram'
import clsx from 'clsx'

const filters = [
  { id: '', label: 'Все' },
  { id: 'pending', label: 'На модерации' },
  { id: 'published', label: 'Опубликованы' },
  { id: 'rejected', label: 'Отклонены' },
  { id: 'scheduled', label: 'Запланированы' },
]

export function Posts() {
  const [activeFilter, setActiveFilter] = useState('')
  const [selectedPost, setSelectedPost] = useState<Post | null>(null)
  const [generating, setGenerating] = useState(false)
  const { haptic } = useTelegram()
  const toast = useToast()
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['posts', activeFilter],
    queryFn: () => postsApi.list({ status: activeFilter || undefined, limit: 50 }),
    select: (res) => res.data,
  })

  const handleGenerate = async () => {
    setGenerating(true)
    haptic('medium')
    try {
      const { data: post } = await postsApi.generate({})
      toast.show('Новый пост сгенерирован!')
      haptic('success')
      queryClient.invalidateQueries({ queryKey: ['posts'] })
      setSelectedPost(post)
    } catch {
      toast.show('Ошибка генерации', 'error')
      haptic('error')
    } finally {
      setGenerating(false)
    }
  }

  const handlePostUpdate = (updated: Post) => {
    setSelectedPost(updated)
    queryClient.invalidateQueries({ queryKey: ['posts'] })
  }

  return (
    <div className="flex flex-col h-full">
      <AnimatePresence mode="wait">
        {selectedPost ? (
          <PostDetail
            key="detail"
            post={selectedPost}
            onBack={() => setSelectedPost(null)}
            onUpdate={handlePostUpdate}
          />
        ) : (
          <motion.div
            key="list"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col h-full"
          >
            {/* Header */}
            <div className="p-4 pb-2">
              <div className="flex items-center justify-between mb-3">
                <h1 className="text-lg font-bold text-silk">Посты</h1>
                <button
                  onClick={handleGenerate}
                  disabled={generating}
                  className="btn-fire text-sm py-2 px-4 flex items-center gap-1.5"
                >
                  <Plus size={16} />
                  {generating ? 'Генерирую...' : 'Новый'}
                </button>
              </div>

              {/* Filters */}
              <div className="flex gap-1.5 overflow-x-auto pb-1 -mx-1 px-1 scrollbar-hide">
                {filters.map((f) => (
                  <button
                    key={f.id}
                    onClick={() => { setActiveFilter(f.id); haptic('selection') }}
                    className={clsx(
                      'px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all',
                      activeFilter === f.id
                        ? 'bg-flame/15 text-flame border border-flame/30'
                        : 'bg-ash/50 text-pearl border border-transparent'
                    )}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Posts list */}
            <div className="flex-1 overflow-y-auto px-4 pb-24">
              <div className="space-y-3 pt-2">
                {isLoading ? (
                  Array.from({ length: 4 }).map((_, i) => <PostCardSkeleton key={i} />)
                ) : data?.posts.length === 0 ? (
                  <EmptyState
                    title="Нет постов"
                    description="Нажмите 'Новый' чтобы сгенерировать первый пост"
                  />
                ) : (
                  data?.posts.map((post, i) => (
                    <PostCard
                      key={post.id}
                      post={post}
                      index={i}
                      onClick={() => { setSelectedPost(post); haptic('light') }}
                    />
                  ))
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
