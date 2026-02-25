import clsx from 'clsx'

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: string | number
  change?: number
  sublabel?: string
  className?: string
}

export function StatCard({ icon, label, value, change, sublabel, className }: StatCardProps) {
  return (
    <div className={clsx('card text-center py-6 group hover:scale-[1.02] transition-transform duration-500', className)}>
      {/* Иконка с мягким свечением */}
      <div className="w-10 h-10 mx-auto mb-3 rounded-xl bg-gradient-to-br from-glow/10 to-nebula-purple/10 flex items-center justify-center relative">
        <span className="text-glow-soft group-hover:animate-twinkle">{icon}</span>
        {/* Свечение при hover */}
        <div className="absolute inset-0 rounded-xl bg-glow/0 group-hover:bg-glow/5 transition-colors duration-500" />
      </div>

      {/* Значение */}
      <div className="text-2xl font-light text-star mb-1">
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>

      {/* Подпись */}
      <div className="text-xs text-dust uppercase tracking-wider">{label}</div>

      {/* Sublabel */}
      {sublabel && (
        <div className="text-xs text-dust/70 mt-1">{sublabel}</div>
      )}

      {/* Изменение */}
      {change !== undefined && (
        <div
          className={clsx(
            'text-xs mt-2 font-medium',
            change >= 0 ? 'text-success' : 'text-error'
          )}
        >
          {change >= 0 ? '+' : ''}{change}%
        </div>
      )}
    </div>
  )
}
