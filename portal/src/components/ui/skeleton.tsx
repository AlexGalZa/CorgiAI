import { type HTMLAttributes } from "react";

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

// ---------- Base skeleton ----------

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  className?: string;
}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn("animate-pulse rounded bg-gray-100", className)}
      {...props}
    />
  );
}

// ---------- SkeletonLine ----------

export function SkeletonLine({
  width = "100%",
  className,
}: {
  width?: string;
  className?: string;
}) {
  return <Skeleton className={cn("h-4", className)} style={{ width }} />;
}

// ---------- SkeletonCard ----------

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-xl border border-gray-200 p-6 space-y-4", className)}>
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
      <div className="space-y-2">
        <SkeletonLine width="90%" />
        <SkeletonLine width="70%" />
        <SkeletonLine width="80%" />
      </div>
      <div className="flex gap-3 pt-2">
        <Skeleton className="h-9 w-24 rounded-lg" />
        <Skeleton className="h-9 w-24 rounded-lg" />
      </div>
    </div>
  );
}

// ---------- SkeletonTable ----------

export function SkeletonTable({
  rows = 5,
  columns = 4,
  className,
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) {
  return (
    <div className={cn("w-full", className)}>
      {/* Header */}
      <div className="flex gap-4 border-b border-gray-200 pb-3 mb-3">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={`h-${i}`} className="h-4 flex-1" />
        ))}
      </div>

      {/* Rows */}
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
  );
}

// ---------- SkeletonPage ----------

export function SkeletonPage() {
  return (
    <div className="space-y-6 p-6">
      {/* Page header */}
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>

      {/* Metric cards row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-gray-200 p-5 space-y-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-7 w-16" />
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="rounded-xl border border-gray-200 p-6">
        <SkeletonTable rows={8} columns={5} />
      </div>
    </div>
  );
}
