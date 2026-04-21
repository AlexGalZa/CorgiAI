import { useState } from 'react'
import { Download } from 'lucide-react'
import { toast } from 'sonner'
import api from '@/lib/api'

interface ExportAllButtonProps {
  /** API endpoint path, e.g. '/admin/policies' */
  endpoint: string
  /** Filename for the downloaded CSV (without extension) */
  filename: string
  /** Column definitions for the CSV header and value extraction */
  columns: { key: string; header: string }[]
}

function toCsv(
  data: Record<string, unknown>[],
  columns: { key: string; header: string }[],
): string {
  const header = columns.map((c) => `"${c.header}"`).join(',')
  const rows = data.map((row) =>
    columns
      .map((c) => {
        const val = row[c.key]
        if (val === null || val === undefined) return '""'
        const str = String(val).replace(/"/g, '""')
        return `"${str}"`
      })
      .join(','),
  )
  return [header, ...rows].join('\n')
}

export default function ExportAllButton({ endpoint, filename, columns }: ExportAllButtonProps) {
  const [isExporting, setIsExporting] = useState(false)

  const handleExportAll = async () => {
    setIsExporting(true)
    try {
      const separator = endpoint.includes('?') ? '&' : '?'
      const { data } = await api.get(`${endpoint}${separator}page_size=10000`)
      const rows = data?.results ?? data
      if (!Array.isArray(rows) || rows.length === 0) {
        toast.info('No data to export')
        return
      }
      const csv = toCsv(rows as Record<string, unknown>[], columns)
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${filename}-all.csv`
      a.click()
      URL.revokeObjectURL(url)
      toast.success(`Exported ${rows.length} rows`)
    } catch (err) {
      toast.error('Export failed — please try again')
      console.error('Export all failed:', err)
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <button
      onClick={handleExportAll}
      disabled={isExporting}
      className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50 disabled:opacity-50"
      title="Export all rows as CSV"
    >
      <Download className={`h-3.5 w-3.5 ${isExporting ? 'animate-pulse' : ''}`} />
      {isExporting ? 'Exporting…' : 'Export All'}
    </button>
  )
}
