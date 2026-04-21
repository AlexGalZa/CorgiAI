import Link from 'next/link';
import type { ReactNode } from 'react';

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen bg-bg">
      <header className="shrink-0 border-b border-border bg-surface">
        <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-4 flex items-center justify-between">
          <Link
            href="/"
            className="font-heading text-xl font-medium text-heading tracking-[-0.5px] no-underline"
          >
            Corgi Insurance
          </Link>
          <nav className="flex items-center gap-4 sm:gap-6 text-sm font-medium text-body">
            <Link href="/legal" className="hover:text-heading no-underline">
              Legal
            </Link>
            <Link href="/disclaimers" className="hover:text-heading no-underline">
              Disclaimers
            </Link>
            <Link href="/broker-licenses" className="hover:text-heading no-underline">
              Licenses
            </Link>
          </nav>
        </div>
      </header>

      <main
        id="main-content"
        className="flex-1 overflow-y-auto"
      >
        {children}
      </main>

      <footer className="shrink-0 border-t border-border bg-surface">
        <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-muted">
          {/* suppressHydrationWarning: year is computed at request time; if
              the build is cached across a year boundary the client re-render
              may differ. Cosmetic, so suppress instead of forcing JS hydration. */}
          <span suppressHydrationWarning>
            &copy; {new Date().getFullYear()} Corgi Insurance Services, Inc. All rights reserved.
          </span>
          <div className="flex items-center gap-4">
            <Link href="/legal" className="hover:text-heading no-underline">
              Terms
            </Link>
            <Link href="/disclaimers" className="hover:text-heading no-underline">
              Disclaimers
            </Link>
            <Link href="/broker-licenses" className="hover:text-heading no-underline">
              Broker licenses
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
