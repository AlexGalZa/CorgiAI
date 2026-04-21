import { useState, useEffect } from 'react'
import { Search, Plus } from 'lucide-react'
import { usePermissions } from '@/lib/permissions'
import DataTable, { type Column, type SortState } from '@/components/ui/DataTable'
import ExportButton from '@/components/ui/ExportButton'
import Pagination from '@/components/ui/Pagination'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import QueryError from '@/components/ui/QueryError'
import CertificateDetailPanel from '@/components/certificates/CertificateDetailPanel'
import CertificateForm from '@/components/certificates/CertificateForm'
import { useCertificates, type CertificateListItem } from '@/hooks/useCertificates'
import { formatDate } from '@/lib/formatters'

const columns: Column<CertificateListItem>[] = [
  { key: 'coi_number', header: 'COI #', sortable: true },
  { key: 'holder_name', header: 'Holder Name', sortable: true },
  {
    key: 'location',
    header: 'Holder Address',
    render: (row) =>
      row.holder_city && row.holder_state
        ? `${row.holder_city}, ${row.holder_state}`
        : row.holder_state || row.holder_city || '—',
  },
  {
    key: 'is_additional_insured',
    header: 'Additional Insured',
    render: (row) =>
      row.is_additional_insured ? (
        <span className="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-[#ff5c00]">
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

export default function CertificatesPage() {
  const { canEditCertificates } = usePermissions()
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [sort, setSort] = useState<SortState>({ key: 'created_at', direction: 'desc' })
  const [selectedCert, setSelectedCert] = useState<CertificateListItem | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const ordering = sort.direction === 'desc' ? `-${sort.key}` : sort.key

  const { data, isLoading, isError, refetch } = useCertificates({
    page,
    search: debouncedSearch || undefined,
    ordering,
  })

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Certificates' }]} />
      <PageHeader
        title="Certificates of Insurance"
        subtitle="Manage certificates of insurance and holder information."
        count={data?.count}
        action={
          <div className="flex items-center gap-3">
            {canEditCertificates && (
              <button
                onClick={() => setShowCreateForm(true)}
                className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-[#ea580c]"
              >
                <Plus className="h-4 w-4" />
                New Certificate
              </button>
            )}
            <ExportButton
              data={(data?.results ?? []) as unknown as Record<string, unknown>[]}
              filename="certificates"
              columns={[
                { key: 'coi_number', header: 'COI #' },
                { key: 'custom_coi_number', header: 'Custom COI #' },
                { key: 'holder_name', header: 'Holder Name' },
                { key: 'holder_city', header: 'City' },
                { key: 'holder_state', header: 'State' },
                { key: 'is_additional_insured', header: 'Additional Insured' },
                { key: 'created_at', header: 'Created' },
              ]}
            />
          </div>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by holder name..."
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
          emptyMessage="No certificates found"
          currentSort={sort}
          onSort={(key, direction) => { setSort({ key, direction }); setPage(1) }}
          onRowClick={(row) => setSelectedCert(row)}
          footer={data && <Pagination page={page} totalCount={data.count} onPageChange={setPage} />}
        />
      )}

      <CertificateDetailPanel
        certificate={selectedCert}
        onClose={() => setSelectedCert(null)}
      />

      <CertificateForm
        open={showCreateForm}
        onClose={() => setShowCreateForm(false)}
      />
    </div>
  )
}
