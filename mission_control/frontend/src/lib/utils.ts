/**
 * Convert ISO date string to Russian relative time.
 * "5 мин назад", "2ч назад", "вчера", etc.
 */
export function timeAgo(dateStr: string | null): string {
  if (!dateStr) return '\u2014'

  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()

  if (diffMs < 0) return '\u0441\u043a\u043e\u0440\u043e'

  const seconds = Math.floor(diffMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 30) return '\u0442\u043e\u043b\u044c\u043a\u043e \u0447\u0442\u043e'
  if (seconds < 60) return `${seconds}\u0441 \u043d\u0430\u0437\u0430\u0434`
  if (minutes < 60) return `${minutes} \u043c\u0438\u043d \u043d\u0430\u0437\u0430\u0434`
  if (hours < 24) return `${hours}\u0447 \u043d\u0430\u0437\u0430\u0434`
  if (days === 1) return '\u0432\u0447\u0435\u0440\u0430'
  if (days < 7) return `${days}\u0434 \u043d\u0430\u0437\u0430\u0434`
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
}

/**
 * Format duration in ms to human readable.
 * "62.6с", "2мин 52с"
 */
export function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return '\u2014'

  const totalSeconds = ms / 1000

  if (totalSeconds < 60) {
    return `${totalSeconds.toFixed(1)}\u0441`
  }

  const minutes = Math.floor(totalSeconds / 60)
  const seconds = Math.floor(totalSeconds % 60)
  return `${minutes}\u043c\u0438\u043d ${seconds}\u0441`
}

/**
 * Convert Unix ms timestamp to "HH:MM DD.MM" format.
 */
export function formatTimestamp(ms: number): string {
  const date = new Date(ms)
  const hours = date.getHours().toString().padStart(2, '0')
  const mins = date.getMinutes().toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  return `${hours}:${mins} ${day}.${month}`
}

/**
 * Parse status string that may contain emoji prefix.
 * e.g. "working on task" -> { emoji: "", text: "working on task" }
 */
export function parseStatus(raw: string): { emoji: string; text: string } {
  if (!raw) return { emoji: '', text: '' }

  // Check if first character is an emoji (non-ASCII, non-Latin)
  const emojiRegex = /^(\p{Emoji_Presentation}|\p{Extended_Pictographic})\s*/u
  const match = raw.match(emojiRegex)

  if (match) {
    return {
      emoji: match[1],
      text: raw.slice(match[0].length),
    }
  }

  return { emoji: '', text: raw }
}

/**
 * Truncate string to max length, adding ellipsis.
 */
export function truncate(str: string, max: number): string {
  if (!str) return ''
  if (str.length <= max) return str
  return str.slice(0, max - 1) + '\u2026'
}

/**
 * Resolve status string to a normalized key for styling.
 */
export function normalizeStatus(
  status: string | null | undefined
): 'active' | 'completed' | 'idle' | 'error' | 'unknown' {
  if (!status) return 'unknown'
  const lower = status.toLowerCase()
  if (
    lower.includes('active') ||
    lower.includes('running') ||
    lower.includes('work')
  )
    return 'active'
  if (lower.includes('completed') || lower.includes('done') || lower === 'ok')
    return 'completed'
  if (lower.includes('idle') || lower.includes('sleep') || lower.includes('wait'))
    return 'idle'
  if (lower.includes('error') || lower.includes('fail'))
    return 'error'
  return 'unknown'
}
