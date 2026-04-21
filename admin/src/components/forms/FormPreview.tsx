import { useState, useMemo } from 'react'
import { cn } from '@/lib/utils'
import type { FormField, ConditionalRule } from '@/hooks/useForms'

const NON_INPUT_TYPES = new Set(['heading', 'paragraph'])

export default function FormPreview({ fields, rules = [] }: { fields: FormField[]; rules?: ConditionalRule[] }) {
  const [formData, setFormData] = useState<Record<string, unknown>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})

  const visibleKeys = useMemo(() => {
    const vis: Record<string, boolean> = {}
    for (const rule of rules) {
      if (!rule.target_field || !rule.conditions.length) continue
      const results = rule.conditions.map(c => {
        const actual = formData[c.field_key]
        switch (c.operator) {
          case 'equals': return String(actual ?? '') === String(c.value)
          case 'not_equals': return String(actual ?? '') !== String(c.value)
          case 'contains': return typeof actual === 'string' && actual.includes(String(c.value))
          case 'gt': return Number(actual) > Number(c.value)
          case 'lt': return Number(actual) < Number(c.value)
          case 'is_empty': return actual === undefined || actual === null || actual === ''
          case 'is_not_empty': return actual !== undefined && actual !== null && actual !== ''
          default: return false
        }
      })
      const met = rule.match === 'any' ? results.some(Boolean) : results.every(Boolean)
      vis[rule.target_field] = rule.action === 'show' ? met : !met
    }
    return vis
  }, [formData, rules])

  const isVisible = (key: string) => !(key in visibleKeys) || visibleKeys[key]

  const setValue = (key: string, value: unknown) => {
    setFormData(prev => ({ ...prev, [key]: value }))
    setErrors(prev => { const n = { ...prev }; delete n[key]; return n })
  }

  const handleSubmit = () => {
    const newErrors: Record<string, string> = {}
    for (const f of fields) {
      if (!isVisible(f.key) || NON_INPUT_TYPES.has(f.field_type)) continue
      if (f.required) {
        const v = formData[f.key]
        if (v === undefined || v === null || v === '' || (Array.isArray(v) && v.length === 0))
          newErrors[f.key] = `${f.label} is required`
      }
    }
    setErrors(newErrors)
    if (!Object.keys(newErrors).length) alert('✓ Valid!\n\n' + JSON.stringify(formData, null, 2))
  }

  const handleReset = () => { setFormData({}); setErrors({}) }

  if (!fields.length) return <p className="text-gray-400 text-sm py-8 text-center">Add fields to see a preview</p>

  const inputCls = (key: string) => cn(
    'w-full rounded-lg border px-3 py-2.5 text-sm transition-colors focus:outline-none focus:ring-1',
    errors[key] ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : 'border-gray-300 focus:border-[#ff5c00] focus:ring-[#ff5c00]',
  )

  const widthCls = (w?: string) => w === 'half' ? 'col-span-1' : w === 'third' ? 'col-span-1' : 'col-span-2'

  return (
    <div className="max-w-2xl mx-auto">
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#ff5c00] to-[#ff7a2e] px-6 py-4">
          <h3 className="text-white font-semibold text-lg">Coverage Questionnaire</h3>
          <p className="text-white/70 text-sm mt-0.5">Required fields are marked with <span className="text-white">*</span></p>
        </div>

        {/* Fields grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-5 p-6">
          {fields.map(f => {
            if (!isVisible(f.key)) return null

            if (f.field_type === 'heading') return (
              <div key={f.key} className="col-span-2 pt-3 pb-1 border-b border-gray-100">
                <h3 className="font-semibold text-base text-gray-900">{f.label}</h3>
              </div>
            )
            if (f.field_type === 'paragraph') return (
              <p key={f.key} className="col-span-2 text-sm text-gray-500 leading-relaxed">{f.label}</p>
            )

            return (
              <div key={f.key} className={widthCls(f.width)}>
                <label className="text-[11px] font-semibold text-gray-700 mb-1.5 block tracking-wide">
                  {f.label}{f.required && <span className="text-[#ff5c00] ml-0.5">*</span>}
                </label>

                {f.field_type === 'textarea' ? (
                  <textarea placeholder={f.placeholder} value={String(formData[f.key] ?? '')} onChange={e => setValue(f.key, e.target.value)} rows={3} className={inputCls(f.key)} />

                ) : f.field_type === 'select' ? (
                  <select value={String(formData[f.key] ?? '')} onChange={e => setValue(f.key, e.target.value)} className={inputCls(f.key)}>
                    <option value="">{f.placeholder || 'Select…'}</option>
                    {(f.options || []).map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>

                ) : f.field_type === 'radio' ? (
                  <div className="flex flex-wrap gap-x-5 gap-y-2 mt-1">
                    {(f.options || []).map(o => (
                      <label key={o.value} className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
                        <input type="radio" name={f.key} value={o.value} checked={formData[f.key] === o.value} onChange={() => setValue(f.key, o.value)} className="accent-[#ff5c00] w-4 h-4" />
                        {o.label}
                      </label>
                    ))}
                  </div>

                ) : f.field_type === 'checkbox' ? (
                  <label className="flex items-center gap-2.5 cursor-pointer text-sm text-gray-700 mt-1">
                    <input type="checkbox" checked={!!formData[f.key]} onChange={e => setValue(f.key, e.target.checked)} className="accent-[#ff5c00] w-4 h-4 rounded" />
                    {f.placeholder || f.label}
                  </label>

                ) : f.field_type === 'checkbox_group' || f.field_type === 'multi_select' ? (
                  <div className="space-y-2 mt-1">
                    {(f.options || []).map(o => {
                      const arr = (formData[f.key] as string[]) || []
                      const checked = arr.includes(o.value)
                      return (
                        <label key={o.value} className="flex items-center gap-2.5 cursor-pointer text-sm text-gray-700">
                          <input type="checkbox" checked={checked} onChange={() => setValue(f.key, checked ? arr.filter(v => v !== o.value) : [...arr, o.value])} className="accent-[#ff5c00] w-4 h-4 rounded" />
                          {o.label}
                        </label>
                      )
                    })}
                  </div>

                ) : f.field_type === 'file_upload' ? (
                  <div className="border-2 border-dashed border-gray-200 rounded-lg p-5 text-center hover:border-[#ff5c00]/40 transition-colors cursor-pointer">
                    <p className="text-sm text-gray-400">Drag & drop, or <span className="text-[#ff5c00] font-medium">browse</span></p>
                  </div>

                ) : f.field_type === 'address' ? (
                  <div className="space-y-2">
                    <input placeholder="Street address" value={String((formData[f.key] as any)?.street || '')} onChange={e => setValue(f.key, { ...(formData[f.key] as any || {}), street: e.target.value })} className={inputCls(f.key)} />
                    <input placeholder="Apt/Suite (optional)" value={String((formData[f.key] as any)?.suite || '')} onChange={e => setValue(f.key, { ...(formData[f.key] as any || {}), suite: e.target.value })} className={inputCls(f.key)} />
                    <div className="grid grid-cols-3 gap-2">
                      <input placeholder="City" value={String((formData[f.key] as any)?.city || '')} onChange={e => setValue(f.key, { ...(formData[f.key] as any || {}), city: e.target.value })} className={inputCls(f.key)} />
                      <input placeholder="State" value={String((formData[f.key] as any)?.state || '')} onChange={e => setValue(f.key, { ...(formData[f.key] as any || {}), state: e.target.value })} className={inputCls(f.key)} />
                      <input placeholder="Zip" value={String((formData[f.key] as any)?.zip || '')} onChange={e => setValue(f.key, { ...(formData[f.key] as any || {}), zip: e.target.value })} className={inputCls(f.key)} />
                    </div>
                  </div>

                ) : (
                  <input
                    type={['number','currency','percentage'].includes(f.field_type) ? 'number' : f.field_type === 'date' ? 'date' : f.field_type === 'email' ? 'email' : 'text'}
                    placeholder={f.placeholder}
                    value={String(formData[f.key] ?? '')}
                    onChange={e => setValue(f.key, ['number','currency','percentage'].includes(f.field_type) ? (e.target.value ? Number(e.target.value) : '') : e.target.value)}
                    className={inputCls(f.key)}
                  />
                )}

                {errors[f.key] && <p className="text-[11px] text-red-500 mt-1">{errors[f.key]}</p>}
                {f.help_text && !errors[f.key] && <p className="text-[11px] text-gray-400 mt-1">{f.help_text}</p>}
              </div>
            )
          })}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-100 px-6 py-4 flex items-center justify-between bg-gray-50/50">
          <button onClick={handleReset} className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors">Reset</button>
          <button onClick={handleSubmit} className="rounded-lg bg-[#ff5c00] px-6 py-2.5 text-sm font-medium text-white hover:bg-[#e05200] transition-colors shadow-sm">Submit</button>
        </div>
      </div>

      {/* Debug data */}
      {Object.keys(formData).length > 0 && (
        <details className="mt-4">
          <summary className="text-xs font-medium text-gray-400 cursor-pointer hover:text-gray-600">Form Data (debug)</summary>
          <pre className="mt-2 rounded-lg bg-gray-900 text-gray-100 p-4 text-xs overflow-auto max-h-60">{JSON.stringify(formData, null, 2)}</pre>
        </details>
      )}
    </div>
  )
}
