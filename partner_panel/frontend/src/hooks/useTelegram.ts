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
      // Mark as ready
      webApp.ready()
      setIsReady(true)

      // Expand to full height
      webApp.expand()
    } else {
      // If not in Telegram, still mark as ready for development
      setIsReady(true)
    }
  }, [webApp])

  // Haptic feedback helpers
  const haptic = useCallback((type: 'light' | 'medium' | 'heavy' | 'success' | 'error' | 'warning') => {
    if (!webApp?.HapticFeedback) return

    if (type === 'success' || type === 'error' || type === 'warning') {
      webApp.HapticFeedback.notificationOccurred(type)
    } else {
      webApp.HapticFeedback.impactOccurred(type)
    }
  }, [webApp])

  // Show alert
  const showAlert = useCallback((message: string) => {
    if (webApp?.showAlert) {
      webApp.showAlert(message)
    } else {
      alert(message)
    }
  }, [webApp])

  // Show confirm
  const showConfirm = useCallback((message: string): Promise<boolean> => {
    return new Promise((resolve) => {
      if (webApp?.showConfirm) {
        webApp.showConfirm(message, (confirmed) => {
          resolve(confirmed)
        })
      } else {
        resolve(confirm(message))
      }
    })
  }, [webApp])

  // Main button
  const setMainButton = useCallback((text: string, onClick: () => void) => {
    if (!webApp?.MainButton) return

    webApp.MainButton.setText(text)
    webApp.MainButton.onClick(onClick)
    webApp.MainButton.show()

    return () => {
      webApp.MainButton.offClick(onClick)
      webApp.MainButton.hide()
    }
  }, [webApp])

  // Back button
  const setBackButton = useCallback((onClick: () => void) => {
    if (!webApp?.BackButton) return

    webApp.BackButton.onClick(onClick)
    webApp.BackButton.show()

    return () => {
      webApp.BackButton.offClick(onClick)
      webApp.BackButton.hide()
    }
  }, [webApp])

  // Close Mini App
  const close = useCallback(() => {
    webApp?.close()
  }, [webApp])

  return {
    webApp,
    user,
    isReady,
    colorScheme: webApp?.colorScheme ?? 'light',
    haptic,
    showAlert,
    showConfirm,
    setMainButton,
    setBackButton,
    close,
  }
}
