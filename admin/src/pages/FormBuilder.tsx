import { useState, useEffect, useMemo } from 'react'
import {
  Search, Plus, Pencil, Copy, Trash2, ChevronUp, ChevronDown,
  GripVertical, X, Eye, Save, ArrowLeft,
  FileText, Zap, Link2,
} from 'lucide-react'
import DataTable, { type Column } from '@/components/ui/DataTable'
import Breadcrumbs from '@/components/ui/Breadcrumbs'
import PageHeader from '@/components/ui/PageHeader'
import StatusBadge from '@/components/ui/StatusBadge'
import Spinner from '@/components/ui/Spinner'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import Select from '@/components/ui/Select'
import Pagination from '@/components/ui/Pagination'
import {
  useForms, useForm, useCreateForm, useUpdateForm, useDeleteForm, useDuplicateForm,
  type FormDefinition, type FormField, type FormDefinitionInput,
  type ConditionalRule, type ConditionalCondition, type FormFieldOption,
} from '@/hooks/useForms'
import { formatDate } from '@/lib/formatters'
import { cn } from '@/lib/utils'
import FormPreviewComponent from '@/components/forms/FormPreview'
import VersionHistory from '@/components/forms/VersionHistory'

// ── Constants ───────────────────────────────────────────────────────────────

const FIELD_TYPES = [
  { value: 'text', label: 'Text' },
  { value: 'textarea', label: 'Textarea' },
  { value: 'number', label: 'Number' },
  { value: 'currency', label: 'Currency' },
  { value: 'percentage', label: 'Percentage' },
  { value: 'date', label: 'Date' },
  { value: 'select', label: 'Select' },
  { value: 'multi_select', label: 'Multi Select' },
  { value: 'radio', label: 'Radio' },
  { value: 'checkbox', label: 'Checkbox' },
  { value: 'checkbox_group', label: 'Checkbox Group' },
  { value: 'file_upload', label: 'File Upload' },
  { value: 'address', label: 'Address' },
  { value: 'phone', label: 'Phone' },
  { value: 'email', label: 'Email' },
  { value: 'ein', label: 'EIN' },
  { value: 'heading', label: 'Heading' },
  { value: 'paragraph', label: 'Paragraph' },
]

const COVERAGE_TYPES = [
  { value: '', label: 'None (Generic)' },
  { value: 'commercial-general-liability', label: 'Commercial General Liability' },
  { value: 'directors-and-officers', label: 'Directors & Officers' },
  { value: 'technology-errors-and-omissions', label: 'Technology E&O' },
  { value: 'cyber-liability', label: 'Cyber Liability' },
  { value: 'fiduciary-liability', label: 'Fiduciary Liability' },
  { value: 'hired-and-non-owned-auto', label: 'Hired & Non-Owned Auto' },
  { value: 'media-liability', label: 'Media Liability' },
  { value: 'employment-practices-liability', label: 'Employment Practices Liability' },
]

const COVERAGE_FILTER = [{ value: '', label: 'All Coverage Types' }, ...COVERAGE_TYPES.filter(c => c.value)]
const ACTIVE_FILTER = [
  { value: '', label: 'All Status' },
  { value: 'true', label: 'Active' },
  { value: 'false', label: 'Inactive' },
]

const OPERATORS = [
  { value: 'equals', label: 'Equals' },
  { value: 'not_equals', label: 'Not Equals' },
  { value: 'contains', label: 'Contains' },
  { value: 'gt', label: 'Greater Than' },
  { value: 'lt', label: 'Less Than' },
  { value: 'is_empty', label: 'Is Empty' },
  { value: 'is_not_empty', label: 'Is Not Empty' },
  { value: 'in', label: 'In' },
  { value: 'not_in', label: 'Not In' },
]

const WIDTH_OPTIONS = [
  { value: 'full', label: 'Full' },
  { value: 'half', label: 'Half' },
  { value: 'third', label: 'Third' },
]

const OPTIONS_TYPES = new Set(['select', 'multi_select', 'radio', 'checkbox_group'])
const NON_INPUT_TYPES = new Set(['heading', 'paragraph'])

function slugify(str: string): string {
  return str.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
}

function makeFieldKey(label: string, existingKeys: Set<string>): string {
  let base = label.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/(^_|_$)/g, '')
  if (!base) base = 'field'
  let key = base
  let i = 2
  while (existingKeys.has(key)) { key = `${base}_${i}`; i++ }
  return key
}

function blankField(order: number, existingKeys: Set<string>): FormField {
  return { key: makeFieldKey('new_field', existingKeys), label: 'New Field', field_type: 'text', required: false, placeholder: '', help_text: '', width: 'full', order }
}

function blankRule(): ConditionalRule {
  return { target_field: '', action: 'show', match: 'all', conditions: [{ field_key: '', operator: 'equals', value: '' }] }
}

// ═══════════════════════════════════════════════════════════════════════════════
// LIST VIEW
// ═══════════════════════════════════════════════════════════════════════════════

function FormList({ onEdit, onCreate }: { onEdit: (id: number) => void; onCreate: () => void }) {
  const { data: forms, isLoading, isError, refetch } = useForms()
  const deleteMut = useDeleteForm()
  const dupMut = useDuplicateForm()
  const [search, setSearch] = useState('')
  const [filterCoverage, setFilterCoverage] = useState('')
  const [filterActive, setFilterActive] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<FormDefinition | null>(null)
  const [page, setPage] = useState(1)

  const filtered = useMemo(() => {
    if (!forms) return []
    return forms.filter((f) => {
      if (search) {
        const q = search.toLowerCase()
        if (!f.name.toLowerCase().includes(q) && !f.slug.toLowerCase().includes(q)) return false
      }
      if (filterCoverage && f.coverage_type !== filterCoverage) return false
      if (filterActive === 'true' && !f.is_active) return false
      if (filterActive === 'false' && f.is_active) return false
      return true
    })
  }, [forms, search, filterCoverage, filterActive])

  const PAGE_SIZE = 25
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const columns: Column<FormDefinition>[] = [
    {
      key: 'name',
      header: 'Name',
      sortable: true,
      render: (row) => row.name,
    },
    {
      key: 'coverage_type',
      header: 'Coverage Type',
      sortable: true,
      render: (row) => row.coverage_type
        ? COVERAGE_TYPES.find(c => c.value === row.coverage_type)?.label || row.coverage_type
        : '—',
    },
    { key: 'version', header: 'Version', render: (row) => `v${row.version}` },
    { key: 'fields', header: 'Fields', render: (row) => String(row.fields?.length ?? 0) },
    {
      key: 'is_active',
      header: 'Status',
      render: (row) => <StatusBadge status={row.is_active ? 'active' : 'inactive'} />,
    },
    {
      key: 'updated_at',
      header: 'Updated',
      sortable: true,
      render: (row) => row.updated_at ? formatDate(row.updated_at) : '—',
    },
    {
      key: 'actions' as any,
      header: '',
      render: (row) => (
        <div className="flex items-center justify-end gap-1">
          <button onClick={(e) => { e.stopPropagation(); onEdit(row.id) }} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors" title="Edit"><Pencil className="h-4 w-4" /></button>
          <button onClick={(e) => { e.stopPropagation(); dupMut.mutate(row.id) }} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors" title="Duplicate"><Copy className="h-4 w-4" /></button>
          <button onClick={(e) => { e.stopPropagation(); setDeleteTarget(row) }} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-red-600 transition-colors" title="Deactivate"><Trash2 className="h-4 w-4" /></button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Form Builder' }]} />
      <PageHeader
        title="Form Builder"
        subtitle="Manage dynamic coverage questionnaire forms."
        count={forms?.length}
        action={
          <button onClick={onCreate} className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-4 py-2 text-sm font-medium text-white hover:bg-[#e05200] transition-colors">
            <Plus className="h-4 w-4" /> New Form
          </button>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by name or slug..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="w-64 rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-3 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]"
          />
        </div>
        <Select value={filterCoverage} onChange={(v) => { setFilterCoverage(v); setPage(1) }} options={COVERAGE_FILTER} placeholder="All Coverage Types" size="sm" className="w-52" />
        <Select value={filterActive} onChange={(v) => { setFilterActive(v); setPage(1) }} options={ACTIVE_FILTER} placeholder="All Status" size="sm" className="w-36" />
      </div>

      <DataTable
        columns={columns}
        data={paged}
        isLoading={isLoading}
        emptyMessage="No forms found"
        onRowClick={(row) => onEdit(row.id)}
        footer={<Pagination page={page} totalCount={filtered.length} pageSize={PAGE_SIZE} onPageChange={setPage} />}
      />

      {deleteTarget && (
        <ConfirmDialog
          open
          title="Deactivate Form"
          message={`Deactivate "${deleteTarget.name}" v${deleteTarget.version}? It will no longer be served to the portal.`}
          confirmLabel="Deactivate"
          variant="danger"
          onConfirm={() => { deleteMut.mutate(deleteTarget.id); setDeleteTarget(null) }}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// FIELD EDITOR CARD
// ═══════════════════════════════════════════════════════════════════════════════

function FieldCard({
  field, index, total, expanded, onToggle, onChange, onMoveUp, onMoveDown, onRemove,
}: {
  field: FormField; index: number; total: number; expanded: boolean
  onToggle: () => void; onChange: (f: FormField) => void; onMoveUp: () => void; onMoveDown: () => void; onRemove: () => void
}) {
  const isOptionsType = OPTIONS_TYPES.has(field.field_type)
  const isNonInput = NON_INPUT_TYPES.has(field.field_type)
  const typeLabel = FIELD_TYPES.find(t => t.value === field.field_type)?.label || field.field_type
  const updateOptions = (options: FormFieldOption[]) => onChange({ ...field, options })

  return (
    <div className={cn('border rounded-lg bg-white transition-all', expanded ? 'border-[#ff5c00]/30 shadow-sm' : 'border-gray-200')}>
      <div className="flex items-center gap-2 px-4 py-3 cursor-pointer select-none" onClick={onToggle}>
        <GripVertical className="h-4 w-4 text-gray-300 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900 truncate text-sm">{field.label || 'Untitled'}</span>
            <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-500 uppercase tracking-wide">{typeLabel}</span>
            {field.required && <span className="text-red-500 text-xs font-bold">*</span>}
            {field.width && field.width !== 'full' && <span className="text-[10px] text-gray-400">{field.width}</span>}
          </div>
          <div className="text-xs text-gray-400 mt-0.5">{field.key}</div>
        </div>
        <div className="flex items-center gap-0.5 shrink-0" onClick={e => e.stopPropagation()}>
          <button onClick={onMoveUp} disabled={index === 0} className="p-1 rounded hover:bg-gray-100 text-gray-400 disabled:opacity-30"><ChevronUp className="h-3.5 w-3.5" /></button>
          <button onClick={onMoveDown} disabled={index === total - 1} className="p-1 rounded hover:bg-gray-100 text-gray-400 disabled:opacity-30"><ChevronDown className="h-3.5 w-3.5" /></button>
          <button onClick={onRemove} className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-600"><X className="h-3.5 w-3.5" /></button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-gray-100 px-4 py-4 space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Key</label>
              <input type="text" value={field.key} onChange={e => onChange({ ...field, key: e.target.value.replace(/[^a-z0-9_]/g, '') })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Label</label>
              <input type="text" value={field.label} onChange={e => onChange({ ...field, label: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Type</label>
              <select value={field.field_type} onChange={e => onChange({ ...field, field_type: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none">
                {FIELD_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
          </div>

          {!isNonInput && (
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Placeholder</label>
                <input type="text" value={field.placeholder || ''} onChange={e => onChange({ ...field, placeholder: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Help Text</label>
                <input type="text" value={field.help_text || ''} onChange={e => onChange({ ...field, help_text: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]" />
              </div>
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-500 mb-1">Width</label>
                  <select value={field.width || 'full'} onChange={e => onChange({ ...field, width: e.target.value as 'full' | 'half' | 'third' })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none">
                    {WIDTH_OPTIONS.map(w => <option key={w.value} value={w.value}>{w.label}</option>)}
                  </select>
                </div>
                <div className="flex items-end pb-1">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input type="checkbox" checked={field.required} onChange={e => onChange({ ...field, required: e.target.checked })} className="rounded border-gray-300 text-[#ff5c00] focus:ring-[#ff5c00]" />
                    <span className="text-xs font-medium text-gray-500">Required</span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {isOptionsType && (
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-2">Options</label>
              <div className="space-y-2">
                {(field.options || []).map((opt, oi) => (
                  <div key={oi} className="flex items-center gap-2">
                    <input type="text" placeholder="Value" value={opt.value} onChange={e => { const o = [...(field.options || [])]; o[oi] = { ...o[oi], value: e.target.value }; updateOptions(o) }} className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-[#ff5c00] focus:outline-none" />
                    <input type="text" placeholder="Label" value={opt.label} onChange={e => { const o = [...(field.options || [])]; o[oi] = { ...o[oi], label: e.target.value }; updateOptions(o) }} className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-[#ff5c00] focus:outline-none" />
                    <button onClick={() => updateOptions((field.options || []).filter((_, i) => i !== oi))} className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-600"><X className="h-3.5 w-3.5" /></button>
                  </div>
                ))}
                <button onClick={() => updateOptions([...(field.options || []), { value: '', label: '' }])} className="text-xs text-[#ff5c00] hover:text-[#e05200] font-medium">+ Add Option</button>
              </div>
            </div>
          )}

          {!isNonInput && (
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-2">Validation</label>
              <div className="grid grid-cols-4 gap-3">
                {['number', 'currency', 'percentage'].includes(field.field_type) && (<>
                  <div><label className="block text-[10px] text-gray-400 mb-0.5">Min</label><input type="number" value={field.validation?.min ?? ''} onChange={e => onChange({ ...field, validation: { ...field.validation, min: e.target.value ? Number(e.target.value) : undefined } })} className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-[#ff5c00] focus:outline-none" /></div>
                  <div><label className="block text-[10px] text-gray-400 mb-0.5">Max</label><input type="number" value={field.validation?.max ?? ''} onChange={e => onChange({ ...field, validation: { ...field.validation, max: e.target.value ? Number(e.target.value) : undefined } })} className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-[#ff5c00] focus:outline-none" /></div>
                </>)}
                {['text', 'textarea'].includes(field.field_type) && (<>
                  <div><label className="block text-[10px] text-gray-400 mb-0.5">Min Length</label><input type="number" value={field.validation?.min_length ?? ''} onChange={e => onChange({ ...field, validation: { ...field.validation, min_length: e.target.value ? Number(e.target.value) : undefined } })} className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-[#ff5c00] focus:outline-none" /></div>
                  <div><label className="block text-[10px] text-gray-400 mb-0.5">Max Length</label><input type="number" value={field.validation?.max_length ?? ''} onChange={e => onChange({ ...field, validation: { ...field.validation, max_length: e.target.value ? Number(e.target.value) : undefined } })} className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-[#ff5c00] focus:outline-none" /></div>
                  <div className="col-span-2"><label className="block text-[10px] text-gray-400 mb-0.5">Pattern (regex)</label><input type="text" value={field.validation?.pattern ?? ''} onChange={e => onChange({ ...field, validation: { ...field.validation, pattern: e.target.value || undefined } })} className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-[#ff5c00] focus:outline-none font-mono" /></div>
                </>)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONDITIONAL LOGIC EDITOR
// ═══════════════════════════════════════════════════════════════════════════════

function LogicEditor({ rules, fieldKeys, onChange }: { rules: ConditionalRule[]; fieldKeys: { key: string; label: string }[]; onChange: (r: ConditionalRule[]) => void }) {
  const updateRule = (i: number, patch: Partial<ConditionalRule>) => { const u = [...rules]; u[i] = { ...u[i], ...patch }; onChange(u) }
  const updateCond = (ri: number, ci: number, patch: Partial<ConditionalCondition>) => { const u = [...rules]; const c = [...u[ri].conditions]; c[ci] = { ...c[ci], ...patch }; u[ri] = { ...u[ri], conditions: c }; onChange(u) }

  return (
    <div className="space-y-4">
      {rules.length === 0 && <p className="text-sm text-gray-400 py-8 text-center">No conditional logic rules yet</p>}
      {rules.map((rule, ri) => (
        <div key={ri} className="border border-gray-200 rounded-lg p-4 space-y-3 bg-white">
          <div className="flex items-center gap-3 flex-wrap">
            <select value={rule.action} onChange={e => updateRule(ri, { action: e.target.value as 'show' | 'hide' })} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"><option value="show">Show</option><option value="hide">Hide</option></select>
            <select value={rule.target_field} onChange={e => updateRule(ri, { target_field: e.target.value })} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm flex-1">
              <option value="">— Target field —</option>
              {fieldKeys.map(f => <option key={f.key} value={f.key}>{f.label} ({f.key})</option>)}
            </select>
            <span className="text-xs text-gray-400">when</span>
            <select value={rule.match} onChange={e => updateRule(ri, { match: e.target.value as 'all' | 'any' })} className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm"><option value="all">ALL</option><option value="any">ANY</option></select>
            <span className="text-xs text-gray-400">match</span>
            <button onClick={() => onChange(rules.filter((_, i) => i !== ri))} className="ml-auto p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-600"><Trash2 className="h-3.5 w-3.5" /></button>
          </div>
          <div className="pl-4 border-l-2 border-gray-100 space-y-2">
            {rule.conditions.map((cond, ci) => (
              <div key={ci} className="flex items-center gap-2">
                <select value={cond.field_key} onChange={e => updateCond(ri, ci, { field_key: e.target.value })} className="rounded border border-gray-300 px-2 py-1.5 text-sm flex-1">
                  <option value="">— Field —</option>
                  {fieldKeys.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                </select>
                <select value={cond.operator} onChange={e => updateCond(ri, ci, { operator: e.target.value })} className="rounded border border-gray-300 px-2 py-1.5 text-sm">
                  {OPERATORS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                {!['is_empty', 'is_not_empty'].includes(cond.operator) && (
                  <input type="text" placeholder="Value" value={String(cond.value ?? '')} onChange={e => updateCond(ri, ci, { value: e.target.value })} className="rounded border border-gray-300 px-2 py-1.5 text-sm flex-1" />
                )}
                <button onClick={() => { const u = [...rules]; u[ri] = { ...u[ri], conditions: u[ri].conditions.filter((_, i) => i !== ci) }; onChange(u) }} className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-600"><X className="h-3 w-3" /></button>
              </div>
            ))}
            <button onClick={() => updateRule(ri, { conditions: [...rule.conditions, { field_key: '', operator: 'equals', value: '' }] })} className="text-xs text-[#ff5c00] hover:text-[#e05200] font-medium">+ Add Condition</button>
          </div>
        </div>
      ))}
      <button onClick={() => onChange([...rules, blankRule()])} className="inline-flex items-center gap-1.5 text-sm text-[#ff5c00] hover:text-[#e05200] font-medium"><Plus className="h-3.5 w-3.5" /> Add Rule</button>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// RATING MAPPINGS EDITOR
// ═══════════════════════════════════════════════════════════════════════════════

function MappingsEditor({ mappings, fieldKeys, onChange }: { mappings: Record<string, string>; fieldKeys: { key: string; label: string }[]; onChange: (m: Record<string, string>) => void }) {
  const entries = Object.entries(mappings)
  return (
    <div className="space-y-3">
      {entries.length === 0 && <p className="text-sm text-gray-400 py-8 text-center">No rating field mappings</p>}
      {entries.map(([key, val]) => (
        <div key={key} className="flex items-center gap-2">
          <select value={key} onChange={e => { const u = { ...mappings }; delete u[key]; u[e.target.value] = val; onChange(u) }} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm flex-1">
            <option value={key}>{fieldKeys.find(f => f.key === key)?.label || key}</option>
            {fieldKeys.filter(f => f.key !== key && !mappings[f.key]).map(f => <option key={f.key} value={f.key}>{f.label} ({f.key})</option>)}
          </select>
          <span className="text-gray-400">→</span>
          <input type="text" placeholder="Rating engine key" value={val} onChange={e => onChange({ ...mappings, [key]: e.target.value })} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm flex-1 font-mono" />
          <button onClick={() => { const u = { ...mappings }; delete u[key]; onChange(u) }} className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-600"><X className="h-3.5 w-3.5" /></button>
        </div>
      ))}
      <button onClick={() => onChange({ ...mappings, [`field_${entries.length + 1}`]: '' })} className="inline-flex items-center gap-1.5 text-sm text-[#ff5c00] hover:text-[#e05200] font-medium"><Plus className="h-3.5 w-3.5" /> Add Mapping</button>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// FORM PREVIEW
// ═══════════════════════════════════════════════════════════════════════════════

// FormPreview is now in @/components/forms/FormPreview

// ═══════════════════════════════════════════════════════════════════════════════
// EDITOR VIEW
// ═══════════════════════════════════════════════════════════════════════════════

type EditorTab = 'fields' | 'logic' | 'mappings' | 'preview'

function FormEditor({ formId, onBack }: { formId: number | null; onBack: () => void }) {
  const { data: existing, isLoading } = useForm(formId)
  const createMut = useCreateForm()
  const updateMut = useUpdateForm()

  const [activeTab, setActiveTab] = useState<EditorTab>('fields')
  const [expandedField, setExpandedField] = useState<number | null>(null)
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [slugManual, setSlugManual] = useState(false)
  const [version, setVersion] = useState(1)
  const [description, setDescription] = useState('')
  const [coverageType, setCoverageType] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [fields, setFields] = useState<FormField[]>([])
  const [rules, setRules] = useState<ConditionalRule[]>([])
  const [mappings, setMappings] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (existing) {
      setName(existing.name); setSlug(existing.slug); setSlugManual(true)
      setVersion(existing.version); setDescription(existing.description || '')
      setCoverageType(existing.coverage_type || ''); setIsActive(existing.is_active)
      setFields(existing.fields || []); setRules(existing.conditional_logic?.rules || [])
      setMappings(existing.rating_field_mappings || {})
    }
  }, [existing])

  useEffect(() => { if (!slugManual) setSlug(slugify(name)) }, [name, slugManual])

  const fieldKeys = useMemo(() => fields.filter(f => !NON_INPUT_TYPES.has(f.field_type)).map(f => ({ key: f.key, label: f.label })), [fields])
  const existingKeySet = useMemo(() => new Set(fields.map(f => f.key)), [fields])

  const handleSave = async () => {
    const payload: FormDefinitionInput = {
      name, slug, version, description,
      fields: fields.map((f, i) => ({ ...f, order: i })),
      conditional_logic: { rules },
      rating_field_mappings: mappings,
      coverage_type: coverageType || null,
      is_active: isActive,
    }
    try {
      if (formId) await updateMut.mutateAsync({ id: formId, ...payload })
      else await createMut.mutateAsync(payload)
      setSaved(true); setTimeout(() => setSaved(false), 2000)
    } catch (err) { console.error('Save failed', err) }
  }

  const addField = (type: string) => {
    const f = blankField(fields.length, existingKeySet)
    f.field_type = type; f.label = FIELD_TYPES.find(t => t.value === type)?.label || 'New Field'
    f.key = makeFieldKey(f.label, existingKeySet)
    setFields([...fields, f]); setExpandedField(fields.length)
  }

  const moveField = (from: number, to: number) => {
    if (to < 0 || to >= fields.length) return
    const arr = [...fields]; const [item] = arr.splice(from, 1); arr.splice(to, 0, item)
    setFields(arr); setExpandedField(to)
  }

  const isSaving = createMut.isPending || updateMut.isPending
  const saveError = createMut.error || updateMut.error

  if (formId && isLoading) return <div className="flex justify-center py-20"><Spinner /></div>

  const TABS: { key: EditorTab; label: string; icon: typeof FileText; badge?: number }[] = [
    { key: 'fields', label: 'Fields', icon: FileText, badge: fields.length },
    { key: 'logic', label: 'Logic', icon: Zap, badge: rules.length || undefined },
    { key: 'mappings', label: 'Mappings', icon: Link2 },
    { key: 'preview', label: 'Preview', icon: Eye },
  ]

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: 'Form Builder', href: '#' }, { label: formId ? name || 'Edit' : 'New Form' }]} />

      {/* Top bar */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors"><ArrowLeft className="h-5 w-5" /></button>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">{formId ? name || 'Untitled' : 'New Form Definition'}</h1>
            {slug && <p className="text-sm text-gray-500 mt-0.5">{slug} · v{version}</p>}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {saved && <span className="text-sm text-green-600 font-medium">✓ Saved</span>}
          {saveError && <span className="text-sm text-red-600">Save failed</span>}
          <button onClick={onBack} className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors">Cancel</button>
          <button onClick={handleSave} disabled={isSaving || !name || !slug} className="inline-flex items-center gap-2 rounded-lg bg-[#ff5c00] px-4 py-2 text-sm font-medium text-white hover:bg-[#e05200] disabled:opacity-50 transition-colors">
            <Save className="h-4 w-4" /> {isSaving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>

      {/* Meta fields card */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="grid grid-cols-6 gap-4">
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-500 mb-1">Name</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Cyber Liability Questionnaire" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Slug</label>
            <input type="text" value={slug} onChange={e => { setSlug(e.target.value); setSlugManual(true) }} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Coverage Type</label>
            <select value={coverageType} onChange={e => setCoverageType(e.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none">
              {COVERAGE_TYPES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Version</label>
              <input type="number" min={1} value={version} onChange={e => setVersion(Number(e.target.value))} className="w-20 rounded-lg border border-gray-300 px-3 py-2 text-sm text-center focus:border-[#ff5c00] focus:outline-none" />
            </div>
            <div className="pt-5">
              <label className="inline-flex items-center gap-2 cursor-pointer select-none">
                <div className="relative" onClick={() => setIsActive(!isActive)}>
                  <div className={cn('w-9 h-5 rounded-full transition-colors', isActive ? 'bg-[#ff5c00]' : 'bg-gray-300')} />
                  <div className={cn('absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform', isActive && 'translate-x-4')} />
                </div>
                <span className={cn('text-sm font-medium', isActive ? 'text-gray-900' : 'text-gray-400')}>{isActive ? 'Active' : 'Inactive'}</span>
              </label>
            </div>
          </div>
          <div className="col-span-6">
            <label className="block text-xs font-medium text-gray-500 mb-1">Description</label>
            <input type="text" value={description} onChange={e => setDescription(e.target.value)} placeholder="Internal description…" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#ff5c00] focus:outline-none focus:ring-1 focus:ring-[#ff5c00]" />
          </div>
        </div>
      </div>

      {/* Tabs — styled like other admin pages */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center border-b border-gray-200 px-1">
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                'inline-flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
                activeTab === tab.key ? 'border-[#ff5c00] text-[#ff5c00]' : 'border-transparent text-gray-500 hover:text-gray-700',
              )}
            >
              <tab.icon className="h-4 w-4" /> {tab.label}
              {tab.badge !== undefined && (
                <span className={cn(
                  'text-[10px] font-semibold px-1.5 py-0.5 rounded-full',
                  activeTab === tab.key ? 'bg-[#ff5c00]/10 text-[#ff5c00]' : 'bg-gray-100 text-gray-500',
                )}>{tab.badge}</span>
              )}
            </button>
          ))}
        </div>

        <div className="p-5">
          {activeTab === 'fields' && (
            <div className="space-y-3">
              {fields.map((field, i) => (
                <FieldCard
                  key={`${field.key}-${i}`} field={field} index={i} total={fields.length}
                  expanded={expandedField === i} onToggle={() => setExpandedField(expandedField === i ? null : i)}
                  onChange={f => { const arr = [...fields]; arr[i] = f; setFields(arr) }}
                  onMoveUp={() => moveField(i, i - 1)} onMoveDown={() => moveField(i, i + 1)}
                  onRemove={() => { setFields(fields.filter((_, fi) => fi !== i)); setExpandedField(null) }}
                />
              ))}
              <div className="border-2 border-dashed border-gray-200 rounded-lg p-4">
                <p className="text-xs font-medium text-gray-500 mb-3">Add Field</p>
                <div className="flex flex-wrap gap-2">
                  {FIELD_TYPES.map(t => (
                    <button key={t.value} onClick={() => addField(t.value)} className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:border-[#ff5c00]/30 hover:text-[#ff5c00] hover:bg-orange-50/50 transition-colors">
                      <Plus className="h-3 w-3" /> {t.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
          {activeTab === 'logic' && <LogicEditor rules={rules} fieldKeys={fieldKeys} onChange={setRules} />}
          {activeTab === 'mappings' && <MappingsEditor mappings={mappings} fieldKeys={fieldKeys} onChange={setMappings} />}
          {activeTab === 'preview' && (
            <FormPreviewComponent fields={fields} rules={rules} />
          )}
        </div>
      </div>

      {/* Version History — only show when editing an existing form */}
      {formId && existing && (
        <VersionHistory
          currentForm={existing}
          onViewVersion={(id) => onBack()}
        />
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ═══════════════════════════════════════════════════════════════════════════════

export default function FormBuilderPage() {
  const [mode, setMode] = useState<'list' | 'edit'>('list')
  const [editId, setEditId] = useState<number | null>(null)

  return mode === 'list' ? (
    <FormList onEdit={id => { setEditId(id); setMode('edit') }} onCreate={() => { setEditId(null); setMode('edit') }} />
  ) : (
    <FormEditor formId={editId} onBack={() => { setMode('list'); setEditId(null) }} />
  )
}
