import { useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useTelegram } from './hooks/useTelegram'
import { useAuth } from './hooks/useAuth'
import { Products } from './pages/Products'
import { Business } from './pages/Business'
import { Loading } from './components/Loading'
import { Navigation } from './components/Navigation'
import { AmbientGlow } from './components/AmbientGlow'
import { GrainOverlay } from './components/GrainOverlay'
import { SPRING_GENTLE } from './lib/animations'

type Page = 'products' | 'business'

// DEV_MODE: true = show interface without Telegram, false = require Telegram
const DEV_MODE = false

function App() {
  const { webApp, isReady } = useTelegram()
  const { authenticate } = useAuth()
  const [currentPage, setCurrentPage] = useState<Page>('products')
  const [forcedTab, setForcedTab] = useState<Page | null>(null)

  // Get initial tab from URL — if set, lock to that tab (no navigation)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const tab = params.get('tab')
    if (tab === 'business') {
      setCurrentPage('business')
      setForcedTab('business')
    } else if (tab === 'products') {
      setCurrentPage('products')
      setForcedTab('products')
    }
  }, [])

  // Authenticate on mount
  useEffect(() => {
    if (isReady && webApp?.initData) {
      authenticate(webApp.initData)
    }
  }, [isReady, webApp?.initData, authenticate])

  // Show loading only while Telegram WebApp initializes (auth happens in background)
  if (!DEV_MODE && !isReady) {
    return <Loading message="Загрузка..." />
  }

  // Show error only if opened outside Telegram (no WebApp object at all)
  if (!DEV_MODE && !webApp) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center">
          <div className="text-6xl mb-4">🤖</div>
          <h1 className="text-xl font-semibold mb-2 text-cream">Curator Mini App</h1>
          <p className="text-stone">
            Откройте это приложение через Telegram
          </p>
        </div>
      </div>
    )
  }

  const showNavigation = forcedTab === null

  return (
    <div className={`min-h-screen relative ${showNavigation ? 'pb-20' : 'pb-4'}`}>
      {/* Ambient warm glow background */}
      <AmbientGlow />

      {/* Film grain overlay */}
      <GrainOverlay />

      {/* Main content with page transitions */}
      <AnimatePresence mode="wait">
        <motion.main
          key={currentPage}
          className="relative z-10"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={SPRING_GENTLE}
        >
          {currentPage === 'products' ? <Products /> : <Business />}
        </motion.main>
      </AnimatePresence>

      {/* Bottom navigation — only when no specific tab forced */}
      {showNavigation && (
        <Navigation currentPage={currentPage} onNavigate={setCurrentPage} />
      )}
    </div>
  )
}

export default App
