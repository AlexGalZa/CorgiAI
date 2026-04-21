/* ─── Coverage explainer tooltips ─── */
export const COVERAGE_TOOLTIPS: Record<string, string> = {
  'technology-errors-and-omissions': 'Covers claims if your software or tech services cause financial loss to a client.',
  'cyber-liability': 'Covers costs from data breaches, hacking, and cyber incidents.',
  'directors-and-officers': 'Protects company leaders from personal liability in business decisions.',
  'commercial-general-liability': 'Covers bodily injury and property damage claims from third parties.',
  'employment-practices-liability': 'Covers claims from employees like wrongful termination or discrimination.',
  'fiduciary-liability': 'Protects against claims related to employee benefit plan mismanagement.',
  'hired-and-non-owned-auto': 'Covers accidents in vehicles your employees use for business but don\'t own.',
  'media-liability': 'Covers claims from your published content — copyright, defamation, etc.',
};

/* ─── Coverage type display config ─── */
export const COVERAGE_CONFIG: Record<
  string,
  { label: string; image: string | null }
> = {
  'directors-and-officers': {
    label: 'Directors & Officers (D&O)',
    image: '/policy-directors-officers-1.png',
  },
  'technology-errors-and-omissions': {
    label: 'Technology E&O',
    image: '/policy-directors-officers-2.png',
  },
  'cyber-liability': { label: 'Cyber Liability', image: null },
  'commercial-general-liability': {
    label: 'Commercial General Liability',
    image: null,
  },
  'employment-practices-liability': {
    label: 'Employment Practices Liability',
    image: '/policy-directors-officers-1.png',
  },
  'fiduciary-liability': { label: 'Fiduciary Liability', image: null },
  'hired-and-non-owned-auto': { label: 'Hired & Non-Owned Auto', image: null },
  'media-liability': { label: 'Media Liability', image: null },
};

export const LIMIT_OPTIONS = [1_000_000, 2_000_000, 3_000_000, 5_000_000];
export const RETENTION_OPTIONS = [5_000, 10_000, 25_000, 50_000];

export const RECOMMENDED_COVERAGES = [
  {
    name: 'Tech E&O',
    slug: 'technology-errors-and-omissions',
    desc: 'Covers financial losses caused by failures of your tech product or services. Required by most enterprise contracts.',
    image: '/rec-tech-professional-liability-1.png',
    socialText: '240+ startups at your stage have this',
    avatars: [
      { letter: 'A', color: 'var(--color-muted)' },
      { letter: 'C', color: 'var(--color-muted)' },
      { letter: 'M', color: 'var(--color-muted)' },
    ],
  },
  {
    name: 'Cyber Liability',
    slug: 'cyber-liability',
    desc: 'Covers data breaches, ransomware, and cyber incidents. Increasingly required by enterprise and mid-market clients.',
    image: '/rec-tech-professional-liability-2.png',
    socialText: 'Up 40% among Series A companies',
    avatars: [
      { letter: 'R', color: 'var(--color-muted)' },
      { letter: 'K', color: 'var(--color-muted)' },
      { letter: 'P', color: 'var(--color-muted)' },
    ],
  },
];

/* ─── Helper functions ─── */

export function getCoverageTooltip(slug: string): string | undefined {
  return COVERAGE_TOOLTIPS[slug];
}

export function getCoverageLabel(slug: string): string {
  return COVERAGE_CONFIG[slug]?.label ?? slug;
}

export function getCoverageImage(slug: string): string | null {
  return COVERAGE_CONFIG[slug]?.image ?? '/policy-directors-officers-1.png';
}

export function formatPolicyDate(dateStr: string): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('en-US', {
    month: '2-digit',
    day: '2-digit',
    year: 'numeric',
  });
}

export function getRemainingDays(expirationDate: string): number {
  const now = new Date();
  const exp = new Date(expirationDate);
  const diff = exp.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}
