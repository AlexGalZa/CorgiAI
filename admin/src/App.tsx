import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { useAuthStore } from '@/stores/auth'
import ErrorBoundary from '@/components/ui/ErrorBoundary'
import CommandPalette from '@/components/ui/CommandPalette'
import AppLayout from '@/components/layout/AppLayout'
import Login from '@/pages/Login'
import NotFoundPage from '@/pages/NotFound'
import DashboardPage from '@/pages/Dashboard'
import BrokeredRequestsPage from '@/pages/BrokeredRequests'
import PipelinePage from '@/pages/Pipeline'
import QuotesPage from '@/pages/Quotes'
import QuoteDetailPage from '@/pages/QuoteDetail'
import PoliciesPage from '@/pages/Policies'
import PolicyDetailPage from '@/pages/PolicyDetail'
import ClaimsPage from '@/pages/Claims'
import ClaimDetailPage from '@/pages/ClaimDetail'
import PaymentsPage from '@/pages/Payments'
import CertificatesPage from '@/pages/Certificates'
import UsersPage from '@/pages/Users'
import ProducersPage from '@/pages/Producers'
import ReportsPage from '@/pages/Reports'
import OrganizationsPage from '@/pages/Organizations'
import ProfilePage from '@/pages/Profile'
import FormBuilderPage from '@/pages/FormBuilder'
import CommissionsPage from '@/pages/Commissions'
import SalesMetricsPage from '@/pages/SalesMetricsPage'
import SalesPerformancePage from '@/pages/SalesPerformancePage'
import FinanceDashboard from '@/pages/FinanceDashboard'
import EntityFinancePage from '@/pages/EntityFinancePage'
import { FINANCE_ROLES, STAFF_ROLES, ALL_INTERNAL_ROLES } from '@/lib/roles'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
})

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function RoleGuard({ allowed, children }: { allowed: readonly string[]; children: React.ReactNode }) {
  const role = useAuthStore((s) => s.user?.role)
  if (!role || !allowed.includes(role)) {
    return <Navigate to="/dashboard" replace />
  }
  return <>{children}</>
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter basename="/ops">
          <CommandPalette />
          <Routes>
            {/* Public */}
            <Route path="/login" element={<Login />} />

            {/* Protected */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="pipeline" element={<RoleGuard allowed={STAFF_ROLES}><PipelinePage /></RoleGuard>} />
              <Route path="brokered-requests" element={<BrokeredRequestsPage />} />
              <Route path="quotes" element={<QuotesPage />} />
              <Route path="quotes/:id" element={<QuoteDetailPage />} />
              <Route path="policies" element={<PoliciesPage />} />
              <Route path="policies/:id" element={<PolicyDetailPage />} />
              <Route path="claims" element={<ClaimsPage />} />
              <Route path="claims/:id" element={<ClaimDetailPage />} />
              <Route path="payments" element={<PaymentsPage />} />
              <Route path="certificates" element={<CertificatesPage />} />
              <Route path="users" element={<RoleGuard allowed={STAFF_ROLES}><UsersPage /></RoleGuard>} />
              <Route path="commissions" element={<RoleGuard allowed={FINANCE_ROLES}><CommissionsPage /></RoleGuard>} />
              <Route path="producers" element={<RoleGuard allowed={FINANCE_ROLES}><ProducersPage /></RoleGuard>} />
              <Route path="reports" element={<RoleGuard allowed={ALL_INTERNAL_ROLES}><ReportsPage /></RoleGuard>} />
              <Route path="organizations" element={<RoleGuard allowed={STAFF_ROLES}><OrganizationsPage /></RoleGuard>} />
              <Route path="form-builder" element={<RoleGuard allowed={STAFF_ROLES}><FormBuilderPage /></RoleGuard>} />
              <Route path="sales-metrics" element={<RoleGuard allowed={STAFF_ROLES}><SalesMetricsPage /></RoleGuard>} />
              <Route path="sales-performance" element={<RoleGuard allowed={STAFF_ROLES}><SalesPerformancePage /></RoleGuard>} />
              <Route path="finance" element={<RoleGuard allowed={FINANCE_ROLES}><FinanceDashboard /></RoleGuard>} />
              <Route path="entity-finance" element={<RoleGuard allowed={FINANCE_ROLES}><EntityFinancePage /></RoleGuard>} />
              <Route path="profile" element={<ProfilePage />} />
            </Route>

            {/* 404 */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
      <Toaster richColors position="top-right" />
    </ErrorBoundary>
  )
}
