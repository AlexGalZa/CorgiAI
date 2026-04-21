import { useState, useEffect } from 'react'
import { Search, Plus } from 'lucide-react'
import { usePermissions } from '@/lib/permissions'
import DataTable, { type Column, type SortState } from '@/components/ui/DataTable'
import ExportButton from '@/components/ui/ExportButton'
import Pagination from '@/components/ui/Pagination'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import QueryError from '@/components/ui/QueryError'
import OrganizationForm from '@/components/organizations/OrganizationForm'
import { useOrganizations, type OrganizationListItem } from '@/hooks/useOrganizations'
import { formatDate } from '@/lib/formatters'

const columns: Column<OrganizationListItem>[] = [
  { key: 'name', header: 'Name', sortable: true },
  {
    key: 'owner',
    header: 'Owner',
    render: (row) => {
      // If the API returns nested owner data, show email/name; otherwise show formatted ID
      if (row.owner_detail) {
        return (
          <span className="text-sm text-gray-700">
            {row.owner_detail.full_name || row.owner_detail.email || `User #${row.owner}`}
          </span>
        )
      }
      return <span className="text-sm text-gray-600">User #{row.owner}</span>
    },
  },
  {
    key: 'is_personal',
    header: 'Personal',
    render: (row) =>
      row.is_personal ? (
        <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700">
          Yes
        </span>
      ) : (
        <span className="text-xs text-gray-400">No</span>
      ),
  },
  {
    key: 'created_at',
    header: 'Created',
    sortable: true,
    render: (row) => formatDate(row.created_at),
  },
]

export default function OrganizationsPage() {
  const { canEditOrgs } = usePermissions()
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [sort, setSort] = useState<SortState>({ key: 'created_at', direction: 'desc' })
  const [formOpen, setFormOpen] = useState(false)
  const [editingOrg, setEditingOrg] = useState<OrganizationListItem | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const ordering = sort.direction === 'desc' ? `-${sort.key}` : sort.key

  const { data, isLoading, isError, refetch } = useOrganizations({
    page,
    search: debouncedSearch || undefined,
    ordering,
  })

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Organizations' }]} />
      <PageHeader
        title="Organizations"
        subtitle="Manage organizational accounts and team workspaces."
        count={data?.count}
        action={
          <div className="flex items-center gap-3">
            <ExportButton
              data={(data?.results ?? []) as unknown as Record<string, unknown>[]}
              filename="organizations"
              columns={[
                { key: 'name', header: 'Name' },
                { key: 'is_personal', header: 'Personal' },
                { key: 'created_at', header: 'Created' },
              ]}
            />
            {canEditOrgs && (
              <button
                onClick={() => { setEditingOrg(null); setFormOpen(true) }}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[#ff5c00] px-3 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#ea580c]"
              >
                <Plus className="h-4 w-4" />
                New Organization
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
            placeholder="Search by name..."
            value={searchInput}
            onChange={(e) => { setSearchInput(e.target.value); setPage(1) }}
            className="w-64 rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-3 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
          />
        </div>
      </div>

      {isError && <QueryError onRetry={refetch} />}

      {!isError && (
        <DataTable
          columns={columns}
          data={data?.results ?? []}
          isLoading={isLoading}
          emptyMessage="No organizations found"
          emptyAction={canEditOrgs ? { label: 'Create Organization', onClick: () => { setEditingOrg(null); setFormOpen(true) } } : undefined}
          currentSort={sort}
          onSort={(key, direction) => { setSort({ key, direction }); setPage(1) }}
          onRowClick={canEditOrgs ? (row) => { setEditingOrg(row); setFormOpen(true) } : undefined}
          footer={data && <Pagination page={page} totalCount={data.count} onPageChange={setPage} />}
        />
      )}

      <OrganizationForm
        organization={editingOrg}
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditingOrg(null) }}
      />
    </div>
  )
}
