import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

/**
 * Subscribe to Server-Sent Events from the backend.
 * When a file changes, invalidate the relevant react-query cache
 * so the UI auto-updates without polling.
 */
export function useSSE() {
  const queryClient = useQueryClient()
  const retryDelay = useRef(1000)

  useEffect(() => {
    let es: EventSource | null = null
    let mounted = true

    function connect() {
      if (!mounted) return
      es = new EventSource('/api/v1/events/stream')

      es.onopen = () => {
        retryDelay.current = 1000 // reset on success
      }

      es.addEventListener('agent_status', () => {
        queryClient.invalidateQueries({ queryKey: ['agents'] })
        queryClient.invalidateQueries({ queryKey: ['agent-detail'] })
        queryClient.invalidateQueries({ queryKey: ['errors-badge'] })
      })

      es.addEventListener('inbox', () => {
        queryClient.invalidateQueries({ queryKey: ['inbox'] })
        queryClient.invalidateQueries({ queryKey: ['agents'] })
      })

      es.addEventListener('council', () => {
        queryClient.invalidateQueries({ queryKey: ['council'] })
      })

      es.addEventListener('tasks', () => {
        queryClient.invalidateQueries({ queryKey: ['tasks'] })
      })

      es.addEventListener('cron', () => {
        queryClient.invalidateQueries({ queryKey: ['cron'] })
        queryClient.invalidateQueries({ queryKey: ['agents'] })
      })

      es.onerror = () => {
        es?.close()
        // Exponential backoff (max 30s)
        const delay = Math.min(retryDelay.current, 30_000)
        retryDelay.current = delay * 2
        setTimeout(connect, delay)
      }
    }

    connect()

    return () => {
      mounted = false
      es?.close()
    }
  }, [queryClient])
}
