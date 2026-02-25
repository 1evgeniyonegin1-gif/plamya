export function GrainOverlay() {
  return (
    <svg
      className="fixed inset-0 w-full h-full pointer-events-none z-[100]"
      style={{ opacity: 0.03, mixBlendMode: 'overlay' }}
    >
      <filter id="grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="4" stitchTiles="stitch" />
      </filter>
      <rect width="100%" height="100%" filter="url(#grain)" />
    </svg>
  )
}
