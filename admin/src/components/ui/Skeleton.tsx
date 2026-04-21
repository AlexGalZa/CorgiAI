import type { HTMLAttributes } from 'react'

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(' ')
}

// ---------- Base ----------

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  className?: string
}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn('animate-pulse rounded bg-gray-200', className)}
      {...props}
    />
  )
}

// ---------- Lines ----------

export function SkeletonLine({ width = '100%', className }: { width?: string; className?: string }) {
  return <Skeleton className={cn('h-4', className)} style={{ width }} />
}

// ---------- Cards ----------

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn('rounded-xl border border-gray-200 bg-white p-6 space-y-4', className)}>
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-6 w-14 rounded-full" />
      </div>
      <Skeleton className="h-8 w-20" />
      <div className="space-y-2">
        <SkeletonLine width="85%" />
        <SkeletonLine width="60%" />
      </div>
    </div>
  )
}

// ---------- Metric cards ----------

export function SkeletonMetricCard() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-7 w-16" />
      <Skeleton className="h-3 w-32" />
    </div>
  )
}

// ---------- Table ----------

export function SkeletonTable({
  rows = 5,
  columns = 4,
  className,
}: {
  rows?: number
  columns?: number
  className?: string
}) {
  return (
    <div className={cn('w-full', className)}>
      <div className="flex gap-4 border-b border-gray-200 pb-3 mb-3">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={`h-${i}`} className="h-4 flex-1" />
        ))}
      </div>
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, row) => (
          <div key={`r-${row}`} className="flex gap-4">
            {Array.from({ length: columns }).map((_, col) => (
              <Skeleton key={`c-${row}-${col}`} className="h-4 flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------- Page ----------

export function SkeletonPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonMetricCard key={i} />
        ))}
      </div>
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <SkeletonTable rows={8} columns={5} />
      </div>
    </div>
  )
}
