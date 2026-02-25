import { useState, useEffect, useCallback } from 'react'

interface TelegramUser {
  id: number
  first_name: string
  last_name?: string
  username?: string
  language_code?: string
  is_premium?: boolean
}

export function useTelegram() {
  const [isReady, setIsReady] = useState(false)
  const webApp = window.Telegram?.WebApp
  const user = webApp?.initDataUnsafe?.user as TelegramUser | undefined

  useEffect(() => {
    if (webApp) {
      webApp.ready()
      setIsReady(true)
      webApp.expand()
    } else {
      setIsReady(true)
    }
  }, [webApp])

  const haptic = useCallback(
    (
      type:
        | 'light'
        | 'medium'
        | 'heavy'
        | 'success'
        | 'error'
        | 'warning'
        | 'selection'
    ) => {
      if (!webApp?.HapticFeedback) return
      if (type === 'selection') {
        ;(webApp.HapticFeedback as any).selectionChanged()
      } else if (type === 'success' || type === 'error' || type === 'warning') {
        webApp.HapticFeedback.notificationOccurred(type)
      } else {
        webApp.HapticFeedback.impactOccurred(type)
      }
    },
    [webApp]
  )

  const showAlert = useCallback(
    (message: string) => {
      if (webApp?.showAlert) webApp.showAlert(message)
      else alert(message)
    },
    [webApp]
  )

  const close = useCallback(() => {
    webApp?.close()
  }, [webApp])

  return {
    webApp,
    user,
    isReady,
    initData: webApp?.initData ?? '',
    haptic,
    showAlert,
    close,
  }
}
