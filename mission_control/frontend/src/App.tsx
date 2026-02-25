import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { useTelegram } from './hooks/useTelegram'
import { useAuth } from './hooks/useAuth'
import { useSSE } from './hooks/useSSE'
import { errorsApi, projectsApi, leadsApi } from './api/client'
import Navigation from './components/Navigation'
import type { TabId } from './components/Navigation'
import RadarSweep from './components/RadarSweep'
import GridOverlay from './components/GridOverlay'
import Overview from './pages/Overview'
import AgentDetail from './pages/AgentDetail'
import Inbox from './pages/Inbox'
import Council from './pages/Council'
import Tasks from './pages/Tasks'
import ErrorLog from './pages/ErrorLog'
import Projects from './pages/Projects'
import MyTasks from './pages/MyTasks'
import Leads from './pages/Leads'

export default function App() {
  const { isReady, initData } = useTelegram()
  const { authenticate, token } = useAuth()

  // SSE for real-time updates
  useSSE()

  // Authenticate with Telegram initData (non-blocking)
  useEffect(() => {
    if (initData && !token) {
      authenticate(initData).catch(() => {})
    }
  }, [initData, token, authenticate])

  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)

  // Error count for navigation badge
  const { data: errorsData } = useQuery({
    queryKey: ['errors-badge'],
    queryFn: () => errorsApi.list().then((r) => r.data),
    refetchInterval: 30_000,
    enabled: isReady,
  })
  const errorCount = errorsData?.total_errors ?? 0

  // My tasks pending count for navigation badge
  const { data: myTasksData } = useQuery({
    queryKey: ['my-tasks-badge'],
    queryFn: () => projectsApi.myTasks().then((r) => r.data),
    refetchInterval: 60_000,
    enabled: isReady,
  })
  const myTasksCount = myTasksData?.pending ?? 0

  // Leads count for navigation badge
  const { data: leadsData } = useQuery({
    queryKey: ['leads-badge'],
    queryFn: () => leadsApi.stats().then((r) => r.data),
    refetchInterval: 60_000,
    enabled: isReady,
  })
  const leadsCount = leadsData?.total ?? 0

  // Loading state
  if (!isReady) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-abyss">
        <RadarSweep />
        <GridOverlay />
        <div className="relative z-10 flex flex-col items-center">
          <div className="w-12 h-12 rounded-full border-2 border-signal/30 border-t-signal animate-spin mb-4" />
          <p className="text-oxide text-sm font-mono">Подключение...</p>
        </div>
      </div>
    )
  }

  const handleTabChange = (tab: TabId) => {
    setSelectedAgent(null)
    setActiveTab(tab)
  }

  return (
    <div className="min-h-screen bg-abyss relative">
      {/* Background effects */}
      <RadarSweep />
      <GridOverlay />

      {/* Main content */}
      <main className="relative z-10 pb-16">
        <AnimatePresence mode="wait">
          {selectedAgent ? (
            <motion.div
              key={`detail-${selectedAgent}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <AgentDetail
                agentId={selectedAgent}
                onBack={() => setSelectedAgent(null)}
              />
            </motion.div>
          ) : (
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15 }}
            >
              {activeTab === 'overview' && (
                <Overview onSelectAgent={setSelectedAgent} />
              )}
              {activeTab === 'council' && <Council />}
              {activeTab === 'tasks' && <Tasks />}
              {activeTab === 'inbox' && <Inbox />}
              {activeTab === 'errors' && <ErrorLog />}
              {activeTab === 'projects' && <Projects />}
              {activeTab === 'mytasks' && <MyTasks />}
              {activeTab === 'leads' && <Leads />}
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Bottom navigation (hide when agent detail is open) */}
      {!selectedAgent && (
        <Navigation
          activeTab={activeTab}
          onTabChange={handleTabChange}
          errorCount={errorCount}
          myTasksCount={myTasksCount}
          leadsCount={leadsCount}
        />
      )}
    </div>
  )
}
