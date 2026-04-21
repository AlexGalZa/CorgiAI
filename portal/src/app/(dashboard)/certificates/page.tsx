'use client';

import { useState, useCallback } from 'react';
import { usePageTitle } from '@/hooks/use-page-title';
import {
  useCertificateStore,
  useCertificates,
  useAvailableCOIs,
  useCreateCertificate,
  useDownloadCertificate,
  useConsolidatedCOI,
} from '@/hooks/use-certificates';
import { usePolicies, usePoliciesMap } from '@/hooks/use-policies';
import { useAppStore } from '@/stores/use-app-store';
import { CertificateDetailModal } from '@/components/certificate-detail-modal';
import { Badge } from '@/components/ui/badge';
import { Btn3DWhite, Btn3DOrange } from '@/components/ui/button';
import { Input, Label } from '@/components/ui/input';
import { CustomSelect } from '@/components/ui/custom-select';
import {
  PlusIcon, CheckIcon, ArrowRightIcon, ArrowLeftIcon,
  CloseIcon, DownloadIcon, ShareIcon, SearchIcon,
  CertificateIcon, HelpCircleIcon, InfoIcon,
  MoreHorizontalIcon, RefreshIcon,
} from '@/components/icons';
import { HelpTooltip } from '@/components/ui/help-tooltip';
import type { CertParty, CertStep, DesignationType, APICertificate } from '@/types';
import { US_STATES, formatDate, formatDateLong, getCoverageLabel } from '@/lib/utils';
import { trackEvent } from '@/lib/analytics';

const DESIG_OPTIONS: { val: DesignationType; title: string; desc: string }[] = [
  { val: 'ai', title: 'Additional Insured', desc: 'Named on and covered by the policy' },
  { val: 'lp', title: 'Loss Payee', desc: 'Receives payouts directly — lenders, lienholders' },
  { val: 'ch', title: 'Certificate Holder', desc: 'Receives and holds the certificate' },
];

/* ─── Reusable summary row ─── */
function SummaryRow({ label, value, border }: { label: string; value: string; border?: boolean }) {
  return (
    <div className={`flex items-center justify-between${border ? ' border-t border-border' : ''}`}>
      <div className="p-3 text-sm font-normal text-body tracking-normal leading-[1.2] w-60 shrink-0">{label}</div>
      <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] leading-[1.2] text-right">{value}</div>
    </div>
  );
}



/* ─── Loading skeleton ─── */
function TableSkeleton() {
  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-6 md:gap-8 animate-pulse">
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-2">
          <div className="h-3 w-32 bg-border rounded" />
          <div className="h-8 w-64 bg-border rounded" />
        </div>
        <div className="h-9 w-40 bg-border rounded-xl" />
      </div>
      <div className="flex gap-4">
        <div className="flex-1 h-20 bg-border rounded-2xl" />
        <div className="flex-1 h-20 bg-border rounded-2xl" />
      </div>
      <div className="bg-surface border border-border rounded-2xl overflow-hidden">
        <div className="px-6 py-3 bg-bg border-b border-border flex gap-6">
          {[120, 100, 120, 80, 80, 60].map((w, i) => (
            <div key={i} className="h-3 bg-border rounded" style={{ width: w }} />
          ))}
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="px-6 py-4 border-b border-border flex gap-6 items-center">
            <div className="w-10 h-10 bg-border rounded-xl shrink-0" />
            <div className="flex-1 flex gap-6">
              {[140, 90, 120, 70, 80].map((w, j) => (
                <div key={j} className="h-4 bg-border rounded" style={{ width: w }} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function getCertBadgeVariant(status: APICertificate['status']): 'active' | 'revoked' | 'expired' {
  if (status === 'active') return 'active';
  if (status === 'revoked') return 'revoked';
  return 'expired';
}

export default function CertificatesPage() {
  usePageTitle('Certificates');
  const store = useCertificateStore();
  const { data: policiesList } = usePolicies();
  const policies = usePoliciesMap();
  const hasPolicies = (policiesList ?? []).length > 0;
  const { showToast } = useAppStore();

  // API hooks
  const { data: certListData, isLoading: isLoadingCerts, isError: isCertsError, refetch } = useCertificates();
  const { data: availableCOIs } = useAvailableCOIs();
  const createCertMutation = useCreateCertificate();
  const downloadMutation = useDownloadCertificate();
  const consolidatedMutation = useConsolidatedCOI();

  const apiCertificates = certListData?.certificates ?? [];

  const [step, setStep] = useState<CertStep>('landing');
  const [searchQuery, setSearchQuery] = useState('');
  const [pendingPolicy, setPendingPolicy] = useState('');
  const [formName, setFormName] = useState('');
  const [formName2, setFormName2] = useState('');
  const [formStreet, setFormStreet] = useState('');
  const [formCity, setFormCity] = useState('');
  const [formState, setFormState] = useState('CA');
  const [formZip, setFormZip] = useState('');
  const [designations, setDesignations] = useState<DesignationType[]>(['ai']);
  const [addFormOpen, setAddFormOpen] = useState(false);
  const [editIndex, setEditIndex] = useState<number | null>(null);
  const [doneCert, setDoneCert] = useState<APICertificate | null>(null);

  // Detail modal state
  const [detailCert, setDetailCert] = useState<APICertificate | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const isFlow = ['step1', 'step2', 'step3'].includes(step);
  const isFlowOrDone = isFlow || step === 'done';

  // Suppress lint warning for availableCOIs (used for prefetch)
  void availableCOIs;

  const clearForm = useCallback(() => {
    setFormName(''); setFormName2(''); setFormStreet(''); setFormCity('');
    setFormState('CA'); setFormZip(''); setDesignations(['ai']); setEditIndex(null);
  }, []);

  const goTo = useCallback((s: CertStep) => {
    setStep(s);
    if (s === 'step2' && store.certParties.length === 0) setAddFormOpen(true);
    else setAddFormOpen(false);
    clearForm();
  }, [store.certParties.length, clearForm]);

  const step1Next = useCallback(() => {
    if (!pendingPolicy) return;
    if (store.certPolicy !== pendingPolicy) store.setCertParties([]);
    store.setCertPolicy(pendingPolicy);
    goTo('step2');
  }, [pendingPolicy, store, goTo]);

  const toggleDesig = useCallback((val: DesignationType) => {
    setDesignations((prev) => prev.includes(val) ? prev.filter((d) => d !== val) : [...prev, val]);
  }, []);

  const addParty = useCallback(() => {
    if (!formName.trim() || designations.length === 0) return;
    const party: CertParty = {
      name: formName.trim(), name2: formName2.trim(), street: formStreet.trim(),
      city: formCity.trim(), state: formState, zip: formZip.trim(), designations: [...designations],
    };
    if (editIndex !== null) store.updateParty(editIndex, party);
    else store.addParty(party);
    setAddFormOpen(false); clearForm();
  }, [formName, formName2, formStreet, formCity, formState, formZip, designations, editIndex, store, clearForm]);

  const editParty = useCallback((i: number) => {
    const p = store.certParties[i];
    if (!p) return;
    setEditIndex(i);
    setFormName(p.name); setFormName2(p.name2); setFormStreet(p.street);
    setFormCity(p.city); setFormState(p.state); setFormZip(p.zip);
    setDesignations([...p.designations]);
    setAddFormOpen(true);
  }, [store.certParties]);

  const generate = useCallback(async () => {
    const firstParty = store.certParties[0];
    if (!firstParty) return;

    try {
      const created = await createCertMutation.mutateAsync({
        coi_number: store.certPolicy,
        holder_name: firstParty.name,
        holder_second_line: firstParty.name2 || undefined,
        holder_street_address: firstParty.street,
        holder_suite: undefined,
        holder_city: firstParty.city,
        holder_state: firstParty.state,
        holder_zip: firstParty.zip,
        is_additional_insured: firstParty.designations.includes('ai'),
        endorsements: [],
      });
      setDoneCert(created);
      setStep('done');
    } catch {
      showToast('Failed to generate certificate. Please try again.');
    }
  }, [store, createCertMutation, showToast]);

  const handleDownload = useCallback(async (certId: number, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      const data = await downloadMutation.mutateAsync(certId);
      trackEvent('certificate_downloaded', { certificate_id: certId });
      window.open(data.url, '_blank');
    } catch {
      showToast('Failed to download certificate');
    }
  }, [downloadMutation, showToast]);

  const handleShare = useCallback(async (certId: number, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    const url = `${window.location.origin}/certificates/${certId}`;
    await navigator.clipboard.writeText(url);
    showToast('Link copied to clipboard');
  }, [showToast]);

  const handleDownloadConsolidated = useCallback(async () => {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/certificates/consolidated?format=pdf`,
        { credentials: 'include' },
      );
      if (!res.ok) throw new Error('PDF download failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'consolidated-coi.pdf';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      trackEvent('certificate_downloaded', { type: 'consolidated' });
      showToast('Consolidated COI downloaded');
    } catch {
      showToast('Failed to download consolidated certificate');
    }
  }, [showToast]);

  const openDetail = useCallback((cert: APICertificate) => {
    setDetailCert(cert);
    setDetailOpen(true);
  }, []);

  const pol = policies[store.certPolicy];
  const filteredPolicies = Object.entries(policies).filter(([key, p]) => {
    const q = searchQuery.toLowerCase();
    return !q || key.toLowerCase().includes(q) || p.coverage_type.toLowerCase().includes(q);
  });

  // Stats (removed — misleading for most users with 1-2 COIs)

  const stepIndex = { step1: 0, step2: 1, step3: 2, done: 3, landing: -1 }[step];
  const stepLabels = ['Policy', 'Parties', 'Review'];

  // Find policy info for a certificate (lookup by coi_number)
  const findPolicyForCert = (cert: APICertificate) => {
    return Object.values(policies).find(p => p.coi_number === cert.coi_number);
  };

  return (
    <div
      className={
        isFlowOrDone
          ? `flex flex-col items-center justify-center min-h-[calc(100vh-var(--spacing-header))] px-4 sm:px-6 md:px-12 gap-6${step === 'done' ? ' pt-[200px]' : ''} pb-20`
          : 'max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-6 md:gap-8'
      }
    >
      {/* Detail modal */}
      <CertificateDetailModal
        certificate={detailCert}
        open={detailOpen}
        onClose={() => { setDetailOpen(false); setDetailCert(null); }}
      />

      {/* ════════════════════════════════════════
           LANDING
         ════════════════════════════════════════ */}
      {step === 'landing' && (
        <>
          {isLoadingCerts ? (
            <TableSkeleton />
          ) : isCertsError ? (
            <div className="flex flex-col gap-8 animate-enter">
              <div className="flex items-end justify-between">
                <div className="flex flex-col gap-1">
                  <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">Certificates of insurance</span>
                  <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">
                    Prove You&apos;re Covered.
                  </h1>
                </div>
              </div>
              <div className="flex flex-col items-center gap-4 pt-12">
                <div className="text-sm text-muted">Failed to load certificates.</div>
                <button
                  onClick={() => refetch()}
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-primary bg-transparent border border-primary rounded-xl px-4 py-2 cursor-pointer hover:bg-primary hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
                >
                  <RefreshIcon size={14} /> Retry
                </button>
              </div>
            </div>
          ) : apiCertificates.length === 0 ? (
            /* Empty state */
            <div className="flex flex-col gap-8 animate-enter">
              <div className="flex items-end justify-between">
                <div className="flex flex-col gap-1">
                  <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">Certificates of insurance</span>
                  <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">
                    Prove You&apos;re Covered.
                  </h1>
                </div>
              </div>
              <div className="border border-dashed border-border rounded-2xl text-center py-16 px-10">
                <div className="mb-4 mx-auto w-12 h-12 flex items-center justify-center">
                  <CertificateIcon className="w-6 h-6 stroke-muted" />
                </div>
                <div className="text-sm font-medium text-heading mb-1">No certificates yet</div>
                <div className="text-[13px] text-muted leading-[1.5] max-w-sm mx-auto">
                  Generate a certificate to share proof of coverage with landlords, investors, or clients.
                </div>
              </div>
            </div>
          ) : (
            /* Populated table layout */
            <div className="flex flex-col gap-8 animate-enter">
              {/* Page header */}
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div className="flex flex-col gap-1">
                  <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">
                    Certificates of insurance
                  </span>
                  <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">
                    Prove You&apos;re Covered.
                  </h1>
                </div>
                <Btn3DOrange onClick={handleDownloadConsolidated} disabled={consolidatedMutation.isPending}>
                  <DownloadIcon size={16} color="currentColor" /> <span className="hidden sm:inline">{consolidatedMutation.isPending ? 'Loading…' : 'Download Current Certificate'}</span><span className="sm:hidden">{consolidatedMutation.isPending ? 'Loading…' : 'Download COI'}</span>
                </Btn3DOrange>
              </div>

              {/* Table */}
              <div className="bg-surface border border-border rounded-2xl overflow-hidden">
                {/* Column headers */}
                <div className="hidden md:grid md:grid-cols-[minmax(180px,2fr)_minmax(160px,1.5fr)_minmax(160px,1.5fr)_90px_100px_90px] px-6 py-3 bg-bg border-b border-border">
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px]">Certificate</div>
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px]">Policy</div>
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px]">Holder</div>
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px]">Status</div>
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px]">Issued</div>
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] text-right">Actions</div>
                </div>

                {/* Table body */}
                <div>
                  {[...apiCertificates].reverse().map((cert) => {
                    const certPolicy = findPolicyForCert(cert);
                    const location = [cert.holder_city, cert.holder_state].filter(Boolean).join(', ');
                    return (
                      <div
                        key={cert.id}
                        onClick={() => openDetail(cert)}
                        className="border-b border-border last:border-b-0 hover:bg-bg transition-colors cursor-pointer"
                      >
                        {/* Desktop row */}
                        <div className="hidden md:grid grid-cols-[minmax(180px,2fr)_minmax(160px,1.5fr)_minmax(160px,1.5fr)_90px_100px_90px] px-6 py-4 items-center">
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="w-10 h-10 bg-success-bg rounded-xl flex items-center justify-center shrink-0">
                              <CertificateIcon className="w-5 h-5 stroke-success" />
                            </div>
                            <div className="min-w-0">
                              <div className="text-sm font-semibold text-heading truncate">{cert.custom_coi_number}</div>
                              <div className="text-[11px] text-muted truncate">{certPolicy?.coverage_type ?? '—'}</div>
                            </div>
                          </div>
                          <div className="text-sm text-body truncate">{certPolicy?.policy_number ?? cert.coi_number}</div>
                          <div className="min-w-0">
                            <div className="text-sm text-heading truncate">{cert.holder_name}</div>
                            {location && <div className="text-[11px] text-muted truncate">{location}</div>}
                          </div>
                          <div>
                            <Badge variant={getCertBadgeVariant(cert.status)}>
                              {cert.status === 'active' ? 'Active' : cert.status === 'revoked' ? 'Revoked' : 'Expired'}
                            </Badge>
                          </div>
                          <div className="text-sm text-body">{formatDateLong(new Date(cert.created_at))}</div>
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={(e) => handleDownload(cert.id, e)} className="w-8 h-8 rounded-lg flex items-center justify-center bg-transparent border-none cursor-pointer text-muted hover:text-heading hover:bg-bg transition-colors" title="Download PDF"><DownloadIcon size={15} /></button>
                            <button onClick={(e) => handleShare(cert.id, e)} className="w-8 h-8 rounded-lg flex items-center justify-center bg-transparent border-none cursor-pointer text-muted hover:text-heading hover:bg-bg transition-colors" title="Share link"><ShareIcon size={15} /></button>
                            <button onClick={(e) => { e.stopPropagation(); openDetail(cert); }} className="w-8 h-8 rounded-lg flex items-center justify-center bg-transparent border-none cursor-pointer text-muted hover:text-heading hover:bg-bg transition-colors" title="More"><MoreHorizontalIcon size={15} /></button>
                          </div>
                        </div>
                        {/* Mobile card */}
                        <div className="md:hidden px-4 py-4 flex flex-col gap-3">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-success-bg rounded-xl flex items-center justify-center shrink-0">
                              <CertificateIcon className="w-5 h-5 stroke-success" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-semibold text-heading truncate">{cert.custom_coi_number}</div>
                              <div className="text-[11px] text-muted truncate">{cert.holder_name}</div>
                            </div>
                            <Badge variant={getCertBadgeVariant(cert.status)}>
                              {cert.status === 'active' ? 'Active' : cert.status === 'revoked' ? 'Revoked' : 'Expired'}
                            </Badge>
                          </div>
                          <div className="flex items-center justify-between text-[11px] text-muted">
                            <span>{certPolicy?.coverage_type ?? '—'}</span>
                            <span>{formatDateLong(new Date(cert.created_at))}</span>
                          </div>
                          <div className="flex items-center gap-1 -ml-1">
                            <button onClick={(e) => handleDownload(cert.id, e)} className="w-8 h-8 rounded-lg flex items-center justify-center bg-transparent border-none cursor-pointer text-muted hover:text-heading hover:bg-bg transition-colors" title="Download"><DownloadIcon size={15} /></button>
                            <button onClick={(e) => handleShare(cert.id, e)} className="w-8 h-8 rounded-lg flex items-center justify-center bg-transparent border-none cursor-pointer text-muted hover:text-heading hover:bg-bg transition-colors" title="Share"><ShareIcon size={15} /></button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* ════════════════════════════════════════
           STEPPER
         ════════════════════════════════════════ */}
      {isFlowOrDone && (
        <div className="w-full max-w-[600px] mx-auto relative z-[2]">
          <div className="flex items-center justify-center">
            <div className="flex items-center gap-2">
              {stepLabels.map((label, i) => {
                const isDone = step === 'done' || i < stepIndex;
                const isActive = i === stepIndex;
                return (
                  <span key={label} className="contents">
                    {i > 0 && (
                      <span
                        className={`w-12 h-0 border-t shrink-0 transition-[border-color] duration-200 ${
                          isDone ? 'border-primary' : 'border-border'
                        }`}
                      />
                    )}
                    <span
                      className={`flex items-center gap-2 text-sm cursor-default tracking-normal ${
                        isDone ? 'text-primary font-medium' : isActive ? 'text-primary font-medium' : 'text-muted font-normal'
                      }`}
                    >
                      <span
                        className={`w-6 h-6 rounded-full border flex items-center justify-center text-sm font-medium shrink-0 transition-all duration-200 ${
                          isDone
                            ? 'bg-primary border-primary text-white'
                            : isActive
                              ? 'bg-[rgba(255,222,204,0.5)] border-transparent text-primary'
                              : 'border-border text-muted'
                        }`}
                      >
                        {isDone ? <CheckIcon size={12} /> : String(i + 1)}
                      </span>
                      {label}
                    </span>
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════
           STEP 1: SELECT POLICY
         ════════════════════════════════════════ */}
      {step === 'step1' && (
        <div className="animate-enter w-full max-w-[600px]">
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">Select a Policy</div>
                <HelpTooltip text="Your certificate will match the coverage and limits of the selected policy." />
              </div>
            </div>
            {/* Search */}
            <div className="p-4">
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"><SearchIcon /></span>
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  type="text"
                  placeholder="Search policies…"
                  className="pl-[34px]"
                />
              </div>
            </div>
            {/* Policy list */}
            <div className="px-4 pb-4 flex flex-col gap-2">
              {filteredPolicies.map(([key, p]) => {
                const selected = pendingPolicy === key;
                return (
                  <div
                    key={key}
                    className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-[border-color,background] duration-200 ${
                      selected
                        ? 'border-primary bg-primary'
                        : 'border-border bg-surface hover:border-[var(--color-border-accent)] hover:bg-bg'
                    }`}
                    onClick={() => setPendingPolicy(key)}
                  >
                    {/* Radio */}
                    <div className={`w-5 h-5 rounded-full border flex items-center justify-center shrink-0 p-1 box-border transition-[border-color] duration-200 ${selected ? 'border-white' : 'border-border'}`}>
                      <div className={`w-full h-full rounded-full transition-colors duration-200 ${selected ? 'bg-surface' : 'bg-transparent'}`} />
                    </div>
                    {/* Policy info */}
                    <div className="flex-1 min-w-0 flex flex-col gap-3">
                      <div className="flex flex-col gap-1">
                        <div className={`text-sm font-semibold leading-[1.2] tracking-normal ${selected ? 'text-white' : 'text-heading'}`}>{getCoverageLabel(p.coverage_type)}</div>
                        <div className={`text-[11px] tracking-normal leading-[1.2] ${selected ? 'text-white' : 'text-muted'}`}>{key}</div>
                      </div>
                      <div className={`flex gap-3 text-xs tracking-[-0.18px] leading-[1.2] ${selected ? 'text-white' : 'text-body'}`}>
                        <span>{p.effective_date}</span>
                        <span>•</span>
                        <span>${(p.per_occurrence_limit ?? 0).toLocaleString()} / ${(p.aggregate_limit ?? 0).toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════
           STEP 2: CERTIFICATE PARTIES
         ════════════════════════════════════════ */}
      {step === 'step2' && (
        <div className="animate-enter w-full max-w-[600px]">
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            {/* Section 1: Header (title + policy banner + info) */}
            <div className="px-6 py-5 border-b border-border flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <div className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">Certificate Parties</div>
                <HelpTooltip text="Add each party that needs to be listed on this certificate. Parties can hold one or more designations." />
              </div>
              {/* Issuing policy banner */}
              <div
                onClick={() => goTo('step1')}
                className="cursor-pointer flex items-center justify-between bg-bg border border-border rounded-xl p-3 overflow-hidden"
              >
                <div className="flex flex-col gap-1 font-sans">
                  <div className="text-[11px] font-semibold text-muted uppercase tracking-normal leading-[1.2]">Issuing policy</div>
                  <div className="text-sm font-semibold text-heading tracking-normal leading-[1.2]">
                    {pol ? `${pol.policy_number} — ${getCoverageLabel(pol?.coverage_type ?? '')}` : '--'}
                  </div>
                </div>
                <span className="text-[11px] font-medium text-primary shrink-0 tracking-normal leading-[1.2] cursor-pointer">Change</span>
              </div>
              {/* Orange info box */}
              <div className="p-3 flex items-start gap-1 bg-[rgba(255,222,204,0.2)] border-[0.5px] border-primary rounded-xl">
                <InfoIcon size={12} />
                <span className="text-[11px] font-normal text-heading leading-[1.2]">
                  Most certificates are issued per person or entity. If multiple parties need coverage, create a separate certificate for each insured.
                </span>
              </div>
            </div>

            {/* Section 2: Content area (parties + form sub-card) */}
            <div className="px-6 py-5 flex flex-col gap-4">
              {/* Party cards */}
              {store.certParties.length > 0 && (
                <div className="flex flex-col gap-4">
                  {store.certParties.map((p, i) => {
                    if (editIndex === i && addFormOpen) return null;
                    const initial = (p.name || '?').charAt(0).toUpperCase();
                    const addrParts = [p.street, p.city, p.state, p.zip].filter(Boolean);
                    return (
                      <div
                        key={i}
                        className="animate-enter border border-border rounded-xl p-3 flex gap-2.5 items-center cursor-pointer"
                        onClick={() => editParty(i)}
                      >
                        <div className="self-stretch shrink-0 bg-bg border border-border rounded-full flex items-center justify-center aspect-square min-w-10">
                          <span className="text-base font-medium text-body tracking-[-0.24px]">{initial}</span>
                        </div>
                        <div className="flex-1 min-w-0 flex flex-col gap-3">
                          <div className="flex gap-2 items-center flex-wrap">
                            <div className="text-sm font-semibold text-heading tracking-normal leading-[1.2]">{p.name}</div>
                            {p.designations.map((d) => <Badge key={d} variant={d} />)}
                          </div>
                          {addrParts.length > 0 && (
                            <div className="text-[11px] font-normal text-body tracking-normal leading-[1.2]">
                              {addrParts.join(', ')}
                            </div>
                          )}
                        </div>
                        <button
                          className="text-[11px] font-medium text-body shrink-0 bg-transparent border-none cursor-pointer font-sans tracking-normal leading-[1.2] self-center hover:underline"
                          onClick={(e) => { e.stopPropagation(); store.removeParty(i); }}
                        >
                          Remove
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Add form sub-card */}
              {addFormOpen && (
                <div className="border border-border rounded-xl overflow-hidden">
                  {/* Cancel row */}
                  <div
                    className="p-4 border-b border-border flex items-center gap-1 cursor-pointer transition-colors duration-200 hover:bg-bg"
                    onClick={() => { setAddFormOpen(false); clearForm(); }}
                  >
                    <CloseIcon size={14} color="var(--color-body)" />
                    <span className="text-sm font-medium text-body tracking-normal leading-[1.2]">Cancel</span>
                  </div>

                  {/* Fields section */}
                  <div className="p-4 border-b border-border flex flex-col gap-4">
                    {/* Designation checkboxes */}
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-1">
                        <Label className="mb-0">Designation</Label>
                      </div>
                      <div className="flex flex-col gap-2">
                        {DESIG_OPTIONS.map(({ val, title, desc }) => {
                          const checked = designations.includes(val);
                          return (
                            <div
                              key={val}
                              className={`border rounded-xl p-2 cursor-pointer transition-[border-color,background] duration-200 select-none ${
                                checked ? 'border-primary bg-primary' : 'border-border hover:border-[var(--color-border-accent)] hover:bg-bg'
                              }`}
                              onClick={() => toggleDesig(val)}
                            >
                              <div className="flex items-start gap-2">
                                <div
                                  className={`w-5 h-5 rounded border shrink-0 flex items-center justify-center ${
                                    checked ? 'bg-primary border-primary' : 'bg-bg border-border'
                                  }`}
                                  style={checked ? { border: '1px solid var(--color-primary)' } : { border: '0.417px solid var(--color-border)' }}
                                >
                                  {checked && (
                                    <svg width="13.3" height="13.3" viewBox="0 0 20 20" fill="none" stroke="currentColor" className="text-white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                      <path d="M16.5 5 7.5 14l-4-4" />
                                    </svg>
                                  )}
                                </div>
                                <div>
                                  <div className={`text-sm font-medium leading-[1.2] tracking-normal ${checked ? 'text-white' : 'text-heading'}`}>{title}</div>
                                  <div className={`text-[11px] mt-0.5 leading-[1.2] tracking-normal ${checked ? 'text-white' : 'text-muted'}`}>{desc}</div>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Form fields */}
                    <div className="flex flex-col gap-4">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <Label>Name</Label>
                          <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="Organization or individual" />
                        </div>
                        <div>
                          <Label>Second line <span className="text-[11px] text-muted font-normal">(optional)</span></Label>
                          <Input value={formName2} onChange={(e) => setFormName2(e.target.value)} placeholder="DBA, c/o, attn:" />
                        </div>
                      </div>
                      <div>
                        <Label>Street address</Label>
                        <Input value={formStreet} onChange={(e) => setFormStreet(e.target.value)} placeholder="123 Main St" />
                      </div>
                      <div className="grid grid-cols-[1fr_96px_96px] gap-2">
                        <div>
                          <Label>City</Label>
                          <Input value={formCity} onChange={(e) => setFormCity(e.target.value)} placeholder="San Francisco" />
                        </div>
                        <div>
                          <Label>State</Label>
                          <CustomSelect value={formState} onChange={setFormState} placeholder="Select state" options={US_STATES.map((s) => ({ value: s, label: s || '—' }))} />
                        </div>
                        <div>
                          <Label>Zip</Label>
                          <Input value={formZip} onChange={(e) => setFormZip(e.target.value)} placeholder="123456" />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Add party button */}
                  <div className="p-4 flex flex-col items-center">
                    <Btn3DWhite fullWidth onClick={addParty}>
                      <PlusIcon size={16} /> Add party
                    </Btn3DWhite>
                  </div>
                </div>
              )}

              {/* Add party trigger (visible when form hidden) */}
              {!addFormOpen && (
                <Btn3DWhite fullWidth onClick={() => { clearForm(); setAddFormOpen(true); }}>
                  <PlusIcon size={14} color="var(--color-heading)" /> Add a party
                </Btn3DWhite>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════
           STEP 3: REVIEW & GENERATE
         ════════════════════════════════════════ */}
      {step === 'step3' && (
        <div className="animate-enter w-full max-w-[600px]">
          <div className="flex flex-col gap-4">
            {/* Title + subtitle */}
            <div className="flex flex-col gap-2 px-4">
              <div className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">Review &amp; Generate</div>
              <div className="text-sm font-normal text-body tracking-normal leading-[1.2]">Everything look right? You can always create another certificate if needed.</div>
            </div>

            {/* Policy card */}
            <div className="bg-surface border border-border rounded-2xl overflow-hidden">
              <div className="px-6 py-5">
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between px-1">
                    <div className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2]">POLICY</div>
                    <button className="text-[11px] font-medium text-primary bg-transparent border-none cursor-pointer font-sans tracking-normal hover:underline" onClick={() => goTo('step1')}>Edit</button>
                  </div>
                  <div className="border border-border rounded-lg overflow-hidden">
                    <SummaryRow label="Policy number" value={pol?.policy_number ?? '--'} />
                    <SummaryRow label="Coverage type" value={getCoverageLabel(pol?.coverage_type ?? '')} border />
                    <SummaryRow label="Effective period" value={pol?.effective_date ?? '--'} border />
                  </div>
                </div>
              </div>
            </div>

            {/* Parties card */}
            <div className="bg-surface border border-border rounded-2xl overflow-hidden">
              <div className="px-6 py-5">
                <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-between px-1">
                    <div className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2]">PARTIES ON THIS CERTIFICATE</div>
                    <button className="text-[11px] font-medium text-primary bg-transparent border-none cursor-pointer font-sans tracking-normal hover:underline" onClick={() => goTo('step2')}>Edit</button>
                  </div>
                  <div className="flex flex-col gap-4">
                    {store.certParties.map((p, i) => {
                      const initial = (p.name || '?').charAt(0).toUpperCase();
                      const addrParts = [p.street, p.city, p.state, p.zip].filter(Boolean);
                      return (
                        <div key={i} className="border border-border rounded-xl p-3 flex gap-2.5 items-center">
                          <div className="self-stretch shrink-0 bg-bg border border-border rounded-full flex items-center justify-center aspect-square min-w-10">
                            <span className="text-base font-medium text-body tracking-[-0.24px]">{initial}</span>
                          </div>
                          <div className="flex-1 min-w-0 flex flex-col gap-3">
                            <div className="flex gap-2 items-center flex-wrap">
                              <div className="text-sm font-semibold text-heading tracking-normal leading-[1.2]">{p.name}</div>
                              {p.designations.map((d) => <Badge key={d} variant={d} />)}
                            </div>
                            {addrParts.length > 0 && (
                              <div className="text-[11px] font-normal text-body tracking-normal leading-[1.2]">
                                {addrParts.join(', ')}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════
           DONE
         ════════════════════════════════════════ */}
      {step === 'done' && doneCert && (
        <div className="animate-enter w-full max-w-[600px] relative">
          <div className="bg-surface border border-border rounded-2xl overflow-hidden relative z-[1]">
            {/* Header */}
            <div className="px-6 py-5 border-b border-border flex flex-col gap-3">
              <div className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">
                Certificate Generated!
              </div>
              <div className="text-sm font-normal text-body tracking-normal leading-[1.2]">
                {doneCert.custom_coi_number} is ready. Download or share it with the parties listed.
              </div>
            </div>
            {/* Certificate summary + buttons */}
            <div className="px-6 py-5 flex flex-col gap-4">
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between px-1">
                  <div className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2]">CERTIFICATE SUMMARY</div>
                  <span className="inline-flex items-center gap-1 bg-success-bg rounded-full py-1 px-2 pl-1.5 leading-none">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-success-dark"><circle cx="12" cy="12" r="10" /><path d="m9 12 2 2 4-4" /></svg>
                    <span className="text-[10px] font-medium text-success-dark tracking-normal whitespace-nowrap">Active</span>
                  </span>
                </div>
                <div className="border border-border rounded-lg overflow-hidden">
                  <SummaryRow label="Certificate number" value={doneCert.custom_coi_number} />
                  <SummaryRow label="Holder" value={doneCert.holder_name} border />
                  <SummaryRow label="Issued" value={formatDate(new Date(doneCert.created_at))} border />
                </div>
              </div>
              {/* Action buttons */}
              <div className="flex gap-4">
                <Btn3DWhite fullWidth onClick={() => handleDownload(doneCert.id)}>
                  <DownloadIcon /> Download PDF
                </Btn3DWhite>
                <Btn3DOrange fullWidth onClick={() => handleShare(doneCert.id)}>
                  <ShareIcon size={16} color="currentColor" /> Share link
                </Btn3DOrange>
              </div>
            </div>
          </div>
          {/* Back to certificates */}
          <div className="text-center mt-6 relative z-[1]">
            <button
              className="text-[11px] font-medium text-body bg-transparent border-none cursor-pointer font-sans tracking-normal hover:underline"
              onClick={() => goTo('landing')}
            >
              Back to certificates
            </button>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════
           FLOW FOOTER (Back + Next)
         ════════════════════════════════════════ */}
      {isFlow && (
        <div className="w-full max-w-[600px] mx-auto">
          <div className="flex items-center justify-between">
            {/* Back button */}
            <button
              className="bg-btn-dark-bg rounded-xl pb-1 cursor-pointer border-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
              onClick={() => {
                if (step === 'step1') goTo('landing');
                else if (step === 'step2') goTo('step1');
                else if (step === 'step3') goTo('step2');
              }}
            >
              <div className="flex items-center gap-1 bg-btn-dark text-white rounded-xl px-4 py-2 text-sm font-medium font-sans tracking-[-0.24px] whitespace-nowrap hover:opacity-88">
                <ArrowLeftIcon /> Back
              </div>
            </button>
            {/* Next button */}
            <button
              className="bg-primary-dark rounded-xl pb-1 cursor-pointer border-none disabled:opacity-40 disabled:cursor-default focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
              disabled={
                (step === 'step1' && !pendingPolicy) ||
                (step === 'step2' && store.certParties.length === 0) ||
                (step === 'step3' && createCertMutation.isPending)
              }
              onClick={() => {
                if (step === 'step1') step1Next();
                else if (step === 'step2' && store.certParties.length > 0) goTo('step3');
                else if (step === 'step3') generate();
              }}
            >
              <div className="flex items-center gap-1 bg-primary text-white rounded-xl px-4 py-2 text-sm font-medium font-sans tracking-[-0.24px] whitespace-nowrap hover:opacity-88">
                {step === 'step3'
                  ? (createCertMutation.isPending ? 'Generating…' : 'Generate certificate')
                  : step === 'step2'
                    ? 'Review certificate'
                    : 'Next'}
                <ArrowRightIcon />
              </div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
