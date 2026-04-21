import { AlertTriangle, RefreshCw } from 'lucide-react'

interface QueryErrorProps {
  message?: string
  onRetry?: () => void
}

export default function QueryError({ message, onRetry }: QueryErrorProps) {
  return (
    <div className="flex min-h-[300px] items-center justify-center p-8">
      <div className="text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
          <AlertTriangle className="h-5 w-5 text-red-600" />
        </div>
        <h3 className="text-sm font-semibold text-gray-900">Something went wrong</h3>
        <p className="mt-1 max-w-sm text-sm text-gray-500">
          {message || 'Failed to load data. Please try again.'}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#ea580c]"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </button>
        )}
      </div>
    </div>
  )
}
