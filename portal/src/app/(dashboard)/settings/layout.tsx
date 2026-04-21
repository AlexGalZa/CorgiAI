'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const SETTINGS_NAV = [
  { href: '/settings/profile', label: 'Profile' },
  { href: '/settings/security', label: 'Security' },
  { href: '/settings/notifications', label: 'Notifications' },
] as const;

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10">
      {/* Page header */}
      <div className="mb-6 md:mb-8">
        <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
          Account
        </span>
        <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none mt-1">
          Settings
        </h1>
      </div>

      <div className="flex flex-col md:flex-row gap-6 md:gap-10">
        {/* Sub-navigation: row on mobile, sidebar on desktop */}
        <nav
          aria-label="Settings navigation"
          className="flex flex-row md:flex-col gap-1 md:w-[180px] md:shrink-0 overflow-x-auto pb-1 md:pb-0"
        >
          {SETTINGS_NAV.map(({ href, label }) => {
            const active = pathname === href || pathname.startsWith(href + '/');
            return (
              <Link
                key={href}
                href={href}
                className={[
                  'rounded-lg px-3 py-2 text-sm font-medium no-underline whitespace-nowrap transition-colors',
                  'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none',
                  active
                    ? 'bg-[rgba(255,222,204,0.5)] dark:bg-[rgba(255,92,0,0.15)] text-primary font-semibold'
                    : 'text-body hover:bg-[var(--color-bg-hover)]',
                ].join(' ')}
              >
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Content */}
        <div className="flex-1 min-w-0">{children}</div>
      </div>
    </div>
  );
}
