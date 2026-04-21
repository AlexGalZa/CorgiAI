/**
 * Shared custom tooltip for Recharts.
 *
 * Drop-in replacement:
 *   <Tooltip content={<ChartTooltip />} isAnimationActive={false} />
 *
 * The component itself only controls rendering. To eliminate jitter,
 * every <Tooltip> that uses this MUST also set:
 *   isAnimationActive={false}
 *   wrapperStyle={{ pointerEvents: 'none' }}
 *
 * Use the TOOLTIP_PROPS spread helper exported below for convenience.
 */

interface Payload {
  name?: string
  value?: number | string
  color?: string
  dataKey?: string
}

interface ChartTooltipProps {
  active?: boolean
  payload?: Payload[]
  label?: string
  formatter?: (value: number | string, name: string) => string
}

export default function ChartTooltip({
  active,
  payload,
  label,
  formatter,
}: ChartTooltipProps) {
  if (!active || !payload?.length) return null

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2.5 shadow-lg ring-1 ring-black/5">
      {label && (
        <p className="mb-1.5 text-xs font-medium text-gray-500">{label}</p>
      )}
      <div className="space-y-1">
        {payload.map((entry, i) => {
          const name = entry.name ?? String(entry.dataKey ?? '')
          const val = entry.value ?? 0
          const display = formatter ? formatter(val, name) : String(val)
          return (
            <div key={i} className="flex items-center gap-2 text-sm">
              <span
                className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: entry.color ?? '#ff5c00' }}
              />
              <span className="text-gray-600">{name}</span>
              <span className="ml-auto pl-3 font-semibold text-gray-900">
                {display}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/**
 * Spread these props onto every <Tooltip> to eliminate jitter/animation lag.
 *
 * Usage:
 *   <Tooltip content={<ChartTooltip />} {...TOOLTIP_PROPS} />
 */
export const TOOLTIP_PROPS = {
  isAnimationActive: false,
  wrapperStyle: { pointerEvents: 'none' as const, zIndex: 20 },
  allowEscapeViewBox: { x: false, y: false },
} as const
