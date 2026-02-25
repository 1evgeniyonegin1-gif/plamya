import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft, TrendingUp, MessageSquare, Reply, Eye,
  Zap, Radio, X, Calendar
} from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { trafficApi } from '../api/client'
import { Loading } from '../components/Loading'
import { StatCard } from '../components/StatCard'
import { ProgressBar } from '../components/ProgressBar'
import { SparkLine } from '../components/SparkLine'
import { StrategyBadge, SegmentBadge } from '../components/StrategyBadge'
import { ChannelCard, type ChannelStatsData } from '../components/ChannelCard'

interface StatsProps {
  onBack: () => void
}

// Types matching backend
interface TrafficOverview {
  comments_today: number
  comments_week: number
  total_comments: number
  replies_today: number
  replies_week: number
  reply_rate: number
  stories_today: number
  stories_week: number
  accounts_active: number
  accounts_total: number
}

interface StrategyData {
  strategy: string
  segment: string
  attempts: number
  successes: number
  score: number
}

interface DailyTraffic {
  date: string
  comments: number
  stories: number
  replies: number
  avg_relevance: number | null
}

interface RecentComment {
  content: string | null
  strategy: string | null
  got_reply: boolean
  reply_count: number
  relevance_score: number | null
  post_topic: string | null
  created_at: string
}

interface ChannelDetail {
  username: string | null
  title: string
  segment: string | null
  comments_today: number
  comments_total: number
  replies: number
  reply_rate: number
  avg_relevance: number | null
  recent_comments: RecentComment[]
  strategy_distribution: StrategyData[]
}

export function Stats({ onBack }: StatsProps) {
  const { setBackButton } = useTelegram()
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null)

  useEffect(() => {
    return setBackButton(onBack)
  }, [onBack, setBackButton])

  // Fetch all data in parallel
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['traffic', 'overview'],
    queryFn: () => trafficApi.getOverview().then(r => r.data as TrafficOverview),
  })

  const { data: channels, isLoading: channelsLoading } = useQuery({
    queryKey: ['traffic', 'channels'],
    queryFn: () => trafficApi.getChannels().then(r => r.data as ChannelStatsData[]),
  })

  const { data: strategies } = useQuery({
    queryKey: ['traffic', 'strategies'],
    queryFn: () => trafficApi.getStrategies().then(r => r.data as StrategyData[]),
  })

  const { data: daily } = useQuery({
    queryKey: ['traffic', 'daily'],
    queryFn: () => trafficApi.getDaily(7).then(r => r.data as DailyTraffic[]),
  })

  // Channel detail (when selected)
  const { data: channelDetail, isLoading: detailLoading } = useQuery({
    queryKey: ['traffic', 'channel', selectedChannel],
    queryFn: () => trafficApi.getChannel(selectedChannel!).then(r => r.data as ChannelDetail),
    enabled: !!selectedChannel,
  })

  if (overviewLoading || channelsLoading) {
    return <Loading />
  }

  // Aggregate strategies (combine across segments)
  const aggregatedStrategies = strategies?.reduce((acc, s) => {
    const existing = acc.find(a => a.strategy === s.strategy)
    if (existing) {
      existing.attempts += s.attempts
      existing.successes += s.successes
      existing.score = existing.attempts > 0 ? existing.successes / existing.attempts : 0
    } else {
      acc.push({ ...s, score: s.attempts > 0 ? s.successes / s.attempts : 0 })
    }
    return acc
  }, [] as StrategyData[])?.sort((a, b) => b.score - a.score)

  const maxAttempts = aggregatedStrategies
    ? Math.max(...aggregatedStrategies.map(s => s.attempts), 1)
    : 1

  // Sparkline data from daily
  const commentsSpark = daily?.map(d => d.comments) || []
  const repliesSpark = daily?.map(d => d.replies) || []

  const activeChannels = channels?.filter(c => c.is_active) || []

  return (
    <div className="p-4 pb-24">
      {/* Header */}
      <header className="flex items-center gap-3 mb-6 pt-4">
        <button
          onClick={onBack}
          className="p-2 -ml-2 hover:bg-void/50 rounded-full transition-colors text-star"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-star">Traffic Engine</h1>
          <p className="text-sm text-dust">Аналитика в реальном времени</p>
        </div>
      </header>

      {/* Section 1: Overview cards */}
      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-glow-soft" />
          Обзор
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            icon={<MessageSquare className="w-5 h-5" />}
            label="Комменты"
            value={overview?.comments_today || 0}
            sublabel={`${overview?.comments_week || 0} за неделю`}
          />
          <StatCard
            icon={<Reply className="w-5 h-5" />}
            label="Ответы"
            value={overview?.replies_today || 0}
            sublabel={`Reply rate: ${overview?.reply_rate || 0}%`}
          />
          <StatCard
            icon={<Eye className="w-5 h-5" />}
            label="Сторис"
            value={overview?.stories_today || 0}
            sublabel={`${overview?.stories_week || 0} за неделю`}
          />
          <StatCard
            icon={<Radio className="w-5 h-5" />}
            label="Аккаунты"
            value={overview?.accounts_active || 0}
            sublabel={`из ${overview?.accounts_total || 0}`}
          />
        </div>
        {/* Sparklines */}
        {commentsSpark.length > 1 && (
          <div className="card mt-3 flex items-center gap-4">
            <div className="flex-1">
              <div className="text-xs text-dust mb-1">Комменты за 7 дней</div>
              <SparkLine data={commentsSpark} color="#818cf8" width={140} height={28} />
            </div>
            <div className="flex-1">
              <div className="text-xs text-dust mb-1">Ответы за 7 дней</div>
              <SparkLine data={repliesSpark} color="#34d399" width={140} height={28} />
            </div>
          </div>
        )}
      </section>

      {/* Section 2: Strategies */}
      {aggregatedStrategies && aggregatedStrategies.length > 0 && (
        <section className="mb-6">
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Zap className="w-5 h-5 text-glow-soft" />
            Стратегии MAB
          </h2>
          <div className="card space-y-3">
            {aggregatedStrategies.map(s => {
              const color = ({
                smart: 'glow' as const,
                supportive: 'green' as const,
                funny: 'amber' as const,
                expert: 'purple' as const,
              })[s.strategy] || 'glow' as const

              return (
                <div key={s.strategy}>
                  <div className="flex items-center gap-2 mb-1">
                    <StrategyBadge strategy={s.strategy} score={s.score} />
                    <span className="text-xs text-dust ml-auto">
                      {s.attempts} {declensionAttempts(s.attempts)}
                    </span>
                  </div>
                  <ProgressBar
                    value={s.attempts}
                    max={maxAttempts}
                    color={color}
                    showPercent={false}
                  />
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Section 3: Channels */}
      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-glow-soft" />
          Каналы
          <span className="text-sm text-dust font-normal ml-auto">
            {activeChannels.length} активных
          </span>
        </h2>
        <div className="space-y-2">
          {channels?.map(ch => (
            <ChannelCard
              key={ch.username || ch.title}
              channel={ch}
              onClick={ch.username ? () => setSelectedChannel(ch.username) : undefined}
            />
          ))}
          {(!channels || channels.length === 0) && (
            <div className="card text-center text-dust py-8">
              Нет подключённых каналов
            </div>
          )}
        </div>
      </section>

      {/* Section 4: Daily breakdown */}
      {daily && daily.length > 0 && (
        <section className="mb-6">
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-glow-soft" />
            По дням
          </h2>
          <div className="space-y-2">
            {[...daily].reverse().map(day => {
              const d = new Date(day.date)
              const dayName = d.toLocaleDateString('ru-RU', { weekday: 'short' })
              const dayNum = d.getDate()

              return (
                <div key={day.date} className="card flex items-center">
                  <div className="w-12 text-center mr-4">
                    <div className="text-xs text-dust uppercase">{dayName}</div>
                    <div className="text-lg font-bold text-star">{dayNum}</div>
                  </div>
                  <div className="flex-1 grid grid-cols-3 gap-2 text-center">
                    <div>
                      <div className="font-semibold text-glow-soft">{day.comments}</div>
                      <div className="text-xs text-dust">комм.</div>
                    </div>
                    <div>
                      <div className={`font-semibold ${day.replies > 0 ? 'text-emerald-400' : 'text-star-dim'}`}>
                        {day.replies}
                      </div>
                      <div className="text-xs text-dust">ответов</div>
                    </div>
                    <div>
                      <div className="font-semibold text-star">{day.stories}</div>
                      <div className="text-xs text-dust">сторис</div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Channel Detail Overlay */}
      {selectedChannel && (
        <ChannelDetailOverlay
          detail={channelDetail || null}
          loading={detailLoading}
          onClose={() => setSelectedChannel(null)}
        />
      )}
    </div>
  )
}


// --- Channel Detail Bottom Sheet ---

function ChannelDetailOverlay({
  detail,
  loading,
  onClose,
}: {
  detail: ChannelDetail | null
  loading: boolean
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Sheet */}
      <div className="relative w-full max-h-[85vh] bg-abyss border-t border-glow rounded-t-3xl overflow-y-auto animate-fade-in">
        {/* Handle */}
        <div className="sticky top-0 bg-abyss/90 backdrop-blur-md z-10 pt-3 pb-2 px-5">
          <div className="w-10 h-1 rounded-full bg-dust/30 mx-auto mb-3" />
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-star">
                {detail?.username ? `@${detail.username}` : detail?.title || 'Loading...'}
              </h3>
              {detail?.segment && <SegmentBadge segment={detail.segment} size="md" />}
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-void/50 rounded-full text-dust"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="py-12"><Loading /></div>
        ) : detail ? (
          <div className="px-5 pb-8 space-y-5">
            {/* Stats row */}
            <div className="grid grid-cols-3 gap-3">
              <div className="card text-center">
                <div className="text-2xl font-bold text-glow-soft">{detail.comments_today}</div>
                <div className="text-xs text-dust">сегодня</div>
              </div>
              <div className="card text-center">
                <div className="text-2xl font-bold text-star">{detail.comments_total}</div>
                <div className="text-xs text-dust">всего</div>
              </div>
              <div className="card text-center">
                <div className={`text-2xl font-bold ${detail.reply_rate > 10 ? 'text-emerald-400' : 'text-star-dim'}`}>
                  {detail.reply_rate}%
                </div>
                <div className="text-xs text-dust">ответов</div>
              </div>
            </div>

            {/* Strategy distribution */}
            {detail.strategy_distribution.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-star mb-2">Стратегии</h4>
                <div className="card space-y-2">
                  {detail.strategy_distribution.map(s => {
                    const color = ({
                      smart: 'glow' as const,
                      supportive: 'green' as const,
                      funny: 'amber' as const,
                      expert: 'purple' as const,
                    })[s.strategy] || 'glow' as const

                    return (
                      <ProgressBar
                        key={s.strategy}
                        value={s.successes}
                        max={s.attempts || 1}
                        label={s.strategy}
                        sublabel={`${s.attempts} комм.`}
                        color={color}
                      />
                    )
                  })}
                </div>
              </div>
            )}

            {/* Recent comments */}
            {detail.recent_comments.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-star mb-2">
                  Последние комменты
                </h4>
                <div className="space-y-2">
                  {detail.recent_comments.map((c, i) => (
                    <div key={i} className="card">
                      <div className="flex items-center gap-2 mb-1.5">
                        {c.strategy && <StrategyBadge strategy={c.strategy} />}
                        {c.got_reply && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400">
                            +{c.reply_count} {declensionReplies(c.reply_count)}
                          </span>
                        )}
                        {c.relevance_score !== null && (
                          <span className="text-xs text-dust ml-auto">
                            rel: {c.relevance_score}
                          </span>
                        )}
                      </div>
                      {c.content && (
                        <p className="text-sm text-star-dim leading-relaxed line-clamp-3">
                          {c.content}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-1.5">
                        {c.post_topic && (
                          <span className="text-xs text-dust truncate">{c.post_topic}</span>
                        )}
                        <span className="text-xs text-dust/50 ml-auto flex-shrink-0">
                          {formatTimeAgo(c.created_at)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}


// --- Helpers ---

function declensionAttempts(n: number): string {
  const mod100 = n % 100
  const mod10 = n % 10
  if (mod100 >= 11 && mod100 <= 14) return 'попыток'
  if (mod10 === 1) return 'попытка'
  if (mod10 >= 2 && mod10 <= 4) return 'попытки'
  return 'попыток'
}

function declensionReplies(n: number): string {
  const mod100 = n % 100
  const mod10 = n % 10
  if (mod100 >= 11 && mod100 <= 14) return 'ответов'
  if (mod10 === 1) return 'ответ'
  if (mod10 >= 2 && mod10 <= 4) return 'ответа'
  return 'ответов'
}

function formatTimeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 60) return `${minutes}м назад`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}ч назад`
  const days = Math.floor(hours / 24)
  return `${days}д назад`
}
