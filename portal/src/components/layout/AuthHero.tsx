import Link from 'next/link';
import { CorgiLogo } from '@/components/icons';
import PartnersStrip from '@/components/layout/PartnersStrip';

interface AuthHeroProps {
  children: React.ReactNode;
  heroImageSrc?: string;
  heroImageAlt?: string;
  /**
   * Optional content rendered under the illustration in the right
   * column on lg+ viewports (e.g. value-prop bullets, testimonial).
   * Hidden on mobile alongside the illustration.
   */
  rightColumnExtra?: React.ReactNode;
}

/**
 * Shared layout for public / unauthenticated pages (get-started, login,
 * register, verify-code). Two-column from `lg:` (1024px+): form on the
 * left, brand hero on the right. Below `lg:` the hero hides and the
 * form takes the full column.
 *
 * Drop the hero illustration at `public/corgi-hero.webp` (or pass a
 * custom `heroImageSrc`). The <img> hides itself if the file is
 * missing so we never ship a broken icon.
 *
 * The root is its own full-viewport scroll container so auth/quote
 * routes scroll correctly even when the dashboard's root <body> is
 * `overflow-hidden`.
 */
export default function AuthHero({
  children,
  heroImageSrc = '/corgi-hero.webp',
  heroImageAlt = 'Corgi mascot',
  rightColumnExtra,
}: AuthHeroProps) {
  return (
    <div className="fixed inset-0 overflow-y-auto bg-bg flex flex-col font-sans">
      <header className="shrink-0 flex items-center justify-between px-5 sm:px-8 lg:px-12 h-14 border-b border-border bg-surface">
        <Link href="/" className="inline-flex items-center no-underline">
          <CorgiLogo className="h-6 w-auto" />
        </Link>
        <Link
          href="https://corgi.insure/help"
          className="text-sm font-medium text-body no-underline hover:text-heading transition-colors"
        >
          Help
        </Link>
      </header>

      <main className="flex-1 flex w-full">
        <div className="w-full max-w-[1280px] mx-auto px-5 sm:px-8 lg:px-12 py-4 lg:py-6 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-6 lg:gap-10 items-center">
          <section className="w-full max-w-[440px] mx-auto lg:mx-0 lg:ml-auto">
            {children}
          </section>
          <aside className="hidden lg:flex flex-col items-center lg:items-start gap-4">
            <img
              src={heroImageSrc}
              alt={heroImageAlt}
              className="w-full max-w-[360px] h-auto select-none pointer-events-none animate-enter"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
            {rightColumnExtra && (
              <div className="w-full max-w-[360px]">{rightColumnExtra}</div>
            )}
          </aside>
        </div>
      </main>

      <footer className="shrink-0 py-4 md:py-5 px-5 border-t border-border/60">
        <PartnersStrip />
      </footer>
    </div>
  );
}
