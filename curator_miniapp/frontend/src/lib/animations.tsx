import { useEffect, useRef, useState } from 'react'
import { motion, useInView, useSpring, useTransform, type Variants } from 'framer-motion'

// ===== Spring Presets =====

export const SPRING_SNAPPY = { type: 'spring' as const, stiffness: 300, damping: 30 }
export const SPRING_BOUNCY = { type: 'spring' as const, stiffness: 200, damping: 15 }
export const SPRING_GENTLE = { type: 'spring' as const, stiffness: 100, damping: 20 }

// ===== Variant Presets =====

export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
    },
  },
}

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 20, scale: 0.97 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: SPRING_SNAPPY,
  },
}

export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 30 },
  show: {
    opacity: 1,
    y: 0,
    transition: SPRING_GENTLE,
  },
}

// ===== AnimatedNumber Component =====

interface AnimatedNumberProps {
  value: number
  prefix?: string
  suffix?: string
  className?: string
  duration?: number
}

export function AnimatedNumber({ value, prefix = '', suffix = '', className = '', duration = 0.8 }: AnimatedNumberProps) {
  const spring = useSpring(0, { stiffness: 100, damping: 30, duration })
  const display = useTransform(spring, (v) => Math.round(v).toLocaleString())
  const [displayValue, setDisplayValue] = useState('0')

  useEffect(() => {
    spring.set(value)
  }, [value, spring])

  useEffect(() => {
    const unsubscribe = display.on('change', (v) => {
      setDisplayValue(v)
    })
    return unsubscribe
  }, [display])

  return (
    <span className={className}>
      {prefix}{displayValue}{suffix}
    </span>
  )
}

// ===== FadeInWhenVisible Component =====

interface FadeInWhenVisibleProps {
  children: React.ReactNode
  className?: string
  delay?: number
}

export function FadeInWhenVisible({ children, className = '', delay = 0 }: FadeInWhenVisibleProps) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-50px' })

  return (
    <motion.div
      ref={ref}
      className={className}
      initial={{ opacity: 0, y: 30, scale: 0.98 }}
      animate={isInView ? { opacity: 1, y: 0, scale: 1 } : undefined}
      transition={{ ...SPRING_GENTLE, delay }}
    >
      {children}
    </motion.div>
  )
}

// Re-export motion for convenience
export { motion }
