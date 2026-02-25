import { useQuery } from '@tanstack/react-query'
import { MessageCircle, Rocket, Check, ChevronDown } from 'lucide-react'
import confetti from 'canvas-confetti'
import { businessApi } from '../api/client'
import { Loading } from '../components/Loading'
import { useTelegram } from '../hooks/useTelegram'
import { motion, staggerContainer, staggerItem, FadeInWhenVisible, SPRING_SNAPPY } from '../lib/animations'

export function Business() {
  const { haptic, openLink, openTelegramLink } = useTelegram()

  // Fetch presentation data
  const { data, isLoading } = useQuery({
    queryKey: ['business-presentation'],
    queryFn: () => businessApi.getPresentation(),
  })

  const presentation = data?.data

  // Handle CTA clicks
  const handleTelegramChat = async () => {
    haptic('medium')
    try {
      await businessApi.trackContact('telegram_chat')
    } catch (e) {
      console.error('Failed to track contact', e)
    }
    openTelegramLink(presentation?.cta.telegram_chat || 'https://t.me/DanilLysenkoNL')
  }

  const handleRegistration = async () => {
    haptic('success')

    // Golden confetti burst
    confetti({
      particleCount: 80,
      spread: 60,
      colors: ['#F59E0B', '#FCD34D', '#D97706', '#FAF7F2'],
      origin: { y: 0.7 },
    })

    try {
      await businessApi.trackContact('registration')
    } catch (e) {
      console.error('Failed to track contact', e)
    }
    openLink(presentation?.cta.registration || 'https://nlstar.com/ref/eiPusg/')
  }

  if (isLoading || !presentation) {
    return <Loading message="Загрузка..." />
  }

  return (
    <div className="p-4 pb-24">
      {/* Hero */}
      <FadeInWhenVisible>
        <div className="text-center mb-8">
          <div className="text-5xl mb-4">💼</div>
          <h1 className="text-2xl font-bold text-gradient-gold mb-2">
            {presentation.headline}
          </h1>
          <p className="text-sand">
            {presentation.tagline}
          </p>
        </div>
      </FadeInWhenVisible>

      {/* Scroll hint */}
      <FadeInWhenVisible delay={0.2}>
        <div className="flex justify-center mb-6">
          <motion.div
            className="flex items-center gap-2 text-amber text-sm"
            animate={{ y: [0, 6, 0] }}
            transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
          >
            <ChevronDown size={16} />
            <span>Листай вниз</span>
            <ChevronDown size={16} />
          </motion.div>
        </div>
      </FadeInWhenVisible>

      {/* Traditional Model */}
      <FadeInWhenVisible delay={0.1}>
        <div className="model-card traditional mb-4">
          <h2 className="text-lg font-semibold text-error mb-3">
            {presentation.traditional_model.title}
          </h2>
          <p className="text-sand text-sm mb-4">
            {presentation.traditional_model.subtitle}
          </p>
          <motion.ul
            className="space-y-3"
            variants={staggerContainer}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: '-30px' }}
          >
            {presentation.traditional_model.items.map((item, i) => (
              <motion.li key={i} className="flex items-center gap-3 text-sm" variants={staggerItem}>
                <span className="text-lg">{item.icon}</span>
                <span className="text-sand">{item.text}</span>
              </motion.li>
            ))}
          </motion.ul>
        </div>
      </FadeInWhenVisible>

      {/* APEXFLOW Model */}
      <FadeInWhenVisible delay={0.1}>
        <div className="model-card apexflow mb-4">
          <h2 className="text-lg font-semibold text-sage mb-3">
            {presentation.apexflow_model.title}
          </h2>
          <p className="text-sand text-sm mb-4">
            {presentation.apexflow_model.subtitle}
          </p>
          <motion.ul
            className="space-y-3"
            variants={staggerContainer}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: '-30px' }}
          >
            {presentation.apexflow_model.items.map((item, i) => (
              <motion.li key={i} className="flex items-center gap-3 text-sm" variants={staggerItem}>
                <span className="text-lg">{item.icon}</span>
                <span className="text-cream">{item.text}</span>
              </motion.li>
            ))}
          </motion.ul>
        </div>
      </FadeInWhenVisible>

      {/* Requirements */}
      <FadeInWhenVisible delay={0.1}>
        <div className="card mb-6">
          <h2 className="text-lg font-semibold text-warning mb-4">
            {presentation.requirements.title}
          </h2>
          <motion.ul
            className="space-y-3"
            variants={staggerContainer}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: '-30px' }}
          >
            {presentation.requirements.items.filter(Boolean).map((item, i) => (
              <motion.li key={i} className="flex items-start gap-3 text-sm" variants={staggerItem}>
                <Check size={16} className="text-sage mt-0.5 flex-shrink-0" />
                <span className="text-sand">{item}</span>
              </motion.li>
            ))}
          </motion.ul>
        </div>
      </FadeInWhenVisible>

      {/* CTA Buttons */}
      <FadeInWhenVisible delay={0.1}>
        <div className="space-y-3">
          <motion.button
            onClick={handleTelegramChat}
            className="btn btn-primary w-full flex items-center justify-center gap-2"
            whileTap={{ scale: 0.96 }}
            transition={SPRING_SNAPPY}
          >
            <MessageCircle size={18} />
            <span>Написать в Telegram</span>
          </motion.button>

          <motion.button
            onClick={handleRegistration}
            className="btn btn-success w-full flex items-center justify-center gap-2"
            whileTap={{ scale: 0.96 }}
            transition={SPRING_SNAPPY}
          >
            <Rocket size={18} />
            <span>Регистрация партнёром</span>
          </motion.button>

          <p className="text-center text-stone text-xs mt-4">
            Telegram: @{presentation.cta.telegram_username}
          </p>
        </div>
      </FadeInWhenVisible>
    </div>
  )
}
