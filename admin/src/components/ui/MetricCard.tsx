import { type LucideIcon, TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: LucideIcon
  trend?: 'up' | 'down'
  trendValue?: string
  isLoading?: boolean
  /** Optional override for the icon background. Defaults to primary. */
  accent?: 'primary' | 'emerald' | 'amber' | 'red' | 'sky'
  /** Optional 0-100 progress bar below the value. */
  progress?: number
  className?: string
}

const accentMap = {
  primary: { bg: 'bg-orange-50',  text: 'text-[#ff5c00]', bar: 'bg-[#ff5c00]' },
  emerald: { bg: 'bg-emerald-50', text: 'text-emerald-600', bar: 'bg-emerald-500' },
  amber:   { bg: 'bg-amber-50',   text: 'text-amber-600', bar: 'bg-amber-500' },
  red:     { bg: 'bg-red-50',     text: 'text-red-600', bar: 'bg-red-500' },
  sky:     { bg: 'bg-sky-50',     text: 'text-sky-600', bar: 'bg-sky-500' },
}

function Skeleton() {
  return (
    <div className="animate-pulse">
      <div className="mb-3 h-3.5 w-24 rounded bg-gray-200" />
      <div className="mb-2 h-8 w-20 rounded bg-gray-200" />
      <div className="h-3.5 w-32 rounded bg-gray-100" />
    </div>
  )
}

export default function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  trendValue,
  isLoading = false,
  accent = 'primary',
  progress,
  className,
}: MetricCardProps) {
  const { bg, text, bar } = accentMap[accent]

  return (
    <div
      className={cn(
        'overflow-hidden rounded-xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5',
        className,
      )}
    >
      {isLoading ? (
        <Skeleton />
      ) : (
        <>
          {/* Header */}
          <p className="truncate text-xs font-medium uppercase tracking-wide text-gray-500">
            {title}
          </p>

          {/* Value */}
          <p className="mt-2 truncate text-xl font-bold tracking-tight text-gray-900 sm:text-2xl">
            {value}
          </p>

          {/* Subtitle / trend */}
          <div className="mt-1 flex items-center gap-2">
            {trend && trendValue && (
              <span
                className={cn(
                  'inline-flex shrink-0 items-center gap-0.5 text-xs font-medium',
                  trend === 'up' ? 'text-emerald-600' : 'text-red-600',
                )}
              >
                {trend === 'up' ? (
                  <TrendingUp className="h-3 w-3" />
                ) : (
                  <TrendingDown className="h-3 w-3" />
                )}
                {trendValue}
              </span>
            )}
            {subtitle && (
              <span className="truncate text-xs text-gray-500">{subtitle}</span>
            )}
          </div>

          {/* Progress bar */}
          {progress !== undefined && (
            <div className="mt-3">
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
                <div
                  className={cn('h-full rounded-full transition-all', bar)}
                  style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
                />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
