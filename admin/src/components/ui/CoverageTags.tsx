import { getCoverageLabel } from '@/lib/formatters'

const TAG_COLORS: Record<string, string> = {
  cgl: 'bg-blue-50 text-blue-700',
  cyber: 'bg-purple-50 text-purple-700',
  tech_eo: 'bg-indigo-50 text-indigo-700',
  workers_comp: 'bg-amber-50 text-amber-700',
  dno: 'bg-rose-50 text-rose-700',
  bop: 'bg-teal-50 text-teal-700',
  crime: 'bg-red-50 text-red-700',
  epl: 'bg-orange-50 text-orange-700',
  cul: 'bg-sky-50 text-sky-700',
  med_malpractice: 'bg-pink-50 text-pink-700',
  comm_auto: 'bg-lime-50 text-lime-700',
  hnoa: 'bg-lime-50 text-lime-700',
  inland_marine: 'bg-cyan-50 text-cyan-700',
  aviation: 'bg-cyan-50 text-cyan-700',
}
const DEFAULT_TAG = 'bg-gray-100 text-gray-700'

interface CoverageTagsProps {
  codes: string | string[] | null | undefined
  /** Max tags before "+N" overflow. Default 4 */
  max?: number
}

export default function CoverageTags({ codes, max = 4 }: CoverageTagsProps) {
  if (!codes) return <span className="text-sm text-gray-400">—</span>

  let arr: string[]
  if (typeof codes === 'string') {
    try { arr = JSON.parse(codes) } catch { arr = [codes] }
  } else {
    arr = codes
  }

  if (!Array.isArray(arr) || arr.length === 0) {
    return <span className="text-sm text-gray-400">—</span>
  }

  const visible = arr.slice(0, max)
  const overflow = arr.length - max

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {visible.map((code) => (
        <span
          key={code}
          className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${TAG_COLORS[code] ?? DEFAULT_TAG}`}
        >
          {getCoverageLabel(code)}
        </span>
      ))}
      {overflow > 0 && (
        <span className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
          +{overflow}
        </span>
      )}
    </div>
  )
}
