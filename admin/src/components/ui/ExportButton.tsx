import { Download } from 'lucide-react'

interface ExportButtonProps<T> {
  data: T[]
  filename: string
  columns: { key: string; header: string }[]
}

function toCsv<T extends Record<string, unknown>>(
  data: T[],
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

export default function ExportButton<T extends Record<string, unknown>>({
  data,
  filename,
  columns,
}: ExportButtonProps<T>) {
  const handleExport = () => {
    const csv = toCsv(data, columns)
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${filename}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <button
      onClick={handleExport}
      disabled={data.length === 0}
      className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50 disabled:opacity-50"
    >
      <Download className="h-3.5 w-3.5" />
      Export
    </button>
  )
}
