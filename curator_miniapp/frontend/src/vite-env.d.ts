/// <reference types="vite/client" />

interface TelegramWebApp {
  initData: string
  initDataUnsafe: {
    user?: {
      id: number
      first_name: string
      last_name?: string
      username?: string
      language_code?: string
      is_premium?: boolean
    }
  }
  colorScheme: 'light' | 'dark'
  ready: () => void
  expand: () => void
  close: () => void
  showAlert: (message: string) => void
  showConfirm: (message: string, callback: (confirmed: boolean) => void) => void
  HapticFeedback?: {
    impactOccurred: (style: 'light' | 'medium' | 'heavy') => void
    notificationOccurred: (type: 'error' | 'success' | 'warning') => void
  }
  MainButton?: {
    text: string
    setText: (text: string) => void
    show: () => void
    hide: () => void
    onClick: (callback: () => void) => void
    offClick: (callback: () => void) => void
  }
  BackButton?: {
    show: () => void
    hide: () => void
    onClick: (callback: () => void) => void
    offClick: (callback: () => void) => void
  }
  openLink: (url: string) => void
  openTelegramLink: (url: string) => void
}

interface Window {
  Telegram?: {
    WebApp: TelegramWebApp
  }
}
