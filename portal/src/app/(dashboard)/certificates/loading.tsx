import { Skeleton } from "@/components/ui/skeleton";

export default function CertificatesLoading() {
  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-2">
          <Skeleton className="h-3 w-36" />
          <Skeleton className="h-8 w-56" />
        </div>
        <Skeleton className="h-9 w-36 rounded-xl" />
      </div>

      {/* Stats strip */}
      <div className="flex gap-4">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="border border-border rounded-2xl px-6 py-4 flex flex-col gap-1.5 flex-1">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-6 w-12" />
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="border border-border rounded-2xl overflow-hidden">
        <div className="px-6 py-3 bg-bg border-b border-border grid grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-3 w-full" />
          ))}
        </div>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="px-6 py-4 border-b border-border grid grid-cols-6 gap-4">
            <div className="flex flex-col gap-1.5">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-3 w-20" />
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-5 w-14 rounded-full" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-8" />
          </div>
        ))}
      </div>
    </div>
  );
}
