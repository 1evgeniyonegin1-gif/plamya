import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, AlertCircle, X } from 'lucide-react'
import { create } from 'zustand'

interface ToastState {
  message: string | null
  type: 'success' | 'error'
  show: (message: string, type?: 'success' | 'error') => void
  hide: () => void
}

export const useToast = create<ToastState>((set) => ({
  message: null,
  type: 'success',
  show: (message, type = 'success') => set({ message, type }),
  hide: () => set({ message: null }),
}))

export function Toast() {
  const { message, type, hide } = useToast()

  useEffect(() => {
    if (message) {
      const timer = setTimeout(hide, 3000)
      return () => clearTimeout(timer)
    }
  }, [message, hide])

  return (
    <AnimatePresence>
      {message && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className="fixed top-4 left-4 right-4 z-[100]"
        >
          <div className={`card flex items-center gap-3 ${type === 'success' ? 'border-jade/30' : 'border-flame/30'}`}>
            {type === 'success' ? (
              <CheckCircle className="text-jade shrink-0" size={20} />
            ) : (
              <AlertCircle className="text-flame shrink-0" size={20} />
            )}
            <span className="text-sm text-silk flex-1">{message}</span>
            <button onClick={hide} className="text-mist">
              <X size={16} />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
