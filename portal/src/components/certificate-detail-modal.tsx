'use client';

import { useState } from 'react';
import { Modal } from '@/components/ui/modal';
import { Badge } from '@/components/ui/badge';
import { Btn3DWhite, Btn3DOrange, BtnDangerConfirm } from '@/components/ui/button';
import { CloseIcon, DownloadIcon, ShareIcon } from '@/components/icons';
import { useRevokeCertificate, useDownloadCertificate } from '@/hooks/use-certificates';
import { useAppStore } from '@/stores/use-app-store';
import { formatDate } from '@/lib/utils';
import type { APICertificate } from '@/types';

const ENDORSEMENT_LABELS: Record<string, string> = {
  waiver_of_subrogation: 'Waiver of Subrogation',
  primary_and_non_contributory: 'Primary and Non-Contributory',
  job_service_location: 'Job/Service Location',
  job_service_you_provide: 'Job/Service You Provide',
  thirty_day_notice: '30 Day Notice of Cancellation',
  coverage_follower: 'Coverage Follower',
};

interface CertificateDetailModalProps {
  certificate: APICertificate | null;
  open: boolean;
  onClose: () => void;
}

export function CertificateDetailModal({ certificate, open, onClose }: CertificateDetailModalProps) {
  const { showToast } = useAppStore();
  const revokeMutation = useRevokeCertificate();
  const downloadMutation = useDownloadCertificate();
  const [confirmRevoke, setConfirmRevoke] = useState(false);

  if (!certificate) return null;

  const handleDownload = async () => {
    try {
      const data = await downloadMutation.mutateAsync(certificate.id);
      window.open(data.url, '_blank');
    } catch {
      showToast('Failed to download certificate');
    }
  };

  const handleShare = async () => {
    const url = `${window.location.origin}/certificates/${certificate.id}`;
    await navigator.clipboard.writeText(url);
    showToast('Link copied to clipboard');
  };

  const handleRevoke = async () => {
    try {
      await revokeMutation.mutateAsync(certificate.id);
      showToast('Certificate revoked');
      setConfirmRevoke(false);
      onClose();
    } catch {
      showToast('Failed to revoke certificate');
    }
  };

  const isActive = certificate.status === 'active';

  return (
    <Modal open={open} onClose={onClose} width={560}>
      <div className="px-6 py-5 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="font-heading text-xl font-normal text-heading tracking-[-0.64px] leading-none">
            {certificate.custom_coi_number}
          </div>
          <Badge variant={isActive ? 'active' : 'expired'}>
            {isActive ? undefined : 'Revoked'}
          </Badge>
        </div>
        <button
          className="bg-transparent border-none cursor-pointer p-1 text-muted hover:text-heading"
          onClick={onClose}
        >
          <CloseIcon size={16} />
        </button>
      </div>

      <div className="px-6 py-5 flex flex-col gap-5">
        {/* Holder info */}
        <div className="flex flex-col gap-2">
          <div className="text-[11px] font-semibold text-muted uppercase tracking-normal leading-[1.2]">
            Certificate Holder
          </div>
          <div className="border border-border rounded-lg overflow-hidden">
            <Row label="Name" value={certificate.holder_name} />
            {certificate.holder_second_line && (
              <Row label="Second line" value={certificate.holder_second_line} border />
            )}
            <Row label="Address" value={certificate.holder_full_address.replace(/\n/g, ', ')} border />
            {certificate.is_additional_insured && (
              <Row label="Designation" value="Additional Insured" border />
            )}
          </div>
        </div>

        {/* Policy info */}
        <div className="flex flex-col gap-2">
          <div className="text-[11px] font-semibold text-muted uppercase tracking-normal leading-[1.2]">
            Policy
          </div>
          <div className="border border-border rounded-lg overflow-hidden">
            <Row label="COI Number" value={certificate.coi_number} />
            <Row label="Certificate Number" value={certificate.custom_coi_number} border />
            <Row label="Generated" value={formatDate(new Date(certificate.created_at))} border />
            {certificate.revoked_at && (
              <Row label="Revoked" value={formatDate(new Date(certificate.revoked_at))} border />
            )}
          </div>
        </div>

        {/* Endorsements */}
        {certificate.endorsements.length > 0 && (
          <div className="flex flex-col gap-2">
            <div className="text-[11px] font-semibold text-muted uppercase tracking-normal leading-[1.2]">
              Endorsements
            </div>
            <div className="flex flex-wrap gap-1.5">
              {certificate.endorsements.map((e) => (
                <span
                  key={e}
                  className="inline-flex items-center bg-bg rounded-full px-2.5 py-1 text-[11px] font-medium text-body"
                >
                  {ENDORSEMENT_LABELS[e] ?? e}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Service location info */}
        {(certificate.service_location_job || certificate.service_location_address) && (
          <div className="flex flex-col gap-2">
            <div className="text-[11px] font-semibold text-muted uppercase tracking-normal leading-[1.2]">
              Service Location
            </div>
            <div className="border border-border rounded-lg overflow-hidden">
              {certificate.service_location_job && (
                <Row label="Job" value={certificate.service_location_job} />
              )}
              {certificate.service_location_address && (
                <Row label="Address" value={certificate.service_location_address} border={!!certificate.service_location_job} />
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <Btn3DWhite fullWidth onClick={handleDownload} disabled={downloadMutation.isPending}>
            <DownloadIcon /> {downloadMutation.isPending ? 'Loading…' : 'Download PDF'}
          </Btn3DWhite>
          <Btn3DOrange fullWidth onClick={handleShare}>
            <ShareIcon size={16} color="currentColor" /> Share link
          </Btn3DOrange>
        </div>

        {/* Revoke */}
        {isActive && (
          <div className="border-t border-border pt-4">
            {!confirmRevoke ? (
              <button
                className="text-[11px] font-medium text-danger bg-transparent border-none cursor-pointer font-sans hover:underline"
                onClick={() => setConfirmRevoke(true)}
              >
                Revoke this certificate
              </button>
            ) : (
              <div className="flex flex-col gap-3">
                <div className="text-sm text-body">
                  Are you sure? This certificate will be permanently marked as revoked and can no longer be used.
                </div>
                <div className="flex gap-3">
                  <Btn3DWhite fullWidth onClick={() => setConfirmRevoke(false)}>
                    Cancel
                  </Btn3DWhite>
                  <BtnDangerConfirm
                    className="w-full"
                    onClick={handleRevoke}
                    disabled={revokeMutation.isPending}
                  >
                    {revokeMutation.isPending ? 'Revoking…' : 'Yes, revoke'}
                  </BtnDangerConfirm>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}

function Row({ label, value, border }: { label: string; value: string; border?: boolean }) {
  return (
    <div className={`flex items-center justify-between ${border ? 'border-t border-border' : ''}`}>
      <div className="p-3 text-sm font-normal text-body w-48 shrink-0">{label}</div>
      <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px] text-right">{value}</div>
    </div>
  );
}
