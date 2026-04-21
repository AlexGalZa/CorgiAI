export function LoadingSkeleton() {
  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-6 md:gap-8 animate-pulse">
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-2">
          <div className="h-3 w-16 bg-border rounded" />
          <div className="h-8 w-48 bg-border rounded" />
        </div>
        <div className="h-9 w-32 bg-border rounded-xl" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-surface border border-border rounded-2xl px-6 py-5 flex flex-col gap-2">
            <div className="h-3 w-20 bg-border rounded" />
            <div className="h-6 w-12 bg-border rounded" />
            <div className="h-3 w-24 bg-border rounded" />
          </div>
        ))}
      </div>
      <div className="h-48 bg-border rounded-2xl" />
    </div>
  );
}
