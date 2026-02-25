import { motion } from 'framer-motion'
import { Eye, Heart, Share2 } from 'lucide-react'
import { StatusBadge } from './StatusBadge'
import type { Post } from '../api/client'

const typeLabels: Record<string, string> = {
  product: 'Продукт',
  motivation: 'Мотивация',
  news: 'Новости',
  tips: 'Советы',
  success_story: 'Успех',
  promo: 'Акция',
  invite_teaser: 'Инвайт',
  vip_content: 'VIP',
}

interface Props {
  post: Post
  index: number
  onClick: () => void
}

export function PostCard({ post, index, onClick }: Props) {
  const preview = post.content.length > 160
    ? post.content.slice(0, 160) + '...'
    : post.content

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.3 }}
      className="card-hover cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-blaze">
          {typeLabels[post.post_type] || post.post_type}
        </span>
        <StatusBadge status={post.status} />
      </div>

      <p className="text-sm text-silk/90 leading-relaxed whitespace-pre-line">
        {preview}
      </p>

      {post.status === 'published' && (
        <div className="flex items-center gap-4 mt-3 text-xs text-pearl">
          <span className="flex items-center gap-1">
            <Eye size={12} /> {post.views_count}
          </span>
          <span className="flex items-center gap-1">
            <Heart size={12} /> {post.reactions_count}
          </span>
          <span className="flex items-center gap-1">
            <Share2 size={12} /> {post.forwards_count}
          </span>
          {post.engagement_rate != null && (
            <span className="ml-auto text-gold font-medium">
              {post.engagement_rate.toFixed(1)}% ER
            </span>
          )}
        </div>
      )}

      {post.generated_at && (
        <div className="mt-2 text-[10px] text-mist">
          {new Date(post.generated_at).toLocaleString('ru-RU', {
            day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
          })}
        </div>
      )}
    </motion.div>
  )
}
