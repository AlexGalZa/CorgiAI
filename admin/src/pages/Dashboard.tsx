import { useAuthStore } from '@/stores/auth'
import OperationsDashboard from '@/components/dashboards/OperationsDashboard'
import BrokerDashboard from '@/components/dashboards/BrokerDashboard'
import FinanceDashboard from '@/components/dashboards/FinanceDashboard'
import BDRDashboard from '@/components/dashboards/BDRDashboard'
import ClaimsAdjusterDashboard from '@/components/dashboards/ClaimsAdjusterDashboard'
import CustomerSupportDashboard from '@/components/dashboards/CustomerSupportDashboard'
import { AEDashboard, AEUnderwritingDashboard } from '@/components/dashboards/AEDashboard'

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const role = user?.role

  switch (role) {
    case 'bdr':
      return <BDRDashboard />
    case 'broker':
      return <BrokerDashboard />
    case 'finance':
      return <FinanceDashboard />
    case 'claims_adjuster':
      return <ClaimsAdjusterDashboard />
    case 'customer_support':
      return <CustomerSupportDashboard />
    case 'ae':
      return <AEDashboard />
    case 'ae_underwriting':
      return <AEUnderwritingDashboard />
    case 'admin':
      return <OperationsDashboard />
    default:
      return <OperationsDashboard />
  }
}
