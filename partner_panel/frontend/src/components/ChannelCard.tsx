import { MessageSquare, Reply, ChevronRight } from 'lucide-react'
import { SegmentBadge } from './StrategyBadge'
import { SparkLine } from './SparkLine'

export interface ChannelStatsData {
  username: string | null
  title: string
  segment: string | null
  is_active: boolean
  comments_today: number
  comments_total: number
  replies: number
  reply_rate: number
  avg_relevance: number | null
  posts_processed: number
}

interface ChannelCardProps {
  channel: ChannelStatsData
  sparkData?: number[]
  onClick?: () => void
}

export function ChannelCard({ channel, sparkData, onClick }: ChannelCardProps) {
  return (
    <button
      onClick={onClick}
      className="card w-full text-left flex items-center gap-3 transition-all duration-200 active:scale-[0.98]"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-star font-medium truncate">
            {channel.username ? `@${channel.username}` : channel.title}
          </span>
          {channel.segment && <SegmentBadge segment={channel.segment} />}
          {!channel.is_active && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-red-500/10 text-red-400">off</span>
          )}
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="flex items-center gap-1 text-dust">
            <MessageSquare className="w-3.5 h-3.5" />
            <span className="text-glow-soft font-medium">{channel.comments_today}</span>
            <span className="text-xs">/ {channel.comments_total}</span>
          </span>
          <span className="flex items-center gap-1 text-dust">
            <Reply className="w-3.5 h-3.5" />
            <span className={`font-medium ${channel.reply_rate > 10 ? 'text-emerald-400' : 'text-star-dim'}`}>
              {channel.reply_rate}%
            </span>
          </span>
        </div>
      </div>
      {sparkData && sparkData.length > 1 && (
        <SparkLine data={sparkData} width={60} height={24} />
      )}
      {onClick && <ChevronRight className="w-4 h-4 text-dust flex-shrink-0" />}
    </button>
  )
}
