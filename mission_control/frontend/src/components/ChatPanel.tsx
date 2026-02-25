import { useState, useRef, useEffect, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, MessageSquare } from 'lucide-react'
import { inboxApi, chatApi } from '../api/client'
import type { InboxMessage } from '../api/client'
import { AGENTS } from '../lib/constants'

interface ChatPanelProps {
  agentId: string
}

// "ДАНИЛ" is always the user in INBOX.md
const MY_NAME = 'ДАНИЛ'

function isMine(msg: InboxMessage): boolean {
  return msg.sender.toUpperCase().includes(MY_NAME)
}

export default function ChatPanel({ agentId }: ChatPanelProps) {
  const webApp = window.Telegram?.WebApp
  const meta = AGENTS[agentId]
  const agentName = meta?.name ?? agentId.toUpperCase()

  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const queryClient = useQueryClient()

  // Fetch conversation (all inbox messages for this agent)
  const { data, isLoading } = useQuery({
    queryKey: ['chat', agentId],
    queryFn: () =>
      inboxApi.list({ agent: agentId, limit: 100 }).then((r) => r.data),
    refetchInterval: 20_000,
  })

  // Reverse messages so oldest is first (inbox returns newest first)
  const messages = data?.messages ? [...data.messages].reverse() : []

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages.length])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 120) + 'px'
    }
  }, [text])

  const handleSend = useCallback(async () => {
    const trimmed = text.trim()
    if (!trimmed || sending) return

    setSending(true)
    try {
      await chatApi.send({ agent_id: agentId, message: trimmed })
      setText('')

      // Haptic feedback
      if (webApp?.HapticFeedback) {
        webApp.HapticFeedback.impactOccurred('light')
      }

      // Refetch messages
      queryClient.invalidateQueries({ queryKey: ['chat', agentId] })
    } catch (err) {
      console.error('Failed to send message:', err)
      if (webApp?.HapticFeedback) {
        webApp.HapticFeedback.notificationOccurred('error')
      }
    } finally {
      setSending(false)
    }
  }, [text, sending, agentId, webApp, queryClient])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col" style={{ height: 'calc(100dvh - 200px)', minHeight: '300px' }}>
      {/* Messages area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-3 py-2 space-y-2 no-scrollbar"
      >
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <div className="shimmer-skeleton w-48 h-4 rounded" />
          </div>
        )}

        {!isLoading && messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <MessageSquare size={32} className="text-oxide mb-2" />
            <p className="text-sm text-oxide">
              Нет сообщений с {agentName}
            </p>
            <p className="text-xs text-oxide/60 mt-1">
              Напиши первое сообщение
            </p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((msg) => {
            const mine = isMine(msg)
            return (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.15 }}
                className={`flex ${mine ? 'justify-end' : 'justify-start'}`}
              >
                <div className={mine ? 'chat-bubble-mine' : 'chat-bubble-agent'}>
                  {/* Subject */}
                  {msg.subject && (
                    <div className="text-[10px] font-semibold text-alloy mb-1 uppercase tracking-wider">
                      {msg.subject}
                    </div>
                  )}
                  {/* Text */}
                  <p className="text-xs text-chrome leading-relaxed whitespace-pre-wrap">
                    {msg.full_text || msg.preview}
                  </p>
                  {/* Timestamp */}
                  <div className="text-[9px] text-oxide mt-1 text-right font-mono">
                    {msg.timestamp}
                  </div>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>

      {/* Input area */}
      <div className="chat-input-area px-3 py-2 flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Написать ${agentName}...`}
          rows={1}
          className="flex-1 bg-steel/50 border border-graphite rounded-lg px-3 py-2 text-xs text-chrome placeholder:text-oxide resize-none focus:outline-none focus:border-signal/30 transition-colors"
          style={{ maxHeight: '120px' }}
        />
        <button
          onClick={handleSend}
          disabled={!text.trim() || sending}
          className="w-9 h-9 flex items-center justify-center rounded-lg bg-signal/20 text-signal disabled:opacity-30 disabled:cursor-not-allowed transition-all active:scale-95"
        >
          <Send size={16} className={sending ? 'animate-pulse' : ''} />
        </button>
      </div>
    </div>
  )
}
