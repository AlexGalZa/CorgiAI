import { SpinnerOverlay } from '@/components/ui/Spinner'
import { cn } from '@/lib/utils'

interface ChartCardProps {
  title: string
  subtitle?: string
  isLoading?: boolean
  isEmpty?: boolean
  height?: string
  children: React.ReactNode
  className?: string
  action?: React.ReactNode
}

export default function ChartCard({
  title,
  subtitle,
  isLoading = false,
  isEmpty = false,
  height = 'h-72',
  children,
  className,
  action,
}: ChartCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-gray-200 bg-white p-5 shadow-sm',
        className,
      )}
    >
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
          {subtitle && (
            <p className="mt-0.5 text-xs text-gray-500">{subtitle}</p>
          )}
        </div>
        {action}
      </div>
      <div className={height}>
        {isLoading ? (
          <SpinnerOverlay height="h-full" />
        ) : isEmpty ? (
          <div className="flex h-full items-center justify-center text-sm text-gray-400">
            No data available
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  )
}
