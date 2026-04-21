import { useState, useEffect } from 'react'
import { Search, Plus, X } from 'lucide-react'
import { usePermissions } from '@/lib/permissions'
import DataTable, { type Column, type SortState } from '@/components/ui/DataTable'
import ExportButton from '@/components/ui/ExportButton'
import Pagination from '@/components/ui/Pagination'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import QueryError from '@/components/ui/QueryError'
import Select from '@/components/ui/Select'
import { useUsers } from '@/hooks/useUsers'
import type { User } from '@/types'
import { formatDate, formatRelativeTime } from '@/lib/formatters'
import { cn } from '@/lib/utils'
import UserForm from '@/components/users/UserForm'
import UserTimeline from '@/components/users/UserTimeline'

const ROLE_OPTIONS = [
  { value: '', label: 'All Roles' },
  { value: 'bdr', label: 'BDR' },
  { value: 'ae', label: 'Account Executive' },
  { value: 'ae_underwriting', label: 'AE + Underwriting' },
  { value: 'finance', label: 'Finance' },
  { value: 'broker', label: 'Broker' },
  { value: 'admin', label: 'Admin' },
]

const roleBadgeColors: Record<string, string> = {
  admin: 'bg-red-100 text-red-700',
  broker: 'bg-emerald-100 text-emerald-700',
  finance: 'bg-amber-100 text-amber-700',
  bdr: 'bg-sky-100 text-sky-700',
  ae: 'bg-orange-100 text-orange-700',
  ae_underwriting: 'bg-purple-100 text-purple-700',
}

function formatRole(role: string): string {
  return role.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

const columns: Column<User>[] = [
  {
    key: 'full_name',
    header: 'Name',
    render: (row) => {
      const name = row.full_name || `${row.first_name} ${row.last_name}`.trim()
      return name || '—'
    },
  },
  { key: 'email', header: 'Email', sortable: true },
  {
    key: 'role',
    header: 'Role',
    sortable: true,
    render: (row) => (
      <span
        className={cn(
          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
          roleBadgeColors[row.role] ?? 'bg-gray-100 text-gray-700',
        )}
      >
        {formatRole(row.role)}
      </span>
    ),
  },
  { key: 'company_name', header: 'Company' },
  {
    key: 'is_active',
    header: 'Active',
    render: (row) => (
      <span className="inline-flex items-center gap-1.5">
        <span
          className={cn(
            'h-2 w-2 rounded-full',
            row.is_active ? 'bg-green-500' : 'bg-red-400',
          )}
        />
        <span className="text-xs text-gray-600">
          {row.is_active ? 'Active' : 'Inactive'}
        </span>
      </span>
    ),
  },
  {
    key: 'updated_at',
    header: 'Last Active',
    render: (row) => {
      return row.updated_at ? formatRelativeTime(row.updated_at) : '—'
    },
  },
  {
    key: 'created_at',
    header: 'Created',
    sortable: true,
    render: (row) => formatDate(row.created_at),
  },
]

export default function UsersPage() {
  const { canCreateStaffAccounts, canEditUsers } = usePermissions()
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [role, setRole] = useState('')
  const [sort, setSort] = useState<SortState>({ key: 'created_at', direction: 'desc' })
  const [formOpen, setFormOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<User | undefined>(undefined)
  const [timelineUser, setTimelineUser] = useState<User | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const ordering = sort.direction === 'desc' ? `-${sort.key}` : sort.key

  const { data, isLoading, isError, refetch } = useUsers({
    page,
    search: debouncedSearch || undefined,
    role: role || undefined,
    ordering,
  })

  const handleRowClick = (user: User) => {
    // Show timeline panel; hold Ctrl/Cmd to open edit form instead
    setTimelineUser((prev) => prev?.id === user.id ? null : user)
  }

  const handleFormClose = () => {
    setFormOpen(false)
    setEditingUser(undefined)
  }

  const handleFormSaved = () => {
    setFormOpen(false)
    setEditingUser(undefined)
  }

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Users' }]} />
      <PageHeader
        title="Users"
        subtitle="Platform user accounts and role management."
        count={data?.count}
        action={
          <div className="flex items-center gap-3">
            <ExportButton
              data={(data?.results ?? []) as unknown as Record<string, unknown>[]}
              filename="users"
              columns={[
                { key: 'email', header: 'Email' },
                { key: 'first_name', header: 'First Name' },
                { key: 'last_name', header: 'Last Name' },
                { key: 'role', header: 'Role' },
                { key: 'company_name', header: 'Company' },
                { key: 'is_active', header: 'Active' },
                { key: 'created_at', header: 'Created' },
              ]}
            />
            {canCreateStaffAccounts && (
              <button
                onClick={() => { setEditingUser(undefined); setFormOpen(true) }}
                className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#ea580c]"
              >
                <Plus className="h-4 w-4" />
                New User
              </button>
            )}
          </div>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by email or name..."
            value={searchInput}
            onChange={(e) => { setSearchInput(e.target.value); setPage(1) }}
            className="w-64 rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-3 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
          />
        </div>
        <Select
          value={role}
          onChange={(val) => { setRole(val); setPage(1) }}
          options={ROLE_OPTIONS}
          placeholder="All Roles"
          size="sm"
          className="w-44"
        />
      </div>

      {isError && <QueryError onRetry={refetch} />}

      {!isError && (
        <DataTable
          columns={columns}
          data={data?.results ?? []}
          isLoading={isLoading}
          onRowClick={handleRowClick}
          emptyMessage="No users found"
          emptyAction={canCreateStaffAccounts ? { label: 'Add User', onClick: () => { setEditingUser(undefined); setFormOpen(true) } } : undefined}
          currentSort={sort}
          onSort={(key, direction) => { setSort({ key, direction }); setPage(1) }}
          footer={data && <Pagination page={page} totalCount={data.count} onPageChange={setPage} />}
        />
      )}

      {/* User Timeline Panel */}
      {timelineUser && (
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">
                {timelineUser.full_name || `${timelineUser.first_name} ${timelineUser.last_name}`.trim() || 'User'} — Activity
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">{timelineUser.email}</p>
            </div>
            <div className="flex items-center gap-2">
              {canEditUsers && (
                <button
                  onClick={() => { setEditingUser(timelineUser); setFormOpen(true) }}
                  className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-50"
                >
                  Edit User
                </button>
              )}
              <button
                onClick={() => setTimelineUser(null)}
                className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="p-5">
            <UserTimeline userId={String(timelineUser.id)} userEmail={timelineUser.email} />
          </div>
        </div>
      )}

      {/* User Form Modal */}
      {formOpen && (
        <UserForm
          user={editingUser}
          onClose={handleFormClose}
          onSaved={handleFormSaved}
        />
      )}
    </div>
  )
}
