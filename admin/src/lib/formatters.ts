// ─── Currency ────────────────────────────────────────────────────────────────

export function formatCurrency(amount: number | string | null): string {
  if (amount === null || amount === undefined) return '—'
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  if (isNaN(num)) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num)
}

// ─── Date ────────────────────────────────────────────────────────────────────

export function formatDate(date: string): string {
  if (!date) return '—'
  return new Date(date).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

// ─── Relative Time ───────────────────────────────────────────────────────────

export function formatRelativeTime(date: string): string {
  if (!date) return '—'
  const now = Date.now()
  const then = new Date(date).getTime()
  const diffMs = now - then

  const seconds = Math.floor(diffMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  const weeks = Math.floor(days / 7)
  const months = Math.floor(days / 30)

  if (seconds < 60) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}d ago`
  if (weeks < 5) return `${weeks}w ago`
  return `${months}mo ago`
}

// ─── Account Executive Name ──────────────────────────────────────────────────

export function getAEName(email: string): string {
  if (!email) return '—'
  const local = email.split('@')[0]
  if (!local) return '—'
  // Capitalize first letter
  return local.charAt(0).toUpperCase() + local.slice(1).toLowerCase()
}

// ─── Coverage Labels ─────────────────────────────────────────────────────────

const coverageLabels: Record<string, string> = {
  // Codes from BrokeredQuoteRequest.COVERAGE_TYPE_CHOICES
  cgl: 'CGL',
  cul: 'Umbrella',
  cyber: 'Cyber',
  tech_eo: 'Tech E&O',
  workers_comp: 'Workers Comp',
  dno: 'D&O',
  bop: 'BOP',
  crime: 'Crime',
  epl: 'EPL',
  med_malpractice: 'Med Mal',
  comm_auto: 'Comm Auto',
  hnoa: 'HNOA',
  kidnap_ransom: 'K&R',
  inland_marine: 'Inland Marine',
  aviation: 'Aviation',
  real_estate_eo: 'Real Estate E&O',
  misc_eo: 'Misc E&O',
  reps_warranties: 'Reps & Warranties',
  fiduciary: 'Fiduciary',
  erisa: 'ERISA',
  pollution: 'Pollution',
  international: 'International',
  media: 'Media',
  crime_bond: 'Crime Bond',
  uas_aviation: 'UAS/Aviation',
  other: 'Other',
  // Legacy/alternate codes
  gl: 'CGL',
  pl: 'Prof. Liability',
  wc: 'Workers Comp',
  do: 'D&O',
  eo: 'E&O',
  auto: 'Comm Auto',
  umbrella: 'Umbrella',
  property: 'Property',
  epli: 'EPL',
  ml: 'Media',
  surety: 'Surety Bond',
}

export function getCoverageLabel(code: string): string {
  if (!code) return '—'
  const normalized = code.toLowerCase().trim()
  return coverageLabels[normalized] ?? code.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function getCoverageLabels(codes: string | string[] | null | undefined): string {
  if (!codes) return '—'
  if (typeof codes === 'string') {
    try {
      const parsed: unknown = JSON.parse(codes)
      if (Array.isArray(parsed)) return (parsed as string[]).map(getCoverageLabel).join(', ')
      return getCoverageLabel(codes)
    } catch {
      return getCoverageLabel(codes)
    }
  }
  if (!Array.isArray(codes) || codes.length === 0) return '—'
  return codes.map(getCoverageLabel).join(', ')
}
