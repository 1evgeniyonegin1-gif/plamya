export function AmbientGlow() {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {/* Amber blob — left side */}
      <div
        className="absolute w-[500px] h-[500px] rounded-full animate-drift-1"
        style={{
          background: 'radial-gradient(circle, rgba(245,158,11,0.04) 0%, transparent 70%)',
          filter: 'blur(100px)',
          top: '10%',
          left: '-10%',
        }}
      />
      {/* Deep gold blob — right side */}
      <div
        className="absolute w-[400px] h-[400px] rounded-full animate-drift-2"
        style={{
          background: 'radial-gradient(circle, rgba(217,119,6,0.03) 0%, transparent 70%)',
          filter: 'blur(100px)',
          top: '50%',
          right: '-10%',
        }}
      />
      {/* Subtle warm rose — center */}
      <div
        className="absolute w-[350px] h-[350px] rounded-full animate-drift-3"
        style={{
          background: 'radial-gradient(circle, rgba(248,113,113,0.02) 0%, transparent 70%)',
          filter: 'blur(100px)',
          top: '30%',
          left: '30%',
        }}
      />
    </div>
  )
}
