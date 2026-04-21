import { Skeleton } from "@/components/ui/skeleton";

export default function QuotesLoading() {
  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-2">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-8 w-64" />
        </div>
      </div>

      {/* Coverage type cards grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="border border-border rounded-2xl overflow-hidden">
            <Skeleton className="h-[90px] w-full rounded-none" />
            <div className="p-4 flex flex-col gap-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-20 mt-2" />
            </div>
          </div>
        ))}
      </div>

      {/* CTA banner */}
      <Skeleton className="h-16 w-full rounded-xl" />
    </div>
  );
}
