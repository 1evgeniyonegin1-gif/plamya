import clsx from 'clsx'

interface Props {
  className?: string
}

export function Skeleton({ className }: Props) {
  return <div className={clsx('skeleton', className)} />
}

export function PostCardSkeleton() {
  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <div className="flex gap-4 pt-1">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-16" />
      </div>
    </div>
  )
}

export function StatCardSkeleton() {
  return (
    <div className="card space-y-2">
      <Skeleton className="h-4 w-20" />
      <Skeleton className="h-8 w-16" />
    </div>
  )
}
