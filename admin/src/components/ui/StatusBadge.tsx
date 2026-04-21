import { cn } from '@/lib/utils'

type Variant = 'brokerage' | 'policy' | 'claim' | 'payment'

interface StatusBadgeProps {
  status: string
  variant?: Variant
  className?: string
}

// Each status gets a unique color so no two look the same at a glance.
// Format: [dotColor, bgColor, textColor]
type BadgeStyle = [string, string, string]

const brokerageStyles: Record<string, BadgeStyle> = {
  received:  ['bg-sky-500',     'bg-sky-50',     'text-sky-700'],
  submitted: ['bg-amber-500',   'bg-amber-50',   'text-amber-700'],
  otm:       ['bg-violet-500',  'bg-violet-50',  'text-violet-700'],
  quoted:    ['bg-teal-500',    'bg-teal-50',    'text-teal-700'],
  on_hold:   ['bg-orange-500',  'bg-orange-50',  'text-orange-700'],
  denied:    ['bg-red-500',     'bg-red-50',     'text-red-700'],
  recalled:  ['bg-gray-400',    'bg-gray-100',   'text-gray-600'],
  blocked:   ['bg-rose-500',    'bg-rose-50',    'text-rose-700'],
  stalled:   ['bg-yellow-500',  'bg-yellow-50',  'text-yellow-700'],
  cancelled: ['bg-gray-400',    'bg-gray-100',   'text-gray-500'],
  bound:     ['bg-emerald-500', 'bg-emerald-50', 'text-emerald-700'],
}

const policyStyles: Record<string, BadgeStyle> = {
  active:    ['bg-emerald-500', 'bg-emerald-50', 'text-emerald-700'],
  expired:   ['bg-gray-400',    'bg-gray-100',   'text-gray-600'],
  cancelled: ['bg-red-500',     'bg-red-50',     'text-red-700'],
  pending:   ['bg-amber-500',   'bg-amber-50',   'text-amber-700'],
}

const claimStyles: Record<string, BadgeStyle> = {
  filed:         ['bg-sky-500',     'bg-sky-50',     'text-sky-700'],
  under_review:  ['bg-amber-500',   'bg-amber-50',   'text-amber-700'],
  investigation: ['bg-orange-500',  'bg-orange-50',  'text-orange-700'],
  resolved:      ['bg-emerald-500', 'bg-emerald-50', 'text-emerald-700'],
  denied:        ['bg-red-500',     'bg-red-50',     'text-red-700'],
  closed:        ['bg-gray-400',    'bg-gray-100',   'text-gray-600'],
}

const paymentStyles: Record<string, BadgeStyle> = {
  pending:  ['bg-amber-500',   'bg-amber-50',   'text-amber-700'],
  paid:     ['bg-emerald-500', 'bg-emerald-50', 'text-emerald-700'],
  failed:   ['bg-red-500',     'bg-red-50',     'text-red-700'],
  refunded: ['bg-violet-500',  'bg-violet-50',  'text-violet-700'],
}

const styleMaps: Record<Variant, Record<string, BadgeStyle>> = {
  brokerage: brokerageStyles,
  policy: policyStyles,
  claim: claimStyles,
  payment: paymentStyles,
}

const fallback: BadgeStyle = ['bg-gray-400', 'bg-gray-100', 'text-gray-600']

function getStyle(status: string, variant?: Variant): BadgeStyle {
  const normalized = status.toLowerCase().replace(/\s+/g, '_')
  if (variant && styleMaps[variant]) {
    return styleMaps[variant][normalized] ?? fallback
  }
  for (const map of Object.values(styleMaps)) {
    if (map[normalized]) return map[normalized]
  }
  return fallback
}

function formatLabel(status: string): string {
  return status
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function StatusBadge({ status, variant, className }: StatusBadgeProps) {
  const [dot, bg, text] = getStyle(status, variant)
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
        bg,
        text,
        className,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', dot)} />
      {formatLabel(status)}
    </span>
  )
}
