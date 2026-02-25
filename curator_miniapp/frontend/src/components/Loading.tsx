interface LoadingProps {
  message?: string
}

export function Loading({ message = 'Загрузка...' }: LoadingProps) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4">
      <div className="relative">
        {/* Outer ring */}
        <div className="w-16 h-16 rounded-full border-2 border-amber/20 animate-spin" />
        {/* Inner dot */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 bg-amber rounded-full animate-breathe" />
      </div>
      <p className="mt-4 text-stone text-sm">{message}</p>
    </div>
  )
}
