import { useState, useEffect } from 'react'
import { useTelegram } from './hooks/useTelegram'
import { useAuth } from './hooks/useAuth'
import { Dashboard } from './pages/Dashboard'
import { Connect } from './pages/Connect'
import { Channels } from './pages/Channels'
import { Stats } from './pages/Stats'
import { Loading } from './components/Loading'
import { Navigation } from './components/Navigation'
import { Stars } from './components/Stars'

type Page = 'dashboard' | 'connect' | 'channels' | 'stats'

// DEV_MODE: true = показывать интерфейс без Telegram, false = требовать Telegram
const DEV_MODE = false

function App() {
  const { webApp, user, isReady } = useTelegram()
  const { isLoading, authenticate } = useAuth()
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')

  // Authenticate on mount
  useEffect(() => {
    if (isReady && webApp?.initData) {
      authenticate(webApp.initData)
    }
  }, [isReady, webApp?.initData, authenticate])

  // Show loading while initializing (skip in dev mode)
  if (!DEV_MODE && (!isReady || isLoading)) {
    return <Loading message="Загрузка..." />
  }

  // Show error if not in Telegram (skip in dev mode)
  if (!DEV_MODE && !user) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center">
          <div className="text-6xl mb-4">🤖</div>
          <h1 className="text-xl font-semibold mb-2">Partner Panel</h1>
          <p className="text-tg-hint">
            Откройте это приложение через Telegram
          </p>
        </div>
      </div>
    )
  }

  // Render current page
  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard onNavigate={setCurrentPage} />
      case 'connect':
        return <Connect onBack={() => setCurrentPage('dashboard')} />
      case 'channels':
        return <Channels onBack={() => setCurrentPage('dashboard')} />
      case 'stats':
        return <Stats onBack={() => setCurrentPage('dashboard')} />
      default:
        return <Dashboard onNavigate={setCurrentPage} />
    }
  }

  return (
    <div className="min-h-screen pb-20 relative">
      {/* Звёзды на фоне */}
      <Stars />

      {/* Main content */}
      <main className="animate-fade-in relative z-10">
        {renderPage()}
      </main>

      {/* Bottom navigation */}
      <Navigation currentPage={currentPage} onNavigate={setCurrentPage} />
    </div>
  )
}

export default App
