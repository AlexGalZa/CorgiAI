export const COVERAGE_CONFIG: Record<string, { label: string; description: string; icon: string; color: string }> = {
  'technology-errors-and-omissions': { label: 'Tech E&O', description: 'Covers claims if your software causes financial loss', icon: 'shield', color: 'var(--color-muted)' },
  'cyber-liability': { label: 'Cyber', description: 'Covers data breaches and cyber incidents', icon: 'lock', color: 'var(--color-muted)' },
  'directors-and-officers': { label: 'D&O', description: 'Protects company leaders from personal liability', icon: 'users', color: 'var(--color-muted)' },
  'commercial-general-liability': { label: 'CGL', description: 'Covers third-party bodily injury and property damage', icon: 'shield', color: 'var(--color-muted)' },
  'employment-practices-liability': { label: 'EPLI', description: 'Covers employee claims like wrongful termination', icon: 'briefcase', color: 'var(--color-muted)' },
  'fiduciary-liability': { label: 'Fiduciary', description: 'Covers benefit plan mismanagement claims', icon: 'scale', color: 'var(--color-muted)' },
  'hired-and-non-owned-auto': { label: 'HNOA', description: 'Covers accidents in non-owned business vehicles', icon: 'car', color: 'var(--color-muted)' },
  'media-liability': { label: 'Media', description: 'Covers copyright and defamation claims', icon: 'megaphone', color: 'var(--color-muted)' },
};

export function getCoverageLabel(slug: string): string {
  return COVERAGE_CONFIG[slug]?.label ?? slug;
}
export function getCoverageDescription(slug: string): string {
  return COVERAGE_CONFIG[slug]?.description ?? '';
}
