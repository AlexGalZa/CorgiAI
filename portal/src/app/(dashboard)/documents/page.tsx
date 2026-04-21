'use client';

import { useState } from 'react';
import { usePageTitle } from '@/hooks/use-page-title';
import { useDocuments, useDownloadDocument } from '@/hooks/use-documents';
import { useAppStore } from '@/stores/use-app-store';
import { Modal } from '@/components/ui/modal';
import { Badge } from '@/components/ui/badge';
import { Btn3DWhite, Btn3DOrange } from '@/components/ui/button';
import { DocumentsIcon, CloseIcon, DownloadIcon, ShareIcon, RefreshIcon } from '@/components/icons';
import { formatDateLong } from '@/lib/utils';
import type { APIDocument } from '@/types';

/* ─── Constants ─── */
const CATEGORY_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  policy:      { label: 'Policy',           color: 'var(--color-muted)', bg: 'var(--color-border)' },
  certificate: { label: 'Certificate',      color: 'var(--color-muted)', bg: 'var(--color-border)' },
  endorsement: { label: 'Endorsement',      color: 'var(--color-muted)', bg: 'var(--color-border)' },
  receipt:     { label: 'Receipt',          color: 'var(--color-muted)', bg: 'var(--color-border)' },
  loss_run:    { label: 'Loss Run Report',  color: 'var(--color-muted)', bg: 'var(--color-border)' },
  claim:       { label: 'Loss Run Report',  color: 'var(--color-muted)', bg: 'var(--color-border)' },
};

function getCategoryStyle(cat: string) {
  return CATEGORY_CONFIG[cat] ?? { label: cat, color: 'var(--color-muted)', bg: 'var(--color-border)' };
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/* ─── Stat Card ─── */
function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex-1 bg-surface border border-border rounded-2xl px-5 py-4 flex flex-col gap-1">
      <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] leading-[1.2]">{label}</div>
      <div className="text-xl font-medium text-heading tracking-[-0.5px] leading-none">{value}</div>
    </div>
  );
}

/* ─── Loading Skeleton ─── */
function TableSkeleton() {
  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-8 animate-pulse">
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-2">
          <div className="h-3 w-24 bg-border rounded" />
          <div className="h-8 w-48 bg-border rounded" />
        </div>
      </div>
      <div className="flex gap-4">
        <div className="flex-1 h-20 bg-border rounded-2xl" />
        <div className="flex-1 h-20 bg-border rounded-2xl" />
        <div className="flex-1 h-20 bg-border rounded-2xl" />
      </div>
      <div className="bg-surface border border-border rounded-2xl overflow-hidden">
        <div className="px-6 py-3 bg-bg border-b border-border flex gap-6">
          {[160, 100, 80, 100, 80, 50].map((w, i) => (
            <div key={i} className="h-3 bg-border rounded" style={{ width: w }} />
          ))}
        </div>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="px-6 py-4 border-b border-border flex gap-6 items-center">
            <div className="w-10 h-10 bg-border rounded-xl shrink-0" />
            <div className="flex-1 flex gap-6">
              {[160, 80, 80, 100, 60].map((w, j) => (
                <div key={j} className="h-4 bg-border rounded" style={{ width: w }} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Document Icon ─── */
function DocIcon({ category }: { category: string }) {
  const { color, bg } = getCategoryStyle(category);
  return (
    <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ backgroundColor: bg }}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
        <path d="M14 2v4a2 2 0 0 0 2 2h4" />
        <path d="M10 13H8" /><path d="M16 17H8" /><path d="M16 13h-2" />
      </svg>
    </div>
  );
}

/* ─── Main Page ─── */
export default function DocumentsPage() {
  usePageTitle('Documents');
  const { data: documents, isLoading, isError, refetch } = useDocuments();
  const downloadDoc = useDownloadDocument();
  const { showToast } = useAppStore();
  const [selectedDoc, setSelectedDoc] = useState<APIDocument | null>(null);
  const [previewDoc, setPreviewDoc] = useState<{ doc: APIDocument; url: string } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const handleDocClick = (doc: APIDocument) => {
    const ext = doc.original_filename?.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') {
      // Show inline preview for PDFs
      setPreviewLoading(true);
      downloadDoc.mutate(doc.id, {
        onSuccess: (result) => {
          setPreviewDoc({ doc, url: result.url });
          setPreviewLoading(false);
        },
        onError: (error) => {
          showToast(`Preview failed: ${error.message}`);
          setPreviewLoading(false);
          // Fall back to detail modal
          setSelectedDoc(doc);
        },
      });
    } else {
      // Non-PDF: show detail modal as before
      setSelectedDoc(doc);
    }
  };

  const handleDownload = (doc: APIDocument, e?: React.MouseEvent) => {
    e?.stopPropagation();
    downloadDoc.mutate(doc.id, {
      onSuccess: (result) => { window.open(result.url, '_blank'); },
      onError: (error) => { showToast(`Download failed: ${error.message}`); },
    });
  };

  const handleShare = (doc: APIDocument, e?: React.MouseEvent) => {
    e?.stopPropagation();
    navigator.clipboard.writeText(`${window.location.origin}/documents/${doc.id}`);
    showToast('Link copied to clipboard');
  };

  if (isLoading) return <TableSkeleton />;

  if (isError) {
    return (
      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-8">
        <div className="flex items-end justify-between">
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">Document center</span>
            <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">Your Documents</h1>
          </div>
        </div>
        <div className="flex flex-col items-center gap-4 pt-12">
          <div className="text-sm text-muted">Failed to load documents.</div>
          <button onClick={() => refetch()} className="inline-flex items-center gap-1.5 text-sm font-medium text-primary bg-transparent border border-primary rounded-xl px-4 py-2 cursor-pointer hover:bg-primary hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none">
            <RefreshIcon size={14} /> Retry
          </button>
        </div>
      </div>
    );
  }

  // Flatten all documents from categories
  const allDocs: APIDocument[] = [];
  if (documents && typeof documents === 'object') {
    for (const docs of Object.values(documents)) {
      if (Array.isArray(docs)) allDocs.push(...docs);
    }
  }
  allDocs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  const totalDocs = allDocs.length;
  const policyDocs = allDocs.filter(d => d.category === 'policy').length;
  const certDocs = allDocs.filter(d => d.category === 'certificate').length;

  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 md:px-12 py-6 md:py-10 flex flex-col gap-8">
      {/* Page header */}
      <div className="flex items-end justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-semibold text-muted tracking-normal leading-[1.2] uppercase">Document center</span>
          <h1 className="font-heading text-[26px] sm:text-[32px] font-medium text-heading tracking-[-1.024px] leading-none">Your Documents</h1>
        </div>
        {allDocs.length > 0 && (
          <Btn3DOrange onClick={async () => {
            if (allDocs.length === 0) return;

            showToast('Preparing download...');

            try {
              const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.corginsurance.com';
              const token = (await import('@/stores/use-auth-store')).useAuthStore.getState().tokens?.access_token;
              const orgId = (await import('@/stores/use-org-store')).useOrgStore.getState().activeOrgId;

              const headers: Record<string, string> = {};
              if (token) headers['Authorization'] = `Bearer ${token}`;
              if (orgId) headers['X-Organization-Id'] = String(orgId);

              const res = await fetch(`${API_BASE}/api/v1/users/documents/download-all`, { headers });

              if (!res.ok) {
                throw new Error(`Server returned ${res.status}`);
              }

              const contentType = res.headers.get('content-type') || '';

              if (contentType.includes('application/zip')) {
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'corgi-documents.zip';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
                showToast('Download started');
              } else {
                // JSON fallback — open individual URLs
                const data = await res.json();
                const files = data?.data?.files || [];
                for (const file of files) {
                  if (file.url) window.open(file.url, '_blank');
                }
                if (files.length === 0) {
                  showToast('No documents available for download');
                }
              }
            } catch (error) {
              showToast(`Download failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
            }
          }}>
            <DownloadIcon size={16} color="currentColor" /> Download Coverage Folder
          </Btn3DOrange>
        )}
      </div>

      {allDocs.length === 0 ? (
        /* Empty state */
        <div className="border border-dashed border-border rounded-2xl text-center py-16 px-10">
          <div className="mb-4 mx-auto w-12 h-12 flex items-center justify-center">
            <DocumentsIcon className="w-6 h-6 stroke-muted" />
          </div>
          <div className="text-sm font-medium text-heading mb-1">No documents yet</div>
          <div className="text-[13px] text-muted leading-[1.5] max-w-sm mx-auto">
            Documents will appear here as policies are issued, certificates generated, and claims processed.
          </div>
        </div>
      ) : (
        <>
          {/* Stats strip */}
          <div className="flex gap-4">
            <StatCard label="Total documents" value={String(totalDocs)} />
            <StatCard label="Policy documents" value={String(policyDocs)} />
            <StatCard label="Certificates" value={String(certDocs)} />
          </div>

          {/* Loss run info banner */}
          <div className="flex items-start gap-2.5 p-4 bg-primary/5 border border-primary/20 rounded-2xl">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 mt-0.5 text-primary">
              <circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" />
            </svg>
            <span className="text-sm text-heading leading-[1.5]">
              Claim-related documents are included in your <strong>Loss Run Reports</strong>. Download a loss run to see your full claims history.
            </span>
          </div>

          {/* Table */}
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            {/* Column headers */}
            <div className="hidden md:grid md:grid-cols-[minmax(200px,3fr)_120px_110px_110px_80px] px-6 py-3 bg-bg border-b border-border">
              <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px]">Document</div>
              <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px]">Type</div>
              <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px]">Date</div>
              <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px]">Size</div>
              <div className="text-[11px] font-semibold text-muted uppercase tracking-[0.3px] text-right">Actions</div>
            </div>

            {/* Table body */}
            {allDocs.map((doc) => {
              const catStyle = getCategoryStyle(doc.category);
              return (
                <div
                  key={doc.id}
                  onClick={() => handleDocClick(doc)}
                  className="grid grid-cols-[minmax(200px,3fr)_120px_110px_110px_80px] px-6 py-4 border-b border-border last:border-b-0 hover:bg-bg transition-colors cursor-pointer items-center"
                >
                  {/* Document */}
                  <div className="flex items-center gap-3 min-w-0">
                    <DocIcon category={doc.category} />
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-heading truncate">{doc.title}</div>
                      <div className="text-[11px] text-muted truncate">
                        {doc.original_filename}
                        {doc.policy_numbers.length > 0 && ` · ${doc.policy_numbers.join(', ')}`}
                      </div>
                    </div>
                  </div>

                  {/* Type */}
                  <div>
                    <span
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold"
                      style={{ backgroundColor: catStyle.bg, color: catStyle.color }}
                    >
                      {catStyle.label}
                    </span>
                  </div>

                  {/* Date */}
                  <div className="text-sm text-body">{formatDateLong(new Date(doc.created_at))}</div>

                  {/* Size */}
                  <div className="text-sm text-muted">{formatFileSize(doc.file_size)}</div>

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={(e) => handleDownload(doc, e)}
                      className="w-8 h-8 rounded-lg flex items-center justify-center bg-transparent border-none cursor-pointer text-muted hover:text-heading hover:bg-bg transition-colors"
                      title="Download"
                    >
                      <DownloadIcon size={15} />
                    </button>
                    <button
                      onClick={(e) => handleShare(doc, e)}
                      className="w-8 h-8 rounded-lg flex items-center justify-center bg-transparent border-none cursor-pointer text-muted hover:text-heading hover:bg-bg transition-colors"
                      title="Copy link"
                    >
                      <ShareIcon size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* PDF Preview Modal */}
      <Modal open={!!previewDoc || previewLoading} onClose={() => { setPreviewDoc(null); setPreviewLoading(false); }} width={800}>
        {previewLoading ? (
          <div className="flex items-center justify-center h-[500px]">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-muted">Loading preview…</span>
            </div>
          </div>
        ) : previewDoc && (
          <div className="flex flex-col">
            {/* Header */}
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <div className="flex flex-col gap-1 min-w-0">
                <div className="font-heading text-lg font-normal text-heading tracking-[-0.5px] leading-none truncate">
                  {previewDoc.doc.title}
                </div>
                <div className="text-[11px] text-muted">{previewDoc.doc.original_filename}</div>
              </div>
              <button
                onClick={() => { setPreviewDoc(null); setPreviewLoading(false); }}
                className="bg-transparent border-none cursor-pointer p-0 leading-none shrink-0 ml-4"
              >
                <CloseIcon size={20} color="var(--color-muted)" />
              </button>
            </div>

            {/* PDF iframe */}
            <div className="bg-heading">
              <iframe
                src={previewDoc.url}
                className="w-full border-none"
                style={{ height: '70vh', minHeight: '400px' }}
                title={`Preview: ${previewDoc.doc.title}`}
              />
            </div>

            {/* Actions */}
            <div className="px-6 py-4 border-t border-border flex gap-4">
              <Btn3DWhite fullWidth onClick={() => { setPreviewDoc(null); setPreviewLoading(false); setSelectedDoc(previewDoc.doc); }}>
                <DocumentsIcon className="w-4 h-4 stroke-current" /> View details
              </Btn3DWhite>
              <Btn3DOrange fullWidth onClick={() => handleDownload(previewDoc.doc)}>
                <DownloadIcon size={16} color="currentColor" /> Download PDF
              </Btn3DOrange>
            </div>
          </div>
        )}
      </Modal>

      {/* Document Detail Modal */}
      <Modal open={!!selectedDoc} onClose={() => setSelectedDoc(null)} width={480}>
        {selectedDoc && (() => {
          const catStyle = getCategoryStyle(selectedDoc.category);
          return (
            <div className="flex flex-col">
              {/* Preview area */}
              <div className="bg-bg border-b border-border flex items-center justify-center h-[200px] p-5 relative">
                <button onClick={() => setSelectedDoc(null)} className="absolute top-4 right-4 bg-transparent border-none cursor-pointer p-0 leading-none">
                  <CloseIcon size={20} color="var(--color-muted)" />
                </button>
                <div className="bg-surface border border-border rounded-xl shadow-[0_0_16px_rgba(25,25,25,0.1)] w-[120px] h-[160px] flex flex-col items-center justify-center gap-3 p-3">
                  <DocIcon category={selectedDoc.category} />
                  <div className="text-center">
                    <div className="text-[10px] font-medium text-heading leading-[1.2] truncate w-full">{selectedDoc.original_filename}</div>
                    <div className="text-[10px] text-muted leading-[1]">PDF · {formatFileSize(selectedDoc.file_size)}</div>
                  </div>
                </div>
              </div>

              {/* Title */}
              <div className="px-6 py-5 border-b border-border flex items-center justify-between">
                <div className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">{selectedDoc.title}</div>
                <span
                  className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold shrink-0"
                  style={{ backgroundColor: catStyle.bg, color: catStyle.color }}
                >
                  {catStyle.label}
                </span>
              </div>

              {/* Details table */}
              <div className="px-6 py-5 border-b border-border">
                <div className="border border-border rounded-lg overflow-hidden">
                  <div className="flex items-center justify-between">
                    <div className="p-3 text-sm font-normal text-body w-[180px]">Source</div>
                    <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] text-right">Corgi</div>
                  </div>
                  <div className="flex items-center justify-between border-t border-border">
                    <div className="p-3 text-sm font-normal text-body w-[180px]">Date</div>
                    <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] text-right">{formatDateLong(new Date(selectedDoc.created_at))}</div>
                  </div>
                  <div className="flex items-center justify-between border-t border-border">
                    <div className="p-3 text-sm font-normal text-body w-[180px]">Format</div>
                    <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] text-right uppercase">{selectedDoc.original_filename?.split('.').pop()?.toUpperCase() || 'PDF'}</div>
                  </div>
                  <div className="flex items-center justify-between border-t border-border">
                    <div className="p-3 text-sm font-normal text-body w-[180px]">Size</div>
                    <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] text-right">{formatFileSize(selectedDoc.file_size)}</div>
                  </div>
                  {selectedDoc.policy_numbers.length > 0 && (
                    <div className="flex items-center justify-between border-t border-border">
                      <div className="p-3 text-sm font-normal text-body w-[180px]">Policies</div>
                      <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] text-right">{selectedDoc.policy_numbers.join(', ')}</div>
                    </div>
                  )}
                  {selectedDoc.effective_date && (
                    <div className="flex items-center justify-between border-t border-border">
                      <div className="p-3 text-sm font-normal text-body w-[180px]">Effective</div>
                      <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] text-right">{selectedDoc.effective_date}</div>
                    </div>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="px-6 py-5 flex gap-4">
                <Btn3DWhite fullWidth onClick={() => handleShare(selectedDoc)}>
                  <ShareIcon size={16} /> Share link
                </Btn3DWhite>
                <Btn3DOrange fullWidth onClick={() => handleDownload(selectedDoc)}>
                  <DownloadIcon size={16} color="currentColor" /> Download PDF
                </Btn3DOrange>
              </div>
            </div>
          );
        })()}
      </Modal>
    </div>
  );
}
