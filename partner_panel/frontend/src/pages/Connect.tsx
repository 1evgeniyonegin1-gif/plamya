import { useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ArrowLeft, Phone, Key, Globe, CheckCircle, Loader2 } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { credentialsApi, channelsApi } from '../api/client'
import clsx from 'clsx'

interface ConnectProps {
  onBack: () => void
}

type Step = 'credentials' | 'proxy' | 'channel' | 'progress' | 'done'
type Segment = 'zozh' | 'mama' | 'business'

const SEGMENTS = [
  { id: 'zozh' as Segment, label: 'ЗОЖ', emoji: '🥗', description: 'Здоровый образ жизни, питание' },
  { id: 'mama' as Segment, label: 'Мамы', emoji: '👶', description: 'Контент для мам и семей' },
  { id: 'business' as Segment, label: 'Бизнес', emoji: '💼', description: 'Заработок и карьера' },
]

export function Connect({ onBack }: ConnectProps) {
  const { setBackButton, haptic, showAlert } = useTelegram()
  const [step, setStep] = useState<Step>('credentials')
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('')

  // Form data
  const [phone, setPhone] = useState('')
  const [sessionString, setSessionString] = useState('')
  const [proxyHost, setProxyHost] = useState('')
  const [proxyPort, setProxyPort] = useState('')
  const [proxyUsername, setProxyUsername] = useState('')
  const [proxyPassword, setProxyPassword] = useState('')
  const [segment, setSegment] = useState<Segment>('zozh')
  const [referralLink, setReferralLink] = useState('')

  // Set back button
  useEffect(() => {
    const cleanup = setBackButton(() => {
      if (step === 'credentials') {
        onBack()
      } else if (step === 'proxy') {
        setStep('credentials')
      } else if (step === 'channel') {
        setStep('proxy')
      } else if (step === 'done') {
        onBack()
      }
    })
    return cleanup
  }, [step, onBack, setBackButton])

  // Validate session mutation
  const validateMutation = useMutation({
    mutationFn: (sessionString: string) => credentialsApi.validate(sessionString),
    onSuccess: (response) => {
      if (response.data.valid) {
        haptic('success')
        setStep('proxy')
      } else {
        haptic('error')
        showAlert(response.data.error || 'Session string невалидный')
      }
    },
    onError: () => {
      haptic('error')
      showAlert('Ошибка проверки')
    },
  })

  // Create credentials mutation
  const createMutation = useMutation({
    mutationFn: async () => {
      // Step 1: Create credentials
      const credResponse = await credentialsApi.create({
        phone,
        session_string: sessionString,
        proxy_type: proxyHost ? 'socks5' : undefined,
        proxy_host: proxyHost || undefined,
        proxy_port: proxyPort ? parseInt(proxyPort) : undefined,
        proxy_username: proxyUsername || undefined,
        proxy_password: proxyPassword || undefined,
      })

      // Step 2: Create channel
      const channelResponse = await channelsApi.create({
        credentials_id: credResponse.data.id,
        segment,
        referral_link: referralLink || undefined,
        posts_per_day: 2,
      })

      return { credentials: credResponse.data, channel: channelResponse.data }
    },
    onSuccess: () => {
      haptic('success')
      setStep('done')
    },
    onError: (error: any) => {
      haptic('error')
      showAlert(error.response?.data?.detail || 'Ошибка создания')
      setStep('channel')
    },
  })

  // Handle step 1: Validate credentials
  const handleValidateCredentials = () => {
    if (!phone.trim()) {
      showAlert('Введите номер телефона')
      return
    }
    if (!sessionString.trim()) {
      showAlert('Введите Session String')
      return
    }
    haptic('light')
    validateMutation.mutate(sessionString)
  }

  // Handle step 2: Continue to channel setup
  const handleContinueToChannel = () => {
    haptic('light')
    setStep('channel')
  }

  // Handle step 3: Start setup
  const handleStartSetup = () => {
    haptic('medium')
    setStep('progress')

    // Simulate progress
    let p = 0
    const messages = [
      'Проверяю credentials...',
      'Подключаюсь к Telegram...',
      'Создаю канал...',
      'Настраиваю персону...',
      'Настраиваю автопостинг...',
      'Завершаю настройку...',
    ]

    const interval = setInterval(() => {
      p += 15
      setProgress(Math.min(p, 95))
      setProgressMessage(messages[Math.floor(p / 20)] || messages[messages.length - 1])

      if (p >= 95) {
        clearInterval(interval)
        createMutation.mutate()
      }
    }, 800)
  }

  // Render steps
  const renderCredentialsStep = () => (
    <div className="space-y-4">
      <div className="card bg-blue-500/10 border border-blue-500/20 mb-6">
        <p className="text-sm">
          Для подключения нужен <strong>Session String</strong> от вашего Telegram аккаунта.
          Получить его можно через бот или скрипт Telethon.
        </p>
      </div>

      <div>
        <label className="label">
          <Phone className="w-4 h-4 inline mr-2" />
          Номер телефона
        </label>
        <input
          type="tel"
          className="input"
          placeholder="+7 900 123 45 67"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
      </div>

      <div>
        <label className="label">
          <Key className="w-4 h-4 inline mr-2" />
          Session String
        </label>
        <textarea
          className="input min-h-[100px] font-mono text-sm"
          placeholder="1BQANOTEuMTA4..."
          value={sessionString}
          onChange={(e) => setSessionString(e.target.value)}
        />
      </div>

      <button
        onClick={handleValidateCredentials}
        disabled={validateMutation.isPending}
        className="btn btn-primary w-full flex items-center justify-center gap-2"
      >
        {validateMutation.isPending ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Проверяю...
          </>
        ) : (
          'Продолжить'
        )}
      </button>
    </div>
  )

  const renderProxyStep = () => (
    <div className="space-y-4">
      <div className="card bg-yellow-500/10 border border-yellow-500/20 mb-6">
        <p className="text-sm">
          <strong>Прокси опционален</strong>, но рекомендуется для безопасности аккаунта.
          Можете пропустить этот шаг.
        </p>
      </div>

      <div>
        <label className="label">
          <Globe className="w-4 h-4 inline mr-2" />
          Хост прокси
        </label>
        <input
          type="text"
          className="input"
          placeholder="proxy.example.com"
          value={proxyHost}
          onChange={(e) => setProxyHost(e.target.value)}
        />
      </div>

      <div>
        <label className="label">Порт</label>
        <input
          type="number"
          className="input"
          placeholder="1080"
          value={proxyPort}
          onChange={(e) => setProxyPort(e.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Логин</label>
          <input
            type="text"
            className="input"
            placeholder="username"
            value={proxyUsername}
            onChange={(e) => setProxyUsername(e.target.value)}
          />
        </div>
        <div>
          <label className="label">Пароль</label>
          <input
            type="password"
            className="input"
            placeholder="••••••"
            value={proxyPassword}
            onChange={(e) => setProxyPassword(e.target.value)}
          />
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={handleContinueToChannel}
          className="btn btn-secondary flex-1"
        >
          Пропустить
        </button>
        <button
          onClick={handleContinueToChannel}
          className="btn btn-primary flex-1"
        >
          Продолжить
        </button>
      </div>
    </div>
  )

  const renderChannelStep = () => (
    <div className="space-y-4">
      <div>
        <label className="label">Сегмент контента</label>
        <div className="space-y-2">
          {SEGMENTS.map((seg) => (
            <button
              key={seg.id}
              onClick={() => {
                haptic('light')
                setSegment(seg.id)
              }}
              className={clsx(
                'w-full card flex items-center gap-3 transition-all',
                segment === seg.id
                  ? 'ring-2 ring-nl-green bg-nl-green/5'
                  : 'hover:opacity-80'
              )}
            >
              <span className="text-2xl">{seg.emoji}</span>
              <div className="text-left">
                <div className="font-medium">{seg.label}</div>
                <div className="text-sm text-dust">{seg.description}</div>
              </div>
              {segment === seg.id && (
                <CheckCircle className="w-5 h-5 text-nl-green ml-auto" />
              )}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="label">Ваша реферальная ссылка NL (опционально)</label>
        <input
          type="url"
          className="input"
          placeholder="https://nlstar.com/ref/..."
          value={referralLink}
          onChange={(e) => setReferralLink(e.target.value)}
        />
        <p className="text-xs text-dust mt-1">
          Будет вставляться в посты канала
        </p>
      </div>

      <button
        onClick={handleStartSetup}
        className="btn btn-primary w-full"
      >
        Создать канал
      </button>
    </div>
  )

  const renderProgressStep = () => (
    <div className="flex flex-col items-center justify-center min-h-[400px] p-4">
      <div className="w-20 h-20 rounded-full border-4 border-nl-green border-t-transparent animate-spin mb-6" />
      <div className="w-full max-w-xs mb-4">
        <div className="h-2 bg-void/50 rounded-full overflow-hidden">
          <div
            className="h-full bg-nl-green transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
      <p className="text-center text-dust">{progressMessage}</p>
    </div>
  )

  const renderDoneStep = () => (
    <div className="flex flex-col items-center justify-center min-h-[400px] p-4 text-center">
      <div className="w-20 h-20 rounded-full bg-nl-green/10 flex items-center justify-center mb-6">
        <CheckCircle className="w-10 h-10 text-nl-green" />
      </div>
      <h2 className="text-xl font-bold mb-2">Готово!</h2>
      <p className="text-dust mb-6">
        Канал создан и настроен. Автопостинг начнётся автоматически.
      </p>
      <button
        onClick={onBack}
        className="btn btn-primary"
      >
        На главную
      </button>
    </div>
  )

  return (
    <div className="p-4 pb-24">
      {/* Header */}
      <header className="flex items-center gap-3 mb-6 pt-4">
        <button
          onClick={() => {
            if (step === 'credentials') onBack()
            else if (step === 'proxy') setStep('credentials')
            else if (step === 'channel') setStep('proxy')
            else if (step === 'done') onBack()
          }}
          className="p-2 -ml-2 hover:bg-void/50 rounded-full transition-colors text-star"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-xl font-bold">Подключить аккаунт</h1>
          <p className="text-sm text-dust">
            {step === 'credentials' && 'Шаг 1 из 3: Credentials'}
            {step === 'proxy' && 'Шаг 2 из 3: Прокси'}
            {step === 'channel' && 'Шаг 3 из 3: Настройка канала'}
            {step === 'progress' && 'Настройка...'}
            {step === 'done' && 'Завершено'}
          </p>
        </div>
      </header>

      {/* Step content */}
      {step === 'credentials' && renderCredentialsStep()}
      {step === 'proxy' && renderProxyStep()}
      {step === 'channel' && renderChannelStep()}
      {step === 'progress' && renderProgressStep()}
      {step === 'done' && renderDoneStep()}
    </div>
  )
}
