import {
  Brain,
  Crosshair,
  Code2,
  Search,
  Bot,
  Heart,
  Factory,
} from 'lucide-react'

export const AGENTS: Record<
  string,
  { name: string; icon: typeof Brain; color: string; role: string }
> = {
  main: {
    name: 'АЛЬТРОН',
    icon: Brain,
    color: 'text-signal',
    role: 'Координатор',
  },
  hunter: {
    name: 'ХАНТЕР',
    icon: Crosshair,
    color: 'text-electric',
    role: 'Сканер лидов',
  },
  coder: {
    name: 'КОДЕР',
    icon: Code2,
    color: 'text-pulse',
    role: 'Разработчик',
  },
  scanner: {
    name: 'СКАНЕР',
    icon: Search,
    color: 'text-caution',
    role: 'Researcher',
  },
  chappie: {
    name: 'ЧАППИ',
    icon: Bot,
    color: 'text-electric',
    role: 'AI-партнёр NL',
  },
  empat: {
    name: 'ЭМПАТ',
    icon: Heart,
    color: 'text-alert',
    role: 'Эмоции',
  },
  producer: {
    name: 'ПРОДЮСЕР',
    icon: Factory,
    color: 'text-caution',
    role: 'Инфопродукты',
  },
}

export const STATUS_COLORS: Record<string, string> = {
  active: 'bg-signal',
  completed: 'bg-signal',
  idle: 'bg-caution',
  error: 'bg-alert',
  unknown: 'bg-oxide',
}

export const AGENT_ORDER = [
  'main',
  'hunter',
  'coder',
  'scanner',
  'chappie',
  'empat',
  'producer',
]
