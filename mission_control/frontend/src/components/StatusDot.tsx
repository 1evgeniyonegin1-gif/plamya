import clsx from 'clsx'

type StatusType = 'active' | 'completed' | 'idle' | 'error' | 'unknown'

interface StatusDotProps {
  status: StatusType
  size?: 'sm' | 'md'
}

const STATUS_CLASSES: Record<StatusType, string> = {
  active: 'status-green',
  completed: 'status-green',
  idle: 'status-yellow',
  error: 'status-red',
  unknown: 'status-gray',
}

export default function StatusDot({ status, size = 'sm' }: StatusDotProps) {
  return (
    <span
      className={clsx(
        'inline-block rounded-full flex-shrink-0',
        STATUS_CLASSES[status],
        size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5',
        status === 'active' && 'animate-pulse-dot'
      )}
    />
  )
}
