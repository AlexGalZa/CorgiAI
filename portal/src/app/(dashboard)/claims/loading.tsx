import { Skeleton } from "@/components/ui/skeleton";

export default function ClaimsLoading() {
  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-8 w-64" />
        </div>
        <Skeleton className="h-9 w-32 rounded-xl" />
      </div>

      {/* Stats strip */}
      <div className="flex gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex-1 border border-border rounded-2xl px-5 py-4 flex flex-col gap-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-6 w-10" />
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="border border-border rounded-2xl overflow-hidden">
        <div className="px-6 py-3 bg-bg border-b border-border flex gap-6">
          {[140, 120, 80, 80, 80, 50].map((w, i) => (
            <Skeleton key={i} className="h-3" style={{ width: w }} />
          ))}
        </div>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="px-6 py-4 border-b border-border flex gap-6 items-center">
            <Skeleton className="w-10 h-10 rounded-xl shrink-0" />
            <div className="flex-1 flex gap-6">
              {[140, 100, 70, 80, 80].map((w, j) => (
                <Skeleton key={j} className="h-4" style={{ width: w }} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
