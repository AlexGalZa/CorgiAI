'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  ShieldIcon, CertificateIcon, ClaimsIcon, DocumentsIcon,
  BillingIcon, QuotesIcon, OrganizationIcon, ActivityIcon,
  ChevronUpIcon, HelpCircleIcon, CorgiLogo,
} from '@/components/icons';
import { useAppStore } from '@/stores/use-app-store';
import { useOrgStore } from '@/stores/use-org-store';
import { BtnDark } from '@/components/ui/button';
import type { User } from '@/stores/use-auth-store';

const NAV_ITEMS = [
  { href: '/', label: 'Coverage', icon: ShieldIcon },
  { href: '/certificates', label: 'Certificates', icon: CertificateIcon },
  { href: '/billing', label: 'Billing', icon: BillingIcon },
  { href: '/documents', label: 'Documents', icon: DocumentsIcon },
  { href: '/claims', label: 'Claims', icon: ClaimsIcon },
  { href: '/quotes', label: 'Quotes', icon: QuotesIcon },
  { href: '/organization', label: 'Organization', icon: OrganizationIcon },
  { href: '/activity', label: 'Activity', icon: ActivityIcon },
] as const;

function getInitials(user: User | null): string {
  if (!user) return '?';
  const f = user.first_name?.[0] || '';
  const l = user.last_name?.[0] || '';
  return (f + l).toUpperCase() || user.email[0].toUpperCase();
}

function getDisplayName(user: User | null): string {
  if (!user) return 'User';
  if (user.first_name || user.last_name) return `${user.first_name} ${user.last_name}`.trim();
  return user.email;
}

interface SidebarProps {
  user?: User | null;
}

function useIsMobile() {
  // Always return false on the server AND on the first client render so SSR
  // markup matches hydration. We only flip to the real value after mount via
  // an effect — this prevents hydration-mismatch warnings when a mobile client
  // re-hydrates a layout that was rendered with desktop defaults on the server.
  const [isMobile, setIsMobile] = useState(false);
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);
  return mounted ? isMobile : false;
}

export default function Sidebar({ user }: SidebarProps) {
  const pathname = usePathname();
  const isMobile = useIsMobile();
  const { sidebarOpen, toggleAccountPopup, accountPopupOpen, setMobileSidebarOpen } = useAppStore();
  // On mobile overlay, sidebar is always expanded regardless of desktop collapsed state
  const collapsed = isMobile ? false : !sidebarOpen;
  const { organizations, activeOrgId, setActiveOrgId } = useOrgStore();
  const [orgPopupOpen, setOrgPopupOpen] = useState(false);
  const activeOrg = organizations.find((o) => o.id === activeOrgId);
  const orgName = activeOrg?.name || user?.company_name || 'My Organization';

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  return (
    <aside className={`shrink-0 flex flex-col bg-[var(--color-sidebar-bg)] border-r border-[var(--color-border-raw)] overflow-y-auto h-screen transition-[width] duration-200 ${collapsed ? 'w-[64px]' : 'w-[280px]'}`}>
      {/* Logo */}
      <div className="h-16 shrink-0 border-b border-[var(--color-border-raw)] flex items-center justify-center px-2">
        <Link href="/" className="flex items-center no-underline">
          {collapsed ? (
            <img src="/corgi-icon.svg" alt="Corgi" className="h-7 w-7 object-contain" />
          ) : (
            <CorgiLogo className="h-[34px] w-[115px]" />
          )}
        </Link>
      </div>

      {/* Combined User + Organization — at the top */}
      {!collapsed && (
        <div className="p-4 border-b border-[var(--color-border-raw)] relative z-30">
          <button
            onClick={() => setOrgPopupOpen(!orgPopupOpen)}
            aria-expanded={orgPopupOpen}
            aria-label="Account and organization"
            className="flex items-center gap-3 bg-[var(--color-sidebar-bg)] border border-[var(--color-border-raw)] rounded-lg py-2.5 px-3 cursor-pointer w-full transition-colors font-sans hover:bg-[var(--color-bg-hover)]"
          >
            <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-[11px] font-medium text-white shrink-0">
              {getInitials(user ?? null)}
            </div>
            <div className="flex flex-col items-start min-w-0 flex-1">
              <span className="text-sm font-medium text-[var(--color-heading-raw)] truncate w-full text-left">{getDisplayName(user ?? null)}</span>
              <span className="text-[11px] text-[var(--color-muted-raw)] truncate w-full text-left">{orgName}</span>
            </div>
            <ChevronUpIcon className={`w-3.5 h-3.5 text-[var(--color-muted-raw)] shrink-0 transition-transform ${orgPopupOpen ? '' : 'rotate-180'}`} />
          </button>

          {orgPopupOpen && (
            <>
              <div className="fixed inset-0 z-20" onClick={() => setOrgPopupOpen(false)} />
              <div className="absolute left-4 right-4 mt-1 bg-[var(--color-popup-bg)] border border-[var(--color-border-raw)] rounded-lg shadow-lg z-30 overflow-hidden">
                {organizations.length > 0 && (<div className="p-1.5">
                  <div className="text-[10px] font-semibold text-[var(--color-muted-raw)] tracking-[0.5px] uppercase px-2.5 py-1.5">Organizations</div>
                  {organizations.map((org) => (
                    <button
                      key={org.id}
                      onClick={() => { setActiveOrgId(org.id); setOrgPopupOpen(false); }}
                      className={`flex items-center justify-between w-full px-2.5 py-2.5 rounded-lg cursor-pointer border-none font-sans text-left transition-colors ${org.id === activeOrgId ? 'bg-[var(--color-bg-hover)]' : 'hover:bg-[var(--color-bg-hover)]'}`}
                    >
                      <div className="flex items-center gap-2.5">
                        {org.id === activeOrgId ? (
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-primary"><path d="M20 6 9 17l-5-5"/></svg>
                        ) : (
                          <div className="w-4 h-4" />
                        )}
                        <span className="text-sm font-medium text-[var(--color-heading-raw)]">{org.name}</span>
                      </div>
                    </button>
                  ))}
                </div>)}
                <div className={`${organizations.length > 0 ? 'border-t border-[var(--color-border-raw)]' : ''} p-1.5`}>
                  <Link href="/organization" onClick={() => setOrgPopupOpen(false)} className="flex items-center gap-2.5 px-2.5 py-2.5 rounded-lg text-sm text-[var(--color-body-raw)] no-underline hover:bg-[var(--color-bg-hover)] transition-colors">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
                    Create organization
                  </Link>
                  <div className="border-t border-[var(--color-border-raw)] mt-1 pt-1">
                    <Link
                      href="/settings"
                      onClick={() => setOrgPopupOpen(false)}
                      className="flex items-center gap-2.5 px-2.5 py-2.5 rounded-lg text-sm text-[var(--color-body-raw)] hover:bg-[var(--color-bg-hover)] transition-colors w-full no-underline focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                      Account settings
                    </Link>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Navigation + CTA */}
      <div className={`flex-1 flex flex-col justify-between overflow-y-auto sidebar-scroll ${collapsed ? 'p-2' : 'p-4'}`}>
        <nav role="navigation" aria-label="Main navigation" className="flex flex-col gap-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                title={collapsed ? label : undefined}
                aria-current={active ? 'page' : undefined}
                onClick={() => isMobile && setMobileSidebarOpen(false)}
                className={`flex items-center rounded-lg no-underline ${
                  collapsed
                    ? `justify-center py-3 px-2 ${active ? 'bg-[rgba(255,222,204,0.5)] dark:bg-[rgba(255,92,0,0.15)]' : 'hover:bg-[var(--color-bg-hover)]'}`
                    : `gap-3 py-3 px-4 text-[15px] font-normal tracking-normal leading-[1.2] ${active ? 'bg-[rgba(255,222,204,0.5)] dark:bg-[rgba(255,92,0,0.15)] text-primary font-semibold' : 'text-[var(--color-body-raw)] hover:bg-[var(--color-bg-hover)]'}`
                }`}
              >
                <Icon className={`w-[18px] h-[18px] shrink-0 ${active ? 'stroke-primary stroke-[2.4]' : 'stroke-current stroke-[1.6]'}`} />
                {!collapsed && label}
              </Link>
            );
          })}
        </nav>

        {/* CTA Card — hidden when collapsed */}
        {!collapsed && (
          <div className="border border-[var(--color-border-raw)] rounded-2xl overflow-hidden mt-auto bg-[var(--color-sidebar-bg)]">
            <div className="p-5 flex flex-col gap-2">
              <span className="text-sm font-semibold text-[var(--color-heading-raw)] leading-[1.3]">Need more coverage?</span>
              <span className="text-xs text-[var(--color-muted-raw)] leading-[1.4]">Explore tailored policies for your business stage.</span>
            </div>
            <div className="px-3 pb-3">
              <BtnDark fullWidth>
                <Link href="/quotes" className="flex items-center text-white no-underline w-full justify-center">
                  Get a quote
                </Link>
              </BtnDark>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className={`border-t border-[var(--color-border-raw)] flex flex-col gap-1 bg-[var(--color-sidebar-bg)] ${collapsed ? 'p-2' : 'p-4'}`}>
        {!collapsed && (
          <Link
            href="/help"
            className="flex items-center gap-2 text-xs font-normal text-[var(--color-body-raw)] tracking-normal leading-[1.2] no-underline py-3 px-3 rounded-lg transition-all hover:text-[var(--color-heading-raw)] hover:bg-[var(--color-bg-hover)] focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
          >
            <HelpCircleIcon size={16} />
            Help
          </Link>
        )}
        {collapsed && (
          <div
            className="flex items-center justify-center cursor-pointer rounded-lg transition-colors hover:bg-[var(--color-bg-hover)] py-2 px-1"
            onClick={toggleAccountPopup}
            title={getDisplayName(user ?? null)}
          >
            <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center text-[10px] font-medium text-white shrink-0">
              {getInitials(user ?? null)}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
