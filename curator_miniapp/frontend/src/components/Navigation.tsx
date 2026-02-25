import { ShoppingBag, Briefcase } from 'lucide-react'
import { motion } from 'framer-motion'
import { useTelegram } from '../hooks/useTelegram'
import { SPRING_SNAPPY } from '../lib/animations'

type Page = 'products' | 'business'

interface NavigationProps {
  currentPage: Page
  onNavigate: (page: Page) => void
}

export function Navigation({ currentPage, onNavigate }: NavigationProps) {
  const { haptic } = useTelegram()

  const navItems = [
    { id: 'products' as Page, label: 'Продукция', icon: ShoppingBag },
    { id: 'business' as Page, label: 'Бизнес', icon: Briefcase },
  ]

  const handleNavigate = (page: Page) => {
    if (page !== currentPage) {
      haptic('selection')
      onNavigate(page)
    }
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 glass border-t border-smoke/60">
      <div className="flex justify-around items-center h-16 max-w-lg mx-auto relative">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = currentPage === item.id

          return (
            <button
              key={item.id}
              onClick={() => handleNavigate(item.id)}
              className="flex flex-col items-center justify-center w-full h-full gap-1 relative z-10"
            >
              <motion.div
                animate={{ scale: isActive ? 1.1 : 1 }}
                transition={SPRING_SNAPPY}
              >
                <Icon
                  size={22}
                  className={isActive ? 'text-amber-soft' : 'text-stone'}
                  style={{ transition: 'color 0.2s ease' }}
                />
              </motion.div>
              <span
                className={`text-xs font-medium ${isActive ? 'text-amber-soft' : 'text-stone'}`}
                style={{ transition: 'color 0.2s ease' }}
              >
                {item.label}
              </span>
              {isActive && (
                <motion.div
                  layoutId="nav-indicator"
                  className="absolute bottom-0 w-12 h-0.5 rounded-full"
                  style={{
                    background: 'linear-gradient(90deg, transparent, #FCD34D, transparent)',
                  }}
                  transition={SPRING_SNAPPY}
                />
              )}
            </button>
          )
        })}
      </div>
    </nav>
  )
}
