'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Header from '@/components/layout/header';
import Sidebar from '@/components/layout/sidebar';
import AccountPopup from '@/components/layout/account-popup';
import Toast from '@/components/ui/toast';
import { useAuthStore } from '@/stores/use-auth-store';
import { useAppStore } from '@/stores/use-app-store';
import WelcomeWizard from '@/components/onboarding/WelcomeWizard';
import SupportWidget from '@/components/ui/SupportWidget';
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts';
import { authApi } from '@/lib/api';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, user, logout, setAuth } = useAuthStore();
  const { sidebarOpen, mobileSidebarOpen, setMobileSidebarOpen } = useAppStore();
  const [stoppingImpersonation, setStoppingImpersonation] = useState(false);
  useKeyboardShortcuts();

  const isImpersonated = user?.is_impersonated === true;

  const stopImpersonation = async () => {
    setStoppingImpersonation(true);
    try {
      const res = await authApi<{ data: { user: unknown; tokens: unknown } }>(
        '/api/v1/users/stop-impersonation',
        { method: 'POST' }
      );
      if (res?.data) {
        const { user: adminUser, tokens } = res.data as { user: Parameters<typeof setAuth>[0]; tokens: Parameters<typeof setAuth>[1] };
        setAuth(adminUser, tokens);
        router.push('/');
      }
    } catch {
      logout();
      router.push('/login');
    } finally {
      setStoppingImpersonation(false);
    }
  };

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace('/login');
    }
  }, [isAuthenticated, router]);

  // Close mobile sidebar on route change
  useEffect(() => {
    setMobileSidebarOpen(false);
  }, [pathname, setMobileSidebarOpen]);

  if (!isAuthenticated) return null;

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Impersonation banner */}
      {isImpersonated && (
        <div className="shrink-0 w-full bg-amber-500 text-white flex items-center justify-between px-4 py-2 z-50">
          <div className="flex items-center gap-2 text-sm font-medium">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
            </svg>
            Viewing as <strong className="ml-1">{user?.email}</strong>
            <span className="text-amber-200 font-normal ml-1">— you are impersonating this account</span>
          </div>
          <button
            onClick={stopImpersonation}
            disabled={stoppingImpersonation}
            className="shrink-0 text-sm font-semibold bg-white text-amber-700 rounded-lg px-3 py-1 border-none cursor-pointer hover:bg-amber-50 transition-colors disabled:opacity-60"
          >
            {stoppingImpersonation ? 'Stopping…' : 'Stop impersonating'}
          </button>
        </div>
      )}
    <div className="flex flex-1 overflow-hidden">
      {/* Desktop sidebar */}
      <div
        className="hidden md:block shrink-0 transition-[width] duration-200 ease-in-out overflow-hidden"
        style={{ width: sidebarOpen ? 280 : 64 }}
      >
        <Sidebar user={user} />
      </div>

      {/* Mobile sidebar overlay */}
      {mobileSidebarOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/50 z-40 transition-opacity"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}
      <div
        className={`md:hidden fixed inset-y-0 left-0 z-50 w-[280px] transition-transform duration-300 ease-in-out ${
          mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <Sidebar user={user} />
      </div>

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Header user={user} />
        <main id="main-content" className="flex-1 overflow-y-auto bg-bg main-scroll">
          <div key={pathname} className="animate-enter">
            {children}
          </div>
        </main>
      </div>
      <AccountPopup />
      <Toast />
      <WelcomeWizard />
      <SupportWidget />
    </div>
    </div>
  );
}
