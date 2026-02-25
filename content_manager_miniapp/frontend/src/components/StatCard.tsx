import { type LucideIcon } from 'lucide-react'

interface Props {
  label: string
  value: string | number
  icon: LucideIcon
  trend?: string
  color?: string
}

export function StatCard({ label, value, icon: Icon, trend, color = 'text-flame' }: Props) {
  return (
    <div className="card space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-pearl">{label}</span>
        <Icon size={14} className={color} />
      </div>
      <div className="text-2xl font-bold text-silk">{value}</div>
      {trend && <span className="text-[10px] text-jade">{trend}</span>}
    </div>
  )
}
