import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import clsx from 'clsx'
import type { InboxMessage } from '../api/client'
import { AGENTS } from '../lib/constants'
import TimeAgo from './TimeAgo'

interface MessageBubbleProps {
  message: InboxMessage
}

function agentDisplayName(id: string): string {
  return AGENTS[id]?.name ?? id
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const [expanded, setExpanded] = useState(false)

  const priorityClass =
    message.priority === 'high'
      ? 'priority-high'
      : message.priority === 'medium'
        ? 'priority-medium'
        : message.priority === 'low'
          ? 'priority-low'
          : ''

  return (
    <motion.div
      layout
      className={clsx('message-bubble', priorityClass)}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-pulse font-medium">
            {agentDisplayName(message.sender)}
          </span>
          <span className="text-oxide">&rarr;</span>
          <span className="text-electric font-medium">
            {agentDisplayName(message.recipient)}
          </span>
        </div>
        <TimeAgo date={message.timestamp} />
      </div>

      {/* Subject */}
      <h4 className="text-sm font-semibold text-chrome mb-1">
        {message.subject}
      </h4>

      {/* Preview */}
      <p className="text-xs text-alloy leading-relaxed">{message.preview}</p>

      {/* Expand indicator */}
      <div className="flex justify-center mt-1.5">
        <motion.div
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown size={14} className="text-oxide" />
        </motion.div>
      </div>

      {/* Full text */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="mt-2 pt-2 border-t border-steel">
              <pre className="text-xs text-alloy whitespace-pre-wrap font-mono leading-relaxed">
                {message.full_text}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
