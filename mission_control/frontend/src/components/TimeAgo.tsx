import { useState, useEffect } from 'react'
import { timeAgo } from '../lib/utils'

interface TimeAgoProps {
  date: string | null
  className?: string
}

export default function TimeAgo({ date, className }: TimeAgoProps) {
  const [display, setDisplay] = useState(() => timeAgo(date))

  useEffect(() => {
    setDisplay(timeAgo(date))

    if (!date) return

    const interval = setInterval(() => {
      setDisplay(timeAgo(date))
    }, 30_000)

    return () => clearInterval(interval)
  }, [date])

  return (
    <span className={className ?? 'text-oxide text-xs font-mono'}>
      {display}
    </span>
  )
}
