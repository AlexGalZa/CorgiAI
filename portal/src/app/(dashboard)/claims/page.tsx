'use client';

import { useState, useCallback, useRef, useMemo } from 'react';
import { usePageTitle } from '@/hooks/use-page-title';
import { useClaims, useCreateClaim, useClaimDetail } from '@/hooks/use-claims';
import { usePolicies } from '@/hooks/use-policies';
import { useAppStore } from '@/stores/use-app-store';
import { Btn3DWhite, Btn3DOrange, Btn3DDark, BtnSecondary } from '@/components/ui/button';
import { Input, Textarea, Label, Select } from '@/components/ui/input';
import { CustomSelect } from '@/components/ui/custom-select';
import { Badge } from '@/components/ui/badge';

import {
  PlusIcon, DownloadIcon, CopyIcon, UploadIcon, CloseIcon,
  ChevronLeftIcon, ClaimsIcon, RefreshIcon,
} from '@/components/icons';
import type { ClaimsStep, APIClaimListItem } from '@/types';
import { formatDateLong, getCoverageLabel } from '@/lib/utils';
import { trackEvent } from '@/lib/analytics';

type ClaimBadgeVariant = 'submitted' | 'under_review' | 'approved' | 'denied' | 'closed' | 'pending';

function getClaimBadgeVariant(status: string): ClaimBadgeVariant {
  const s = status.toLowerCase();
  if (s === 'open' || s === 'submitted') return 'submitted';
  if (s === 'in_progress' || s === 'in progress' || s === 'under_review') return 'under_review';
  if (s === 'approved' || s === 'resolved') return 'approved';
  if (s === 'denied' || s === 'rejected') return 'denied';
  if (s === 'closed') return 'closed';
  return 'pending';
}

/* ─── Stat card ─── */
function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex-1 bg-surface border border-border rounded-2xl px-5 py-4 flex flex-col gap-1">
      <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] leading-[1.2]">{label}</div>
      <div className="text-xl font-medium text-heading tracking-[-0.5px] leading-none">{value}</div>
    </div>
  );
}

/* ─── Loading skeleton ─── */
function TableSkeleton() {
  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-8 animate-pulse">
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-2">
          <div className="h-3 w-16 bg-border rounded" />
          <div className="h-8 w-64 bg-border rounded" />
        </div>
        <div className="h-9 w-32 bg-border rounded-xl" />
      </div>
      <div className="flex gap-4">
        <div className="flex-1 h-20 bg-border rounded-2xl" />
        <div className="flex-1 h-20 bg-border rounded-2xl" />
        <div className="flex-1 h-20 bg-border rounded-2xl" />
      </div>
      <div className="bg-surface border border-border rounded-2xl overflow-hidden">
        <div className="px-6 py-3 bg-bg border-b border-border flex gap-6">
          {[140, 120, 80, 80, 80, 50].map((w, i) => (
            <div key={i} className="h-3 bg-border rounded" style={{ width: w }} />
          ))}
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="px-6 py-4 border-b border-border flex gap-6 items-center">
            <div className="w-10 h-10 bg-border rounded-xl shrink-0" />
            <div className="flex-1 flex gap-6">
              {[140, 100, 70, 80, 80].map((w, j) => (
                <div key={j} className="h-4 bg-border rounded" style={{ width: w }} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function truncateText(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max).trim() + '…';
}

export default function ClaimsPage() {
  usePageTitle('Claims');
  const { data: claims, isLoading, isError, refetch } = useClaims();
  const { data: policies } = usePolicies();
  const createClaimMutation = useCreateClaim();
  const { showToast } = useAppStore();

  const hasActivePolicies = (policies ?? []).filter((p) => p.status === 'active').length > 0;
  const [step, setStep] = useState<ClaimsStep>('landing');
  const [formPolicyId, setFormPolicyId] = useState('');
  const [formFname, setFormFname] = useState('');
  const [formLname, setFormLname] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formPhone, setFormPhone] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [doneClaim, setDoneClaim] = useState<{ number: string; policy: string; date: string } | null>(null);
  const [expandedClaimNumber, setExpandedClaimNumber] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: claimDetail } = useClaimDetail(expandedClaimNumber);

  const isFormReady =
    formPolicyId && formFname.trim() && formLname.trim() && formEmail.trim() && formPhone.trim() && formDesc.trim();

  const goTo = useCallback((s: ClaimsStep) => {
    setStep(s);
    if (s === 'form') {
      setFormPolicyId('');
      setFormFname('');
      setFormLname('');
      setFormEmail('');
      setFormPhone('');
      setFormDesc('');
      setFiles([]);
    }
  }, []);

  const submit = useCallback(() => {
    const policy = policies?.find((p) => String(p.id) === formPolicyId);
    if (!policy) return;

    createClaimMutation.mutate(
      {
        data: {
          policy_id: policy.id,
          organization_name: '',
          first_name: formFname,
          last_name: formLname,
          email: formEmail,
          phone_number: formPhone,
          description: formDesc,
        },
        attachments: files.length > 0 ? files : undefined,
      },
      {
        onSuccess: (claim) => {
          trackEvent('claim_filed', { claim_number: claim.claim_number, policy_id: policy.id });
          setDoneClaim({
            number: claim.claim_number,
            policy: getCoverageLabel(policy.coverage_type),
            date: formatDateLong(new Date(claim.created_at)),
          });
          setStep('done');
          showToast('Claim submitted successfully');
        },
        onError: (error) => {
          showToast(`Error: ${error.message}`);
        },
      }
    );
  }, [formPolicyId, formFname, formLname, formEmail, formPhone, formDesc, files, policies, createClaimMutation, showToast]);

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const hasActiveFilters = searchQuery !== '' || statusFilter !== 'all' || dateFrom !== '' || dateTo !== '';

  const clearFilters = useCallback(() => {
    setSearchQuery('');
    setStatusFilter('all');
    setDateFrom('');
    setDateTo('');
  }, []);

  // Stats
  const claimsList = claims ?? [];
  const openClaims = claimsList.filter((c: APIClaimListItem) => {
    const s = c.status.toLowerCase();
    return s !== 'closed' && s !== 'resolved' && s !== 'denied';
  }).length;
  const totalFiled = claimsList.length;

  // Filtered list (client-side)
  const filteredClaims = useMemo(() => {
    let list = [...claimsList].reverse();
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      list = list.filter((c) =>
        c.claim_number.toLowerCase().includes(q) ||
        c.policy_number.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q)
      );
    }
    if (statusFilter !== 'all') {
      list = list.filter((c) => c.status.toLowerCase() === statusFilter.toLowerCase());
    }
    if (dateFrom) {
      const from = new Date(dateFrom).getTime();
      list = list.filter((c) => new Date(c.created_at).getTime() >= from);
    }
    if (dateTo) {
      const to = new Date(dateTo).getTime() + 86400000; // inclusive
      list = list.filter((c) => new Date(c.created_at).getTime() <= to);
    }
    return list;
  }, [claimsList, searchQuery, statusFilter, dateFrom, dateTo]);

  // Unique statuses derived from data
  const uniqueStatuses = useMemo(() => {
    const set = new Set(claimsList.map((c) => c.status.toLowerCase()));
    return Array.from(set);
  }, [claimsList]);

  if (isLoading) return <TableSkeleton />;

  if (isError) {
    return (
      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-8">
        <div className="flex items-end justify-between">
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">Claims</span>
            <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">File &amp; Track Your Claims.</h1>
          </div>
        </div>
        <div className="flex flex-col items-center gap-4 pt-12">
          <div className="text-sm text-muted">Failed to load claims.</div>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-primary bg-transparent border border-primary rounded-xl px-4 py-2 cursor-pointer hover:bg-primary hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
          >
            <RefreshIcon size={14} /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={step === 'form' || step === 'done'
      ? `flex flex-col items-center ${step === 'done' ? 'justify-center pt-[200px]' : 'justify-start'} min-h-[calc(100vh-var(--spacing-header))] px-4 sm:px-6 md:px-12 py-6 md:py-10 pb-20 gap-6`
      : 'max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-8'
    }>

      {/* LANDING */}
      {step === 'landing' && (
        <>
          {(!claims || claims.length === 0) ? (
            /* Empty state */
            <div className="flex flex-col gap-8 animate-enter">
              <div className="flex items-end justify-between">
                <div className="flex flex-col gap-1">
                  <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">Claims</span>
                  <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">File &amp; Track Your Claims.</h1>
                </div>
                {hasActivePolicies && (
                  <BtnSecondary onClick={() => goTo('form')}>
                    <PlusIcon /> File a claim
                  </BtnSecondary>
                )}
              </div>
              <div className="border border-dashed border-border rounded-2xl text-center py-16 px-10">
                <div className="mb-4 mx-auto w-12 h-12 flex items-center justify-center">
                  <ClaimsIcon className="w-6 h-6 stroke-muted" />
                </div>
                <div className="text-sm font-medium text-heading mb-1">No claims yet</div>
                <div className="text-[13px] text-muted leading-[1.5] max-w-sm mx-auto mb-5">
                  {hasActivePolicies
                    ? "File a claim if you've experienced a covered incident. Our advocate team is here to help."
                    : "You need an active policy before you can file a claim. Get a quote to get started."}
                </div>
                {hasActivePolicies && (
                  <button
                    onClick={() => goTo('form')}
                    className="inline-flex items-center gap-1.5 text-sm font-medium text-primary bg-transparent border border-primary rounded-xl px-4 py-2 cursor-pointer hover:bg-primary hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                  >
                    <PlusIcon size={14} /> File a claim
                  </button>
                )}
              </div>
            </div>
          ) : (
            /* Populated – claim cards + inline detail */
            <div className="flex flex-col gap-8 animate-enter">
              {/* Page header */}
              <div className="flex items-end justify-between">
                <div className="flex flex-col gap-1">
                  <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">Claims</span>
                  <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">File &amp; Track Your Claims.</h1>
                </div>
                {hasActivePolicies && (
                  <BtnSecondary onClick={() => goTo('form')}>
                    <PlusIcon /> File a claim
                  </BtnSecondary>
                )}
              </div>

              {/* Stats strip */}
              <div className="flex gap-4">
                <StatCard label="Open claims" value={String(openClaims)} />
                <StatCard label="Total filed" value={String(totalFiled)} />
                <StatCard label="Status" value={openClaims > 0 ? 'Active' : 'All clear'} />
              </div>

              {/* Search + filter bar */}
              <div className="flex flex-col gap-3">
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[180px]">
                    <Label htmlFor="claims-search">Search</Label>
                    <div className="relative">
                      <span className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-muted)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                      </span>
                      <Input
                        id="claims-search"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Claim #, policy #, or description"
                        className="pl-8"
                      />
                    </div>
                  </div>

                  <div className="w-44">
                    <Label htmlFor="claims-status">Status</Label>
                    <Select
                      id="claims-status"
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                    >
                      <option value="all">All statuses</option>
                      {['open', 'submitted', 'in_progress', 'in progress', 'under_review', 'approved', 'resolved', 'paid', 'denied', 'rejected', 'closed']
                        .filter((s) => uniqueStatuses.includes(s))
                        .map((s) => (
                          <option key={s} value={s}>{s.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}</option>
                        ))}
                    </Select>
                  </div>

                  <div className="w-40">
                    <Label htmlFor="claims-from">From</Label>
                    <Input
                      id="claims-from"
                      type="date"
                      value={dateFrom}
                      onChange={(e) => setDateFrom(e.target.value)}
                    />
                  </div>

                  <div className="w-40">
                    <Label htmlFor="claims-to">To</Label>
                    <Input
                      id="claims-to"
                      type="date"
                      value={dateTo}
                      onChange={(e) => setDateTo(e.target.value)}
                    />
                  </div>

                  {hasActiveFilters && (
                    <BtnSecondary onClick={clearFilters}>
                      Clear filters
                    </BtnSecondary>
                  )}
                </div>
              </div>

              {/* Claim cards */}
              {filteredClaims.length === 0 && hasActiveFilters ? (
                <div className="border border-dashed border-border rounded-2xl text-center py-12 px-10 flex flex-col items-center gap-4">
                  <div className="text-sm font-medium text-heading">No claims match these filters</div>
                  <div className="text-[13px] text-muted leading-[1.5] max-w-sm">
                    Try adjusting your search or filters to find what you are looking for.
                  </div>
                  <BtnSecondary onClick={clearFilters}>Clear filters</BtnSecondary>
                </div>
              ) : (
              <div className="flex flex-col gap-4">
                {filteredClaims.map((claim: APIClaimListItem) => {
                  const isExpanded = expandedClaimNumber === claim.claim_number;
                  return (
                    <div key={claim.id} className="flex flex-col">
                      {/* Card */}
                      <div
                        onClick={() => setExpandedClaimNumber(isExpanded ? null : claim.claim_number)}
                        className={`bg-surface border rounded-2xl px-6 py-5 cursor-pointer transition-all hover:shadow-sm ${isExpanded ? 'border-primary/40 shadow-sm rounded-b-none' : 'border-border'}`}
                      >
                        <div className="flex items-center gap-4">
                          {/* Icon */}
                          <div className="w-10 h-10 bg-bg rounded-xl flex items-center justify-center shrink-0">
                            <ClaimsIcon className="w-5 h-5 stroke-heading" />
                          </div>

                          {/* Main info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-sm font-semibold text-heading">{claim.claim_number}</span>
                              <Badge variant={getClaimBadgeVariant(claim.status)} />
                            </div>
                            <div className="text-[13px] text-body leading-[1.4]">{truncateText(claim.description, 100)}</div>
                          </div>

                          {/* Date + chevron */}
                          <div className="flex items-center gap-3 shrink-0">
                            <div className="text-xs text-muted">{formatDateLong(new Date(claim.created_at))}</div>
                            <ChevronLeftIcon className={`w-4 h-4 text-muted transition-transform ${isExpanded ? '-rotate-90' : 'rotate-180'}`} />
                          </div>
                        </div>
                      </div>

                      {/* Expanded detail */}
                      {isExpanded && (
                        <div className="bg-bg border border-t-0 border-primary/40 rounded-b-2xl px-6 py-5 flex flex-col gap-5 animate-enter">
                          {claimDetail && claimDetail.claim_number === claim.claim_number ? (
                            <>
                              {/* Full description */}
                              <div className="flex flex-col gap-2">
                                <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px]">Full Description</div>
                                <div className="bg-surface border border-border rounded-lg p-4 text-sm text-body leading-[1.6]">
                                  {claimDetail.description}
                                </div>
                              </div>

                              {/* Claim info grid */}
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                <div className="bg-surface border border-border rounded-lg p-3">
                                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] mb-1">Policy</div>
                                  <div className="text-sm font-medium text-heading">{claimDetail.policy_number}</div>
                                </div>
                                <div className="bg-surface border border-border rounded-lg p-3">
                                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] mb-1">Filed</div>
                                  <div className="text-sm font-medium text-heading">{formatDateLong(new Date(claimDetail.created_at))}</div>
                                </div>
                                <div className="bg-surface border border-border rounded-lg p-3">
                                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] mb-1">Contact</div>
                                  <div className="text-sm font-medium text-heading">{claimDetail.first_name} {claimDetail.last_name}</div>
                                </div>
                                <div className="bg-surface border border-border rounded-lg p-3">
                                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] mb-1">Status</div>
                                  <Badge variant={getClaimBadgeVariant(claimDetail.status)} />
                                </div>
                              </div>

                              {/* Documents */}
                              {claimDetail.documents.length > 0 && (
                                <div className="flex flex-col gap-2">
                                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px]">
                                    Attachments ({claimDetail.documents.length})
                                  </div>
                                  <div className="bg-surface border border-border rounded-lg overflow-hidden">
                                    {claimDetail.documents.map((doc) => (
                                      <div key={doc.id} className="flex items-center justify-between px-4 py-3 border-b border-border last:border-b-0">
                                        <div className="flex items-center gap-2">
                                          <DownloadIcon className="w-4 h-4 text-muted" />
                                          <span className="text-sm text-heading">{doc.original_filename}</span>
                                        </div>
                                        <span className="text-xs text-muted">{(doc.file_size / 1024).toFixed(0)} KB</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Non-editable notice */}
                              <div className="bg-primary/5 border border-primary/20 rounded-xl px-4 py-3 flex items-start gap-2.5">
                                <div className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                                  <span className="text-primary text-xs font-bold">!</span>
                                </div>
                                <div className="text-[13px] text-body leading-[1.4]">
                                  This claim cannot be edited after submission. If you need to provide additional information, please contact your advocate.
                                </div>
                              </div>
                            </>
                          ) : (
                            /* Loading state for detail */
                            <div className="flex items-center justify-center py-8">
                              <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              )}
            </div>
          )}
        </>
      )}

      {/* FORM */}
      {step === 'form' && (
        <div className="animate-enter w-[600px]">
          <div className="px-4 mb-4">
            <button onClick={() => goTo('landing')} className="inline-flex items-center gap-1 text-xs font-medium text-muted py-1.5 px-3 pl-2 rounded-lg border-none bg-transparent cursor-pointer font-sans transition-all hover:bg-black/5 hover:text-heading focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none">
              <ChevronLeftIcon /> Back to claims
            </button>
          </div>
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            <div className="px-6 py-5 border-b border-border flex flex-col gap-3">
              <div className="flex flex-col gap-2">
                <div className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">File a Claim</div>
                <div className="text-sm font-normal text-body">This is the reason you&apos;re insured in the first place. Corgi is here for you.</div>
              </div>
              <div className="bg-[rgba(255,222,204,0.2)] border border-primary rounded-xl p-3 flex flex-col gap-1">
                <div className="text-sm font-semibold text-heading tracking-normal leading-[1.2]">What to expect</div>
                <ul className="m-0 pl-[18px] flex flex-col gap-1">
                  <li className="text-[11px] font-normal text-body tracking-normal leading-[1.2]">Our advocate will contact you today or the next business day to discuss your claim and advise you of the next steps.</li>
                  <li className="text-[11px] font-normal text-body tracking-normal leading-[1.2]">You should write down as much information as possible so we can move as fast as we can.</li>
                </ul>
              </div>
            </div>
            <div className="px-6 py-5 flex flex-col gap-4">
              <div>
                <Label>Select a policy</Label>
                <CustomSelect
                  value={formPolicyId}
                  onChange={setFormPolicyId}
                  placeholder="e.g. Employment Practices Liability"
                  options={(policies ?? []).map((p) => ({
                    value: String(p.id),
                    label: `${getCoverageLabel(p.coverage_type)}${p.company_name ? ` — ${p.company_name}` : ''} (${p.policy_number})`,
                  }))}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div><Label>First name</Label><Input value={formFname} onChange={(e) => setFormFname(e.target.value)} placeholder="Jane" /></div>
                <div><Label>Last name</Label><Input value={formLname} onChange={(e) => setFormLname(e.target.value)} placeholder="Doe" /></div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div><Label>Email</Label><Input type="email" value={formEmail} onChange={(e) => setFormEmail(e.target.value)} placeholder="your@company.com" /></div>
                <div><Label>Phone</Label><Input type="tel" value={formPhone} onChange={(e) => setFormPhone(e.target.value)} placeholder="+1" /></div>
              </div>
              <div className="flex flex-col gap-2">
                <Label className="mb-0">Description of what happened</Label>
                <Textarea rows={4} value={formDesc} onChange={(e) => setFormDesc(e.target.value)} placeholder="Describe the incident, when it occurred, and any relevant details..." />
              </div>
              <div className="border border-dashed border-border rounded-xl py-12 flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors hover:border-border-accent" onClick={() => fileRef.current?.click()}>
                <input ref={fileRef} type="file" multiple className="hidden" onChange={(e) => setFiles(Array.from(e.target.files || []))} />
                <UploadIcon />
                <div className="text-[11px] font-semibold text-muted tracking-[-0.165px] leading-[1.2]">Upload any supporting documents</div>
                <div className="text-[11px] font-normal text-muted">Any pictures, evidence, or documents that you consider important</div>
                {files.length > 0 && <div className="text-[11px] font-bold text-primary">{files.map((f) => f.name).join(', ')}</div>}
              </div>
              <div className="flex gap-4">
                <Btn3DDark onClick={() => goTo('landing')}>
                  <CloseIcon size={16} color="currentColor" /> Cancel
                </Btn3DDark>
                <Btn3DOrange
                  fullWidth
                  className={!isFormReady || createClaimMutation.isPending ? 'opacity-50 pointer-events-none' : ''}
                  onClick={submit}
                >
                  {createClaimMutation.isPending ? 'Submitting...' : 'File your claim'}
                </Btn3DOrange>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* DONE */}
      {step === 'done' && doneClaim && (
        <div className="animate-enter w-[600px] relative">
          <div className="bg-surface border border-border rounded-2xl overflow-hidden relative z-[1]">
            <div className="px-6 py-5 border-b border-border flex flex-col gap-3">
              <div className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">
                Claim Submitted!
              </div>
              <div className="text-sm font-normal text-body">Your claim has been received. An advocate will reach out today or the next business day.</div>
            </div>
            <div className="px-6 py-5 flex flex-col gap-4">
              <div className="flex flex-col gap-1">
                <div className="px-1 text-[11px] font-semibold text-muted">CLAIM SUMMARY</div>
                <div className="border border-border rounded-lg overflow-hidden">
                  <div className="flex items-center justify-between">
                    <div className="p-3 text-sm font-normal text-body w-60 shrink-0">Claim number</div>
                    <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">{doneClaim.number}</div>
                  </div>
                  <div className="flex items-center justify-between border-t border-border">
                    <div className="p-3 text-sm font-normal text-body w-60 shrink-0">Policy</div>
                    <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">{doneClaim.policy}</div>
                  </div>
                  <div className="flex items-center justify-between border-t border-border">
                    <div className="p-3 text-sm font-normal text-body w-60 shrink-0">Status</div>
                    <div className="p-3"><Badge variant="submitted" /></div>
                  </div>
                  <div className="flex items-center justify-between border-t border-border">
                    <div className="p-3 text-sm font-normal text-body w-60 shrink-0">Date submitted</div>
                    <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">{doneClaim.date}</div>
                  </div>
                </div>
              </div>
              <div className="flex gap-4">
                <Btn3DWhite fullWidth onClick={() => showToast('Downloading claim PDF...')}>
                  <DownloadIcon /> Download PDF
                </Btn3DWhite>
                <Btn3DOrange fullWidth onClick={() => {
                  navigator.clipboard.writeText(doneClaim.number);
                  showToast('Claim number copied to clipboard');
                }}>
                  <CopyIcon size={16} /> Copy claim #
                </Btn3DOrange>
              </div>
            </div>
          </div>
          <div className="text-center mt-6 relative z-[1]">
            <button onClick={() => goTo('landing')} className="inline-flex items-center gap-1 text-xs font-medium text-muted py-1.5 px-3 pl-2 rounded-lg border-none bg-transparent cursor-pointer font-sans transition-all hover:bg-black/5 hover:text-heading focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none">
              <ChevronLeftIcon /> Back to claims
            </button>
          </div>
        </div>
      )}


    </div>
  );
}


