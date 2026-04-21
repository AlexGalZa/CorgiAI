import { cn } from '@/lib/utils'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface LabelProps {
  htmlFor?: string
  required?: boolean
  children: React.ReactNode
  className?: string
  hint?: string
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function Label({
  htmlFor,
  required = false,
  children,
  className,
  hint,
}: LabelProps) {
  return (
    <label
      htmlFor={htmlFor}
      className={cn('mb-1.5 block text-sm font-medium text-gray-700', className)}
    >
      <span className="inline-flex items-center gap-1.5">
        {children}
        {required && (
          <span className="inline-block h-1 w-1 rounded-full bg-primary-500" />
        )}
        {hint && (
          <span className="text-xs font-normal text-gray-400">{hint}</span>
        )}
      </span>
    </label>
  )
}
