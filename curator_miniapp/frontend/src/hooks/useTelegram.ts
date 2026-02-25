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
      // For development without Telegram
      setIsReady(true)
    }
  }, [webApp])

  // Haptic feedback
  const haptic = useCallback((type: 'light' | 'medium' | 'heavy' | 'success' | 'error' | 'warning' | 'selection') => {
    if (!webApp?.HapticFeedback) return

    if (type === 'selection') {
      (webApp.HapticFeedback as any).selectionChanged()
    } else if (type === 'success' || type === 'error' || type === 'warning') {
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

  // Open external link
  const openLink = useCallback((url: string) => {
    if (webApp?.openLink) {
      webApp.openLink(url)
    } else {
      window.open(url, '_blank')
    }
  }, [webApp])

  // Open Telegram link
  const openTelegramLink = useCallback((url: string) => {
    if (webApp?.openTelegramLink) {
      webApp.openTelegramLink(url)
    } else {
      window.open(url, '_blank')
    }
  }, [webApp])

  // Close Mini App
  const close = useCallback(() => {
    webApp?.close()
  }, [webApp])

  // Back Button
  const showBackButton = useCallback((callback: () => void) => {
    if (!webApp?.BackButton) return
    webApp.BackButton.show()
    webApp.BackButton.offClick(callback) // Remove previous handler first
    webApp.BackButton.onClick(callback)
  }, [webApp])

  const hideBackButton = useCallback(() => {
    if (!webApp?.BackButton) return
    webApp.BackButton.hide()
  }, [webApp])

  return {
    webApp,
    user,
    isReady,
    colorScheme: webApp?.colorScheme ?? 'dark',
    haptic,
    showAlert,
    showConfirm,
    openLink,
    openTelegramLink,
    close,
    showBackButton,
    hideBackButton,
  }
}
