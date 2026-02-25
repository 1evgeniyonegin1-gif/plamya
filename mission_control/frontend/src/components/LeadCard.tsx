import { motion } from 'framer-motion'
import { MapPin, Phone, Globe, MessageCircle } from 'lucide-react'
import clsx from 'clsx'
import type { Lead } from '../api/client'

const PRIORITY_STYLES = {
  hot: { border: 'border-l-alert', dot: 'status-red', label: 'HOT' },
  warm: { border: 'border-l-caution', dot: 'status-yellow', label: 'WARM' },
  cold: { border: 'border-l-electric', dot: 'status-gray', label: 'COLD' },
}

interface LeadCardProps {
  lead: Lead
  onClick: () => void
}

export default function LeadCard({ lead, onClick }: LeadCardProps) {
  const style = PRIORITY_STYLES[lead.priority] || PRIORITY_STYLES.cold
  const contactCount = Object.keys(lead.contacts).length
  const hasProposal = !!(lead.proposal_telegram || lead.proposal_email)

  return (
    <motion.button
      onClick={onClick}
      className={clsx(
        'card w-full text-left border-l-[3px]',
        style.border
      )}
      whileTap={{ scale: 0.98 }}
      layout
    >
      <div className="flex items-start justify-between gap-2">
        {/* Left: name + meta */}
        <div className="flex-1 min-w-0">
          <h3 className="text-chrome text-sm font-semibold truncate">
            {lead.name}
          </h3>
          <div className="flex items-center gap-2 mt-1">
            <MapPin size={12} className="text-oxide flex-shrink-0" />
            <span className="text-oxide text-xs truncate">
              {lead.city}
            </span>
            {lead.category && (
              <>
                <span className="text-graphite">|</span>
                <span className="text-oxide text-xs truncate">
                  {lead.category}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Right: priority badge */}
        <div className="flex flex-col items-end gap-1">
          <span className={clsx(
            'badge',
            lead.priority === 'hot' && 'badge-error',
            lead.priority === 'warm' && 'badge-warning',
            lead.priority === 'cold' && 'badge-info',
          )}>
            {style.label}
          </span>
          <span className="text-oxide text-[10px] font-mono">
            {lead.priority_score}pt
          </span>
        </div>
      </div>

      {/* Bottom row: contacts + status indicators */}
      <div className="flex items-center gap-3 mt-2 pt-2 border-t border-steel">
        {/* Contact indicators */}
        <div className="flex items-center gap-1.5">
          {lead.contacts.phone && (
            <Phone size={12} className="text-signal" />
          )}
          {lead.contacts.website && (
            <Globe size={12} className="text-electric" />
          )}
          {(lead.contacts.telegram || lead.contacts.vk || lead.contacts.instagram || lead.contacts.whatsapp) && (
            <MessageCircle size={12} className="text-pulse" />
          )}
          {contactCount === 0 && (
            <span className="text-oxide text-[10px]">no contacts</span>
          )}
        </div>

        <div className="flex-1" />

        {/* Status */}
        <span className={clsx(
          'text-[10px] font-mono',
          lead.status === 'proposal_ready' && 'text-signal',
          lead.status === 'contacted' && 'text-electric',
          lead.status === 'replied' && 'text-caution',
          lead.status === 'delivered' && 'text-alloy',
        )}>
          {lead.status === 'proposal_ready' && 'READY'}
          {lead.status === 'delivered' && 'SENT'}
          {lead.status === 'contacted' && 'CONTACTED'}
          {lead.status === 'replied' && 'REPLIED'}
          {lead.status === 'negotiating' && 'NEGOTIATING'}
        </span>

        {hasProposal && (
          <div className="w-1.5 h-1.5 rounded-full bg-signal" />
        )}
      </div>
    </motion.button>
  )
}
