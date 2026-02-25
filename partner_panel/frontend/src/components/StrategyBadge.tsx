interface StrategyBadgeProps {
  strategy: string
  score?: number
  size?: 'sm' | 'md'
}

const strategyConfig: Record<string, { label: string; bg: string; text: string }> = {
  smart: { label: 'Smart', bg: 'rgba(99, 102, 241, 0.15)', text: '#818cf8' },
  supportive: { label: 'Support', bg: 'rgba(16, 185, 129, 0.15)', text: '#34d399' },
  funny: { label: 'Funny', bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24' },
  expert: { label: 'Expert', bg: 'rgba(124, 58, 237, 0.15)', text: '#a78bfa' },
}

export function StrategyBadge({ strategy, score, size = 'sm' }: StrategyBadgeProps) {
  const config = strategyConfig[strategy] || { label: strategy, bg: 'rgba(100, 116, 139, 0.15)', text: '#94a3b8' }

  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1'

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${sizeClasses}`}
      style={{ background: config.bg, color: config.text }}
    >
      {config.label}
      {score !== undefined && (
        <span className="opacity-70">{Math.round(score * 100)}%</span>
      )}
    </span>
  )
}

interface SegmentBadgeProps {
  segment: string
  size?: 'sm' | 'md'
}

const segmentConfig: Record<string, { label: string; bg: string; text: string }> = {
  zozh: { label: 'ZOH', bg: 'rgba(16, 185, 129, 0.15)', text: '#34d399' },
  mama: { label: 'Mama', bg: 'rgba(236, 72, 153, 0.15)', text: '#f472b6' },
  business: { label: 'Biz', bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24' },
  student: { label: 'Stud', bg: 'rgba(59, 130, 246, 0.15)', text: '#60a5fa' },
  universal: { label: 'All', bg: 'rgba(100, 116, 139, 0.15)', text: '#94a3b8' },
}

export function SegmentBadge({ segment, size = 'sm' }: SegmentBadgeProps) {
  const config = segmentConfig[segment] || segmentConfig.universal

  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1'

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${sizeClasses}`}
      style={{ background: config.bg, color: config.text }}
    >
      {config.label}
    </span>
  )
}
