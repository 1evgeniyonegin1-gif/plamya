interface LoadingProps {
  message?: string
}

export function Loading({ message }: LoadingProps) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4">
      {/* Cosmic loader — орбиты и центральная звезда */}
      <div className="relative w-16 h-16 mb-8">
        {/* Внешняя орбита */}
        <div className="absolute inset-0 border border-glow/20 rounded-full animate-spin" style={{ animationDuration: '8s' }} />

        {/* Средняя орбита */}
        <div className="absolute inset-2 border border-glow/30 rounded-full animate-spin" style={{ animationDuration: '5s', animationDirection: 'reverse' }} />

        {/* Внутренняя орбита */}
        <div className="absolute inset-4 border border-glow/40 rounded-full animate-spin" style={{ animationDuration: '3s' }} />

        {/* Центральная звезда */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-2 h-2 bg-glow-soft rounded-full animate-breathe" />
        </div>

        {/* Орбитальная точка */}
        <div
          className="absolute w-1.5 h-1.5 bg-glow rounded-full"
          style={{
            top: '0',
            left: '50%',
            transform: 'translateX(-50%)',
            animation: 'orbit 4s linear infinite',
          }}
        />
      </div>
      {message && (
        <p className="text-dust text-sm tracking-widest uppercase animate-breathe">{message}</p>
      )}
    </div>
  )
}
