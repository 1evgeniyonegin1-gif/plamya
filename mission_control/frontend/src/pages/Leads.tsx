import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Target, Flame, Thermometer, Snowflake } from 'lucide-react'
import clsx from 'clsx'
import { leadsApi } from '../api/client'
import type { Lead } from '../api/client'
import LeadCard from '../components/LeadCard'
import LeadDetail from './LeadDetail'

type PriorityFilter = 'all' | 'hot' | 'warm' | 'cold'

export default function Leads() {
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>('all')
  const [selectedLead, setSelectedLead] = useState<number | null>(null)

  // Fetch leads
  const { data, isLoading } = useQuery({
    queryKey: ['leads', priorityFilter],
    queryFn: () =>
      leadsApi
        .list({
          priority: priorityFilter === 'all' ? undefined : priorityFilter,
          limit: 100,
        })
        .then((r) => r.data),
    refetchInterval: 60_000,
  })

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['leads-stats'],
    queryFn: () => leadsApi.stats().then((r) => r.data),
    refetchInterval: 60_000,
  })

  const leads = data?.leads ?? []
  const total = data?.total ?? 0

  // If a lead is selected, show detail view
  if (selectedLead !== null) {
    return (
      <LeadDetail
        leadId={selectedLead}
        onBack={() => setSelectedLead(null)}
      />
    )
  }

  return (
    <div className="px-3 pt-3 safe-bottom">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <Target size={18} className="text-signal" />
        <h1 className="text-chrome text-lg font-bold">Лиды</h1>
        <span className="badge badge-success font-mono ml-auto">
          {total}
        </span>
      </div>

      {/* Stats bar */}
      {stats && (
        <div className="flex items-center gap-3 mb-3 overflow-x-auto no-scrollbar">
          <div className="flex items-center gap-1.5 text-[11px] font-mono whitespace-nowrap">
            <Flame size={12} className="text-alert" />
            <span className="text-alert">{stats.priorities?.hot ?? 0}</span>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] font-mono whitespace-nowrap">
            <Thermometer size={12} className="text-caution" />
            <span className="text-caution">{stats.priorities?.warm ?? 0}</span>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] font-mono whitespace-nowrap">
            <Snowflake size={12} className="text-electric" />
            <span className="text-electric">{stats.priorities?.cold ?? 0}</span>
          </div>
        </div>
      )}

      {/* Priority filter chips */}
      <div className="flex gap-2 mb-3 overflow-x-auto no-scrollbar pb-1">
        {[
          { id: 'all' as PriorityFilter, label: 'Все' },
          { id: 'hot' as PriorityFilter, label: 'Hot' },
          { id: 'warm' as PriorityFilter, label: 'Warm' },
          { id: 'cold' as PriorityFilter, label: 'Cold' },
        ].map((f) => (
          <button
            key={f.id}
            onClick={() => setPriorityFilter(f.id)}
            className={clsx('chip', priorityFilter === f.id && 'chip-active')}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="shimmer-skeleton h-[80px]" />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && leads.length === 0 && (
        <div className="text-center py-12">
          <Target size={32} className="text-oxide mx-auto mb-3" />
          <p className="text-oxide text-sm">Нет лидов</p>
          <p className="text-oxide/60 text-xs mt-1">
            Запустите biz_scanner для поиска бизнесов
          </p>
        </div>
      )}

      {/* Lead cards */}
      <AnimatePresence initial={false}>
        <motion.div className="space-y-2" layout>
          {leads.map((lead: Lead) => (
            <LeadCard
              key={lead.id}
              lead={lead}
              onClick={() => setSelectedLead(lead.id)}
            />
          ))}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
