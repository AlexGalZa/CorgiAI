import { type LucideIcon, Inbox } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon?: LucideIcon
  title?: string
  message?: string
  action?: React.ReactNode
  className?: string
}

export default function EmptyState({
  icon: Icon = Inbox,
  title = 'Nothing here yet',
  message,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-16 text-center', className)}>
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
        <Icon className="h-6 w-6 text-gray-400" />
      </div>
      <p className="text-sm font-medium text-gray-900">{title}</p>
      {message && (
        <p className="mt-1 max-w-sm text-sm text-gray-500">{message}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
