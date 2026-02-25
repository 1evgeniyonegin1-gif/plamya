import { useQuery } from '@tanstack/react-query'
import { Users, Eye, MousePointerClick, Radio, Plus, ChevronRight, MessageSquare, Reply, Zap } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useTelegram } from '../hooks/useTelegram'
import { statsApi, trafficApi } from '../api/client'
import { StatCard } from '../components/StatCard'
import { Loading } from '../components/Loading'

type Page = 'dashboard' | 'connect' | 'channels' | 'stats'

interface DashboardProps {
  onNavigate: (page: Page) => void
}

export function Dashboard({ onNavigate }: DashboardProps) {
  const { partner } = useAuth()
  const { user, haptic } = useTelegram()

  // Fetch overview stats
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats', 'overview'],
    queryFn: () => statsApi.getOverview().then(res => res.data),
  })

  // Fetch traffic overview
  const { data: traffic } = useQuery({
    queryKey: ['traffic', 'overview'],
    queryFn: () => trafficApi.getOverview().then(res => res.data as {
      comments_today: number; replies_today: number; reply_rate: number;
      accounts_active: number; accounts_total: number
    }),
  })

  if (isLoading) {
    return <Loading />
  }

  const handleNavigate = (page: Page) => {
    haptic('light')
    onNavigate(page)
  }

  return (
    <div className="p-4 pt-8 pb-24">
      {/* Header — космический */}
      <header className="mb-8 text-center">
        <h1 className="text-2xl font-light mb-2 text-gradient">
          {user?.first_name || partner?.first_name || 'Партнёр'}
        </h1>
        <p className="text-dust text-sm tracking-wide">
          Твоя вселенная возможностей
        </p>
      </header>

      {/* Quick Stats — парящие карточки */}
      <section className="mb-8">
        <div className="grid grid-cols-2 gap-4">
          <StatCard
            icon={<Radio className="w-5 h-5" />}
            label="Каналы"
            value={stats?.total_channels ?? partner?.total_channels ?? 0}
          />
          <StatCard
            icon={<Users className="w-5 h-5" />}
            label="Подписчики"
            value={stats?.total_subscribers ?? partner?.total_subscribers ?? 0}
            change={stats?.subscribers_today ? Math.round(stats.subscribers_today / (stats.total_subscribers || 1) * 100) : undefined}
          />
          <StatCard
            icon={<Eye className="w-5 h-5" />}
            label="Просмотры"
            value={stats?.total_views ?? 0}
          />
          <StatCard
            icon={<MousePointerClick className="w-5 h-5" />}
            label="Лиды"
            value={stats?.total_leads ?? partner?.total_leads ?? 0}
          />
        </div>
      </section>

      {/* Traffic Engine widget */}
      {traffic && (traffic.comments_today > 0 || traffic.accounts_active > 0) && (
        <section className="mb-8">
          <button
            onClick={() => handleNavigate('stats')}
            className="w-full card group"
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-star flex items-center gap-2">
                <Zap className="w-4 h-4 text-glow-soft" />
                Traffic Engine
              </h3>
              <ChevronRight className="w-4 h-4 text-dust group-hover:text-glow-soft transition-colors" />
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <div className="flex items-center justify-center gap-1 mb-0.5">
                  <MessageSquare className="w-3.5 h-3.5 text-glow-soft" />
                  <span className="text-lg font-semibold text-star">{traffic.comments_today}</span>
                </div>
                <div className="text-xs text-dust">комментов</div>
              </div>
              <div>
                <div className="flex items-center justify-center gap-1 mb-0.5">
                  <Reply className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-lg font-semibold text-star">{traffic.replies_today}</span>
                </div>
                <div className="text-xs text-dust">ответов</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-star mb-0.5">
                  {traffic.reply_rate}%
                </div>
                <div className="text-xs text-dust">reply rate</div>
              </div>
            </div>
          </button>
        </section>
      )}

      {/* Quick Actions — путь к звёздам */}
      <section className="mb-8 space-y-3">
        {/* Connect new account */}
        <button
          onClick={() => handleNavigate('connect')}
          className="w-full card flex items-center gap-4 group"
        >
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-glow/20 to-nebula-purple/20 flex items-center justify-center group-hover:scale-105 transition-transform">
            <Plus className="w-5 h-5 text-glow-soft" />
          </div>
          <div className="text-left flex-1">
            <div className="font-medium text-star">Подключить аккаунт</div>
            <div className="text-xs text-dust">Новая точка во вселенной</div>
          </div>
          <ChevronRight className="w-5 h-5 text-dust group-hover:text-glow-soft transition-colors" />
        </button>

        {/* View channels */}
        <button
          onClick={() => handleNavigate('channels')}
          className="w-full card flex items-center gap-4 group"
        >
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-nebula-blue/20 to-glow/20 flex items-center justify-center group-hover:scale-105 transition-transform">
            <Radio className="w-5 h-5 text-nebula-blue" />
          </div>
          <div className="text-left flex-1">
            <div className="font-medium text-star">Мои каналы</div>
            <div className="text-xs text-dust">Созвездия твоей сети</div>
          </div>
          <ChevronRight className="w-5 h-5 text-dust group-hover:text-glow-soft transition-colors" />
        </button>

        {/* View stats */}
        <button
          onClick={() => handleNavigate('stats')}
          className="w-full card flex items-center gap-4 group"
        >
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-nebula-purple/20 to-nebula-blue/20 flex items-center justify-center group-hover:scale-105 transition-transform">
            <Eye className="w-5 h-5 text-nebula-purple" />
          </div>
          <div className="text-left flex-1">
            <div className="font-medium text-star">Аналитика</div>
            <div className="text-xs text-dust">Взгляд на галактику</div>
          </div>
          <ChevronRight className="w-5 h-5 text-dust group-hover:text-glow-soft transition-colors" />
        </button>
      </section>

      {/* Status — пульс космоса */}
      <section>
        <div className="card animate-glow">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 bg-glow rounded-full animate-breathe" />
            <span className="text-sm text-dust">Всё работает</span>
          </div>
        </div>
      </section>
    </div>
  )
}
