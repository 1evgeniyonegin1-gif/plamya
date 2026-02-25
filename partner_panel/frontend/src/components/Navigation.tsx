import { Home, Link, Radio, BarChart3 } from 'lucide-react'
import clsx from 'clsx'

type Page = 'dashboard' | 'connect' | 'channels' | 'stats'

interface NavigationProps {
  currentPage: Page
  onNavigate: (page: Page) => void
}

const navItems: { page: Page; icon: typeof Home; label: string }[] = [
  { page: 'dashboard', icon: Home, label: 'Центр' },
  { page: 'connect', icon: Link, label: 'Связь' },
  { page: 'channels', icon: Radio, label: 'Каналы' },
  { page: 'stats', icon: BarChart3, label: 'Данные' },
]

export function Navigation({ currentPage, onNavigate }: NavigationProps) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 glass z-50">
      <div className="flex justify-around items-center h-16 max-w-md mx-auto">
        {navItems.map(({ page, icon: Icon, label }) => (
          <button
            key={page}
            onClick={() => onNavigate(page)}
            className={clsx(
              'flex flex-col items-center justify-center w-16 h-full transition-all duration-300',
              currentPage === page
                ? 'text-glow-soft'
                : 'text-dust hover:text-star-dim'
            )}
          >
            <div className={clsx(
              'p-2 rounded-xl transition-all duration-300',
              currentPage === page && 'bg-glow/10'
            )}>
              <Icon className="w-5 h-5" />
            </div>
            <span className="text-[10px] mt-1 tracking-wide">{label}</span>
          </button>
        ))}
      </div>
    </nav>
  )
}
