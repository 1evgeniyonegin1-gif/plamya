import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeft, X, RefreshCw, Wand2, Edit3, Copy, Send } from 'lucide-react'
import { StatusBadge } from './StatusBadge'
import { useToast } from './Toast'
import { postsApi, type Post } from '../api/client'
import { useTelegram } from '../hooks/useTelegram'
import confetti from 'canvas-confetti'

interface Props {
  post: Post
  onBack: () => void
  onUpdate: (post: Post) => void
}

export function PostDetail({ post, onBack, onUpdate }: Props) {
  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState(post.content)
  const [aiPrompt, setAiPrompt] = useState('')
  const [showAiEdit, setShowAiEdit] = useState(false)
  const [loading, setLoading] = useState<string | null>(null)
  const { haptic } = useTelegram()
  const toast = useToast()

  const handleAction = async (action: string) => {
    setLoading(action)
    haptic('medium')
    try {
      if (action === 'publish') {
        const { data } = await postsApi.moderate(post.id, { action: 'publish' })
        onUpdate(data)
        toast.show('Пост опубликован!')
        confetti({ particleCount: 60, spread: 70, origin: { y: 0.7 } })
      } else if (action === 'reject') {
        const { data } = await postsApi.moderate(post.id, { action: 'reject' })
        onUpdate(data)
        toast.show('Пост отклонён', 'error')
      } else if (action === 'regenerate') {
        const { data } = await postsApi.regenerate(post.id)
        onUpdate(data)
        toast.show('Пост перегенерирован!')
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Ошибка'
      toast.show(detail, 'error')
      haptic('error')
    } finally {
      setLoading(null)
    }
  }

  const handleSaveEdit = async () => {
    if (editText === post.content) {
      setIsEditing(false)
      return
    }
    setLoading('save')
    try {
      const { data } = await postsApi.editContent(post.id, editText)
      onUpdate(data)
      setIsEditing(false)
      toast.show('Текст сохранён')
      haptic('success')
    } catch {
      toast.show('Ошибка сохранения', 'error')
    } finally {
      setLoading(null)
    }
  }

  const handleAiEdit = async () => {
    if (!aiPrompt.trim()) return
    setLoading('ai')
    try {
      const { data } = await postsApi.aiEdit(post.id, aiPrompt)
      onUpdate(data)
      setShowAiEdit(false)
      setAiPrompt('')
      toast.show('AI отредактировал пост')
      haptic('success')
    } catch {
      toast.show('Ошибка AI', 'error')
    } finally {
      setLoading(null)
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(post.content)
    haptic('light')
    toast.show('Скопировано')
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -40 }}
      className="flex flex-col h-full"
    >
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-smoke/30">
        <button onClick={onBack} className="text-pearl hover:text-silk transition-colors">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <StatusBadge status={post.status} />
        </div>
        <button onClick={handleCopy} className="text-pearl hover:text-silk p-1">
          <Copy size={18} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 pb-32">
        {isEditing ? (
          <div className="space-y-3">
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              className="w-full min-h-[300px] bg-ash border border-smoke rounded-xl p-3 text-sm text-silk resize-none focus:outline-none focus:border-flame/50"
              autoFocus
            />
            <div className="flex gap-2">
              <button
                onClick={handleSaveEdit}
                disabled={loading === 'save'}
                className="btn-fire flex-1 text-sm py-2"
              >
                {loading === 'save' ? 'Сохраняю...' : 'Сохранить'}
              </button>
              <button onClick={() => { setIsEditing(false); setEditText(post.content) }} className="btn-ghost text-sm">
                Отмена
              </button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-silk/90 leading-relaxed whitespace-pre-line">
            {post.content}
          </p>
        )}

        {/* AI Edit panel */}
        <AnimatePresence>
          {showAiEdit && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 space-y-2"
            >
              <textarea
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                placeholder="Что изменить? Например: сделай короче, добавь эмодзи..."
                className="w-full h-20 bg-ash border border-smoke rounded-xl p-3 text-sm text-silk resize-none focus:outline-none focus:border-flame/50"
                autoFocus
              />
              <div className="flex gap-2">
                <button
                  onClick={handleAiEdit}
                  disabled={loading === 'ai' || !aiPrompt.trim()}
                  className="btn-fire flex-1 text-sm py-2 flex items-center justify-center gap-2"
                >
                  <Wand2 size={14} />
                  {loading === 'ai' ? 'AI думает...' : 'Применить'}
                </button>
                <button onClick={() => setShowAiEdit(false)} className="btn-ghost text-sm">
                  Отмена
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Metrics for published posts */}
        {post.status === 'published' && post.views_count != null && (
          <div className="grid grid-cols-3 gap-2 mt-6">
            <div className="card text-center">
              <div className="text-lg font-bold text-silk">{post.views_count}</div>
              <div className="text-[10px] text-pearl">Просмотры</div>
            </div>
            <div className="card text-center">
              <div className="text-lg font-bold text-silk">{post.reactions_count}</div>
              <div className="text-[10px] text-pearl">Реакции</div>
            </div>
            <div className="card text-center">
              <div className="text-lg font-bold text-gold">{post.engagement_rate?.toFixed(1) || '—'}%</div>
              <div className="text-[10px] text-pearl">ER</div>
            </div>
          </div>
        )}
      </div>

      {/* Bottom actions — only for pending/draft */}
      {(post.status === 'pending' || post.status === 'draft') && !isEditing && (
        <div className="fixed bottom-[72px] left-0 right-0 p-4 bg-void/95 backdrop-blur-lg border-t border-smoke/30">
          <div className="flex gap-2 mb-2">
            <button
              onClick={() => handleAction('publish')}
              disabled={!!loading}
              className="btn-fire flex-1 text-sm py-2.5 flex items-center justify-center gap-1.5"
            >
              <Send size={14} />
              {loading === 'publish' ? '...' : 'Опубликовать'}
            </button>
            <button
              onClick={() => handleAction('reject')}
              disabled={!!loading}
              className="bg-flame/10 text-flame border border-flame/20 py-2.5 px-4 rounded-xl text-sm"
            >
              <X size={16} />
            </button>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setIsEditing(true)} className="btn-ghost flex-1 text-sm flex items-center justify-center gap-1.5">
              <Edit3 size={13} /> Редактировать
            </button>
            <button onClick={() => setShowAiEdit(!showAiEdit)} className="btn-ghost flex-1 text-sm flex items-center justify-center gap-1.5">
              <Wand2 size={13} /> AI Edit
            </button>
            <button
              onClick={() => handleAction('regenerate')}
              disabled={!!loading}
              className="btn-ghost text-sm flex items-center justify-center gap-1.5 px-3"
            >
              <RefreshCw size={13} className={loading === 'regenerate' ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      )}
    </motion.div>
  )
}
