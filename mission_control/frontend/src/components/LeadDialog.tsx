import { useState, useRef, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Copy, Check, Lightbulb, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { leadsApi } from '../api/client'
import type { DialogMessage } from '../api/client'

interface LeadDialogProps {
  leadId: number
  leadName: string
}

export default function LeadDialog({ leadId }: LeadDialogProps) {
  const [input, setInput] = useState('')
  const [copiedId, setCopiedId] = useState<number | null>(null)
  const [lastTip, setLastTip] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  // Fetch dialog history
  const { data: historyData } = useQuery({
    queryKey: ['lead-history', leadId],
    queryFn: () => leadsApi.history(leadId).then(r => r.data),
  })

  const messages = historyData?.messages ?? []

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  // Send dialog mutation
  const sendMutation = useMutation({
    mutationFn: (clientMessage: string) =>
      leadsApi.dialog(leadId, clientMessage).then(r => r.data),
    onSuccess: (data) => {
      setLastTip(data.tips)
      setInput('')
      queryClient.invalidateQueries({ queryKey: ['lead-history', leadId] })
    },
  })

  const handleSend = () => {
    const msg = input.trim()
    if (!msg || sendMutation.isPending) return
    sendMutation.mutate(msg)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const copyToClipboard = async (text: string, msgId: number) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(msgId)
      // Telegram Mini App haptic feedback
      if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred('light')
      }
      setTimeout(() => setCopiedId(null), 2000)
    } catch {
      // Fallback: select text
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <p className="text-oxide text-sm">
              Вставь ответ клиента после отправки предложения
            </p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((msg: DialogMessage) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={clsx(
                'flex flex-col',
                msg.direction === 'outgoing' ? 'items-end' : 'items-start'
              )}
            >
              {/* Role label */}
              <span className={clsx(
                'text-[10px] font-mono mb-0.5 px-1',
                msg.direction === 'outgoing' ? 'text-signal' : 'text-oxide'
              )}>
                {msg.direction === 'outgoing' ? 'ДАНИЛ' : 'КЛИЕНТ'}
              </span>

              {/* Message bubble */}
              <div className={clsx(
                msg.direction === 'outgoing'
                  ? 'chat-bubble-mine'
                  : 'chat-bubble-agent'
              )}>
                <p className="text-sm text-chrome whitespace-pre-wrap">
                  {msg.message_text}
                </p>

                {/* Copy button for outgoing (AI-generated) messages */}
                {msg.direction === 'outgoing' && (
                  <button
                    onClick={() => copyToClipboard(msg.message_text, msg.id)}
                    className="flex items-center gap-1 mt-1.5 text-[10px] text-oxide hover:text-signal transition-colors"
                  >
                    {copiedId === msg.id ? (
                      <>
                        <Check size={10} className="text-signal" />
                        <span className="text-signal">Скопировано</span>
                      </>
                    ) : (
                      <>
                        <Copy size={10} />
                        <span>Скопировать</span>
                      </>
                    )}
                  </button>
                )}
              </div>

              {/* Timestamp */}
              <span className="text-[9px] text-oxide/50 mt-0.5 px-1 font-mono">
                {new Date(msg.sent_at).toLocaleTimeString('ru-RU', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Loading indicator */}
        {sendMutation.isPending && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 justify-end"
          >
            <div className="chat-bubble-mine flex items-center gap-2">
              <Loader2 size={14} className="text-signal animate-spin" />
              <span className="text-xs text-oxide">AI генерирует ответ...</span>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* AI Tip */}
      <AnimatePresence>
        {lastTip && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-3 py-1.5 border-t border-steel"
          >
            <div className="flex items-start gap-1.5">
              <Lightbulb size={12} className="text-caution flex-shrink-0 mt-0.5" />
              <p className="text-[11px] text-caution">{lastTip}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input area */}
      <div className="chat-input-area px-3 py-2">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Вставь ответ клиента..."
            rows={1}
            className="flex-1 bg-steel text-chrome text-sm rounded-lg px-3 py-2 resize-none
                       border border-graphite focus:border-signal/30 focus:outline-none
                       placeholder:text-oxide min-h-[38px] max-h-[120px]"
            style={{
              height: 'auto',
              minHeight: '38px',
            }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement
              target.style.height = 'auto'
              target.style.height = Math.min(target.scrollHeight, 120) + 'px'
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sendMutation.isPending}
            className={clsx(
              'p-2 rounded-lg transition-all',
              input.trim() && !sendMutation.isPending
                ? 'bg-signal text-abyss'
                : 'bg-steel text-oxide'
            )}
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}
