import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Send, Target, AlertTriangle, Clock, CheckCircle2 } from 'lucide-react'
import { toast } from 'sonner'
import {
  usePipeline,
  useSendFollowUp,
  type PipelineRow,
  type PipelineNextAction,
} from '@/hooks/usePipeline'
import DataTable, { type Column } from '@/components/ui/DataTable'
import PageHeader from '@/components/ui/PageHeader'
import StatusBadge from '@/components/ui/StatusBadge'
import QueryError from '@/components/ui/QueryError'
import { formatCurrency } from '@/lib/formatters'

const ACTION_LABEL: Record<PipelineNextAction, string> = {
  send_followup: 'Send follow-up',
  send_expiry_warning: 'Quote expiring',
  review_underwriting: 'Review underwriting',
  awaiting_rating: 'Awaiting rating',
  none: '—',
}

const ACTION_TONE: Record<PipelineNextAction, string> = {
  send_followup: 'bg-orange-50 text-[#ff5c00] border-orange-200',
  send_expiry_warning: 'bg-red-50 text-red-700 border-red-200',
  review_underwriting: 'bg-amber-50 text-amber-700 border-amber-200',
  awaiting_rating: 'bg-gray-50 text-gray-600 border-gray-200',
  none: 'bg-gray-50 text-gray-400 border-gray-200',
}

function NextActionPill({ action }: { action: PipelineNextAction }) {
  const Icon =
    action === 'send_expiry_warning'
      ? AlertTriangle
      : action === 'awaiting_rating'
        ? Clock
        : action === 'none'
          ? CheckCircle2
          : Target
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${ACTION_TONE[action]}`}
    >
      <Icon className="h-3 w-3" />
      {ACTION_LABEL[action]}
    </span>
  )
}

function FollowUpButton({ row }: { row: PipelineRow }) {
  const sendFollowUp = useSendFollowUp()
  const [justSent, setJustSent] = useState(false)
  const eligible =
    row.next_action === 'send_followup' || row.next_action === 'send_expiry_warning'

  const onClick = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!eligible || sendFollowUp.isPending) return
    try {
      const result = await sendFollowUp.mutateAsync({ quote_id: row.quote_id })
      setJustSent(true)
      toast.success(`Follow-up sent to ${result.sent_to}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to send follow-up'
      toast.error(msg)
    }
  }

  if (justSent) {
    return (
      <span className="inline-flex items-center gap-1 text-[12px] text-emerald-700">
        <CheckCircle2 className="h-3.5 w-3.5" />
        Sent
      </span>
    )
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!eligible || sendFollowUp.isPending}
      className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-2.5 py-1 text-[12px] font-medium text-gray-700 transition-colors hover:bg-gray-50 hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-40"
      title={
        eligible
          ? 'Send a templated follow-up email to the customer'
          : 'No follow-up needed yet'
      }
    >
      <Send className="h-3.5 w-3.5" />
      {sendFollowUp.isPending ? 'Sending…' : 'Follow up'}
    </button>
  )
}

function ExpiryCell({ row }: { row: PipelineRow }) {
  if (row.days_until_expiry === null) return <span className="text-gray-400">—</span>
  const tone =
    row.days_until_expiry <= 3
      ? 'text-red-700 font-semibold'
      : row.days_until_expiry <= 7
        ? 'text-amber-700 font-medium'
        : 'text-gray-700'
  return (
    <span className={tone}>
      {row.days_until_expiry === 0 ? 'today' : `${row.days_until_expiry}d`}
    </span>
  )
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(score, 200) / 2 // 0-100 visual scale
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 rounded-full bg-gray-100 overflow-hidden">
        <div
          className="h-full bg-[#ff5c00] transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[11px] tabular-nums text-gray-500">{score}</span>
    </div>
  )
}

const columns: Column<PipelineRow>[] = [
  {
    key: 'company_name',
    header: 'Company',
    render: (row) => (
      <div className="flex flex-col">
        <Link
          to={`/quotes/${row.quote_id}`}
          className="text-sm font-medium text-gray-900 hover:text-[#ff5c00]"
          onClick={(e) => e.stopPropagation()}
        >
          {row.company_name}
        </Link>
        <span className="text-[11px] text-gray-500">{row.quote_number}</span>
      </div>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    render: (row) => <StatusBadge status={row.status} />,
  },
  {
    key: 'premium',
    header: 'Premium',
    align: 'right',
    render: (row) =>
      row.premium ? (
        <span className="text-sm tabular-nums">
          {formatCurrency(row.premium)}
          <span className="ml-0.5 text-[11px] text-gray-400">
            /{row.billing_frequency === 'monthly' ? 'mo' : 'yr'}
          </span>
        </span>
      ) : (
        <span className="text-gray-400">—</span>
      ),
  },
  {
    key: 'days_since_update',
    header: 'Last touch',
    align: 'right',
    render: (row) => (
      <span className="text-sm tabular-nums text-gray-700">
        {row.days_since_update === 0 ? 'today' : `${row.days_since_update}d ago`}
      </span>
    ),
  },
  {
    key: 'days_until_expiry',
    header: 'Expires',
    align: 'right',
    render: (row) => <ExpiryCell row={row} />,
  },
  {
    key: 'next_action',
    header: 'Next action',
    render: (row) => <NextActionPill action={row.next_action} />,
  },
  {
    key: 'closeability_score',
    header: 'Score',
    align: 'right',
    render: (row) => <ScoreBar score={row.closeability_score} />,
  },
  {
    key: 'actions',
    header: '',
    align: 'right',
    render: (row) => <FollowUpButton row={row} />,
  },
]

export default function PipelinePage() {
  const { data, isLoading, error, refetch } = usePipeline()
  const items = data?.items ?? []
  const total = data?.total ?? 0

  return (
    <div className="space-y-4">
      <PageHeader
        title="Next actions"
        subtitle="Open deals ranked by closeability — one click to follow up."
        count={total}
      />
      {error ? (
        <QueryError onRetry={refetch} />
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white">
          <DataTable<PipelineRow>
            columns={columns}
            data={items}
            isLoading={isLoading}
            emptyMessage="No open deals — pipeline is clear."
          />
        </div>
      )}
    </div>
  )
}
