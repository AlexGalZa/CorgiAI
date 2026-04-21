import { useState, useEffect, useMemo } from 'react'
import { Search, DollarSign, Clock, CheckCircle, TrendingUp, Download } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import MetricCard from '@/components/ui/MetricCard'
import DataTable, { type Column } from '@/components/ui/DataTable'
import Pagination from '@/components/ui/Pagination'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import QueryError from '@/components/ui/QueryError'
import Select from '@/components/ui/Select'
import { useProducers, type ProducerListItem } from '@/hooks/useProducers'
import { usePolicies, type PolicyListItem } from '@/hooks/usePolicies'
import { formatCurrency, formatDate } from '@/lib/formatters'
import type { PaginatedResponse } from '@/types'

// ─── Types ───────────────────────────────────────────────────────────────────

interface PolicyTransaction {
  id: number
  policy: number
  policy_number: string
  transaction_type: string
  amount: string
  effective_date: string
  description: string
  created_at: string
}

interface CommissionRow {
  id: string
  producer_name: string
  producer_id: number
  policy_number: string
  insured_name: string
  premium: number
  commission_rate: number
  commission_amount: number
  status: 'earned' | 'pending' | 'paid'
  effective_date: string
  created_at: string
}

// ─── Hook: Policy Transactions ───────────────────────────────────────────────

function usePolicyTransactions(filters: { page?: number; ordering?: string } = {}) {
  return useQuery<PaginatedResponse<PolicyTransaction>>({
    queryKey: ['policy-transactions', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.set('page', String(filters.page))
      if (filters.ordering) params.set('ordering', filters.ordering)
      const { data } = await api.get(`/admin/policy-transactions?${params.toString()}`)
      return data
    },
  })
}

// ─── Constants ───────────────────────────────────────────────────────────────

const DEFAULT_COMMISSION_RATE = 0.10

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'earned', label: 'Earned' },
  { value: 'pending', label: 'Pending' },
  { value: 'paid', label: 'Paid' },
]

// ─── Component ───────────────────────────────────────────────────────────────

export default function CommissionsPage() {
  const [page, setPage] = useState(1)
  const [producerFilter, setProducerFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  // Fetch data
  const producersQ = useProducers({ page: 1, ordering: 'name' })
  const policiesQ = usePolicies({
    page: 1,
    ordering: '-created_at',
    is_brokered: true,
    ...(dateFrom ? { effective_date_after: dateFrom } : {}),
    ...(dateTo ? { effective_date_before: dateTo } : {}),
  })
  const transactionsQ = usePolicyTransactions({ ordering: '-created_at' })

  const producers = producersQ.data?.results ?? []
  const policies = policiesQ.data?.results ?? []
  const transactions = transactionsQ.data?.results ?? []

  // Build producer options for filter
  const producerOptions = useMemo(() => [
    { value: '', label: 'All Producers' },
    ...producers.map((p) => ({ value: String(p.id), label: p.name })),
  ], [producers])

  // ─── Derive commission rows from brokered policies ─────────────────────────
  // In a real setup the backend would provide producer<->policy mapping.
  // For now we derive from brokered policies + producer list.

  const commissionRows: CommissionRow[] = useMemo(() => {
    // Map each brokered policy to a commission row
    return policies.map((p) => {
      const premium = parseFloat(p.premium ?? '0') || 0
      const rate = DEFAULT_COMMISSION_RATE
      const commissionAmount = premium * rate

      // Determine status based on policy status
      let status: 'earned' | 'pending' | 'paid' = 'pending'
      if (p.status === 'active' || p.status === 'bound') {
        status = 'earned'
      } else if (p.status === 'expired' || p.status === 'cancelled') {
        status = 'paid'
      }

      // Try to match a producer (heuristic: first active broker)
      const matchedProducer = producers.find((pr) => pr.producer_type === 'broker' && pr.is_active) ?? producers[0]

      return {
        id: `comm-${p.id}`,
        producer_name: matchedProducer?.name ?? 'Unassigned',
        producer_id: matchedProducer?.id ?? 0,
        policy_number: p.policy_number,
        insured_name: p.insured_legal_name,
        premium,
        commission_rate: rate,
        commission_amount: commissionAmount,
        status,
        effective_date: p.effective_date ?? '',
        created_at: p.created_at,
      }
    })
  }, [policies, producers])

  // ─── Apply filters ─────────────────────────────────────────────────────────

  const filteredRows = useMemo(() => {
    let rows = commissionRows

    if (producerFilter) {
      rows = rows.filter((r) => String(r.producer_id) === producerFilter)
    }

    if (statusFilter) {
      rows = rows.filter((r) => r.status === statusFilter)
    }

    if (debouncedSearch) {
      const q = debouncedSearch.toLowerCase()
      rows = rows.filter((r) =>
        r.producer_name.toLowerCase().includes(q) ||
        r.policy_number.toLowerCase().includes(q) ||
        r.insured_name.toLowerCase().includes(q)
      )
    }

    return rows
  }, [commissionRows, producerFilter, statusFilter, debouncedSearch])

  // ─── Pagination ────────────────────────────────────────────────────────────

  const PAGE_SIZE = 20
  const totalCount = filteredRows.length
  const paginatedRows = filteredRows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  // ─── Summary metrics ──────────────────────────────────────────────────────

  const totalCommissions = commissionRows.reduce((s, r) => s + r.commission_amount, 0)
  const pendingPayout = commissionRows.filter((r) => r.status === 'earned').reduce((s, r) => s + r.commission_amount, 0)
  const paidOut = commissionRows.filter((r) => r.status === 'paid').reduce((s, r) => s + r.commission_amount, 0)
  const pendingBind = commissionRows.filter((r) => r.status === 'pending').reduce((s, r) => s + r.commission_amount, 0)

  // ─── Table columns ────────────────────────────────────────────────────────

  const columns: Column<CommissionRow>[] = [
    { key: 'producer_name', header: 'Producer' },
    { key: 'policy_number', header: 'Policy #' },
    { key: 'insured_name', header: 'Insured' },
    {
      key: 'premium',
      header: 'Premium',
      align: 'right',
      render: (r) => formatCurrency(r.premium),
    },
    {
      key: 'commission_rate',
      header: 'Rate',
      align: 'right',
      render: (r) => `${(r.commission_rate * 100).toFixed(0)}%`,
    },
    {
      key: 'commission_amount',
      header: 'Commission',
      align: 'right',
      render: (r) => (
        <span className="font-semibold text-gray-900">{formatCurrency(r.commission_amount)}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (r) => {
        const styles = {
          earned: 'bg-emerald-50 text-emerald-700',
          pending: 'bg-amber-50 text-amber-700',
          paid: 'bg-sky-50 text-sky-700',
        }
        return (
          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[r.status]}`}>
            {r.status.charAt(0).toUpperCase() + r.status.slice(1)}
          </span>
        )
      },
    },
    {
      key: 'effective_date',
      header: 'Effective',
      render: (r) => formatDate(r.effective_date),
    },
  ]

  const isLoading = producersQ.isLoading || policiesQ.isLoading
  const isError = producersQ.isError || policiesQ.isError

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Finance' }, { label: 'Commissions' }]} />
      <PageHeader
        title="Commissions"
        subtitle="Track producer commissions, payouts, and earnings across all brokered policies."
        count={totalCount}
      />

      {/* ─── Summary Cards ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total Commissions"
          value={formatCurrency(totalCommissions)}
          subtitle={`${commissionRows.length} policies`}
          icon={DollarSign}
          isLoading={isLoading}
        />
        <MetricCard
          title="Pending Payout"
          value={formatCurrency(pendingPayout)}
          subtitle="Earned, awaiting payout"
          icon={Clock}
          accent="amber"
          isLoading={isLoading}
        />
        <MetricCard
          title="Paid Out"
          value={formatCurrency(paidOut)}
          subtitle="Completed payouts"
          icon={CheckCircle}
          accent="emerald"
          isLoading={isLoading}
        />
        <MetricCard
          title="Pending Bind"
          value={formatCurrency(pendingBind)}
          subtitle="Awaiting policy bind"
          icon={TrendingUp}
          accent="sky"
          isLoading={isLoading}
        />
      </div>

      {/* ─── Filters ────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search producer, policy, insured..."
            value={searchInput}
            onChange={(e) => { setSearchInput(e.target.value); setPage(1) }}
            className="w-72 rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-3 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
          />
        </div>
        <Select
          value={producerFilter}
          onChange={(val) => { setProducerFilter(val); setPage(1) }}
          options={producerOptions}
          placeholder="All Producers"
          size="sm"
          className="w-44"
        />
        <Select
          value={statusFilter}
          onChange={(val) => { setStatusFilter(val); setPage(1) }}
          options={STATUS_OPTIONS}
          placeholder="All Statuses"
          size="sm"
          className="w-36"
        />
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(1) }}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
            placeholder="From"
          />
          <span className="text-xs text-gray-400">to</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(1) }}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
            placeholder="To"
          />
        </div>
      </div>

      {/* ─── Table ──────────────────────────────────────────────────────────── */}
      {isError && <QueryError onRetry={() => { producersQ.refetch(); policiesQ.refetch() }} />}

      {!isError && (
        <DataTable
          columns={columns}
          data={paginatedRows}
          isLoading={isLoading}
          emptyMessage="No commission data found"
          footer={
            totalCount > PAGE_SIZE ? (
              <Pagination page={page} totalCount={totalCount} onPageChange={setPage} />
            ) : undefined
          }
        />
      )}
    </div>
  )
}
