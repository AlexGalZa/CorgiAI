import { Skeleton } from "@/components/ui/skeleton";

function PolicyCardSkeleton() {
  return (
    <div className="border border-border rounded-2xl overflow-hidden flex">
      {/* Left column */}
      <div className="w-[240px] shrink-0 p-5 flex flex-col gap-3 border-r border-border">
        <div className="flex items-center gap-2">
          <Skeleton className="w-5 h-5 rounded-full" />
          <Skeleton className="h-3 w-32" />
        </div>
        <Skeleton className="h-5 w-36" />
        <Skeleton className="h-3 w-40" />
        <Skeleton className="h-5 w-14 rounded-full" />
        <Skeleton className="h-[100px] w-full rounded-lg mt-auto" />
      </div>
      {/* Right column */}
      <div className="flex-1 p-5 flex flex-col gap-4">
        <div className="flex gap-16">
          <div className="flex flex-col gap-1.5">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-4 w-44" />
          </div>
          <div className="flex flex-col gap-1.5">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-4 w-16" />
          </div>
        </div>
        <div>
          <Skeleton className="h-3 w-16 mb-3" />
          <div className="border border-border rounded-lg">
            {Array.from({ length: 3 }).map((_, j) => (
              <div key={j} className={`flex items-center justify-between px-4 py-3.5 ${j < 2 ? 'border-b border-border' : ''}`}>
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-4 w-24" />
              </div>
            ))}
          </div>
        </div>
        <div className="flex gap-3 mt-auto">
          <Skeleton className="h-10 w-36 rounded-xl" />
          <Skeleton className="h-10 w-36 rounded-xl" />
          <Skeleton className="h-10 w-28 rounded-xl" />
        </div>
      </div>
    </div>
  );
}

export default function DashboardLoading() {
  return (
    <div className="max-w-[1100px] mx-auto px-12 py-10 flex flex-col gap-8">
      {/* Page header */}
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
            Insurance
          </span>
          <Skeleton className="h-9 w-64" />
        </div>
        <Skeleton className="h-10 w-36 rounded-xl" />
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-surface border border-border rounded-2xl px-6 py-5 flex flex-col gap-2.5">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-7 w-24" />
            <Skeleton className="h-3 w-32" />
          </div>
        ))}
      </div>

      {/* Active policies */}
      <div className="flex flex-col gap-3">
        <div className="pl-4 text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
          Active policies
        </div>
        <PolicyCardSkeleton />
        <PolicyCardSkeleton />
      </div>

      {/* Recommended section */}
      <div className="border border-border rounded-2xl px-6 pt-6 pb-6">
        <div className="flex items-start justify-between mb-6">
          <div className="flex flex-col gap-2">
            <Skeleton className="h-3 w-44" />
            <Skeleton className="h-6 w-72" />
            <Skeleton className="h-6 w-48" />
          </div>
          <Skeleton className="h-10 w-36 rounded-xl" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="bg-white border border-border rounded-2xl overflow-hidden">
              <Skeleton className="h-[160px] w-full rounded-none" />
              <div className="p-4 flex flex-col gap-2.5">
                <Skeleton className="h-4 w-36" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-24 mt-1" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
