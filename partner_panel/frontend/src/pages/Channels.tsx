import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Radio, Users, Eye, Play, Pause, Settings, Plus, MessageSquare } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { channelsApi, trafficApi } from '../api/client'
import { Loading } from '../components/Loading'
import clsx from 'clsx'

interface ChannelsProps {
  onBack: () => void
}

interface Channel {
  id: number
  channel_id: number
  channel_username: string | null
  channel_title: string
  segment: string
  persona_name: string
  status: string
  posting_enabled: boolean
  posts_per_day: number
  subscribers_count: number
  posts_count: number
  avg_views: number
  created_at: string
}

const STATUS_COLORS: Record<string, string> = {
  creating: 'bg-yellow-500',
  warming: 'bg-orange-500',
  active: 'bg-green-500',
  paused: 'bg-gray-500',
  banned: 'bg-red-500',
}

const STATUS_LABELS: Record<string, string> = {
  creating: 'Создаётся',
  warming: 'Прогрев',
  active: 'Активен',
  paused: 'Пауза',
  banned: 'Заблокирован',
}

const SEGMENT_EMOJI: Record<string, string> = {
  zozh: '🥗',
  mama: '👶',
  business: '💼',
}

export function Channels({ onBack }: ChannelsProps) {
  const { setBackButton, haptic } = useTelegram()

  // Set back button
  useEffect(() => {
    return setBackButton(onBack)
  }, [onBack, setBackButton])

  // Fetch channels
  const { data: channels, isLoading, refetch } = useQuery({
    queryKey: ['channels'],
    queryFn: () => channelsApi.list().then(res => res.data as Channel[]),
  })

  // Fetch traffic stats per channel
  const { data: trafficChannels } = useQuery({
    queryKey: ['traffic', 'channels'],
    queryFn: () => trafficApi.getChannels().then(res => res.data as {
      username: string | null; comments_today: number; comments_total: number;
      reply_rate: number
    }[]),
  })

  const handleTogglePosting = async (channel: Channel) => {
    haptic('medium')
    try {
      if (channel.posting_enabled) {
        await channelsApi.pause(channel.id)
      } else {
        await channelsApi.resume(channel.id)
      }
      refetch()
    } catch (error) {
      console.error('Error toggling posting:', error)
    }
  }

  if (isLoading) {
    return <Loading />
  }

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
        <div className="flex-1">
          <h1 className="text-xl font-bold text-star">Мои каналы</h1>
          <p className="text-sm text-dust">
            {channels?.length || 0} каналов
          </p>
        </div>
      </header>

      {/* Channels list */}
      {channels && channels.length > 0 ? (
        <div className="space-y-3">
          {channels.map((channel) => (
            <div key={channel.id} className="card">
              {/* Channel header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-void/50 rounded-full flex items-center justify-center text-2xl">
                    {SEGMENT_EMOJI[channel.segment] || '📢'}
                  </div>
                  <div>
                    <div className="font-medium text-star">{channel.channel_title}</div>
                    <div className="text-sm text-dust">
                      Персона: {channel.persona_name}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <div className={clsx('w-2 h-2 rounded-full', STATUS_COLORS[channel.status])} />
                  <span className="text-xs text-dust">
                    {STATUS_LABELS[channel.status]}
                  </span>
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-4 gap-2 mb-3">
                <div className="text-center p-2 bg-void/30 rounded-lg">
                  <Users className="w-4 h-4 mx-auto mb-1 text-dust" />
                  <div className="font-semibold text-star">{channel.subscribers_count}</div>
                  <div className="text-xs text-dust">подп.</div>
                </div>
                <div className="text-center p-2 bg-void/30 rounded-lg">
                  <Radio className="w-4 h-4 mx-auto mb-1 text-dust" />
                  <div className="font-semibold text-star">{channel.posts_count}</div>
                  <div className="text-xs text-dust">постов</div>
                </div>
                <div className="text-center p-2 bg-void/30 rounded-lg">
                  <Eye className="w-4 h-4 mx-auto mb-1 text-dust" />
                  <div className="font-semibold text-star">{channel.avg_views}</div>
                  <div className="text-xs text-dust">просм.</div>
                </div>
                {(() => {
                  const tc = trafficChannels?.find(t => t.username === channel.channel_username)
                  return tc ? (
                    <div className="text-center p-2 bg-void/30 rounded-lg">
                      <MessageSquare className="w-4 h-4 mx-auto mb-1 text-glow-soft" />
                      <div className="font-semibold text-glow-soft">{tc.comments_today}</div>
                      <div className="text-xs text-dust">комм.</div>
                    </div>
                  ) : (
                    <div className="text-center p-2 bg-void/30 rounded-lg">
                      <MessageSquare className="w-4 h-4 mx-auto mb-1 text-dust" />
                      <div className="font-semibold text-dust">—</div>
                      <div className="text-xs text-dust">комм.</div>
                    </div>
                  )
                })()}
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  onClick={() => handleTogglePosting(channel)}
                  className={clsx(
                    'flex-1 btn flex items-center justify-center gap-2',
                    channel.posting_enabled ? 'btn-secondary' : 'btn-primary'
                  )}
                >
                  {channel.posting_enabled ? (
                    <>
                      <Pause className="w-4 h-4" />
                      Пауза
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Запустить
                    </>
                  )}
                </button>
                <button className="btn btn-secondary p-3">
                  <Settings className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-void/50 rounded-full flex items-center justify-center mx-auto mb-4">
            <Radio className="w-8 h-8 text-dust" />
          </div>
          <h2 className="text-lg font-semibold mb-2 text-star">Нет каналов</h2>
          <p className="text-dust mb-6">
            Подключите аккаунт, чтобы создать первый канал
          </p>
          <button
            onClick={onBack}
            className="btn btn-primary inline-flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Подключить аккаунт
          </button>
        </div>
      )}
    </div>
  )
}
