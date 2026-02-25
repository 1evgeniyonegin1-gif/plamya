import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Calendar, Star, TrendingUp, Search, RefreshCw, BookOpen, Clock, Send } from 'lucide-react'
import { directorApi, diaryApi, scheduleApi } from '../api/client'
import { EmptyState } from '../components/EmptyState'
import { useTelegram } from '../hooks/useTelegram'
import { useToast } from '../components/Toast'
import clsx from 'clsx'

type Section = 'plan' | 'review' | 'insights' | 'competitors' | 'diary' | 'schedule'

const sections: { id: Section; label: string; icon: typeof Calendar }[] = [
  { id: 'plan', label: 'План', icon: Calendar },
  { id: 'review', label: 'Ревью', icon: Star },
  { id: 'insights', label: 'Инсайты', icon: TrendingUp },
  { id: 'competitors', label: 'Тренды', icon: Search },
  { id: 'diary', label: 'Дневник', icon: BookOpen },
  { id: 'schedule', label: 'Расписание', icon: Clock },
]

export function Director() {
  const [activeSection, setActiveSection] = useState<Section>('plan')
  const [segment] = useState('main')
  const { haptic } = useTelegram()

  return (
    <div className="p-4 pb-24 space-y-4 overflow-y-auto">
      <h1 className="text-lg font-bold text-silk">AI Director</h1>

      {/* Section selector */}
      <div className="flex gap-1.5 overflow-x-auto -mx-1 px-1">
        {sections.map((s) => {
          const Icon = s.icon
          const isActive = activeSection === s.id
          return (
            <button
              key={s.id}
              onClick={() => { setActiveSection(s.id); haptic('selection') }}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium whitespace-nowrap transition-all',
                isActive
                  ? 'bg-flame/15 text-flame border border-flame/30'
                  : 'bg-ash/50 text-pearl border border-transparent'
              )}
            >
              <Icon size={14} />
              {s.label}
            </button>
          )
        })}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={activeSection}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
        >
          {activeSection === 'plan' && <PlanSection segment={segment} />}
          {activeSection === 'review' && <ReviewSection segment={segment} />}
          {activeSection === 'insights' && <InsightsSection segment={segment} />}
          {activeSection === 'competitors' && <CompetitorsSection segment={segment} />}
          {activeSection === 'diary' && <DiarySection />}
          {activeSection === 'schedule' && <ScheduleSection />}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

function PlanSection({ segment }: { segment: string }) {
  const [generating, setGenerating] = useState(false)
  const toast = useToast()
  const { haptic } = useTelegram()
  const queryClient = useQueryClient()

  const { data: plan, isLoading } = useQuery({
    queryKey: ['director-plan', segment],
    queryFn: () => directorApi.getPlan(segment),
    select: (res) => res.data,
  })

  const handleGenerate = async () => {
    setGenerating(true)
    haptic('medium')
    try {
      await directorApi.generatePlan(segment)
      queryClient.invalidateQueries({ queryKey: ['director-plan'] })
      toast.show('План сгенерирован!')
      haptic('success')
    } catch {
      toast.show('Ошибка генерации', 'error')
    } finally {
      setGenerating(false)
    }
  }

  if (isLoading) return <div className="skeleton h-40 rounded-2xl" />

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-pearl">
          {plan?.week_start ? `Неделя от ${plan.week_start}` : 'Нет плана'}
        </span>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="btn-ghost text-xs flex items-center gap-1"
        >
          <RefreshCw size={12} className={generating ? 'animate-spin' : ''} />
          {generating ? 'Генерирую...' : 'Обновить'}
        </button>
      </div>

      {plan && plan.slots.length > 0 ? (
        <div className="space-y-2">
          {plan.slots.map((slot, i) => (
            <div key={i} className="card flex items-center gap-3">
              <div className="text-xs text-mist w-10">{slot.day}</div>
              <div className="flex-1">
                <span className="text-sm text-silk font-medium">{slot.post_type}</span>
                {slot.topic && <p className="text-xs text-pearl mt-0.5">{slot.topic}</p>}
              </div>
              <span className={clsx(
                'text-[10px] font-medium px-2 py-0.5 rounded-full',
                slot.status === 'published' ? 'bg-jade/15 text-jade' :
                slot.status === 'generated' ? 'bg-amber/15 text-amber' :
                'bg-smoke/30 text-mist'
              )}>
                {slot.status}
              </span>
            </div>
          ))}
          <div className="text-xs text-pearl text-center">
            {plan.used}/{plan.total} слотов использовано
          </div>
        </div>
      ) : (
        <EmptyState
          title="Нет плана"
          description="Сгенерируйте план на неделю"
          action={
            <button onClick={handleGenerate} disabled={generating} className="btn-fire text-sm">
              Сгенерировать
            </button>
          }
        />
      )}
    </div>
  )
}

function ReviewSection({ segment }: { segment: string }) {
  const { data: review, isLoading } = useQuery({
    queryKey: ['director-review', segment],
    queryFn: () => directorApi.getReview(segment),
    select: (res) => res.data,
  })

  if (isLoading) return <div className="skeleton h-40 rounded-2xl" />
  if (!review) return <EmptyState title="Нет ревью" />

  return (
    <div className="space-y-3">
      <div className="text-xs text-pearl">
        Проанализировано {review.posts_reviewed} постов
      </div>

      {review.strengths.length > 0 && (
        <div className="card">
          <h4 className="text-xs font-semibold text-jade mb-2">Сильные стороны</h4>
          <ul className="space-y-1">
            {review.strengths.map((s, i) => (
              <li key={i} className="text-xs text-silk/80 flex gap-2">
                <span className="text-jade">+</span> {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {review.weaknesses.length > 0 && (
        <div className="card">
          <h4 className="text-xs font-semibold text-flame mb-2">Слабые стороны</h4>
          <ul className="space-y-1">
            {review.weaknesses.map((w, i) => (
              <li key={i} className="text-xs text-silk/80 flex gap-2">
                <span className="text-flame">-</span> {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {review.recommendations.length > 0 && (
        <div className="card">
          <h4 className="text-xs font-semibold text-blaze mb-2">Рекомендации</h4>
          <ul className="space-y-1">
            {review.recommendations.map((r, i) => (
              <li key={i} className="text-xs text-silk/80">{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function InsightsSection({ segment }: { segment: string }) {
  const { data: insights, isLoading } = useQuery({
    queryKey: ['director-insights', segment],
    queryFn: () => directorApi.getInsights(segment),
    select: (res) => res.data,
  })

  if (isLoading) return <div className="skeleton h-40 rounded-2xl" />
  if (!insights) return <EmptyState title="Нет данных" />

  return (
    <div className="space-y-3">
      {insights.recommended_type && (
        <div className="card border-gold/30">
          <span className="text-xs text-pearl">Рекомендуемый тип:</span>
          <span className="text-sm font-semibold text-gold ml-2">{insights.recommended_type}</span>
        </div>
      )}

      {insights.type_performance?.length > 0 && (
        <div className="card">
          <h4 className="text-xs font-semibold text-silk mb-2">Эффективность по типам</h4>
          <div className="space-y-2">
            {insights.type_performance.map((t: any) => (
              <div key={t.type} className="flex items-center justify-between text-xs">
                <span className="text-pearl">{t.type}</span>
                <div className="flex items-center gap-3">
                  <span className="text-mist">{t.count} posts</span>
                  {t.avg_engagement != null && (
                    <span className="text-gold font-medium">{t.avg_engagement.toFixed(1)}% ER</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {insights.best_hours?.length > 0 && (
        <div className="card">
          <h4 className="text-xs font-semibold text-silk mb-2">Лучшие часы</h4>
          <div className="flex gap-2 flex-wrap">
            {insights.best_hours.map((h: number) => (
              <span key={h} className="text-xs bg-ash px-2 py-1 rounded text-silk">{h}:00</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function CompetitorsSection({ segment }: { segment: string }) {
  const { data: competitors, isLoading } = useQuery({
    queryKey: ['director-competitors', segment],
    queryFn: () => directorApi.getCompetitors(segment),
    select: (res) => res.data,
  })

  if (isLoading) return <div className="skeleton h-40 rounded-2xl" />
  if (!competitors) return <EmptyState title="Нет данных" />

  return (
    <div className="space-y-3">
      {competitors.trend_context && (
        <div className="card">
          <h4 className="text-xs font-semibold text-silk mb-2">Контекст трендов</h4>
          <p className="text-xs text-pearl/80 leading-relaxed">{competitors.trend_context}</p>
        </div>
      )}

      {competitors.trending_topics?.length > 0 && (
        <div className="card">
          <h4 className="text-xs font-semibold text-silk mb-2">Тренды</h4>
          <div className="flex gap-1.5 flex-wrap">
            {competitors.trending_topics.map((t: string, i: number) => (
              <span key={i} className="text-xs bg-flame/10 text-flame px-2 py-1 rounded-lg">{t}</span>
            ))}
          </div>
        </div>
      )}

      {competitors.hooks?.length > 0 && (
        <div className="card">
          <h4 className="text-xs font-semibold text-silk mb-2">Рабочие хуки</h4>
          <ul className="space-y-1">
            {competitors.hooks.map((h: string, i: number) => (
              <li key={i} className="text-xs text-silk/80">"{h}"</li>
            ))}
          </ul>
        </div>
      )}

      {competitors.our_angle && (
        <div className="card border-gold/30">
          <h4 className="text-xs font-semibold text-gold mb-1">Наш угол</h4>
          <p className="text-xs text-silk/80">{competitors.our_angle}</p>
        </div>
      )}
    </div>
  )
}

function DiarySection() {
  const [text, setText] = useState('')
  const [saving, setSaving] = useState(false)
  const toast = useToast()
  const { haptic } = useTelegram()
  const queryClient = useQueryClient()

  const { data: entries, isLoading } = useQuery({
    queryKey: ['diary'],
    queryFn: () => diaryApi.list(15),
    select: (res) => res.data.entries,
  })

  const handleSave = async () => {
    if (!text.trim()) return
    setSaving(true)
    haptic('medium')
    try {
      await diaryApi.create(text.trim())
      setText('')
      queryClient.invalidateQueries({ queryKey: ['diary'] })
      toast.show('Запись сохранена')
      haptic('success')
    } catch {
      toast.show('Ошибка', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (isLoading) return <div className="skeleton h-40 rounded-2xl" />

  return (
    <div className="space-y-3">
      {/* New entry */}
      <div className="card space-y-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Мысли, идеи, события дня..."
          className="w-full h-24 bg-ash border border-smoke rounded-xl p-3 text-sm text-silk resize-none focus:outline-none focus:border-flame/50"
        />
        <button
          onClick={handleSave}
          disabled={saving || !text.trim()}
          className="btn-fire w-full text-sm py-2 flex items-center justify-center gap-1.5"
        >
          <Send size={14} />
          {saving ? 'Сохраняю...' : 'Записать'}
        </button>
      </div>

      {/* Entries list */}
      {entries && entries.length > 0 ? (
        <div className="space-y-2">
          {entries.map((entry) => (
            <div key={entry.id} className="card">
              <p className="text-xs text-silk/80 leading-relaxed whitespace-pre-line">{entry.entry_text}</p>
              <div className="text-[10px] text-mist mt-2">
                {new Date(entry.created_at).toLocaleString('ru-RU', {
                  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
                })}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="Дневник пуст" description="Записывай мысли — AI использует их для генерации контента" />
      )}
    </div>
  )
}

function ScheduleSection() {
  const toast = useToast()
  const { haptic } = useTelegram()
  const queryClient = useQueryClient()

  const { data: schedules, isLoading } = useQuery({
    queryKey: ['schedules'],
    queryFn: () => scheduleApi.list(),
    select: (res) => res.data.schedules,
  })

  const handleToggle = async (id: number, isActive: boolean) => {
    haptic('selection')
    try {
      await scheduleApi.update(id, !isActive)
      queryClient.invalidateQueries({ queryKey: ['schedules'] })
      toast.show(isActive ? 'Расписание выключено' : 'Расписание включено')
    } catch {
      toast.show('Ошибка', 'error')
    }
  }

  if (isLoading) return <div className="skeleton h-40 rounded-2xl" />

  if (!schedules || schedules.length === 0) {
    return <EmptyState title="Нет расписаний" description="Расписания настраиваются через бота" />
  }

  return (
    <div className="space-y-2">
      {schedules.map((s: any) => (
        <div key={s.id} className="card flex items-center gap-3">
          <div className="flex-1">
            <div className="text-sm text-silk font-medium">{s.post_type}</div>
            <div className="text-[10px] text-mist font-mono">{s.cron_expression}</div>
            {s.next_run && (
              <div className="text-[10px] text-pearl mt-0.5">
                Следующий: {new Date(s.next_run).toLocaleString('ru-RU', {
                  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
                })}
              </div>
            )}
          </div>
          <button
            onClick={() => handleToggle(s.id, s.is_active)}
            className={clsx(
              'w-12 h-6 rounded-full transition-all relative',
              s.is_active ? 'bg-jade' : 'bg-smoke'
            )}
          >
            <div className={clsx(
              'w-5 h-5 bg-white rounded-full absolute top-0.5 transition-all',
              s.is_active ? 'left-6' : 'left-0.5'
            )} />
          </button>
        </div>
      ))}
    </div>
  )
}
