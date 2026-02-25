import { useMemo, useEffect, useState, useRef } from 'react'

interface Star {
  id: number
  x: number
  y: number
  z: number // глубина (1 = близко, 3 = далеко)
  size: number
  opacity: number
  twinkle: boolean
}

// Определяем мобильное устройство
const isMobile = () => {
  if (typeof window === 'undefined') return false
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
}

export function Stars() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [motion, setMotion] = useState({ x: 0, y: 0 })
  const [isActive, setIsActive] = useState(false)

  // Генерируем звёзды с разной глубиной
  const stars = useMemo(() => {
    const result: Star[] = []

    // Слой 1 — далёкие звёзды (много, мелкие)
    for (let i = 0; i < 80; i++) {
      result.push({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        z: 3, // далеко
        size: 1,
        opacity: 0.2 + Math.random() * 0.2,
        twinkle: Math.random() > 0.8,
      })
    }

    // Слой 2 — средние звёзды
    for (let i = 80; i < 120; i++) {
      result.push({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        z: 2, // средне
        size: 1.5,
        opacity: 0.3 + Math.random() * 0.3,
        twinkle: Math.random() > 0.7,
      })
    }

    // Слой 3 — близкие яркие звёзды (мало, крупные)
    for (let i = 120; i < 140; i++) {
      result.push({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        z: 1, // близко
        size: 2 + Math.random(),
        opacity: 0.5 + Math.random() * 0.5,
        twinkle: Math.random() > 0.5,
      })
    }

    return result
  }, [])

  // Обработка движения — мышь на десктопе, гироскоп на мобильных
  useEffect(() => {
    const mobile = isMobile()

    if (mobile) {
      // Мобильный — используем гироскоп
      const handleOrientation = (e: DeviceOrientationEvent) => {
        if (e.gamma === null || e.beta === null) return

        setIsActive(true)

        // gamma: наклон влево-вправо (-90 до 90)
        // beta: наклон вперёд-назад (-180 до 180)
        // Нормализуем до -1...1, ограничиваем диапазон для мягкости
        const x = Math.max(-1, Math.min(1, e.gamma / 30))
        const y = Math.max(-1, Math.min(1, (e.beta - 45) / 30)) // 45° — нейтральное положение телефона

        setMotion({ x, y })
      }

      // Запрашиваем разрешение на iOS 13+
      if (typeof (DeviceOrientationEvent as any).requestPermission === 'function') {
        // Для iOS нужен клик пользователя, добавим слушатель
        const requestPermission = async () => {
          try {
            const permission = await (DeviceOrientationEvent as any).requestPermission()
            if (permission === 'granted') {
              window.addEventListener('deviceorientation', handleOrientation)
            }
          } catch (e) {
            console.log('Gyroscope permission denied')
          }
        }

        // Слушаем первый тап для запроса разрешения
        const handleFirstTouch = () => {
          requestPermission()
          window.removeEventListener('touchstart', handleFirstTouch)
        }
        window.addEventListener('touchstart', handleFirstTouch, { once: true })
      } else {
        // Android и старые iOS — просто подключаемся
        window.addEventListener('deviceorientation', handleOrientation)
      }

      return () => {
        window.removeEventListener('deviceorientation', handleOrientation)
      }
    } else {
      // Десктоп — используем мышь
      const handleMouseMove = (e: MouseEvent) => {
        if (!containerRef.current) return

        const rect = containerRef.current.getBoundingClientRect()
        const centerX = rect.width / 2
        const centerY = rect.height / 2

        const x = (e.clientX - rect.left - centerX) / centerX
        const y = (e.clientY - rect.top - centerY) / centerY

        setMotion({ x, y })
        setIsActive(true)
      }

      const handleMouseLeave = () => {
        setIsActive(false)
        setMotion({ x: 0, y: 0 })
      }

      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseleave', handleMouseLeave)

      return () => {
        window.removeEventListener('mousemove', handleMouseMove)
        window.removeEventListener('mouseleave', handleMouseLeave)
      }
    }
  }, [])

  // Вычисляем смещение для каждого слоя — мягкий параллакс
  const getParallaxOffset = (z: number) => {
    // Чем меньше z (ближе), тем больше смещение
    // Мягкий эффект для комфортного восприятия
    const factor = (4 - z) * 5
    return {
      x: motion.x * factor,
      y: motion.y * factor,
    }
  }

  return (
    <div
      ref={containerRef}
      className="stars-container"
      style={{ perspective: '1000px' }}
    >
      {/* Туманности на фоне */}
      <div
        className="absolute inset-0 opacity-30"
        style={{
          background: `
            radial-gradient(ellipse at ${30 + motion.x * 5}% ${70 + motion.y * 5}%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
            radial-gradient(ellipse at ${70 - motion.x * 5}% ${30 - motion.y * 5}%, rgba(124, 58, 237, 0.06) 0%, transparent 50%),
            radial-gradient(ellipse at ${50 + motion.x * 3}% ${50 + motion.y * 3}%, rgba(59, 130, 246, 0.04) 0%, transparent 60%)
          `,
          transition: isActive ? 'none' : 'background 1s ease-out',
        }}
      />

      {/* Звёзды с параллаксом */}
      {stars.map((star) => {
        const offset = getParallaxOffset(star.z)

        return (
          <div
            key={star.id}
            className={`star ${star.twinkle ? 'animate' : ''}`}
            style={{
              left: `calc(${star.x}% + ${offset.x}px)`,
              top: `calc(${star.y}% + ${offset.y}px)`,
              width: `${star.size}px`,
              height: `${star.size}px`,
              opacity: star.opacity,
              boxShadow: star.z === 1 ? `0 0 ${star.size * 3}px rgba(129, 140, 248, 0.5)` : 'none',
              transition: isActive ? 'left 0.15s ease-out, top 0.15s ease-out' : 'left 1s ease-out, top 1s ease-out',
              transform: `translateZ(${(3 - star.z) * 10}px)`,
              animationDelay: star.twinkle ? `${Math.random() * 5}s` : undefined,
              animationDuration: star.twinkle ? `${2 + Math.random() * 3}s` : undefined,
            }}
          />
        )
      })}

      {/* Падающая звезда (редко) */}
      <ShootingStar />
    </div>
  )
}

// Падающая звезда
function ShootingStar() {
  const [visible, setVisible] = useState(false)
  const [position, setPosition] = useState({ x: 0, y: 0 })

  useEffect(() => {
    const scheduleNext = () => {
      // Случайный интервал 10-30 секунд
      const delay = 10000 + Math.random() * 20000

      setTimeout(() => {
        setPosition({
          x: 20 + Math.random() * 60,
          y: 10 + Math.random() * 30,
        })
        setVisible(true)

        // Скрыть через 1 секунду
        setTimeout(() => {
          setVisible(false)
          scheduleNext()
        }, 1000)
      }, delay)
    }

    scheduleNext()
  }, [])

  if (!visible) return null

  return (
    <div
      className="shooting-star"
      style={{
        left: `${position.x}%`,
        top: `${position.y}%`,
      }}
    />
  )
}
