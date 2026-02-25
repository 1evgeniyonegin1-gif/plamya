import { Flame } from 'lucide-react'

interface Props {
  title: string
  description?: string
  action?: React.ReactNode
}

export function EmptyState({ title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="w-16 h-16 rounded-2xl bg-ash flex items-center justify-center mb-4">
        <Flame className="text-flame/40" size={28} />
      </div>
      <h3 className="text-silk font-semibold text-lg mb-1">{title}</h3>
      {description && <p className="text-pearl text-sm max-w-[280px]">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
