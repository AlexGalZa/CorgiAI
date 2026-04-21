'use client';

import { useState } from 'react';
import Image from 'next/image';
import { Modal } from '@/components/ui/modal';
import { Badge } from '@/components/ui/badge';
import { Btn3DWhite, Btn3DOrange } from '@/components/ui/button';
import { CustomSelect } from '@/components/ui/custom-select';
import { DatePicker } from '@/components/ui/date-picker';
import { CloseIcon, InfoIcon, ShieldIcon } from '@/components/icons';
import { formatCurrency } from '@/lib/utils';
import type { APIPolicy } from '@/types';
import {
  getCoverageLabel,
  getCoverageImage,
  formatPolicyDate,
  getRemainingDays,
  LIMIT_OPTIONS,
  RETENTION_OPTIONS,
} from './constants';
import { CoverageLabel } from './CoverageTooltip';

export interface ModifyLimitsModalProps {
  policy: APIPolicy | null;
  open: boolean;
  onClose: () => void;
}

export function ModifyLimitsModal({
  policy,
  open,
  onClose,
}: ModifyLimitsModalProps) {
  const [occurrenceLimit, setOccurrenceLimit] = useState<number>(LIMIT_OPTIONS[0]);
  const [aggregateLimit, setAggregateLimit] = useState<number>(LIMIT_OPTIONS[0]);
  const [retentionValue, setRetentionValue] = useState<number>(RETENTION_OPTIONS[0]);
  const [endorsementDate, setEndorsementDate] = useState<string>('');
  const [step, setStep] = useState<'edit' | 'confirm'>('edit');
  const [confirmSignature, setConfirmSignature] = useState('');

  const aggregateError = aggregateLimit < occurrenceLimit;
  const filteredAggregateOptions = LIMIT_OPTIONS.filter((v) => v >= occurrenceLimit);

  if (!policy) return null;

  const coverageLabel = getCoverageLabel(policy.coverage_slug || policy.coverage_type);
  const coverageImage = getCoverageImage(policy.coverage_slug || policy.coverage_type);

  const today = new Date().toISOString().split('T')[0];

  // Premium delta calculations
  const currentPremium = policy.premium ?? 0;
  const oldAggregate = policy.aggregate_limit ?? 1;
  const ratio = oldAggregate > 0 ? aggregateLimit / oldAggregate : 1;
  const estimatedNewPremium = Math.round(currentPremium * ratio * 100) / 100;
  const premiumDifference = Math.round((estimatedNewPremium - currentPremium) * 100) / 100;
  const isIncrease = premiumDifference > 0;
  const isSavings = premiumDifference < 0;
  const remainingDays = getRemainingDays(policy.expiration_date);
  const proratedAmount = Math.round((remainingDays / 365) * Math.abs(premiumDifference) * 100) / 100;

  const handleClose = () => {
    setStep('edit');
    setConfirmSignature('');
    onClose();
  };

  const canConfirmFinal = confirmSignature.trim().length >= 2;

  // Confirm step
  if (step === 'confirm') {
    return (
      <Modal open={open} onClose={handleClose} width={520} titleId="confirm-payment-title">
        <div className="px-6 pt-6 flex flex-col gap-4">
          <div className="flex items-start justify-between">
            <div className="flex flex-col gap-2">
              <div id="confirm-payment-title" className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">
                Confirm payment
              </div>
              <div className="text-sm font-normal text-body leading-[1.2]">
                Review the details below and authorize the charge.
              </div>
            </div>
            <button
              onClick={handleClose}
              aria-label="Close"
              className="bg-transparent border-none cursor-pointer p-0 leading-none shrink-0"
            >
              <CloseIcon size={24} color="var(--color-heading)" />
            </button>
          </div>
        </div>

        <div className="p-5 px-6 flex flex-col gap-4">
          {/* Summary table */}
          <div className="bg-bg border border-border rounded-lg overflow-hidden">
            <div className="flex items-center justify-between border-b border-border">
              <div className="p-3 text-sm font-normal text-body">Current premium</div>
              <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">
                {formatCurrency(currentPremium)}/yr
              </div>
            </div>
            <div className="flex items-center justify-between border-b border-border">
              <div className="p-3 text-sm font-normal text-body">New premium</div>
              <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">
                {formatCurrency(estimatedNewPremium)}/yr
              </div>
            </div>
            <div className="flex items-center justify-between border-b border-border">
              <div className="p-3 text-sm font-normal text-body">Remaining policy period</div>
              <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">
                {remainingDays} days
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div className="p-3 text-sm font-semibold text-heading">
                {isIncrease ? 'Prorated amount due today' : 'Prorated credit'}
              </div>
              <div className={`p-3 text-sm font-bold tracking-[-0.21px] ${isIncrease ? 'text-primary' : 'text-success-dark'}`}>
                {isIncrease ? '' : '-'}{formatCurrency(proratedAmount)}
              </div>
            </div>
          </div>

          {/* Authorization text */}
          <div className="p-3 flex items-start gap-2 bg-primary/10 border border-primary/50 rounded-xl">
            <InfoIcon size={16} color="var(--color-primary)" />
            <span className="text-[11px] font-normal text-body leading-[1.4]">
              {isIncrease
                ? `You will be charged ${formatCurrency(proratedAmount)} for the remaining policy period. By confirming, you authorize this charge to your payment method on file.`
                : `A credit of ${formatCurrency(proratedAmount)} will be applied to your account for the remaining policy period. By confirming, you authorize this coverage adjustment.`}
            </span>
          </div>

          {/* Signature field */}
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-semibold text-heading leading-[1.2]">
              Type your full name to authorize
            </label>
            <input
              type="text"
              value={confirmSignature}
              onChange={(e) => setConfirmSignature(e.target.value)}
              placeholder="Full legal name"
              className="w-full bg-white border border-border rounded-lg px-3 py-2.5 text-sm text-heading font-sans placeholder:text-muted"
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-3">
            <Btn3DWhite fullWidth onClick={() => setStep('edit')}>
              Back
            </Btn3DWhite>
            <Btn3DOrange
              fullWidth
              onClick={handleClose}
              disabled={!canConfirmFinal}
              className={!canConfirmFinal ? 'opacity-40 pointer-events-none' : ''}
            >
              <ShieldIcon className="w-4 h-4 stroke-white shrink-0" />
              {isIncrease ? 'Confirm & Pay' : 'Confirm adjustment'}
            </Btn3DOrange>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal open={open} onClose={handleClose} width={600} titleId="modify-limits-title">
      {/* Header with corgi illustration */}
      <div className="bg-bg border-b border-border h-[240px] flex flex-col items-center justify-end overflow-hidden relative px-6">
        <button
          onClick={handleClose}
          aria-label="Close"
          className="absolute top-5 right-5 cursor-pointer w-6 h-6 flex items-center justify-center bg-transparent border-none p-0"
        >
          <CloseIcon size={20} color="var(--color-muted)" />
        </button>
        {coverageImage && (
          <Image
            src={coverageImage}
            alt={coverageLabel}
            width={552}
            height={200}
            className="w-full object-contain"
            priority
          />
        )}
      </div>

      {/* Policy info */}
      <div className="p-5 px-6 border-b border-border flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div id="modify-limits-title" className="font-heading text-2xl font-normal text-heading tracking-[-0.768px] leading-none">
            <CoverageLabel slug={policy.coverage_slug || policy.coverage_type} />
          </div>
          <Badge variant="active" />
        </div>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
          <div className="flex flex-col gap-1">
            <div className="text-[11px] font-semibold text-muted uppercase leading-[1.2]">Carrier</div>
            <div className="text-sm font-semibold text-heading leading-[1.2]">{policy.carrier}</div>
          </div>
          <div className="flex flex-col gap-1">
            <div className="text-[11px] font-semibold text-muted uppercase leading-[1.2]">Effective</div>
            <div className="text-sm font-semibold text-heading leading-[1.2]">
              {formatPolicyDate(policy.effective_date)} - {formatPolicyDate(policy.expiration_date)}
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <div className="text-[11px] font-semibold text-muted uppercase leading-[1.2]">Premium</div>
            <div className="text-sm font-semibold text-heading leading-[1.2]">
              {formatCurrency(policy.premium)}
              <span className="text-[11px] font-normal text-muted">/yr</span>
            </div>
          </div>
        </div>
      </div>

      {/* Editable limits */}
      <div className="p-5 px-6 flex flex-col gap-4">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-semibold text-heading leading-[1.2]">Each occurrence</label>
            <CustomSelect
              value={String(occurrenceLimit)}
              onChange={(val) => {
                const num = Number(val);
                setOccurrenceLimit(num);
                if (aggregateLimit < num) setAggregateLimit(num);
              }}
              options={LIMIT_OPTIONS.map((v) => ({ value: String(v), label: formatCurrency(v) }))}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-semibold text-heading leading-[1.2]">Aggregate</label>
            <CustomSelect
              value={String(aggregateLimit)}
              onChange={(val) => setAggregateLimit(Number(val))}
              options={filteredAggregateOptions.map((v) => ({ value: String(v), label: formatCurrency(v) }))}
              error={aggregateError}
            />
            {aggregateError && (
              <span className="text-xs font-medium text-danger leading-[1.2]">
                Aggregate must be ≥ per occurrence limit
              </span>
            )}
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-semibold text-heading leading-[1.2]">Retention</label>
            <CustomSelect
              value={String(retentionValue)}
              onChange={(val) => setRetentionValue(Number(val))}
              options={RETENTION_OPTIONS.map((v) => ({ value: String(v), label: formatCurrency(v) }))}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-semibold text-heading leading-[1.2]">
              Endorsement effective date
            </label>
            <DatePicker
              value={endorsementDate || today}
              onChange={setEndorsementDate}
              min={today}
            />
            <span className="text-[11px] font-normal text-muted leading-[1.2]">
              Endorsements cannot be backdated. The earliest effective date is today.
            </span>
          </div>
        </div>

        {/* Premium delta section */}
        {premiumDifference !== 0 && (
          <div className="flex flex-col gap-1">
            <div className="px-1 text-[11px] font-semibold text-muted uppercase leading-[1.2]">
              Premium impact
            </div>
            <div className="bg-bg border border-border rounded-lg overflow-hidden">
              <div className="flex items-center justify-between border-b border-border">
                <div className="p-3 text-sm font-normal text-body">Current premium</div>
                <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">
                  {formatCurrency(currentPremium)}/yr
                </div>
              </div>
              <div className="flex items-center justify-between border-b border-border">
                <div className="p-3 text-sm font-normal text-body">Estimated new premium</div>
                <div className="p-3 text-sm font-medium text-heading tracking-[-0.21px]">
                  {formatCurrency(estimatedNewPremium)}/yr
                </div>
              </div>
              <div className="flex items-center justify-between border-b border-border">
                <div className="p-3 text-sm font-normal text-body">Difference</div>
                <div className={`p-3 text-sm font-semibold tracking-[-0.21px] ${isIncrease ? 'text-primary' : 'text-success-dark'}`}>
                  {isIncrease ? '+' : '-'}{formatCurrency(Math.abs(premiumDifference))}/yr
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="p-3 text-sm font-semibold text-heading">
                  Prorated amount due today
                </div>
                <div className={`p-3 text-sm font-bold tracking-[-0.21px] ${isIncrease ? 'text-primary' : 'text-success-dark'}`}>
                  {isIncrease ? '' : '-'}{formatCurrency(proratedAmount)}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Warning box */}
        <div className="p-3 flex items-start gap-2 bg-primary/10 border border-primary/50 rounded-xl">
          <InfoIcon size={16} color="var(--color-primary)" />
          <span className="text-[11px] font-normal text-body leading-[1.2]">
            Changing your limits will generate a new quote. Your premium may adjust based on the
            selected coverage levels.
          </span>
        </div>

        {/* Buttons */}
        <div className="flex gap-3">
          <Btn3DWhite fullWidth onClick={handleClose}>
            Cancel
          </Btn3DWhite>
          <Btn3DOrange
            fullWidth
            onClick={() => setStep('confirm')}
            disabled={aggregateError}
            className={aggregateError ? 'opacity-40 pointer-events-none' : ''}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-white"
            >
              <path d="M20 6 9 17l-5-5" />
            </svg>
            {isIncrease ? 'Review & Pay' : 'Confirm adjustment'}
          </Btn3DOrange>
        </div>
      </div>
    </Modal>
  );
}
