import { useState } from 'react'
import { History, Eye, RotateCcw, Check, ChevronDown, ChevronRight } from 'lucide-react'
import { useForms, useDuplicateForm, type FormDefinition } from '@/hooks/useForms'
import { formatDate } from '@/lib/formatters'
import StatusBadge from '@/components/ui/StatusBadge'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { cn } from '@/lib/utils'

interface VersionHistoryProps {
  currentForm: FormDefinition
  onViewVersion?: (formId: number) => void
}

export default function VersionHistory({ currentForm, onViewVersion }: VersionHistoryProps) {
  const [open, setOpen] = useState(false)
  const [restoreTarget, setRestoreTarget] = useState<FormDefinition | null>(null)
  const { data: allForms } = useForms()
  const dupMut = useDuplicateForm()

  // Filter forms by same slug to find all versions
  const versions = (allForms ?? [])
    .filter((f) => f.slug === currentForm.slug)
    .sort((a, b) => b.version - a.version)

  if (versions.length <= 1) return null

  const handleRestore = (form: FormDefinition) => {
    // Duplicate the old version — the backend increments version automatically
    dupMut.mutate(form.id, {
      onSuccess: () => {
        setRestoreTarget(null)
      },
    })
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-5 py-4 text-left text-sm font-semibold text-gray-900 transition-colors hover:bg-gray-50"
      >
        {open ? <ChevronDown className="h-4 w-4 text-gray-400" /> : <ChevronRight className="h-4 w-4 text-gray-400" />}
        <History className="h-4 w-4 text-gray-400" />
        Version History
        <span className="text-xs font-normal text-gray-400">({versions.length} versions)</span>
      </button>

      {open && (
        <div className="border-t border-gray-100">
          <div className="divide-y divide-gray-50">
            {versions.map((form) => {
              const isCurrent = form.id === currentForm.id

              return (
                <div
                  key={form.id}
                  className={cn(
                    'flex items-center gap-4 px-5 py-3 transition-colors',
                    isCurrent && 'bg-orange-50/50',
                  )}
                >
                  {/* Version info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">
                        v{form.version}
                      </span>
                      {isCurrent && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-[#ff5c00]/10 px-2 py-0.5 text-[10px] font-semibold text-[#ff5c00]">
                          <Check className="h-2.5 w-2.5" /> Current
                        </span>
                      )}
                      <StatusBadge status={form.is_active ? 'active' : 'inactive'} />
                    </div>
                    <p className="mt-0.5 text-xs text-gray-400">
                      Created {formatDate(form.created_at ?? '')}
                      {form.updated_at && ` · Updated ${formatDate(form.updated_at)}`}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 shrink-0">
                    {onViewVersion && (
                      <button
                        onClick={() => onViewVersion(form.id)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-50"
                        title="View this version"
                      >
                        <Eye className="h-3 w-3" /> View
                      </button>
                    )}
                    {!isCurrent && (
                      <button
                        onClick={() => setRestoreTarget(form)}
                        disabled={dupMut.isPending}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-[#ff5c00] transition-colors hover:bg-orange-50 disabled:opacity-50"
                        title="Restore as new version"
                      >
                        <RotateCcw className="h-3 w-3" /> Restore
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {restoreTarget && (
        <ConfirmDialog
          open
          title="Restore Version"
          message={`This will duplicate v${restoreTarget.version} as a new version of "${restoreTarget.name}". The current version will remain unchanged.`}
          confirmLabel={dupMut.isPending ? 'Restoring…' : 'Restore'}
          variant="warning"
          onConfirm={() => handleRestore(restoreTarget)}
          onCancel={() => setRestoreTarget(null)}
        />
      )}
    </div>
  )
}
