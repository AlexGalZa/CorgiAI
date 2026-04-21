import type {
  Formatter,
  NameType,
  ValueType,
} from 'recharts/types/component/DefaultTooltipContent'

import { formatCurrency } from './formatters'

function toNumber(value: ValueType | undefined): number {
  if (value === undefined) return NaN
  if (Array.isArray(value)) return Number(value[0])
  return Number(value)
}

export const currencyFormatter: Formatter<ValueType, NameType> = (value) =>
  formatCurrency(toNumber(value))

export const percentFormatter: Formatter<ValueType, NameType> = (value) => {
  const num = toNumber(value)
  if (Number.isNaN(num)) return '—'
  return `${num.toFixed(1)}%`
}
