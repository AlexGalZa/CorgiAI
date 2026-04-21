import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-bg flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        {/* Logo */}
        <div className="mb-8">
          <div className="font-heading text-2xl font-bold text-heading tracking-[-0.768px]">corgi</div>
        </div>

        {/* 404 */}
        <div className="font-heading text-[80px] font-bold text-primary leading-none tracking-[-3px] mb-2">
          404
        </div>

        <h1 className="font-heading text-[28px] font-medium text-heading tracking-[-0.896px] leading-none mb-3">
          Page not found.
        </h1>

        <p className="text-sm text-body leading-[1.6] mb-8 max-w-[340px] mx-auto">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
          Let&apos;s get you back on track.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 bg-primary text-white rounded-xl px-6 py-2.5 text-sm font-medium no-underline hover:bg-primary-dark transition-colors"
          >
            Go to Dashboard
          </Link>
          <Link
            href="/quotes"
            className="inline-flex items-center gap-2 bg-white border border-border text-heading rounded-xl px-6 py-2.5 text-sm font-medium no-underline hover:bg-bg transition-colors"
          >
            Explore Coverages
          </Link>
        </div>
      </div>
    </div>
  );
}
