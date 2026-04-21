import { StatusCheckIcon, ClockIcon } from '@/components/icons';

interface BadgeProps {
  variant: 'active' | 'pending' | 'expired' | 'submitted' | 'closed' | 'ai' | 'lp' | 'ch' | 'under_review' | 'approved' | 'denied' | 'revoked';
  children?: React.ReactNode;
}

const DESIGNATION_LABELS: Record<string, string> = {
  ai: 'Additional insured',
  lp: 'Loss payee',
  ch: 'Certificate holder',
};

export function Badge({ variant, children }: BadgeProps) {
  const styles: Record<string, string> = {
    active: 'bg-success-bg text-success-dark',
    pending: 'bg-badge-pending-bg text-badge-pending-text',
    expired: 'bg-bg text-muted',
    submitted: 'bg-warning-bg border border-warning-border text-warning-text',
    closed: 'bg-bg text-muted',
    ai: 'bg-badge-orange-bg text-primary',
    lp: 'bg-badge-orange-bg text-primary',
    ch: 'bg-badge-orange-bg text-primary',
    under_review: 'bg-bg text-heading',
    approved: 'bg-success-bg text-success-dark',
    denied: 'bg-danger-bg text-danger',
    revoked: 'bg-danger-bg text-danger',
  };

  const labels: Record<string, string> = {
    active: 'Active',
    pending: 'In Progress',
    expired: 'Expired',
    submitted: 'Submitted',
    closed: 'Closed',
    under_review: 'Under Review',
    approved: 'Approved',
    denied: 'Denied',
    revoked: 'Revoked',
  };

  if (['ai', 'lp', 'ch'].includes(variant)) {
    return (
      <span className={`inline-flex items-center gap-1 rounded-full py-1 px-2 pl-1.5 leading-none ${styles[variant]}`}>
        <StatusCheckIcon size={10} color="var(--color-primary)" />
        <span className="text-[10px] font-semibold whitespace-nowrap">
          {DESIGNATION_LABELS[variant]}
        </span>
      </span>
    );
  }

  if (variant === 'active' || variant === 'approved') {
    return (
      <span className={`inline-flex items-center gap-1 rounded-full py-1 px-2 pl-1.5 leading-none ${styles[variant]}`}>
        <StatusCheckIcon />
        <span className="text-[10px] font-semibold whitespace-nowrap">{children ?? labels[variant]}</span>
      </span>
    );
  }

  if (variant === 'submitted') {
    return (
      <span className={`inline-flex items-center gap-1 rounded-full py-[4.5px] px-[8.5px] pl-[4.5px] leading-none ${styles[variant]}`}>
        <ClockIcon />
        <span className="text-[10px] font-semibold whitespace-nowrap">{children ?? 'Submitted'}</span>
      </span>
    );
  }

  if (variant === 'under_review') {
    return (
      <span className={`inline-flex items-center gap-1 rounded-full py-[4.5px] px-[8.5px] pl-[4.5px] leading-none ${styles[variant]}`}>
        <ClockIcon size={14} color="var(--color-heading)" />
        <span className="text-[10px] font-semibold whitespace-nowrap">{children ?? 'Under Review'}</span>
      </span>
    );
  }

  return (
    <span className={`inline-block text-[10px] font-semibold py-1 px-2 pl-1.5 rounded-full ${styles[variant] || ''}`}>
      {children ?? labels[variant] ?? variant}
    </span>
  );
}
