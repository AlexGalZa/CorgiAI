import { Outlet } from 'react-router-dom'
import { Toaster } from 'sonner'
import Sidebar from '@/components/layout/Sidebar'
import TopBar from '@/components/layout/TopBar'
import ImpersonationBanner from '@/components/layout/ImpersonationBanner'

export default function AppLayout() {
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#f9f9f9]">
      <ImpersonationBanner />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <TopBar />
          <main className="flex-1 overflow-y-auto px-4 py-4 sm:px-6 sm:py-5">
            <Outlet />
          </main>
        </div>
      </div>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            fontFamily: 'var(--font-sans)',
            fontSize: '13px',
          },
        }}
      />
    </div>
  )
}
