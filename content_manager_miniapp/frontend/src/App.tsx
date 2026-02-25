import { useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { Navigation, type TabId } from './components/Navigation'
import { Toast } from './components/Toast'
import { Posts } from './pages/Posts'
import { Analytics } from './pages/Analytics'
import { Traffic } from './pages/Traffic'
import { Director } from './pages/Director'
import { useTelegram } from './hooks/useTelegram'
import { useAuth } from './hooks/useAuth'
import { postsApi } from './api/client'
import { Flame } from 'lucide-react'

// Set true for local development without Telegram
const DEV_MODE = !window.Telegram?.WebApp?.initData

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>('posts')
  const { isReady, initData } = useTelegram()
  const { token, isLoading, error, authenticate } = useAuth()

  // Auto-authenticate on mount
  useEffect(() => {
    if (isReady && !token && !isLoading) {
      if (DEV_MODE) {
        // Skip auth in dev mode — set fake token
        useAuth.setState({
          token: 'dev-token',
          user: { telegram_id: 756877849, first_name: 'Dev', is_admin: true },
        })
      } else if (initData) {
        authenticate(initData)
      }
    }
  }, [isReady, token, isLoading, initData, authenticate])

  // Pending count for badge
  const { data: pendingData } = useQuery({
    queryKey: ['posts', 'pending'],
    queryFn: () => postsApi.list({ status: 'pending', limit: 1 }),
    select: (res) => res.data.total,
    enabled: !!token,
    refetchInterval: 60_000,
  })

  // Loading screen
  if (!isReady || isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        >
          <Flame className="text-flame" size={40} />
        </motion.div>
        <span className="text-pearl text-sm">Loading...</span>
      </div>
    )
  }

  // Error screen
  if (error && !DEV_MODE) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4 px-8 text-center">
        <Flame className="text-flame/40" size={40} />
        <p className="text-pearl text-sm">{error}</p>
        <button onClick={() => window.location.reload()} className="btn-ghost text-sm">
          Попробовать снова
        </button>
      </div>
    )
  }

  const pages: Record<TabId, React.ReactNode> = {
    posts: <Posts />,
    analytics: <Analytics />,
    traffic: <Traffic />,
    director: <Director />,
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Toast />

      <main className="flex-1">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            {pages[activeTab]}
          </motion.div>
        </AnimatePresence>
      </main>

      <Navigation
        activeTab={activeTab}
        onTabChange={setActiveTab}
        pendingCount={pendingData}
      />
    </div>
  )
}
