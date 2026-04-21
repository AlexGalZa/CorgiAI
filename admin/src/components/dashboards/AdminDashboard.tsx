/**
 * Admin Dashboard — wraps OperationsDashboard with a Security tab.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import OperationsDashboard from './OperationsDashboard'
import MetricCard from '@/components/ui/MetricCard'
import DataTable, { type Column } from '@/components/ui/DataTable'
import PageHeader from '@/components/ui/PageHeader'
import Pagination from '@/components/ui/Pagination'
import { cn } from '@/lib/utils'
import api from '@/lib/api'
import { formatDate } from '@/lib/formatters'
import { useAuditLog } from '@/hooks/useAuditLog'
import type { AuditEntry } from '@/types'

// ─── Types ───────────────────────────────────────────────────────────────────

interface SecuritySummary {
  total_staff_users: number
  locked_out_count: number
  recent_login_failures: Array<{
    email: string
    failed_attempts: number
    locked_until: string | null
    last_attempt: string | null
  }>
  active_impersonations: Array<{
    id: number
    admin_email: string | null
    target_email: string | null
    started_at: string | null
  }>
  users_with_password_auth: number
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

function useSecuritySummary() {
  return useQuery<SecuritySummary>({
    queryKey: ['analytics', 'security-summary'],
    queryFn: async () => {
      const { data } = await api.get('/admin/analytics/security-summary')
      return data
    },
  })
}

// ─── Tabs ─────────────────────────────────────────────────────────────────────

type Tab = 'dashboard' | 'security'

const TABS: { id: Tab; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'security', label: 'Security' },
]

// ─── Security Panel ───────────────────────────────────────────────────────────

function SecurityPanel() {
  const [auditPage, setAuditPage] = useState(1)
  const securityQ = useSecuritySummary()
  const auditQ = useAuditLog({ limit: 25, offset: (auditPage - 1) * 25 })

  const d = securityQ.data

  const auditCols: Column<AuditEntry>[] = [
    { key: 'timestamp', header: 'Time', render: (r) => formatDate(r.timestamp) },
    { key: 'user_email', header: 'Actor', render: (r) => r.user_email || '—' },
    { key: 'action', header: 'Action' },
    { key: 'entity_type', header: 'Object', render: (r) => `${r.entity_type} #${r.entity_id}` },
    { key: 'field_changed', header: 'Field', render: (r) => r.field_changed || '—' },
    { key: 'old_value', header: 'From', render: (r) => r.old_value || '—' },
    { key: 'new_value', header: 'To', render: (r) => r.new_value || '—' },
  ]

  return (
    <div className="space-y-6">
      {/* Summary metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Staff Users"
          value={d?.total_staff_users ?? 0}
          subtitle="Active internal staff"
          isLoading={securityQ.isLoading}
        />
        <MetricCard
          title="Locked Out"
          value={d?.locked_out_count ?? 0}
          subtitle="Currently locked accounts"
          accent={d?.locked_out_count ? 'red' : 'emerald'}
          isLoading={securityQ.isLoading}
        />
        <MetricCard
          title="Failed Logins"
          value={d?.recent_login_failures?.length ?? 0}
          subtitle="Users with recent failures"
          accent={d?.recent_login_failures?.length ? 'amber' : 'emerald'}
          isLoading={securityQ.isLoading}
        />
        <MetricCard
          title="Active Sessions"
          value={d?.active_impersonations?.length ?? 0}
          subtitle="Active impersonations"
          accent="sky"
          isLoading={securityQ.isLoading}
        />
      </div>

      {/* Recent Login Failures */}
      {(d?.recent_login_failures?.length ?? 0) > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold text-gray-900 flex items-center gap-2">
            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-red-100 text-red-700 text-xs font-bold">!</span>
            Recent Login Failures
          </h2>
          <div className="overflow-hidden rounded-xl border border-red-200 bg-white">
            <table className="w-full text-sm">
              <thead className="border-b border-red-200 bg-red-50">
                <tr>
                  {['Email', 'Failed Attempts', 'Locked Until', 'Last Attempt'].map((h) => (
                    <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-red-700">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {d!.recent_login_failures.map((f, i) => (
                  <tr key={i} className="border-b border-gray-100 last:border-0">
                    <td className="px-4 py-2.5 text-xs text-gray-800">{f.email}</td>
                    <td className="px-4 py-2.5 text-xs font-semibold text-red-600">{f.failed_attempts}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-600">{f.locked_until ? formatDate(f.locked_until) : '—'}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-500">{f.last_attempt ? formatDate(f.last_attempt) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Active Impersonation Sessions */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-900">Active Sessions / Impersonations</h2>
        {(d?.active_impersonations?.length ?? 0) === 0 ? (
          <p className="text-sm text-gray-500">No active impersonation sessions.</p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  {['Admin', 'Impersonating', 'Started'].map((h) => (
                    <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {d!.active_impersonations.map((imp) => (
                  <tr key={imp.id} className="border-b border-gray-100 last:border-0">
                    <td className="px-4 py-2.5 text-xs text-gray-800">{imp.admin_email ?? '—'}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-600">{imp.target_email ?? '—'}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-500">{imp.started_at ? formatDate(imp.started_at) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 2FA Status */}
      <div className="rounded-lg border border-sky-200 bg-sky-50 p-4 text-sm text-sky-800">
        <p className="font-semibold mb-1">Authentication Methods</p>
        <p className="text-xs">
          {d?.users_with_password_auth ?? 0} staff users use password authentication.
          Email OTP (magic link) is available to all users.
          Hardware 2FA (TOTP/FIDO) is not yet configured — consider enabling it for admin accounts.
        </p>
      </div>

      {/* Audit Log */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-900">Audit Log</h2>
        <DataTable
          columns={auditCols}
          data={auditQ.data?.entries ?? []}
          isLoading={auditQ.isLoading}
          emptyMessage="No audit entries found"
        />
        {auditQ.data && (
          <Pagination
            page={auditPage}
            pageSize={25}
            total={auditQ.data.total}
            onPageChange={setAuditPage}
          />
        )}
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function AdminDashboard() {
  const [tab, setTab] = useState<Tab>('dashboard')

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-1 -mb-px">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                'px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                tab === t.id
                  ? 'border-[#ff5c00] text-[#ff5c00]'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {tab === 'dashboard' && <OperationsDashboard />}
      {tab === 'security' && <SecurityPanel />}
    </div>
  )
}
