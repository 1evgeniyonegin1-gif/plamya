export function ShimmerCategoryGrid() {
  return (
    <div className="grid grid-cols-2 gap-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="shimmer-skeleton h-28 rounded-2xl" />
      ))}
    </div>
  )
}

export function ShimmerProductGrid() {
  return (
    <div className="grid grid-cols-2 gap-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="space-y-3">
          <div className="shimmer-skeleton aspect-[3/4] rounded-xl" />
          <div className="shimmer-skeleton h-4 w-3/4 rounded" />
          <div className="shimmer-skeleton h-4 w-1/2 rounded" />
        </div>
      ))}
    </div>
  )
}
