interface ProgressBarProps {
  value: number
  max: number
  label?: string
  sublabel?: string
  color?: 'glow' | 'green' | 'amber' | 'purple' | 'blue'
  showPercent?: boolean
}

const colorMap = {
  glow: 'from-glow-muted to-glow-soft',
  green: 'from-emerald-600 to-emerald-400',
  amber: 'from-amber-600 to-amber-400',
  purple: 'from-purple-600 to-purple-400',
  blue: 'from-blue-600 to-blue-400',
}

const bgMap = {
  glow: 'rgba(99, 102, 241, 0.15)',
  green: 'rgba(16, 185, 129, 0.15)',
  amber: 'rgba(245, 158, 11, 0.15)',
  purple: 'rgba(124, 58, 237, 0.15)',
  blue: 'rgba(59, 130, 246, 0.15)',
}

export function ProgressBar({ value, max, label, sublabel, color = 'glow', showPercent = true }: ProgressBarProps) {
  const percent = max > 0 ? Math.min(Math.round((value / max) * 100), 100) : 0

  return (
    <div className="space-y-1.5">
      {(label || showPercent) && (
        <div className="flex items-center justify-between text-sm">
          {label && <span className="text-star-dim">{label}</span>}
          <div className="flex items-center gap-2">
            {sublabel && <span className="text-xs text-dust">{sublabel}</span>}
            {showPercent && <span className="text-star font-medium">{percent}%</span>}
          </div>
        </div>
      )}
      <div
        className="h-2 rounded-full overflow-hidden"
        style={{ background: bgMap[color] }}
      >
        <div
          className={`h-full rounded-full bg-gradient-to-r ${colorMap[color]} transition-all duration-700 ease-out`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  )
}
