import { useState, useEffect } from 'react'
import { Search, Plus } from 'lucide-react'
import { usePermissions } from '@/lib/permissions'
import DataTable, { type Column } from '@/components/ui/DataTable'
import Pagination from '@/components/ui/Pagination'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import QueryError from '@/components/ui/QueryError'
import Select from '@/components/ui/Select'
import { useProducers, type ProducerListItem } from '@/hooks/useProducers'
import { formatDate } from '@/lib/formatters'
import { cn } from '@/lib/utils'
import ProducerForm from '@/components/producers/ProducerForm'

const TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'broker', label: 'Broker' },
  { value: 'agent', label: 'Agent' },
  { value: 'mga', label: 'MGA' },
]

function formatType(t: string): string {
  if (t === 'mga') return 'MGA'
  return t.charAt(0).toUpperCase() + t.slice(1)
}

const columns: Column<ProducerListItem>[] = [
  { key: 'name', header: 'Name' },
  {
    key: 'producer_type',
    header: 'Type',
    render: (row) => (
      <span className="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-[#ff5c00]">
        {formatType(row.producer_type)}
      </span>
    ),
  },
  { key: 'email', header: 'Email' },
  { key: 'license_number', header: 'License #' },
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
    key: 'created_at',
    header: 'Created',
    render: (row) => formatDate(row.created_at),
  },
]

export default function ProducersPage() {
  const { canEditProducers } = usePermissions()
  const [page, setPage] = useState(1)
  const [producerType, setProducerType] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editingProducer, setEditingProducer] = useState<ProducerListItem | undefined>(undefined)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const { data, isLoading, isError, refetch } = useProducers({
    page,
    producer_type: producerType || undefined,
    search: debouncedSearch || undefined,
    ordering: '-created_at',
  })

  const handleRowClick = (producer: ProducerListItem) => {
    if (!canEditProducers) return
    setEditingProducer(producer)
    setFormOpen(true)
  }

  const handleFormClose = () => {
    setFormOpen(false)
    setEditingProducer(undefined)
  }

  const handleFormSaved = () => {
    setFormOpen(false)
    setEditingProducer(undefined)
  }

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Producers' }]} />
      <PageHeader
        title="Producers"
        subtitle="Manage insurance producers, brokers, and agents."
        count={data?.count}
        action={
          canEditProducers ? (
            <div className="flex items-center gap-3">
              <button
                onClick={() => { setEditingProducer(undefined); setFormOpen(true) }}
                className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#ea580c]"
              >
                <Plus className="h-4 w-4" />
                New Producer
              </button>
            </div>
          ) : undefined
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
        <Select
          value={producerType}
          onChange={(val) => { setProducerType(val); setPage(1) }}
          options={TYPE_OPTIONS}
          placeholder="All Types"
          size="sm"
          className="w-36"
        />
      </div>

      {isError && <QueryError onRetry={refetch} />}

      {!isError && (
        <DataTable
          columns={columns}
          data={data?.results ?? []}
          isLoading={isLoading}
          onRowClick={canEditProducers ? handleRowClick : undefined}
          emptyMessage="No producers found"
          emptyAction={canEditProducers ? { label: 'Add Producer', onClick: () => { setEditingProducer(undefined); setFormOpen(true) } } : undefined}
          footer={data && <Pagination page={page} totalCount={data.count} onPageChange={setPage} />}
        />
      )}

      {/* Producer Form Modal */}
      {formOpen && (
        <ProducerForm
          producer={editingProducer}
          onClose={handleFormClose}
          onSaved={handleFormSaved}
        />
      )}
    </div>
  )
}
