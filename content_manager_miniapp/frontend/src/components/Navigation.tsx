import { motion } from 'framer-motion'
import { FileText, BarChart3, Radio, Sparkles } from 'lucide-react'
import clsx from 'clsx'

export type TabId = 'posts' | 'analytics' | 'traffic' | 'director'

interface Props {
  activeTab: TabId
  onTabChange: (tab: TabId) => void
  pendingCount?: number
}

const tabs: { id: TabId; label: string; icon: typeof FileText }[] = [
  { id: 'posts', label: 'Посты', icon: FileText },
  { id: 'analytics', label: 'Аналитика', icon: BarChart3 },
  { id: 'traffic', label: 'Traffic', icon: Radio },
  { id: 'director', label: 'Director', icon: Sparkles },
]

export function Navigation({ activeTab, onTabChange, pendingCount }: Props) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-ember/95 backdrop-blur-lg border-t border-smoke/50 z-50">
      <div className="flex items-center justify-around px-2 pb-[env(safe-area-inset-bottom)]">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={clsx(
                'flex flex-col items-center gap-0.5 py-2 px-3 relative transition-colors min-w-[64px]',
                isActive ? 'text-flame' : 'text-mist'
              )}
            >
              <div className="relative">
                <Icon size={22} strokeWidth={isActive ? 2.2 : 1.8} />
                {tab.id === 'posts' && pendingCount && pendingCount > 0 && (
                  <span className="absolute -top-1.5 -right-2.5 bg-flame text-white text-[10px] font-bold min-w-[16px] h-4 flex items-center justify-center rounded-full px-1">
                    {pendingCount > 99 ? '99+' : pendingCount}
                  </span>
                )}
              </div>
              <span className="text-[10px] font-medium">{tab.label}</span>
              {isActive && (
                <motion.div
                  layoutId="tab-indicator"
                  className="absolute top-0 left-2 right-2 tab-indicator"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}
            </button>
          )
        })}
      </div>
    </nav>
  )
}
