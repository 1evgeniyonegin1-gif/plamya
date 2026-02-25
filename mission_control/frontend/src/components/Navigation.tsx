import { motion } from 'framer-motion'
import {
  LayoutGrid,
  MessageSquare,
  BarChart2,
  Zap,
  Target,
} from 'lucide-react'
import clsx from 'clsx'

export type TabId = 'overview' | 'projects' | 'tasks' | 'inbox' | 'errors' | 'council' | 'mytasks' | 'leads'

interface Tab {
  id: TabId
  label: string
  icon: typeof LayoutGrid
}

const TABS: Tab[] = [
  { id: 'overview', label: 'Агенты', icon: LayoutGrid },
  { id: 'leads', label: 'Лиды', icon: Target },
  { id: 'projects', label: 'Проекты', icon: BarChart2 },
  { id: 'mytasks', label: 'Мне', icon: Zap },
  { id: 'inbox', label: 'Почта', icon: MessageSquare },
]

interface NavigationProps {
  activeTab: TabId
  onTabChange: (tab: TabId) => void
  errorCount: number
  myTasksCount?: number
  leadsCount?: number
}

export default function Navigation({
  activeTab,
  onTabChange,
  errorCount,
  myTasksCount = 0,
  leadsCount = 0,
}: NavigationProps) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 glass nav-safe-bottom">
      <div className="flex items-center justify-around h-14 max-w-lg mx-auto px-1">
        {TABS.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className="relative flex flex-col items-center justify-center w-full h-full gap-0.5"
            >
              {isActive && (
                <motion.div
                  layoutId="nav-indicator"
                  className="absolute inset-x-1 -top-0.5 h-0.5 bg-signal rounded-full"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}
              <div className="relative">
                <Icon
                  size={18}
                  className={clsx(
                    'transition-colors duration-200',
                    isActive ? 'text-signal' : 'text-oxide'
                  )}
                />
                {tab.id === 'leads' && leadsCount > 0 && (
                  <span className="absolute -top-1.5 -right-2.5 min-w-[16px] h-4 flex items-center justify-center px-1 rounded-full bg-signal text-abyss text-[10px] font-bold font-mono">
                    {leadsCount > 99 ? '99+' : leadsCount}
                  </span>
                )}
                {tab.id === 'mytasks' && myTasksCount > 0 && (
                  <span className="absolute -top-1.5 -right-2.5 min-w-[16px] h-4 flex items-center justify-center px-1 rounded-full bg-red-500 text-white text-[10px] font-bold font-mono">
                    {myTasksCount > 9 ? '9+' : myTasksCount}
                  </span>
                )}
                {tab.id === 'errors' && errorCount > 0 && (
                  <span className="absolute -top-1.5 -right-2.5 min-w-[16px] h-4 flex items-center justify-center px-1 rounded-full bg-alert text-abyss text-[10px] font-bold font-mono">
                    {errorCount > 99 ? '99+' : errorCount}
                  </span>
                )}
              </div>
              <span
                className={clsx(
                  'text-[9px] font-medium transition-colors duration-200',
                  isActive ? 'text-signal' : 'text-oxide'
                )}
              >
                {tab.label}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
