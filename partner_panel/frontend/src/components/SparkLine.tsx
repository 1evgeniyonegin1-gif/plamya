interface SparkLineProps {
  data: number[]
  color?: string
  width?: number
  height?: number
}

export function SparkLine({ data, color = '#818cf8', width = 80, height = 24 }: SparkLineProps) {
  if (!data || data.length < 2) return null

  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1

  const padding = 2
  const innerW = width - padding * 2
  const innerH = height - padding * 2

  const points = data.map((val, i) => {
    const x = padding + (i / (data.length - 1)) * innerW
    const y = padding + innerH - ((val - min) / range) * innerH
    return `${x},${y}`
  }).join(' ')

  // Fill area under the line
  const firstX = padding
  const lastX = padding + innerW
  const bottomY = height - padding
  const fillPoints = `${firstX},${bottomY} ${points} ${lastX},${bottomY}`

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="inline-block">
      <defs>
        <linearGradient id={`spark-fill-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={fillPoints}
        fill={`url(#spark-fill-${color.replace('#', '')})`}
      />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
