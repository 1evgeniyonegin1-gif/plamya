import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft,
  Phone,
  Mail,
  Globe,
  Copy,
  Check,
  ExternalLink,
  Send,
  SkipForward,
  AlertTriangle,
} from 'lucide-react'
import clsx from 'clsx'
import { leadsApi } from '../api/client'
import LeadDialog from '../components/LeadDialog'

// SVG icons for social platforms
function VkIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} width="16" height="16">
      <path d="M13.162 18.994c.5 0 .5-.29.5-.573v-3.421c0-.284 0-.484.29-.484s.5.2.79.587l2.079 2.636c.58.734.79 1.055 1.285 1.055h2.133c.29 0 .5-.1.5-.384 0-.19-.094-.344-.289-.59l-1.882-2.353c-.393-.5-.588-.734-.588-.923s.094-.384.289-.59l2.375-2.735c.289-.334.484-.58.484-.83 0-.25-.195-.384-.484-.384h-2.133c-.484 0-.69.294-1.09.923l-1.582 2.245c-.393.55-.588.734-.788.734s-.29-.19-.29-.49V7.93c0-.49-.094-.63-.484-.63H12.18c-.29 0-.484.19-.484.384 0 .4.588.49.588 1.628v3.474c0 .384 0 .59-.195.59-.393 0-1.187-1.44-1.68-3.088-.29-.924-.393-1.287-.884-1.287H7.393c-.393 0-.484.19-.484.384 0 .44.29 2.636 2.672 5.537 1.582 1.978 3.806 3.05 5.83 3.05h.75z" />
    </svg>
  )
}

function TelegramIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} width="16" height="16">
      <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.479.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z" />
    </svg>
  )
}

function WhatsAppIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} width="16" height="16">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
    </svg>
  )
}

function InstagramIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} width="16" height="16">
      <path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678a6.162 6.162 0 100 12.324 6.162 6.162 0 100-12.324zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405a1.441 1.441 0 11-2.882 0 1.441 1.441 0 012.882 0z" />
    </svg>
  )
}

interface LeadDetailProps {
  leadId: number
  onBack: () => void
}

type ViewMode = 'info' | 'dialog'

export default function LeadDetail({ leadId, onBack }: LeadDetailProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('info')
  const [copiedField, setCopiedField] = useState('')
  const [proposalFormat, setProposalFormat] = useState<'telegram' | 'email' | 'phone'>('telegram')
  const queryClient = useQueryClient()

  // Fetch lead detail
  const { data: lead, isLoading } = useQuery({
    queryKey: ['lead-detail', leadId],
    queryFn: () => leadsApi.detail(leadId).then((r) => r.data),
  })

  // Status mutation
  const statusMutation = useMutation({
    mutationFn: ({ status, notes }: { status: string; notes?: string }) =>
      leadsApi.updateStatus(leadId, status, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead-detail', leadId] })
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['leads-stats'] })
    },
  })

  const copyText = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedField(field)
      if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred('light')
      }
      setTimeout(() => setCopiedField(''), 2000)
    } catch {
      // Fallback
    }
  }

  const getProposalText = (): string => {
    if (!lead) return ''
    if (proposalFormat === 'telegram') return lead.proposal_telegram || ''
    if (proposalFormat === 'email') return lead.proposal_email || ''
    return lead.proposal_phone_script || ''
  }

  if (isLoading || !lead) {
    return (
      <div className="px-3 pt-3">
        <button onClick={onBack} className="flex items-center gap-1 text-oxide text-sm mb-3">
          <ArrowLeft size={16} /> Назад
        </button>
        <div className="space-y-3">
          <div className="shimmer-skeleton h-[60px]" />
          <div className="shimmer-skeleton h-[100px]" />
          <div className="shimmer-skeleton h-[200px]" />
        </div>
      </div>
    )
  }

  const proposalText = getProposalText()

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <div className="px-3 pt-3 pb-2">
        <button onClick={onBack} className="flex items-center gap-1 text-oxide text-sm mb-2">
          <ArrowLeft size={16} /> Назад
        </button>
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h2 className="text-chrome text-base font-bold truncate">{lead.name}</h2>
            <p className="text-oxide text-xs">{lead.city} | {lead.category}</p>
          </div>
          <span className={clsx(
            'badge',
            lead.priority === 'hot' && 'badge-error',
            lead.priority === 'warm' && 'badge-warning',
            lead.priority === 'cold' && 'badge-info',
          )}>
            {lead.priority.toUpperCase()} {lead.priority_score}pt
          </span>
        </div>
      </div>

      {/* View mode tabs */}
      <div className="flex gap-1 px-3 mb-2">
        <button
          onClick={() => setViewMode('info')}
          className={clsx('chip flex-1 text-center', viewMode === 'info' && 'chip-active')}
        >
          Инфо
        </button>
        <button
          onClick={() => setViewMode('dialog')}
          className={clsx('chip flex-1 text-center', viewMode === 'dialog' && 'chip-active')}
        >
          Диалог
        </button>
      </div>

      <AnimatePresence mode="wait">
        {viewMode === 'info' ? (
          <motion.div
            key="info"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 8 }}
            className="flex-1 px-3 safe-bottom overflow-y-auto"
          >
            {/* Contacts */}
            <div className="card mb-2">
              <h3 className="text-chrome text-xs font-semibold uppercase tracking-wider mb-2">
                Контакты
              </h3>
              <div className="space-y-1.5">
                {lead.contacts.phone && (
                  <ContactLink
                    icon={<Phone size={14} />}
                    label={lead.contacts.phone}
                    href={`tel:${lead.contacts.phone}`}
                    color="text-signal"
                  />
                )}
                {lead.contacts.email && (
                  <ContactLink
                    icon={<Mail size={14} />}
                    label={lead.contacts.email}
                    href={`mailto:${lead.contacts.email}`}
                    color="text-electric"
                  />
                )}
                {lead.contacts.website && (
                  <ContactLink
                    icon={<Globe size={14} />}
                    label={new URL(lead.contacts.website).hostname}
                    href={lead.contacts.website}
                    color="text-electric"
                  />
                )}
                {lead.contacts.telegram && (
                  <ContactLink
                    icon={<TelegramIcon className="text-electric" />}
                    label="Telegram"
                    href={lead.contacts.telegram}
                    color="text-electric"
                  />
                )}
                {lead.contacts.vk && (
                  <ContactLink
                    icon={<VkIcon className="text-electric" />}
                    label="VK"
                    href={lead.contacts.vk}
                    color="text-electric"
                  />
                )}
                {lead.contacts.instagram && (
                  <ContactLink
                    icon={<InstagramIcon className="text-electric" />}
                    label="Instagram"
                    href={lead.contacts.instagram}
                    color="text-electric"
                  />
                )}
                {lead.contacts.whatsapp && (
                  <ContactLink
                    icon={<WhatsAppIcon className="text-signal" />}
                    label="WhatsApp"
                    href={`https://wa.me/${lead.contacts.whatsapp.replace(/\D/g, '')}`}
                    color="text-signal"
                  />
                )}
                {Object.keys(lead.contacts).length === 0 && (
                  <div className="flex items-center gap-2 text-oxide text-xs">
                    <AlertTriangle size={12} />
                    <span>Контакты не найдены</span>
                  </div>
                )}
              </div>
            </div>

            {/* Problems */}
            {lead.problems.length > 0 && (
              <div className="card mb-2">
                <h3 className="text-chrome text-xs font-semibold uppercase tracking-wider mb-2">
                  Проблемы
                </h3>
                <ul className="space-y-1">
                  {lead.problems.map((p, i) => (
                    <li key={i} className="text-oxide text-xs flex items-start gap-1.5">
                      <span className="text-alert mt-0.5">-</span>
                      <span>{p}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Proposal */}
            {proposalText && (
              <div className="card mb-2">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-chrome text-xs font-semibold uppercase tracking-wider">
                    Предложение
                  </h3>
                  <button
                    onClick={() => copyText(proposalText, 'proposal')}
                    className={clsx(
                      'btn-primary text-xs flex items-center gap-1 !py-1.5 !px-3',
                      copiedField === 'proposal' && '!bg-pulse'
                    )}
                  >
                    {copiedField === 'proposal' ? (
                      <><Check size={12} /> Скопировано</>
                    ) : (
                      <><Copy size={12} /> Скопировать</>
                    )}
                  </button>
                </div>

                {/* Format selector */}
                <div className="flex gap-1 mb-2">
                  {(['telegram', 'email', 'phone'] as const).map((fmt) => (
                    <button
                      key={fmt}
                      onClick={() => setProposalFormat(fmt)}
                      className={clsx(
                        'text-[10px] font-mono px-2 py-0.5 rounded border',
                        proposalFormat === fmt
                          ? 'border-signal/30 text-signal bg-signal/5'
                          : 'border-steel text-oxide'
                      )}
                    >
                      {fmt === 'telegram' ? 'TG' : fmt === 'email' ? 'Email' : 'Phone'}
                    </button>
                  ))}
                </div>

                <pre className="text-chrome text-xs whitespace-pre-wrap font-sans leading-relaxed bg-abyss/50 rounded-lg p-2.5 border border-steel max-h-[300px] overflow-y-auto">
                  {proposalText || 'Предложение не сгенерировано'}
                </pre>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => {
                  statusMutation.mutate({ status: 'contacted' })
                  setViewMode('dialog')
                }}
                className="btn-primary flex-1 flex items-center justify-center gap-1.5"
              >
                <Send size={14} />
                Написал
              </button>
              <button
                onClick={() => statusMutation.mutate({ status: 'skipped', notes: 'Пропущен' })}
                className="btn-secondary flex items-center justify-center gap-1.5"
              >
                <SkipForward size={14} />
                Пропустить
              </button>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="dialog"
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -8 }}
            className="flex-1 flex flex-col min-h-0"
          >
            <LeadDialog leadId={leadId} leadName={lead.name} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── Contact link sub-component ──────────────────

function ContactLink({
  icon,
  label,
  href,
  color,
}: {
  icon: React.ReactNode
  label: string
  href: string
  color: string
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={clsx(
        'flex items-center gap-2 p-1.5 rounded-lg hover:bg-steel/50 transition-colors',
        color
      )}
    >
      {icon}
      <span className="text-xs flex-1 truncate">{label}</span>
      <ExternalLink size={10} className="text-oxide flex-shrink-0" />
    </a>
  )
}
