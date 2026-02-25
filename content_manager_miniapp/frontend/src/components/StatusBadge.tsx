import clsx from 'clsx'

const statusConfig: Record<string, { label: string; class: string }> = {
  pending: { label: 'На модерации', class: 'badge-pending' },
  published: { label: 'Опубликован', class: 'badge-published' },
  rejected: { label: 'Отклонён', class: 'badge-rejected' },
  scheduled: { label: 'Запланирован', class: 'badge-scheduled' },
  draft: { label: 'Черновик', class: 'badge-draft' },
  approved: { label: 'Одобрен', class: 'badge-published' },
}

interface Props {
  status: string
  className?: string
}

export function StatusBadge({ status, className }: Props) {
  const config = statusConfig[status] || { label: status, class: 'badge-draft' }
  return <span className={clsx(config.class, className)}>{config.label}</span>
}
